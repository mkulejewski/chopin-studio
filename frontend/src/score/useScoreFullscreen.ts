import { useEffect, useRef, useState, type RefObject } from "react";

export function useScoreFullscreen(
  shell: RefObject<HTMLDivElement | null>,
  fullscreenTarget: RefObject<HTMLDivElement | null> | undefined,
  onFullscreenHost: ((element: HTMLElement | null) => void) | undefined,
  onError: (error: unknown) => void,
) {
  const [scoreFull, setScoreFull] = useState(false);
  // Keep the subscription stable across Learning's status polls. The current
  // callback lives in a ref; re-renders must not detach a fullscreen listener
  // while the browser is dispatching the fullscreen change to the app.
  const fullscreenCallback = useRef(onFullscreenHost);
  fullscreenCallback.current = onFullscreenHost;
  const syncFullscreen = () => {
    const host = fullscreenTarget?.current || shell.current;
    const active = !!host && document.fullscreenElement === host;
    setScoreFull(active);
    fullscreenCallback.current?.(active ? host : null);
  };
  useEffect(() => {
    const changed = () => syncFullscreen();
    changed();
    document.addEventListener("fullscreenchange", changed);
    return () => {
      document.removeEventListener("fullscreenchange", changed);
      fullscreenCallback.current?.(null);
    };
  }, [fullscreenTarget]);
  const scoreFullscreen = () => {
    const host = fullscreenTarget?.current || shell.current;
    if (!host) return;
    // Read the DOM instead of trusting a potentially delayed React update.
    const action =
      document.fullscreenElement === host
        ? document.exitFullscreen()
        : host.requestFullscreen();
    void action.then(syncFullscreen).catch(onError);
  };
  return { scoreFull, scoreFullscreen };
}
