const EVT = "notifications:refresh";

/** Emitir un refresh global (lo usa la card, la campanita, etc.) */
export function emitNotificationsRefresh() {
  window.dispatchEvent(new CustomEvent(EVT));
}

/** Escuchar refresh global; devuelve un "off" para desuscribirse */
export function onNotificationsRefresh(handler) {
  const fn = () => handler?.();
  window.addEventListener(EVT, fn);
  return () => window.removeEventListener(EVT, fn);
}
