import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { axiosAuth } from "../utils/axiosAuth";
import { onNotificationsRefresh } from "../utils/notificationsBus";

/**
 * Lee /notificaciones/unread_count/ de forma resiliente.
 * - pollMs: polling (default 60s)
 * - refresh on window focus
 * - escucha evento global "notifications:refresh" para sincronizar UI
 */
export function useUnreadCount(accessToken, { pollMs = 60000 } = {}) {
  const api = useMemo(() => (accessToken ? axiosAuth(accessToken) : null), [accessToken]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const mounted = useRef(false);

  const load = useCallback(async () => {
    if (!api) return;
    try {
      setLoading(true);
      const res = await api.get("notificaciones/unread_count/");
      setCount(res.data?.unread_count ?? 0);
    } catch (err) {
      console.error("[useUnreadCount] failed", err);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    if (!api) return;
    load();
    mounted.current = true;

    const onFocus = () => load();
    window.addEventListener("visibilitychange", onFocus);

    const offBus = onNotificationsRefresh(load); // sync con otras vistas

    let id;
    if (pollMs) id = setInterval(load, pollMs);

    return () => {
      window.removeEventListener("visibilitychange", onFocus);
      if (id) clearInterval(id);
      offBus && offBus();
    };
  }, [api, load, pollMs]);

  return { count, loading, reload: load };
}
