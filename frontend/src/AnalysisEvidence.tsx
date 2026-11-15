import { PassageComparison, type PassageData } from "./PassageComparison";
import { captureWarning } from "./captureWarning";
import {
  comparisonJudgement,
  type ComparisonMode,
} from "./comparisonJudgement";
import { ScoreComparison } from "./ScoreComparison";
import { keyFifths, pitchLabel } from "./comparisonScore";
import { useState } from "react";
import { clock } from "./api";
import { TouchButton as Button } from "./TouchButton";

export type NoteJudgement = {
  severity: "error" | "review";
  reason: string;
  explanation: string;
};
export type NoteGroup = {
  key_fifths?: number | null;
  live_missing?: number[];
  live_neutral?: number[];
  measure: number | null;
  beat?: number;
  time: number | null;
  expected: number[];
  observed: number[];
  score_notes?: {
    pitch: number;
    key_fifths?: number | null;
    spelling?: { step: string; alter: number; octave: number } | null;
    duration: number;
    staff?: number | null;
    display_staff?: number | null;
    staff_source?: string | null;
    clef_sign?: string | null;
    beam_group?: string | null;
    beaming_source?: string | null;
    beat_group_size?: number | null;
    measure_start?: number | null;
    voice?: string | null;
    part?: number | null;
    grace?: boolean | null;
  }[];
  played_notes?: { pitch: number; onset: number; duration: number }[];
  timing_review?: { ratio: number; explanation: string };
  musical_context?: {
    expected: Record<string, NoteJudgement>;
    observed: Record<string, NoteJudgement>;
  };
};
export type Observation = NoteGroup & {
  id: string;
  kind: string;
  pitch: number;
  uncertainty?: string;
  musical_judgement?: NoteJudgement;
};
export type Analysis = {
  id: string;
  session_id: string;
  segment_id: string;
  created: string;
  result: {
    key_fifths?: number | null;
    audio?: {
      available: boolean;
      notice: string;
      piano_presence?: {
        status: string;
        notice: string;
        auto_discard: boolean;
      } | null;
      discarded_for_headphone_play?: boolean;
      rms_dbfs?: number;
      peak_dbfs?: number;
      clipped_sample_fraction?: number;
      quiet_fraction?: number;
      capture_error?: string;
      acoustic_attacks?: number;
      coverage_seconds?: number;
      correlation?: {
        status: string;
        audio_minus_midi_seconds?: number;
        matched_groups?: number;
        midi_groups?: number;
        median_absolute_residual_ms?: number;
        notice: string;
        events?: {
          midi_time: number;
          audio_time: number;
          residual_ms: number;
          attack_dbfs: number;
          midi_velocity: number;
        }[];
      };
    };
    passages?: PassageData;
    midi_resolution?: Record<string, number>;
    notes: number;
    notice?: string;
    velocity_mean?: number;
    observations?: Observation[];
    observations_truncated?: boolean;
    note_comparison?: NoteGroup[];
    unaligned_played_groups?: number;
    reference_quality?: string;
    musical_review?: {
      version: string;
      red_pitch_differences: number;
      blue_pitch_differences: number;
      notice: string;
      timing_flags: {
        measure: number | null;
        time: number;
        ratio: number;
        explanation: string;
        severity: string;
      }[];
    };
    segment_snapshot?: Record<string, unknown>;
    assessment?: {
      precision_score: number;
      level?: string | null;
      audio_candidate?: boolean;
      coverage: number;
      pitch_precision: number;
      pitch_recall: number;
      notice: string;
    };
    tempo?: { bpm: number | null; notice?: string };
  };
};

export function latestActivityAnalysis(
  analyses: Analysis[],
  sessionId: string,
  segmentId: string,
) {
  return analyses
    .filter((a) => a.session_id === sessionId && a.segment_id === segmentId)
    .sort(
      (a, b) => b.created.localeCompare(a.created) || b.id.localeCompare(a.id),
    )[0];
}

export function noteName(pitch: number) {
  return `${["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"][pitch % 12]}${Math.floor(pitch / 12) - 1}`;
}

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
      {result.audio?.available && (
        <details className="chart-panel" open>
          <summary>Microphone analysis & MIDI correlation</summary>
          <p>
            Recorded RMS {result.audio.rms_dbfs?.toFixed(1)} dBFS · peak{" "}
            {result.audio.peak_dbfs?.toFixed(1)} dBFS · clipping{" "}
            {((result.audio.clipped_sample_fraction || 0) * 100).toFixed(3)}% ·{" "}
            {result.audio.acoustic_attacks} detected attacks ·{" "}
            {result.audio.coverage_seconds?.toFixed(1)} s covered
          </p>
          {captureWarning(result.audio.capture_error) && (
            <p role="alert">{captureWarning(result.audio.capture_error)}</p>
          )}
          <p>{result.audio.notice}</p>
          {result.audio.piano_presence && (
            <p>{result.audio.piano_presence.notice}</p>
          )}
          <p>
            Alignment: {result.audio.correlation?.status}.
            {result.audio.correlation?.status === "estimated" && (
              <>
                {" "}
                Audio minus MIDI offset{" "}
                {(
                  (result.audio.correlation.audio_minus_midi_seconds || 0) *
                  1000
                ).toFixed(0)}{" "}
                ms; {result.audio.correlation.matched_groups}/
                {result.audio.correlation.midi_groups} attack groups matched;
                median residual{" "}
                {result.audio.correlation.median_absolute_residual_ms?.toFixed(
                  1,
                )}{" "}
                ms.
              </>
            )}{" "}
            {result.audio.correlation?.notice}
          </p>
          {!!result.audio.correlation?.events?.length && (
            <details>
              <summary>Correlated attacks (session timestamps)</summary>
              <table>
                <thead>
                  <tr>
                    <th>MIDI seconds</th>
                    <th>Audio seconds</th>
                    <th>Residual ms</th>
                    <th>Attack dBFS</th>
                    <th>MIDI velocity</th>
                  </tr>
                </thead>
                <tbody>
                  {result.audio.correlation.events
                    .slice(0, 100)
                    .map((event, i) => (
                      <tr key={i}>
                        <td>{event.midi_time.toFixed(3)}</td>
                        <td>{event.audio_time.toFixed(3)}</td>
                        <td>{event.residual_ms.toFixed(1)}</td>
                        <td>{event.attack_dbfs.toFixed(1)}</td>
                        <td>{event.midi_velocity.toFixed(0)}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
              <p>
                First 100 matched attacks; the JSON analysis contains up to
                2,000.
              </p>
            </details>
          )}
        </details>
      )}
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
                    <line
                      x1="40"
                      x2="100%"
                      y1={y(p)}
                      y2={y(p)}
                      stroke="#d9d5ca"
                    />
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
                          : comparisonJudgement(g, p, "expected", mode)
                                .severity === "review"
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
                          comparisonJudgement(g, p, "observed", mode)
                            .severity === "review"
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
