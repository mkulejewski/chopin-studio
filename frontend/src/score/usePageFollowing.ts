import {
  useEffect,
  type Dispatch,
  type RefObject,
  type SetStateAction,
} from "react";
import type { PageCommand } from "../appTypes";

type Options = {
  doc: unknown;
  calibrating: boolean;
  automaticCommand: PageCommand | null;
  piece: { id: string } | null;
  lastManualTurn: RefObject<number>;
  start: number;
  end: number;
  page: number;
  two: boolean;
  setPage: Dispatch<SetStateAction<number>>;
  setPan: Dispatch<SetStateAction<{ x: number; y: number }>>;
};

export function usePageFollowing({
  doc,
  calibrating,
  automaticCommand,
  piece,
  lastManualTurn,
  start,
  end,
  page,
  two,
  setPage,
  setPan,
}: Options) {
  useEffect(() => {
    if (
      !doc ||
      calibrating ||
      automaticCommand?.action !== "go" ||
      automaticCommand.piece_id !== piece?.id ||
      !automaticCommand.page
    )
      return;
    const target = automaticCommand.page;
    let timer: ReturnType<typeof setTimeout>;
    const apply = () => {
      const remaining = 10000 - (Date.now() - lastManualTurn.current);
      if (remaining > 0) {
        timer = setTimeout(apply, remaining);
        return;
      }
      setPage(Math.max(start, Math.min(end, target)));
      setPan({ x: 0, y: 0 });
    };
    apply();
    return () => clearTimeout(timer);
  }, [
    automaticCommand?.id,
    piece?.id,
    doc,
    two,
    start,
    end,
    page,
    calibrating,
  ]);
}
