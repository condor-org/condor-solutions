import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { axiosAuth } from "../utils/axiosAuth";
import { onNotificationsRefresh } from "../utils/notificationsBus";

/**
 * Lee /notificaciones/unread_count/ de forma resiliente.
 * - pollMs: polling (default 60s)
 * - refresh on window focus/visibility
 * - escucha evento global "notifications:refresh" para sincronizar UI
 */
export function useUnreadCount(accessToken, { pollMs = 60000 } = {}) {
  const api = useMemo(() => (accessToken ? axiosAuth(accessToken) : null), [accessToken]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(Boolean(api));
  const mounted = useRef(false);

  const load = useCallback(async () => {
    if (!api) return;
    let cancelled = false;
    try {
      setLoading(true);
      const res = await api.get("notificaciones/unread_count/");
      if (!mounted.current || cancelled) return;
      setCount(res.data?.unread_count ?? 0);
    } catch (err) {
      if (!mounted.current) return;
      // Evitamos ruido de 401 cuando expira el token
      if (err?.response?.status !== 401) {
        console.error("[useUnreadCount] failed", err);
      }
    } finally {
      if (mounted.current) setLoading(false);
    }
    return () => { cancelled = true; };
  }, [api]);

  useEffect(() => {
    mounted.current = true;

    // si no hay token, reseteamos a estado base
    if (!api) {
      setCount(0);
      setLoading(false);
      return () => { mounted.current = false; };
    }

    // carga inicial
    load();

    const onFocus = () => {
      // sólo refrescar si el tab está visible
      if (document.visibilityState === "visible") load();
    };
    window.addEventListener("focus", onFocus);
    window.addEventListener("visibilitychange", onFocus);

    // sync con otras vistas (mark-all / toggle)
    const offBus = onNotificationsRefresh(load);

    // polling opcional
    let id = null;
    if (pollMs) id = setInterval(load, pollMs);

    return () => {
      mounted.current = false;
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("visibilitychange", onFocus);
      if (id) clearInterval(id);
      offBus && offBus();
    };
  }, [api, load, pollMs]);

  return { count, loading, reload: load };
}
