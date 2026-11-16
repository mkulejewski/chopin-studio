import { useState } from "react";
import { AudioEvidence } from "./analysis/AudioEvidence";
import { PianoRoll } from "./analysis/PianoRoll";
import { clock } from "./api";
import {
  comparisonJudgement,
  type ComparisonMode,
} from "./comparisonJudgement";
import { keyFifths, pitchLabel } from "./comparisonScore";
import { PassageComparison } from "./PassageComparison";
import { ScoreComparison } from "./ScoreComparison";
import { TouchButton as Button } from "./TouchButton";

import type { Analysis, NoteGroup } from "./types/analysis";
export {
  latestActivityAnalysis,
  midiNoteName as noteName,
} from "./analysisUtils";
export type {
  Analysis,
  NoteGroup,
  NoteJudgement,
  Observation,
} from "./types/analysis";

export function AnalysisEvidence({
  analysis,
  title,
  stale,
  musicalKey,
}: {
  analysis: Analysis;
  title: string;
  stale: boolean;
  musicalKey?: string;
}) {
  const [mode, setMode] = useState<ComparisonMode>("musical");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<NoteGroup | null>(null);
  const [measure, setMeasure] = useState<string>("all");
  const result = analysis.result;
  const observations = result.observations || [];
  // Historical analyses contain discrepancy groups only. Never imply those are
  // the complete score or reconstruct correct notes from absent evidence.
  const groups = result.note_comparison;
  const fifths = result.key_fifths ?? keyFifths(musicalKey) ?? 0;
  const names = (group?: NoteGroup | null) => (pitch: number) => {
    const context = group?.score_notes
      ? group
      : group &&
        groups?.find(
          (g) =>
            g.measure === group.measure &&
            g.time === group.time &&
            (g.expected.includes(pitch) || g.observed.includes(pitch)),
        );
    const source = context?.score_notes?.find((n) => n.pitch === pitch);
    return pitchLabel(
      pitch,
      context?.key_fifths ?? group?.key_fifths ?? fifths,
      source?.spelling,
    );
  };
  const measures = [
    ...new Set((groups || observations).map((g) => String(g.measure ?? "?"))),
  ];
  const filtered = (groups || []).filter(
    (g) => measure === "all" || String(g.measure ?? "?") === measure,
  );
  const pages = Math.max(1, Math.ceil(filtered.length / 24));
  const visible = filtered.slice(page * 24, (page + 1) * 24);
  const pitches = visible.flatMap((g) => [...g.expected, ...g.observed]);
  const low = Math.min(48, ...pitches),
    high = Math.max(72, ...pitches);
  const height = Math.max(240, (high - low + 4) * 7);
  const y = (pitch: number) => 40 + (high - pitch) * 7;
  const issues = observations.filter(
    (o) => measure === "all" || String(o.measure ?? "?") === measure,
  );
  const assessment = result.assessment;
  const focusMeasures = [
    ...new Set(observations.map((o) => String(o.measure ?? "?"))),
  ]
    .map((m) => ({
      measure: m,
      count: observations.filter((o) => String(o.measure ?? "?") === m).length,
      red: observations.filter(
        (o) =>
          String(o.measure ?? "?") === m &&
          o.musical_judgement?.severity === "error",
      ).length,
    }))
    .sort(
      (a, b) => (mode === "musical" ? b.red - a.red : 0) || b.count - a.count,
    )
    .slice(0, 5);
  return (
    <section
      className="chart-panel analysis-evidence"
      aria-label="Selected activity analysis"
    >
      <span className="eyebrow">
        Latest analysis · {new Date(analysis.created).toLocaleString()}
      </span>
      <h2>Analysis · {title}</h2>
      {result.audio?.available && <AudioEvidence audio={result.audio} />}
      {result.audio && !result.audio.available && (
        <p className="muted">{result.audio.notice}</p>
      )}
      {stale && (
        <p role="status" className="info-box">
          This analysis predates activity edits. Save timeline edits and analyse
          this activity again to refresh the comparison.
        </p>
      )}
      <div className="analysis-metrics">
        <div>
          <strong>{result.notes.toLocaleString()}</strong>
          <span>played notes</span>
        </div>
        <div>
          <strong>
            {observations.length}
            {result.observations_truncated ? "+" : ""}
          </strong>
          <span>potential pitch discrepancies</span>
        </div>
        <div>
          <strong>{assessment ? `${assessment.precision_score}%` : "—"}</strong>
          <span>strict reference pitch score</span>
        </div>
        <div>
          <strong>
            {assessment ? `${Math.round(assessment.coverage * 100)}%` : "—"}
          </strong>
          <span>reference coverage</span>
        </div>
        <div>
          <strong>
            {result.tempo?.bpm != null
              ? `♩ = ${Math.round(result.tempo.bpm)}`
              : "—"}
          </strong>
          <span>inferred tempo</span>
        </div>
      </div>
      {(assessment?.level || assessment?.audio_candidate) && (
        <p>
          {assessment.level
            ? `Automatic technical level: ${assessment.level}. `
            : ""}
          {assessment.audio_candidate
            ? "★ Candidate for audio production."
            : ""}
        </p>
      )}
      <p className="muted">
        Reference: {result.reference_quality || "unavailable"}. Potential
        discrepancies need review: repeats, ornaments and edition differences
        can affect alignment. The pitch score is a technical estimate. Your
        personal notes and learning level stay separate.
      </p>
      <label>
        Comparison method
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as ComparisonMode)}
        >
          <option value="strict">Strict digital reference</option>
          <option value="musical">Musical context (conservative)</option>
        </select>
      </label>
      {mode === "musical" && (
        <div className="musical-summary">
          <p>
            <span className="score-error">Red: likely pitch/chord error</span> ·{" "}
            <span className="score-review">
              Blue: possible adaptation, edition difference or uncertainty
            </span>
            . Local deterministic rules; no LLM is used.
          </p>
          {result.musical_review ? (
            <>
              <p>
                <strong>{result.musical_review.red_pitch_differences}</strong>{" "}
                red pitch differences ·{" "}
                <strong>{result.musical_review.blue_pitch_differences}</strong>{" "}
                blue pitch differences. Octave redistribution and possible chord
                reductions stay blue. The strict pitch score above is unchanged.
              </p>
              <details>
                <summary>How musical judgements are made</summary>
                <p>{result.musical_review.notice}</p>
              </details>
              {!!result.musical_review.timing_flags.length && (
                <details>
                  <summary>
                    Timing changes to review ·{" "}
                    {result.musical_review.timing_flags.length}
                  </summary>
                  {result.musical_review.timing_flags.map((f, i) => (
                    <p className="score-review" key={i}>
                      Measure {f.measure ?? "?"} · {clock(f.time)} · {f.ratio}×
                      nearby time per beat. {f.explanation}
                    </p>
                  ))}
                </details>
              )}
            </>
          ) : (
            <p>
              Analyse this activity again to generate musical-context
              explanations. Until then, all reference differences stay blue in
              this mode.
            </p>
          )}
        </div>
      )}
      <h3>Where to focus</h3>
      {focusMeasures.length > 0 && (
        <div
          className="button-row"
          aria-label="Measures with most potential discrepancies"
        >
          {focusMeasures.map((m) => (
            <Button
              key={m.measure}
              className="secondary"
              onClick={() => {
                setMeasure(m.measure);
                setPage(0);
                setSelected(null);
              }}
            >
              Measure {m.measure} ·{" "}
              {mode === "musical"
                ? `${m.red} red / ${m.count - m.red} blue`
                : `${m.count} to review`}
            </Button>
          ))}
        </div>
      )}
      <label>
        Measure to review
        <select
          value={measure}
          onChange={(e) => {
            setMeasure(e.target.value);
            setPage(0);
            setSelected(null);
          }}
        >
          <option value="all">All analysed measures</option>
          {measures.map((m) => (
            <option key={m} value={m}>
              Measure {m} ·{" "}
              {
                observations.filter((o) => String(o.measure ?? "?") === m)
                  .length
              }{" "}
              potential discrepancies
            </option>
          ))}
        </select>
      </label>
      {!!groups?.length && (
        <ScoreComparison
          groups={visible}
          allGroups={groups}
          mode={mode}
          title={title}
          fifths={fifths}
        />
      )}
      <PassageComparison
        selectedBeat={selected?.beat}
        data={result.passages}
        beats={visible.map((g) => g.beat ?? -1)}
        pieceId={
          typeof result.segment_snapshot?.piece_id === "string"
            ? result.segment_snapshot.piece_id
            : undefined
        }
        onSelect={(p) =>
          setSelected(
            groups?.find((g) => g.beat === p.beat && g.measure === p.measure) ||
              null,
          )
        }
      />
      {result.midi_resolution && (
        <p>
          CC88 ordering: {result.midi_resolution.paired_prefixes || 0} paired
          prefixes · {result.midi_resolution.interrupted_prefixes || 0}{" "}
          interrupted · {result.midi_resolution.orphan_prefixes || 0} orphaned ·{" "}
          {result.midi_resolution.stale_prefixes || 0} stale ·{" "}
          {result.midi_resolution.out_of_order_events || 0} out-of-order events.
          Counts cover the source journal.
        </p>
      )}
      {!!groups?.length && (
        <nav aria-label="Comparison note navigation">
          <div className="button-row">
            <Button
              className="secondary"
              disabled={page === 0}
              onClick={() => {
                setPage((p) => p - 1);
                setSelected(null);
              }}
            >
              Previous notes
            </Button>
            <span>
              Page {page + 1} of {pages} · {filtered.length} score groups
            </span>
            <Button
              className="secondary"
              disabled={page + 1 >= pages}
              onClick={() => {
                setPage((p) => p + 1);
                setSelected(null);
              }}
            >
              Next notes
            </Button>
          </div>
        </nav>
      )}
      <h3>Piano roll comparison</h3>
      <p className="muted">
        A schematic piano roll in score order: pitch runs vertically, each
        column is a score onset. Spacing does not represent rhythm or duration.
        Select a column for note names and recording time.
      </p>
      <div className="note-legend">
        <span className="note-matched">● Matched</span>
        <span>○ Expected / possibly missing · × Played / possibly extra</span>
        <span className="score-error">
          Red:{" "}
          {mode === "strict" ? "strict differences" : "likely musical errors"}
        </span>
        {mode === "musical" && (
          <span className="score-review">Blue: adaptation or uncertainty</span>
        )}
      </div>
      {groups?.length ? (
        <>
          <PianoRoll
            visible={visible}
            height={height}
            high={high}
            low={low}
            y={y}
            names={names}
            mode={mode}
            page={page}
            selected={selected}
            setSelected={setSelected}
          />
        </>
      ) : (
        <p>
          {groups
            ? "No aligned note groups available."
            : "This saved analysis has no note overlay. Analyse this activity again to generate one; existing discrepancies remain below."}
        </p>
      )}
      {selected && (
        <div className="info-box" role="status">
          Measure {selected.measure ?? "?"} ·{" "}
          {selected.time == null
            ? "No aligned recording time"
            : `Recording ${clock(selected.time)}`}
          <br />
          Expected:{" "}
          {selected.expected.map(names(selected)).join(", ") || "none"}
          <br />
          {mode === "musical" && selected.timing_review && (
            <p className="score-review">
              Timing review: {selected.timing_review.explanation}
            </p>
          )}
          Played:{" "}
          {selected.observed.map(names(selected)).join(", ") ||
            "no aligned notes"}
          {mode === "musical" &&
            [
              ...new Set([
                ...selected.expected
                  .filter((p) => !selected.observed.includes(p))
                  .map(
                    (p) =>
                      comparisonJudgement(selected, p, "expected", mode)
                        .explanation,
                  ),
                ...selected.observed
                  .filter((p) => !selected.expected.includes(p))
                  .map(
                    (p) =>
                      comparisonJudgement(selected, p, "observed", mode)
                        .explanation,
                  ),
              ]),
            ].map((text) => <p key={text}>{text}</p>)}
        </div>
      )}
      {!!result.unaligned_played_groups && (
        <p>
          {result.unaligned_played_groups} played onset groups could not be
          aligned; these are not plotted or classified as extra notes.
        </p>
      )}
      <details>
        <summary>
          Pitch discrepancy list · {issues.length}
          {result.observations_truncated ? "+" : ""}
        </summary>
        <p>
          Missing notes without recording times may also indicate uncertain
          repeat alignment.
        </p>
        <div className="analysis-issue-list">
          {issues.slice(0, 100).map((o) => (
            <div
              key={o.id}
              className={
                mode === "musical"
                  ? o.musical_judgement?.severity === "error"
                    ? "score-error"
                    : "score-review"
                  : undefined
              }
            >
              <strong>
                Measure {o.measure ?? "?"} ·{" "}
                {o.kind === "extra" ? "Possibly extra" : "Possibly missing"}{" "}
                {names(o)(o.pitch)}
              </strong>
              <span>
                {o.time == null
                  ? "No aligned recording time"
                  : `Recording ${clock(o.time)}`}{" "}
                · Expected {o.expected.map(names(o)).join(", ") || "none"};
                played{" "}
                {o.observed.map(names(o)).join(", ") || "no aligned notes"}
              </span>
              {mode === "musical" && (
                <span>
                  {o.musical_judgement?.explanation ||
                    "Reanalyse to generate a musical-context explanation."}
                </span>
              )}
            </div>
          ))}
        </div>
        {!issues.length && (
          <p>
            No potential discrepancies reported for this selection. This does
            not certify an error-free performance.
          </p>
        )}
        {issues.length > 100 && (
          <p>
            Showing the first 100 discrepancies. Filter by measure to narrow the
            list; all evidence is available in the JSON export.
          </p>
        )}
      </details>
      <details>
        <summary>How to interpret this analysis</summary>
        <p>{result.notice}</p>
        <p>{assessment?.notice}</p>
        <p>{result.tempo?.notice}</p>
        <p>
          Pitch precision {assessment?.pitch_precision ?? "—"}% · recall{" "}
          {assessment?.pitch_recall ?? "—"}%. Mean MIDI velocity{" "}
          {result.velocity_mean?.toFixed(1) ?? "—"}. Expressive tempo changes
          are not classified as errors.
        </p>
      </details>
    </section>
  );
}
