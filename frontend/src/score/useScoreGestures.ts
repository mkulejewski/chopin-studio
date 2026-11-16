import {
  useRef,
  type Dispatch,
  type PointerEvent,
  type SetStateAction,
} from "react";
import type { Settings } from "../api";

type Point = { x: number; y: number };
type Options = {
  enabled: boolean;
  zoom: number;
  pan: Point;
  settings: Settings;
  setZoom: Dispatch<SetStateAction<number>>;
  setPan: Dispatch<SetStateAction<Point>>;
  turn: (direction: number) => void;
  onToggle: () => void;
};

export function useScoreGestures({
  enabled,
  zoom,
  pan,
  settings,
  setZoom,
  setPan,
  turn,
  onToggle,
}: Options) {
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const gesture = useRef({
    x: 0,
    y: 0,
    at: 0,
    distance: 0,
    zoom: 1,
    pan: { x: 0, y: 0 },
    multi: false,
  });
  const lastTap = useRef(0);
  const down = (e: PointerEvent) => {
    if (!enabled) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.current.size === 1)
      gesture.current = {
        x: e.clientX,
        y: e.clientY,
        at: Date.now(),
        distance: 0,
        zoom,
        pan,
        multi: false,
      };
    if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()];
      gesture.current.distance = Math.hypot(a.x - b.x, a.y - b.y);
      gesture.current.zoom = zoom;
      gesture.current.multi = true;
    }
  };
  const move = (e: PointerEvent) => {
    if (!pointers.current.has(e.pointerId)) return;
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.current.size === 2 && settings.pinch) {
      const [a, b] = [...pointers.current.values()];
      setZoom(
        Math.max(
          0.5,
          Math.min(
            4,
            (gesture.current.zoom * Math.hypot(a.x - b.x, a.y - b.y)) /
              Math.max(gesture.current.distance, 1),
          ),
        ),
      );
    } else if (
      pointers.current.size === 1 &&
      zoom > 1.05 &&
      !gesture.current.multi
    )
      setPan({
        x: gesture.current.pan.x + e.clientX - gesture.current.x,
        y: gesture.current.pan.y + e.clientY - gesture.current.y,
      });
  };
  const up = (e: PointerEvent) => {
    const g = gesture.current;
    const dx = e.clientX - g.x,
      dy = e.clientY - g.y;
    pointers.current.delete(e.pointerId);
    if (g.multi) return;
    if (
      zoom <= 1.05 &&
      settings.swipe &&
      Math.abs(dx) > 75 &&
      Math.abs(dx) > Math.abs(dy) * 1.8 &&
      Date.now() - g.at < 900
    )
      turn(dx < 0 ? 1 : -1);
    else if (Math.hypot(dx, dy) < 14) {
      if (Date.now() - lastTap.current < 320 && settings.double_tap) {
        setZoom((z) => (z > 1.05 ? 1 : 1.5));
        setPan({ x: 0, y: 0 });
        lastTap.current = 0;
      } else {
        lastTap.current = Date.now();
        if (settings.tap_overlay) onToggle();
      }
    }
  };
  const cancel = (e: PointerEvent) => {
    pointers.current.delete(e.pointerId);
    gesture.current.multi = true;
  };
  return { down, move, up, cancel };
}
