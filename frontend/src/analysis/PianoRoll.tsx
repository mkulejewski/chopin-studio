import type React from "react";
import {
  comparisonJudgement,
  type ComparisonMode,
} from "../comparisonJudgement";
import type { NoteGroup } from "../types/analysis";

type Props = {
  visible: NoteGroup[];
  height: number;
  high: number;
  low: number;
  y: (pitch: number) => number;
  names: (group?: NoteGroup | null) => (pitch: number) => string;
  mode: ComparisonMode;
  page: number;
  selected: NoteGroup | null;
  setSelected: React.Dispatch<React.SetStateAction<NoteGroup | null>>;
};

export function PianoRoll({
  visible,
  height,
  high,
  low,
  y,
  names,
  mode,
  page,
  selected,
  setSelected,
}: Props) {
  return (
    <div className="note-overlay-scroll">
      <svg
        className="note-overlay"
        role="group"
        aria-label="Expected score notes and detected pitch discrepancies"
        width={Math.max(600, visible.length * 48 + 60)}
        height={height + 45}
      >
        {Array.from({ length: high - low + 1 }, (_, i) => high - i)
          .filter((p) => p % 12 === 0)
          .map((p) => (
            <g key={p}>
              <line x1="40" x2="100%" y1={y(p)} y2={y(p)} stroke="#d9d5ca" />
              <text x="3" y={y(p) + 4}>
                {names()(p)}
              </text>
            </g>
          ))}
        {visible.map((g, i) => (
          <g key={i}>
            <text
              x={62 + i * 48}
              y="18"
              textAnchor="middle"
              className={
                mode === "musical" && g.timing_review
                  ? "note-review-extra"
                  : undefined
              }
            >
              {g.measure ?? "?"}
              {mode === "musical" && g.timing_review ? " *" : ""}
            </text>
            {g.expected.map((p) => (
              <circle
                key={`e${p}`}
                cx={62 + i * 48}
                cy={y(p)}
                r="4"
                className={
                  g.observed.includes(p)
                    ? "note-matched"
                    : comparisonJudgement(g, p, "expected", mode).severity ===
                        "review"
                      ? "note-review-missing"
                      : "note-error-missing"
                }
              />
            ))}
            {g.observed
              .filter((p) => !g.expected.includes(p))
              .map((p) => (
                <text
                  key={`o${p}`}
                  x={62 + i * 48}
                  y={y(p) + 5}
                  textAnchor="middle"
                  className={
                    comparisonJudgement(g, p, "observed", mode).severity ===
                    "review"
                      ? "note-review-extra"
                      : "note-extra"
                  }
                >
                  ×
                </text>
              ))}
            <rect
              x={40 + i * 48}
              y="0"
              width="44"
              height={height + 40}
              className="note-column-target"
              role="button"
              tabIndex={0}
              aria-label={`Measure ${g.measure ?? "?"}, group ${page * 24 + i + 1}: expected ${g.expected.map(names(g)).join(", ")}; played ${g.observed.map(names(g)).join(", ") || "no aligned notes"}`}
              aria-pressed={selected === g}
              onClick={() => setSelected(g)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setSelected(g);
                }
              }}
            />
          </g>
        ))}
      </svg>
    </div>
  );
}
