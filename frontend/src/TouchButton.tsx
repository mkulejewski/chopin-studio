import { useRef, type ButtonHTMLAttributes, type MouseEvent } from "react";

/** Activate on touch pointer-up, including browsers suppressing clicks after pinch.
 * Suppress the following compatibility click so a tap can never activate twice.
 * Native mouse, keyboard, form validation and disabled semantics are retained.
 */
export function TouchButton({
  onClick,
  onPointerDown,
  onPointerUp,
  onPointerCancel,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  const touch = useRef<{ x: number; y: number } | null>(null);
  const lastTouch = useRef(-Infinity);
  return (
    <button
      {...props}
      onPointerDown={(e) => {
        onPointerDown?.(e);
        if (e.pointerType === "touch")
          touch.current = { x: e.clientX, y: e.clientY };
      }}
      onPointerCancel={(e) => {
        touch.current = null;
        onPointerCancel?.(e);
      }}
      onPointerUp={(e) => {
        onPointerUp?.(e);
        if (e.pointerType !== "touch") return;
        lastTouch.current = performance.now();
        const start = touch.current;
        touch.current = null;
        if (
          !start ||
          props.disabled ||
          Math.hypot(e.clientX - start.x, e.clientY - start.y) > 16
        )
          return;
        if (onClick) onClick(e as unknown as MouseEvent<HTMLButtonElement>);
        else if (
          e.currentTarget.form &&
          (props.type === undefined || props.type === "submit")
        )
          e.currentTarget.form.requestSubmit(e.currentTarget);
      }}
      onClick={(e) => {
        if (performance.now() - lastTouch.current < 700 && e.detail !== 0) {
          e.preventDefault();
          return;
        }
        onClick?.(e);
      }}
    />
  );
}
