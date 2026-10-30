import { AiConfig } from "./AiConfig";
import { useEffect, useState } from "react";
import { api, json, clock, upload, type Piece, type Session } from "./api";
import { TouchButton as Button } from "./TouchButton";

type Segment = {
  id: string;
  start: number;
  end: number;
  piece_id: string | null;
  label: string;
  confidence: number;
  first_measure: number | null;
  last_measure: number | null;
  kind: string;
  group_id: string | null;
  complete: boolean;
  discarded: boolean;
  revision: number;
  details: string;
};
type Job = {
  id: string;
  kind: string;
  status: string;
  error: string | null;
  result: string | null;
};
export function PracticeReview({
  session,
  pieces,
  onError,
}: {
  session: Session;
  pieces: Piece[];
  onError: (error: unknown) => void;
}) {
  const [segments, setSegments] = useState<Segment[]>([]),
    [revision, setRevision] = useState(0),
    [dirty, setDirty] = useState(false),
    [selected, setSelected] = useState(""),
    [split, setSplit] = useState(0),
    [jobs, setJobs] = useState<Job[]>([]),
    [analyses, setAnalyses] = useState<any[]>([]),
    [reports, setReports] = useState<any[]>([]),
    [fonts, setFonts] = useState<string[]>([]),
    [font, setFont] = useState(""),
    [format, setFormat] = useState("wav"),
    [question, setQuestion] = useState(
      "What should I practise next, based on the available evidence?",
    ),
    [cloud, setCloud] = useState(false),
    [model, setModel] = useState("gpt-4.1-mini"),
    [busy, setBusy] = useState(false),
    [detail, setDetail] = useState<any>(null);
  const [reportEdit, setReportEdit] = useState<{
    id: string;
    text: string;
  } | null>(null);
  const [timelineZoom, setTimelineZoom] = useState(1);
  const [ports, setPorts] = useState<string[]>([]),
    [port, setPort] = useState(""),
    [captureDevice, setCaptureDevice] = useState("");
  useEffect(() => {
    void api("/audio/hardware")
      .then((value) => setPorts(value.ports))
      .catch(onError);
  }, []);

  const load = async () => {
    const s = await api<Segment[]>(`/sessions/${session.id}/segments`);
    setSegments(s);
    setRevision(Math.max(0, ...s.map((s) => s.revision)));
    setDirty(false);
  };
  const results = async () => {
    const [j, a, r] = await Promise.all([
      api<Job[]>("/jobs"),
      api<any[]>(`/sessions/${session.id}/analyses`),
      api<any[]>(`/sessions/${session.id}/reports`),
    ]);
    setJobs(j);
    setAnalyses(a);
    setReports(r);
  };
  useEffect(() => {
    void load().catch(onError);
    void results().catch(onError);
    void api("/audio/engines")
      .then((r) => {
        setFonts(r.soundfonts);
        setFont(r.soundfonts[0] || "");
      })
      .catch(onError);
  }, [session.id]);
  useEffect(() => {
    const timer = setInterval(() => {
      void results().catch(() => {});
      if (!dirty) void load().catch(() => {});
    }, 2000);
    return () => clearInterval(timer);
  }, [session.id, dirty]);
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await results();
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  };
  const change = (id: string, update: Partial<Segment>) => {
    setSegments((items) =>
      items.map((s) => (s.id === id ? { ...s, ...update } : s)),
    );
    setDirty(true);
  };
  const row = segments.find((s) => s.id === selected);
  const renderJobs = jobs.filter(
    (j) =>
      j.kind === "render" &&
      j.status === "done" &&
      j.result &&
      JSON.parse(j.result).filename &&
      JSON.parse(j.result).session_id === session.id,
  );
  return (
    <div className="practice-review">
      <a
        className="button secondary"
        href={`/api/sessions/${session.id}/bundle`}
      >
        Export MIDI, audio & reports bundle
      </a>
      <a
        className="button secondary"
        href={`/api/sessions/${session.id}/preanalysis`}
      >
        Export structured LLM preanalysis (JSON)
      </a>
      <div className="section-heading">
        <h2>Your activity timeline</h2>
        <p>
          Experimental candidate boundaries and piece matches. Check long
          expressive pauses and repeated sections. Original-session times stay
          exact.
        </p>
      </div>
      <div className="button-row">
        <Button
          className="secondary"
          disabled={busy || dirty}
          onClick={() =>
            void run(async () => {
              await api(`/sessions/${session.id}/organise?force=true`, {
                method: "POST",
              });
            })
          }
        >
          Rebuild candidate timeline (undo available)
        </Button>
        <Button
          className="secondary"
          disabled={busy}
          onClick={() =>
            void run(async () => {
              await api(`/sessions/${session.id}/segments/undo`, {
                method: "POST",
              });
              await load();
            })
          }
        >
          Undo last timeline edit
        </Button>
        {dirty && (
          <Button
            className="primary"
            disabled={busy}
            onClick={() =>
              void run(async () => {
                await api(
                  `/sessions/${session.id}/segments`,
                  json("PUT", { segments, expected_revision: revision }),
                );
                await load();
              })
            }
          >
            Save timeline edits
          </Button>
        )}
      </div>
      <div className="button-row">
        <Button
          className="secondary"
          onClick={() => setTimelineZoom((z) => Math.max(0.75, z - 0.25))}
        >
          Zoom timeline out
        </Button>
        <Button
          className="secondary"
          onClick={() => setTimelineZoom((z) => Math.min(3, z + 0.25))}
        >
          Zoom timeline in
        </Button>
      </div>
      <div className="timeline-touch" aria-label="Activity timeline">
        {segments.map((s) => (
          <Button
            key={s.id}
            style={{ minWidth: 240 * timelineZoom }}
            className={
              selected === s.id ? "timeline-item selected" : "timeline-item"
            }
            onClick={() => {
              setSelected(s.id);
              setSplit(Math.round(((s.start + s.end) / 2) * 100) / 100);
            }}
          >
            <strong>
              {s.piece_id
                ? pieces.find((p) => p.id === s.piece_id)?.catalogue_path ||
                  s.piece_id
                : "Unidentified material"}
            </strong>
            <span>
              {clock(s.start)}–{clock(s.end)} · {s.label} · similarity{" "}
              {s.confidence.toFixed(2)}
            </span>
            <small>
              {s.first_measure != null
                ? `Measures ${s.first_measure}–${s.last_measure}`
                : "No reliable score measures"}
              {s.group_id ? " · Repeated-attempt group" : ""}
              {s.discarded ? " · Disposable" : ""}
            </small>
          </Button>
        ))}
      </div>
      {!segments.length && (
        <p className="muted">
          Waiting for candidate organisation. Silence-only recordings have no
          musical activities.
        </p>
      )}
      {row && (
        <div className="chart-panel">
          <h3>Edit selected activity</h3>
          <div className="form-grid">
            <label>
              Start in original session (seconds)
              <input
                aria-label="Segment start seconds"
                type="number"
                min="0"
                step=".01"
                value={row.start}
                onChange={(e) =>
                  change(row.id, { start: Number(e.target.value) })
                }
              />
            </label>
            <label>
              End in original session (seconds)
              <input
                aria-label="Segment end seconds"
                type="number"
                min="0"
                step=".01"
                value={row.end}
                onChange={(e) =>
                  change(row.id, { end: Number(e.target.value) })
                }
              />
            </label>
            <label>
              Piece
              <select
                value={row.piece_id || ""}
                onChange={(e) =>
                  change(row.id, {
                    piece_id: e.target.value || null,
                    label: e.target.value
                      ? "Manually identified"
                      : "Unknown piece",
                    confidence: 0,
                  })
                }
              >
                <option value="">Unknown / technical material</option>
                {pieces.map((p) => (
                  <option value={p.id} key={p.id}>
                    {p.catalogue_path}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Activity type
              <select
                value={row.kind}
                onChange={(e) =>
                  change(row.id, {
                    kind: e.target.value,
                    complete: e.target.value === "complete",
                  })
                }
              >
                {["unknown", "partial", "exercise", "complete"].map((k) => (
                  <option key={k}>{k}</option>
                ))}
              </select>
            </label>
            <label>
              First measure
              <input
                type="number"
                min="0"
                value={row.first_measure ?? ""}
                onChange={(e) =>
                  change(row.id, {
                    first_measure: e.target.value
                      ? Number(e.target.value)
                      : null,
                  })
                }
              />
            </label>
            <label>
              Last measure
              <input
                type="number"
                min="0"
                value={row.last_measure ?? ""}
                onChange={(e) =>
                  change(row.id, {
                    last_measure: e.target.value
                      ? Number(e.target.value)
                      : null,
                  })
                }
              />
            </label>
            <label>
              Label
              <input
                value={row.label}
                onChange={(e) => change(row.id, { label: e.target.value })}
              />
            </label>
            <label>
              Split at original-session seconds
              <input
                aria-label="Split time seconds"
                type="number"
                min={row.start}
                max={row.end}
                step=".01"
                value={split}
                onChange={(e) => setSplit(Number(e.target.value))}
              />
            </label>
          </div>
          <label className="toggle-row">
            Mark disposable (original retained)
            <input
              type="checkbox"
              checked={!!row.discarded}
              onChange={(e) => change(row.id, { discarded: e.target.checked })}
            />
          </label>
          <div className="button-row">
            <Button
              className="secondary"
              disabled={split <= row.start || split >= row.end}
              onClick={() => {
                const id = crypto.randomUUID().replaceAll("-", "");
                setSegments((items) =>
                  items.flatMap((s) =>
                    s.id === row.id
                      ? [
                          { ...s, end: split },
                          { ...s, id, start: split, group_id: null },
                        ]
                      : [s],
                  ),
                );
                setDirty(true);
              }}
            >
              Split activity
            </Button>
            <Button
              className="secondary"
              disabled={segments.indexOf(row) === segments.length - 1}
              onClick={() => {
                const i = segments.indexOf(row),
                  next = segments[i + 1];
                setSegments((items) =>
                  items
                    .filter((s) => s.id !== next.id)
                    .map((s) =>
                      s.id === row.id
                        ? {
                            ...s,
                            end: next.end,
                            complete: false,
                            kind: "partial",
                          }
                        : s,
                    ),
                );
                setDirty(true);
              }}
            >
              Merge with next
            </Button>
            <Button
              className="secondary"
              disabled={segments.indexOf(row) === 0}
              onClick={() => {
                const previous = segments[segments.indexOf(row) - 1];
                const group =
                  previous.group_id || crypto.randomUUID().replaceAll("-", "");
                change(previous.id, { group_id: group });
                change(row.id, { group_id: group, kind: "exercise" });
              }}
            >
              Group with previous attempt
            </Button>
          </div>
          <p className="muted">
            Save edits before exporting, analysing or rendering. You can correct
            boundaries numerically without precision dragging.
          </p>
          <div className="button-row">
            <a
              className={`button secondary ${dirty ? "disabled-link" : ""}`}
              aria-disabled={dirty}
              href={dirty ? undefined : `/api/segments/${row.id}/midi`}
            >
              Export activity MIDI
            </a>
            <Button
              className="primary"
              disabled={dirty || busy}
              onClick={() =>
                void run(() =>
                  api(`/segments/${row.id}/analyse`, { method: "POST" }),
                )
              }
            >
              Analyse activity
            </Button>
            <Button
              className="secondary"
              disabled={dirty || !row.piece_id || busy}
              onClick={() =>
                void run(() =>
                  api(`/segments/${row.id}/learn`, { method: "POST" }),
                )
              }
            >
              Remember labelled MIDI reference
            </Button>
          </div>
        </div>
      )}
      {row && (
        <div className="chart-panel">
          <h2>Optional audio</h2>
          <p>
            Rendering starts only when requested. Original MIDI is retained.
            Page-control pedal messages are excluded from generated sound.
          </p>
          <h3>AP-470 built-in sound</h3>
          <p>
            Record WAV to a USB flash drive while playing, or replay this take
            through the physical piano. Computer USB carries MIDI. For computer
            audio capture, connect PHONES/OUTPUT to an audio interface and enter
            its ALSA input device. Leave input blank to use the piano's USB
            flash recorder during playback.
          </p>
          <label>
            MIDI output
            <select value={port} onChange={(e) => setPort(e.target.value)}>
              <option value="">Choose the AP-470 output</option>
              {ports.map((p) => (
                <option key={p}>{p}</option>
              ))}
            </select>
          </label>
          <Button
            className="secondary"
            onClick={() =>
              void run(async () => {
                const value = await api("/audio/hardware");
                setPorts(value.ports);
              })
            }
          >
            Refresh MIDI outputs
          </Button>
          <label>
            Audio interface ALSA input (optional)
            <input
              value={captureDevice}
              onChange={(e) => setCaptureDevice(e.target.value)}
              placeholder="plughw:CARD=YourInterface,DEV=0"
            />
          </label>
          <Button
            className="secondary"
            disabled={dirty || busy || !port}
            onClick={() =>
              void run(() =>
                api(
                  `/segments/${row.id}/ap470`,
                  json("POST", { port, capture_device: captureDevice }),
                ),
              )
            }
          >
            {captureDevice
              ? "Play through AP-470 and capture audio"
              : "Play through AP-470 (start piano audio recorder first)"}
          </Button>
          <label>
            Attach AP-470 WAV to this activity
            <input
              type="file"
              accept=".wav"
              disabled={dirty || busy}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file)
                  void run(() => upload(`/segments/${row.id}/audio`, file));
                e.target.value = "";
              }}
            />
          </label>
          <h3>Software soundfont</h3>
          <div className="form-grid">
            <label>
              Soundfont
              <select value={font} onChange={(e) => setFont(e.target.value)}>
                <option value="">Choose a local soundfont</option>
                {fonts.map((f) => (
                  <option key={f}>{f}</option>
                ))}
              </select>
            </label>
            <label>
              Custom SF2 / SF3 path
              <input
                placeholder="/home/you/Piano.sf2"
                value={font}
                onChange={(e) => setFont(e.target.value)}
              />
            </label>
            <label>
              Audio format
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value)}
              >
                <option value="wav">WAV</option>
                <option value="flac">FLAC</option>
              </select>
            </label>
          </div>
          <Button
            className="secondary"
            disabled={dirty || busy || !font}
            onClick={() =>
              void run(() =>
                api(
                  `/segments/${row.id}/render`,
                  json("POST", { soundfont: font, format }),
                ),
              )
            }
          >
            Render this activity with FluidSynth
          </Button>
          {renderJobs.map((j) => (
            <div className="audio-result" key={j.id}>
              <span>
                {JSON.parse(j.result!).engine} ·{" "}
                {JSON.parse(j.result!).format.toUpperCase()}
              </span>
              <audio controls preload="none" src={`/api/audio/${j.id}`} />
              <a
                className="button secondary"
                href={`/api/audio/${j.id}`}
                download
              >
                Download audio
              </a>
            </div>
          ))}
        </div>
      )}
      {analyses.map((a) => (
        <div className="chart-panel" key={a.id}>
          <span className="eyebrow">
            ANALYSIS {a.id.slice(0, 6)} · {a.version}
          </span>
          <h2>Evidence, with context</h2>
          <p>{a.result.notice}</p>
          <p>
            {a.result.notes} note onsets · mean MIDI velocity{" "}
            {a.result.velocity_mean?.toFixed(1) ?? "—"} ·{" "}
            {a.result.observations?.length || 0} potential pitch discrepancies.
            Definitive accuracy percentage remains withheld.
          </p>
          {a.result.assessment && (
            <p>
              Automatic pitch score: {a.result.assessment.precision_score}% ·
              precision {a.result.assessment.pitch_precision}% · recall{" "}
              {a.result.assessment.pitch_recall}% · reference coverage{" "}
              {Math.round(a.result.assessment.coverage * 100)}% ·{" "}
              {a.result.assessment.level || "Assessment needs reference review"}
              .
              {a.result.assessment.audio_candidate
                ? " ★ Candidate for audio production."
                : ""}{" "}
              {a.result.assessment.notice}
            </p>
          )}
          <p>
            Automatic assessments are saved separately from your personal notes
            and learning level.
          </p>
          {a.result.tempo_curve?.length > 0 && (
            <div className="tempo-touch">
              {a.result.tempo_curve.slice(0, 240).map((p: any, i: number) => (
                <Button
                  key={i}
                  aria-label={`Tempo near ${clock(p.time)}`}
                  onClick={() =>
                    setDetail({
                      time: p.time,
                      local_tempo_bpm: p.bpm,
                      interpretation:
                        "Local score-relative tempo estimate; expressive rubato is not an error.",
                    })
                  }
                >
                  {Math.round(p.bpm)}
                  <small>{clock(p.time)}</small>
                </Button>
              ))}
            </div>
          )}
          <div className="observations">
            {a.result.observations?.slice(0, 100).map((o: any) => (
              <Button
                className="secondary"
                key={o.id}
                onClick={() => setDetail(o)}
              >
                Measure {o.measure ?? "?"} · {o.kind} pitch {o.pitch} ·{" "}
                {o.time == null ? "unlocated" : clock(o.time)}
              </Button>
            ))}
          </div>
          <small>
            Showing up to 100 evidence rows. Full structured results are
            retained locally.
          </small>
        </div>
      ))}
      {detail && (
        <div className="chart-panel" role="status">
          <h3>Selected evidence</h3>
          <pre className="evidence-detail">
            {JSON.stringify(detail, null, 2)}
          </pre>
          <Button className="secondary" onClick={() => setDetail(null)}>
            Close evidence
          </Button>
        </div>
      )}
      <div className="chart-panel">
        <h2>Your practice report</h2>
        <p>
          Local reports use deterministic evidence. Cloud interpretation is
          optional and sends the structured analysis, personal notes and levels,
          recent reports and question to OpenAI, only after the explicit button
          below. It does not upload your score PDFs, MIDI files or audio.
        </p>
        <label>
          Question or follow-up
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={2}
          />
        </label>
        <div className="button-row">
          <Button
            className="primary"
            disabled={busy}
            onClick={() =>
              void run(() =>
                api(
                  `/sessions/${session.id}/teacher`,
                  json("POST", { provider: "local", question }),
                ),
              )
            }
          >
            Generate local report
          </Button>
          <Button className="secondary" onClick={() => setCloud(!cloud)}>
            Optional AI interpretation
          </Button>
        </div>
        {cloud && (
          <div className="info-box">
            <div>
              <AiConfig onError={onError} />
              <label>
                OpenAI model
                <input
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                />
              </label>
              <p>
                Uses OPENAI_API_KEY configured on the backend. Charges and
                provider terms may apply. Review the analysis evidence above
                before sharing.
              </p>
              <Button
                className="secondary"
                disabled={busy}
                onClick={() =>
                  void run(() =>
                    api(
                      `/sessions/${session.id}/teacher`,
                      json("POST", { provider: "openai", model, question }),
                    ),
                  )
                }
              >
                Send analysis evidence to OpenAI
              </Button>
            </div>
          </div>
        )}
        {reports.map((r) => (
          <article className="report" key={r.id}>
            <span className="eyebrow">
              {r.provider} · {new Date(r.created).toLocaleString()}
            </span>
            <div className="report-text">{r.text}</div>
            <Button
              className="secondary"
              onClick={() => setReportEdit({ id: r.id, text: r.text })}
            >
              Edit a new report revision
            </Button>
            <a className="button secondary" href={`/api/reports/${r.id}/text`}>
              Export report
            </a>
          </article>
        ))}
      </div>
      {reportEdit && (
        <div className="chart-panel">
          <label>
            Edit report
            <textarea
              rows={10}
              value={reportEdit.text}
              onChange={(e) =>
                setReportEdit({ ...reportEdit, text: e.target.value })
              }
            />
          </label>
          <Button
            className="primary"
            disabled={busy}
            onClick={() =>
              void run(async () => {
                await api(
                  `/reports/${reportEdit.id}/revision`,
                  json("POST", { text: reportEdit.text }),
                );
                setReportEdit(null);
              })
            }
          >
            Save new report revision
          </Button>
        </div>
      )}
      <div className="jobs-list" aria-label="Background jobs">
        {jobs
          .filter((j) => ["queued", "running", "failed"].includes(j.status))
          .slice(0, 6)
          .map((j) => (
            <div className="job-row" key={j.id}>
              <span>
                {j.kind} · {j.status}
                {j.error ? " · " + j.error : ""}
              </span>
              {["queued", "running"].includes(j.status) && (
                <Button
                  className="secondary"
                  onClick={() =>
                    void run(() =>
                      api(`/jobs/${j.id}/cancel`, { method: "POST" }),
                    )
                  }
                >
                  Cancel job
                </Button>
              )}
            </div>
          ))}
      </div>
    </div>
  );
}
