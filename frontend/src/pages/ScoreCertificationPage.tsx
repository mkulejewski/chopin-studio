import { useEffect, useRef, useState } from "react";
import { api, json, type Piece, type Settings, type Volume } from "../api";
import { pitchLabel } from "../comparisonScore";
import { StaffNotation } from "../components/StaffNotation";
import { Score } from "../Score";
import { TouchButton as Button } from "../TouchButton";
import type { NoteGroup } from "../types/analysis";

type Take = {
  id: string;
  session_id: string | null;
  created: string;
  status: "recording" | "saved" | "interrupted";
  notice: string | null;
  revision: string;
  start_measure: number;
  end_measure: number;
  through_pause: boolean;
  correction_count: number;
  origin: "certification" | "learning" | "corrections";
  manual_corrections?: ManualCorrection[];
};

type ManualCorrection = {
  note_id: string;
  measure: number;
  staff: number;
  pitch: number;
  original_pitch: number;
  spelling: NonNullable<NoteGroup["score_notes"]>[number]["spelling"];
};

type Certification = {
  title: string;
  revision: string;
  ready: boolean;
  notice: string;
  volume_id: string;
  measures: { number: number; pdf_page: number }[];
  learned_end: number | null;
  correction_measures: number[];
  first_page: number;
  last_page: number;
  takes: Take[];
};

type Played = { pitch: number; played_index: number };
type Expected = {
  id: string;
  pitch: number;
  spelling: NonNullable<NoteGroup["score_notes"]>[number]["spelling"];
  staff: number;
  played_index: number | null;
};
type Attack = {
  beat: string;
  expected: Expected[];
  extra: Played[];
  suggestion?: "replace" | "remove" | "add";
};
type Measure = {
  number: number;
  pdf_page: number;
  key_fifths: number;
  attacks: Attack[];
};
type Review = {
  measures: Measure[];
  matched_count: number;
  missing_count: number;
  extra_count: number;
  played_count: number;
  pause_endpoint: {
    measure: number;
    attack: number;
    partial_measure: boolean;
    partial_attack: boolean;
  } | null;
};
type Live = { played_count: number; recent: number[] };

function liveGroups(recent: number[]): NoteGroup[] {
  return recent.map((pitch, index) => ({
    measure: 1,
    beat: index / 4,
    time: null,
    expected: [],
    observed: [pitch],
    live_neutral: [pitch],
  }));
}

function reviewGroups(measure: Measure): NoteGroup[] {
  const groups: NoteGroup[] = [];
  for (const attack of measure.attacks) {
    groups.push({
      measure: measure.number,
      beat: groups.length / 4,
      time: null,
      expected: attack.expected.map((note) => note.pitch),
      observed: attack.expected
        .filter((note) => note.played_index !== null)
        .map((note) => note.pitch),
      score_notes: attack.expected.map((note) => ({
        pitch: note.pitch,
        staff: note.staff,
        spelling: note.spelling,
        duration: 0.25,
      })),
    });
    for (const note of attack.extra) {
      groups.push({
        measure: measure.number,
        beat: groups.length / 4,
        time: null,
        expected: [],
        observed: [note.pitch],
      });
    }
  }
  return groups;
}

function differenceCount(measure: Measure) {
  return measure.attacks.reduce(
    (count, attack) =>
      count +
      attack.extra.length +
      attack.expected.filter((note) => note.played_index === null).length,
    0,
  );
}

function measureName(number: number) {
  return number === 0 ? "Pickup" : `Measure ${number}`;
}

function MeasurePicker({
  measures,
  value,
  onChange,
}: {
  measures: { number: number; differences: number }[];
  value: number;
  onChange: (number: number) => void;
}) {
  return (
    <label>
      Measure{" "}
      <select
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      >
        {measures.map(({ number, differences }) => (
          <option key={number} value={number}>
            {measureName(number)} · {differences}{" "}
            {differences === 1 ? "difference" : "differences"}
          </option>
        ))}
      </select>
    </label>
  );
}

function ManualCorrectionReview({
  corrections,
  selected,
  onSelect,
}: {
  corrections: ManualCorrection[];
  selected: ManualCorrection;
  onSelect: (note: ManualCorrection) => void;
}) {
  const index = corrections.indexOf(selected);
  const { measure, staff, original_pitch, pitch, spelling } = selected;
  const counts = new Map<number, number>();
  for (const note of corrections)
    counts.set(note.measure, (counts.get(note.measure) ?? 0) + 1);
  const step = (delta: number) =>
    onSelect(
      corrections[(index + delta + corrections.length) % corrections.length],
    );

  return (
    <>
      <p role="status">
        Correction {index + 1} of {corrections.length}
      </p>
      <div className="button-row">
        <MeasurePicker
          measures={Array.from(counts, ([number, differences]) => ({
            number,
            differences,
          }))}
          value={measure}
          onChange={(number) => {
            const first = corrections.find((note) => note.measure === number);
            if (first) onSelect(first);
          }}
        />
        <Button disabled={corrections.length < 2} onClick={() => step(-1)}>
          Previous discrepancy
        </Button>
        <Button disabled={corrections.length < 2} onClick={() => step(1)}>
          Next discrepancy
        </Button>
      </div>
      <StaffNotation
        groups={[
          {
            measure,
            beat: 0,
            time: null,
            expected: [original_pitch],
            observed: [pitch],
            score_notes: [{ pitch: original_pitch, staff, duration: 0.25 }],
          },
        ]}
        layout="overlay"
        expected
        fifths={0}
        context={selected.note_id}
        label="Original and corrected notes on staves"
      />
      <p className="certification-difference">
        {measureName(measure)} · {staff === 1 ? "upper" : "lower"} staff ·{" "}
        {pitchLabel(original_pitch)} → {pitchLabel(pitch, 0, spelling)}
      </p>
    </>
  );
}

function ReviewMeasure({ measure, take }: { measure: Measure; take: Take }) {
  const [window, setWindow] = useState(0);
  const groups = reviewGroups(measure);
  const pageSize = 32;
  const pages = Math.ceil(groups.length / pageSize);
  const name = (pitch: number, spelling?: Expected["spelling"]) =>
    pitchLabel(pitch, measure.key_fifths, spelling);
  return (
    <>
      <StaffNotation
        groups={groups.slice(window * pageSize, (window + 1) * pageSize)}
        layout="overlay"
        expected
        fifths={measure.key_fifths}
        context={`${take.id}:${measure.number}`}
      />
      {pages > 1 && (
        <div className="button-row">
          <Button disabled={window === 0} onClick={() => setWindow(window - 1)}>
            Previous staff section
          </Button>
          <span>
            Staff section {window + 1} of {pages}
          </span>
          <Button
            disabled={window + 1 >= pages}
            onClick={() => setWindow(window + 1)}
          >
            Next staff section
          </Button>
        </div>
      )}
      {measure.attacks.length === 0 && (
        <p>No written attacks in this measure.</p>
      )}
      <ol className="certification-attacks">
        {measure.attacks.map((attack, index) => {
          const missing = attack.expected.filter(
            (note) => note.played_index === null,
          );
          const matched = attack.expected.filter(
            (note) => note.played_index !== null,
          );
          const expectedName = (note: Expected) =>
            `${name(note.pitch, note.spelling)} (${note.staff === 1 ? "upper" : "lower"} staff)`;
          return (
            <li key={attack.beat}>
              <strong>Attack {index + 1}</strong>
              {matched.length > 0 && (
                <p>Matched {matched.map(expectedName).join(", ")}</p>
              )}
              {missing.length > 0 && (
                <p className="certification-difference">
                  Reference only {missing.map(expectedName).join(", ")}
                </p>
              )}
              {attack.extra.length > 0 && (
                <p className="certification-difference">
                  Played only{" "}
                  {attack.extra
                    .map(
                      (note) =>
                        `${name(note.pitch)} (MIDI attack ${note.played_index + 1})`,
                    )
                    .join(", ")}
                </p>
              )}
              {attack.suggestion && (
                <p>
                  <strong>Proposed score edit</strong>{" "}
                  {attack.suggestion === "replace"
                    ? `Replace ${expectedName(missing[0])} with ${name(attack.extra[0].pitch)}.`
                    : attack.suggestion === "remove"
                      ? `Remove ${expectedName(missing[0])}.`
                      : `Add ${name(attack.extra[0].pitch)} near this attack.`}
                </p>
              )}
            </li>
          );
        })}
      </ol>
    </>
  );
}

export function ScoreCertificationPage({
  piece,
  volumes,
  settings,
  recording,
  recordingCertificationPiece,
  saving,
  onBack,
  onLibrary,
}: {
  piece: Piece;
  volumes: Volume[];
  settings: Settings;
  recording: string | null;
  recordingCertificationPiece: string | null;
  saving: boolean;
  onBack: () => void;
  onLibrary: () => void;
}) {
  const endpoint = `/score-certification/${piece.id}`;
  const workspace = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<Certification | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [start, setStart] = useState<number | null>(null);
  const [end, setEnd] = useState<number | null>(null);
  const [includeCorrections, setIncludeCorrections] = useState(false);
  const captureVersion = useRef(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notationError, setNotationError] = useState("");
  const [review, setReview] = useState<Review | null>(null);
  const [live, setLive] = useState<Live | null>(null);
  const [measureNumber, setMeasureNumber] = useState<number | null>(null);
  const [manualNoteId, setManualNoteId] = useState<string | null>(null);
  const active = state?.takes.find((take) => take.status === "recording");
  const take =
    active ??
    state?.takes.find((take) => take.id === selected) ??
    state?.takes[0];
  const measure = review?.measures.find((m) => m.number === measureNumber);
  const corrections = take?.manual_corrections ?? [];
  const manualNote =
    corrections.find((note) => note.note_id === manualNoteId) ?? corrections[0];
  const manualPage = state?.measures.find(
    (m) => m.number === manualNote?.measure,
  )?.pdf_page;
  const first = start ?? state?.measures[0].number;
  const last = end ?? state?.measures.at(-1)?.number;
  const validRange = first !== undefined && last !== undefined && first <= last;
  const correctionCount =
    state?.correction_measures.filter(
      (number) => validRange && number >= first && number <= last,
    ).length ?? 0;
  const rangeStartPage = state?.measures.find(
    (m) => m.number === (active ? active.start_measure : first),
  )?.pdf_page;

  // Reconcile reloads, disconnects and stops from another browser window.
  useEffect(() => {
    let pending = true;
    const version = captureVersion.current;
    void api<Certification>(endpoint)
      .then((value) => {
        if (pending && version === captureVersion.current) setState(value);
      })
      .catch((e: Error) => {
        if (pending) setError(e.message);
      });
    return () => {
      pending = false;
    };
  }, [endpoint, recording]);

  useEffect(() => {
    setLive(null);
    setReview(null);
    setMeasureNumber(null);
    setManualNoteId(null);
    setNotationError("");
    if (!take || take.status === "interrupted" || take.origin === "corrections")
      return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const options = { signal: controller.signal };
    const takeEndpoint = `${endpoint}/${take.id}`;
    const poll = async () => {
      try {
        const value = await api<Live>(`${takeEndpoint}/live`, options);
        if (!controller.signal.aborted) {
          setLive(value);
          setNotationError("");
        }
      } catch (e) {
        if (!controller.signal.aborted)
          setNotationError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(poll, 450);
      }
    };
    if (take.status === "recording") void poll();
    else {
      void api<Review>(`${takeEndpoint}/review`, options)
        .then((value) => {
          if (controller.signal.aborted) return;
          setReview(value);
          setMeasureNumber(
            (value.measures.find(differenceCount) ?? value.measures[0]).number,
          );
        })
        .catch((e: Error) => {
          if (!controller.signal.aborted) setNotationError(e.message);
        });
    }
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [endpoint, take?.id, take?.status, take?.origin]);

  async function changeCapture(path: string) {
    captureVersion.current += 1;
    setBusy(true);
    setError("");
    try {
      const value = await api<Certification>(
        `${endpoint}/${path}`,
        path === "start"
          ? json("POST", {
              start_measure: first,
              end_measure: last,
              include_corrections: includeCorrections && correctionCount > 0,
            })
          : { method: "POST" },
      );
      captureVersion.current += 1;
      setState(value);
      setSelected(value.takes[0]?.id ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const volume = volumes.find((v) => v.id === state?.volume_id);
  const nextDifference = review?.measures.find(
    (m) =>
      measureNumber !== null &&
      m.number > measureNumber &&
      differenceCount(m) > 0,
  );
  const shownPiece = state && {
    ...piece,
    volume_id: state.volume_id,
    start_page: state.first_page,
    end_page: state.last_page,
  };
  return (
    <section className="content certification">
      <div className="page-heading">
        <div>
          <h1>Score certification</h1>
          <p>{state?.title ?? piece.title}</p>
        </div>
        <Button className="secondary" onClick={onBack}>
          Back
        </Button>
      </div>
      <div ref={workspace} className="certification-workspace">
        {state?.ready && shownPiece && (
          <div className="certification-score">
            <Score
              key={take?.status ?? "ready"}
              learningMode
              fullscreenTarget={workspace}
              piece={shownPiece}
              volume={volume}
              settings={settings}
              requestedPage={
                measure?.pdf_page ??
                manualPage ??
                rangeStartPage ??
                state.first_page
              }
              command={null}
              automaticCommand={null}
              onLibrary={onLibrary}
              onClear={() => {}}
              onToggle={() => {}}
              onAutoTurnChange={async () => {}}
              onError={(e) =>
                setError(e instanceof Error ? e.message : String(e))
              }
            />
          </div>
        )}
        <div className="certification-controls">
          <p>
            Play verbatim from your copy of the Paderewski edition to check that
            the digital counterpart matches the printed score.
          </p>
          <p>
            Read from the first written attack to the last, using both staves.
            Play each chord together or one key at a time before moving on. Skip
            repeat paths and play the written pitches of ornaments. Take as long
            as you need between notes.
          </p>
          {state && !state.ready && (
            <div className="learning-card">
              <p className="warning-text">{state.notice}</p>
              <Button className="secondary" onClick={onLibrary}>
                Open Score Library
              </Button>
            </div>
          )}
          {error && (
            <p role="alert" className="warning-text">
              {error}
            </p>
          )}
          {state && !active && (
            <fieldset className="certification-range">
              <legend>Measures to certify</legend>
              <div className="button-row">
                <label>
                  From{" "}
                  <select
                    value={first}
                    onChange={(e) => setStart(Number(e.target.value))}
                  >
                    {state.measures.map((m) => (
                      <option key={m.number} value={m.number}>
                        {measureName(m.number)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Through{" "}
                  <select
                    value={last}
                    onChange={(e) => setEnd(Number(e.target.value))}
                  >
                    {state.measures.map((m) => (
                      <option key={m.number} value={m.number}>
                        {measureName(m.number)}
                      </option>
                    ))}
                  </select>
                </label>
                {state.learned_end !== null && (
                  <Button
                    className="secondary"
                    onClick={() => {
                      setStart(null);
                      setEnd(state.learned_end);
                    }}
                  >
                    Use learned range
                  </Button>
                )}
              </div>
              {!validRange && (
                <p className="warning-text">
                  Choose an end at or after the start.
                </p>
              )}
              {correctionCount > 0 && (
                <label className="certification-corrections">
                  <input
                    type="checkbox"
                    checked={includeCorrections}
                    onChange={(e) => setIncludeCorrections(e.target.checked)}
                  />
                  Include saved Learning score corrections ({correctionCount})
                </label>
              )}
            </fieldset>
          )}
          {active && (
            <p>
              {measureName(active.start_measure)} through{" "}
              {measureName(active.end_measure)}
              {active.correction_count > 0 &&
                ` · ${active.correction_count} saved score corrections included`}
            </p>
          )}
          <div className="button-row certification-capture">
            {active ? (
              <>
                <Button
                  className="primary"
                  disabled={busy || saving}
                  onClick={() => void changeCapture(`${active.id}/finish`)}
                >
                  Finish and review
                </Button>
                <Button
                  className="secondary"
                  disabled={busy || saving || !live?.played_count}
                  onClick={() => void changeCapture(`${active.id}/pause`)}
                >
                  Pause and review up to here
                </Button>
              </>
            ) : (
              <Button
                className="primary"
                disabled={
                  busy || saving || !!recording || !state?.ready || !validRange
                }
                onClick={() => void changeCapture("start")}
              >
                Start certification take
              </Button>
            )}
            {!active && recording && (
              <span>
                {recordingCertificationPiece
                  ? "A certification take is active."
                  : "Finish the active recording first."}
              </span>
            )}
          </div>
          {notationError && (
            <p role="alert" className="warning-text">
              {notationError}
            </p>
          )}
          {active ? (
            <section
              className="learning-staves"
              aria-label="Live MIDI registration"
            >
              <h2>Live MIDI registration</h2>
              <p role="status">
                {live?.played_count ?? 0} captured attacks · latest eight shown
              </p>
              <StaffNotation
                groups={liveGroups(live?.recent ?? [])}
                layout="played"
                expected={false}
                fifths={0}
                context={active.id}
              />
              {!!live?.recent.length && (
                <p aria-label="Latest captured pitches">
                  {live.recent.map((pitch) => pitchLabel(pitch)).join(", ")}
                </p>
              )}
            </section>
          ) : (
            take && (
              <section
                className="learning-staves"
                aria-label="Certification review"
              >
                <h2>Certification review</h2>
                <div className="button-row">
                  <label>
                    Saved review{" "}
                    <select
                      value={take.id}
                      onChange={(event) => setSelected(event.target.value)}
                    >
                      {state?.takes.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.origin === "corrections"
                            ? "Hand-entered score corrections"
                            : new Date(item.created).toLocaleString()}
                          {item.status === "interrupted"
                            ? " · interrupted"
                            : ""}
                        </option>
                      ))}
                    </select>
                  </label>
                  {take.session_id && (
                    <a href={`/api/sessions/${take.session_id}/midi`}>
                      Download MIDI
                    </a>
                  )}
                </div>
                <p className="muted">
                  {measureName(take.start_measure)} through{" "}
                  {measureName(
                    review?.pause_endpoint?.measure ?? take.end_measure,
                  )}
                  {review?.pause_endpoint?.partial_measure &&
                    ` · through attack ${review.pause_endpoint.attack}`}
                  {" · "}
                  {take.correction_count} saved score corrections included
                  {" · "}Reference {take.revision}
                </p>
                {take.through_pause && review?.pause_endpoint && (
                  <p>
                    The last matched attack sets the estimated pause point. The
                    review includes any earlier discrepancies and trailing
                    played-only pitches.
                  </p>
                )}
                {review?.pause_endpoint?.partial_attack && (
                  <p>
                    The take stopped within a chord. Its remaining keys are
                    outside the review.
                  </p>
                )}
                {take.origin === "learning" && (
                  <p>
                    Source MIDI came from a saved Learning take. Hand-order
                    differences and played ornaments can appear as
                    discrepancies.
                  </p>
                )}
                {take.notice && <p className="warning-text">{take.notice}</p>}
                {take.origin === "corrections" ? (
                  manualNote && (
                    <ManualCorrectionReview
                      corrections={corrections}
                      selected={manualNote}
                      onSelect={(note) => setManualNoteId(note.note_id)}
                    />
                  )
                ) : review && measure ? (
                  <>
                    <p role="status">
                      {review.matched_count} matched · {review.missing_count}{" "}
                      reference only · {review.extra_count} played only ·{" "}
                      {review.played_count} MIDI attacks
                    </p>
                    <p className="muted">
                      Red marks pitch differences. Compare proposed edits with
                      the scan. Passages with repeated pitches can admit more
                      than one alignment.
                    </p>
                    <div className="button-row">
                      <MeasurePicker
                        measures={review.measures.map((m) => ({
                          number: m.number,
                          differences: differenceCount(m),
                        }))}
                        value={measure.number}
                        onChange={setMeasureNumber}
                      />
                      <Button
                        disabled={!nextDifference}
                        onClick={() =>
                          nextDifference &&
                          setMeasureNumber(nextDifference.number)
                        }
                      >
                        Next discrepancy
                      </Button>
                    </div>
                    <ReviewMeasure
                      key={`${take.id}:${measure.number}`}
                      measure={measure}
                      take={take}
                    />
                  </>
                ) : (
                  take.status === "saved" &&
                  !notationError && (
                    <p role="status">Comparing the saved MIDI…</p>
                  )
                )}
              </section>
            )
          )}
        </div>
      </div>
    </section>
  );
}
