import { useEffect, useState } from "react";
import { api, json } from "./api";

import { LearningWorkspace } from "./learning/LearningWorkspace";
import type { LearningProps, LessonChoice } from "./learning/types";

export function Learning(props: LearningProps) {
  const [choices, setChoices] = useState<LessonChoice[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [switching, setSwitching] = useState(false);
  const remember = (pieceId: string) => {
    try {
      localStorage.setItem("chopin-learning-piece", pieceId);
    } catch {
      /* Server also remembers the choice. */
    }
    props.onPieceChange(pieceId);
    setSelected(pieceId);
  };
  useEffect(() => {
    let live = true;
    void api<{ selected_piece: string; pieces: LessonChoice[] }>("/learning")
      .then((value) => {
        if (live) {
          setChoices(value.pieces);
          remember(value.selected_piece);
        }
      })
      .catch(props.onError);
    return () => {
      live = false;
    };
  }, []);
  async function select(pieceId: string) {
    if (switching || pieceId === selected) return;
    setSwitching(true);
    try {
      const value = await api<{ selected_piece: string }>(
        "/learning/selection",
        json("POST", { piece_id: pieceId }),
      );
      remember(value.selected_piece);
    } catch (error) {
      props.onError(error);
    } finally {
      setSwitching(false);
    }
  }
  return selected ? (
    <LearningWorkspace
      key={selected}
      {...props}
      pieceId={selected}
      choices={choices}
      switching={switching}
      onSelect={select}
    />
  ) : (
    <section className="content">
      <p>Loading Learning…</p>
    </section>
  );
}
