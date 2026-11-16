import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";
import { api } from "../api";
import type { Status } from "../appTypes";

type Service = "running" | "stopping" | "stopped";

export function useAppStatus(
  service: Service,
  setService: Dispatch<SetStateAction<Service>>,
  setError: Dispatch<SetStateAction<string>>,
  onRecordingSaved: () => Promise<void>,
  onError: (error: unknown) => void,
) {
  const [status, setStatus] = useState<Status | null>(null);
  const callbacks = useRef({ onRecordingSaved, onError });
  callbacks.current = { onRecordingSaved, onError };
  useEffect(() => {
    if (service !== "running") return;
    let live = true;
    let previousRecording: string | null = null;
    const poll = async () => {
      try {
        const s = await api<Status>("/status", {
          headers: { "X-Chopin-Frontend": "1" },
        });
        if (live) {
          if (previousRecording && previousRecording !== s.active)
            void callbacks.current
              .onRecordingSaved()
              .catch(callbacks.current.onError);
          previousRecording = s.active;
          setStatus(s);
          if (s.shutting_down) setService("stopping");
          setError((e) =>
            e ===
            "Local service unavailable. Recording may still be running; reconnect before starting another session."
              ? ""
              : e,
          );
        }
      } catch {
        if (live)
          setError(
            "Local service unavailable. Recording may still be running; reconnect before starting another session.",
          );
      }
    };
    void poll();
    const id = setInterval(poll, 700);
    return () => {
      live = false;
      clearInterval(id);
    };
  }, [service]);
  return { status, setStatus };
}
