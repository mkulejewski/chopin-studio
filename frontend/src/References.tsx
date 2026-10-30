import { SymbolicPreview } from "./SymbolicPreview";
import { useEffect, useRef, useState } from "react";
import { api, json, upload, type Piece } from "./api";
import { TouchButton as Button } from "./TouchButton";
export function References({
  pieces,
  onError,
  onChanged,
}: {
  pieces: Piece[];
  onError: (error: unknown) => void;
  onChanged: () => Promise<unknown>;
}) {
  const [piece, setPiece] = useState("n9-1"),
    [refs, setRefs] = useState<any[]>([]),
    [current, setCurrent] = useState<any>(null),
    [measure, setMeasure] = useState(1),
    [mapping, setMapping] = useState<any[]>([]),
    [mapMeasure, setMapMeasure] = useState(1),
    [mapPage, setMapPage] = useState(1),
    [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState(false);
  const load = async () => {
    setRefs(await api(`/pieces/${piece}/references`));
    setMapping(await api(`/pieces/${piece}/pages`));
  };
  useEffect(() => {
    setCurrent(null);
    void load().catch(onError);
  }, [piece]);
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await load();
      await onChanged();
    } catch (e) {
      onError(e);
    } finally {
      setBusy(false);
    }
  };
  const editNote = (index: number, field: string, value: unknown) =>
    setCurrent((ref: any) => ({
      ...ref,
      notes: ref.notes.map((n: any, i: number) =>
        i === index ? { ...n, [field]: value } : n,
      ),
    }));
  return (
    <div className="chart-panel reference-manager">
      <h2>Machine references & page maps</h2>
      <p>
        MusicXML supports analysis and live recognition. First-edition
        conversions are provisional and may differ from your Paderewski or
        Schott score. Verify notes, ornament treatment, repeats and measure
        structure before marking a reference verified.
      </p>
      <label>
        Reference piece
        <select
          aria-label="Reference piece"
          value={piece}
          onChange={(e) => setPiece(e.target.value)}
        >
          {pieces.map((p) => (
            <option value={p.id} key={p.id}>
              {p.catalogue_path}
            </option>
          ))}
        </select>
      </label>
      <div className="button-row">
        <Button
          className="secondary"
          disabled={busy}
          onClick={() => input.current?.click()}
        >
          Import MusicXML / MXL
        </Button>
        <a
          className="button secondary"
          href={`/api/pieces/${piece}/references`}
          target="_blank"
          rel="noreferrer"
        >
          Reference metadata
        </a>
      </div>
      <input
        ref={input}
        hidden
        type="file"
        accept=".xml,.musicxml,.mxl"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void run(() => upload(`/pieces/${piece}/references`, file));
          e.target.value = "";
        }}
      />
      {!refs.length && (
        <p>
          No symbolic reference attached yet. A PDF alone cannot provide
          note-level analysis.
        </p>
      )}
      {refs.map((r) => (
        <div className="reference-row" key={r.id}>
          <div>
            <strong>
              {r.quality} · {r.edition}
            </strong>
            <p>{r.licence}</p>
            <a
              href={r.source.startsWith("http") ? r.source : undefined}
              target="_blank"
              rel="noreferrer"
            >
              {r.source}
            </a>
          </div>
          <Button
            className="secondary"
            disabled={busy}
            onClick={() =>
              void run(async () => {
                const ref = await api(`/references/${r.id}`);
                setCurrent(ref);
                setMeasure(ref.notes[0]?.measure || 1);
              })
            }
          >
            Review reference
          </Button>
          {r.filename.endsWith(".musicxml") && (
            <a
              className="button secondary"
              href={`/api/references/${r.id}/musicxml`}
            >
              Download source MusicXML
            </a>
          )}
        </div>
      ))}
      {current && (
        <div className="reference-editor">
          <h3>Reference verification</h3>
          {current.filename.endsWith(".musicxml") && (
            <Button className="secondary" onClick={() => setPreview(!preview)}>
              Preview symbolic score
            </Button>
          )}
          {preview && (
            <SymbolicPreview referenceId={current.id} onError={onError} />
          )}
          <label>
            Edition and review note
            <input
              value={current.edition}
              onChange={(e) =>
                setCurrent({ ...current, edition: e.target.value })
              }
            />
          </label>
          <label>
            Show measure
            <input
              type="number"
              min="0"
              value={measure}
              onChange={(e) => setMeasure(Number(e.target.value))}
            />
          </label>
          <p className="muted">
            Editable analysis representation. Source MusicXML download remains
            immutable; corrected note data and prior revisions are retained
            locally. Timing below is in score quarter-note units.
          </p>
          <div className="note-editor">
            {current.notes
              .map((n: any, i: number) => ({ n, i }))
              .filter(({ n }: any) => n.measure === measure)
              .slice(0, 120)
              .map(({ n, i }: any) => (
                <div className="note-editor-row" key={i}>
                  <label>
                    MIDI pitch
                    <input
                      aria-label={`Reference pitch ${i}`}
                      type="number"
                      min="0"
                      max="127"
                      value={n.pitch}
                      onChange={(e) =>
                        editNote(i, "pitch", Number(e.target.value))
                      }
                    />
                  </label>
                  <label>
                    Onset
                    <input
                      type="number"
                      min="0"
                      step=".125"
                      value={n.onset}
                      onChange={(e) =>
                        editNote(i, "onset", Number(e.target.value))
                      }
                    />
                  </label>
                  <label>
                    Duration
                    <input
                      type="number"
                      min="0"
                      step=".125"
                      value={n.duration}
                      onChange={(e) =>
                        editNote(i, "duration", Number(e.target.value))
                      }
                    />
                  </label>
                  <label>
                    Measure
                    <input
                      type="number"
                      min="0"
                      value={n.measure}
                      onChange={(e) =>
                        editNote(i, "measure", Number(e.target.value))
                      }
                    />
                  </label>
                  <label className="toggle-row">
                    Grace
                    <input
                      type="checkbox"
                      checked={!!n.grace}
                      onChange={(e) => editNote(i, "grace", e.target.checked)}
                    />
                  </label>
                </div>
              ))}
          </div>
          <label>
            Quality status
            <select
              value={current.quality}
              onChange={(e) =>
                setCurrent({ ...current, quality: e.target.value })
              }
            >
              <option value="provisional">Provisional — not yet checked</option>
              <option value="verified">
                Verified — I checked against my edition
              </option>
              <option value="rejected">
                Rejected — exclude from recognition
              </option>
            </select>
          </label>
          <div className="button-row">
            <Button
              className="primary"
              disabled={busy}
              onClick={() =>
                void run(() =>
                  api(
                    `/references/${current.id}`,
                    json("PUT", {
                      edition: current.edition,
                      quality: current.quality,
                      notes: current.notes,
                    }),
                  ),
                )
              }
            >
              Save reference review
            </Button>
            <Button className="secondary" onClick={() => setCurrent(null)}>
              Close review
            </Button>
          </div>
        </div>
      )}
      <h3>Measure-to-PDF-page map</h3>
      <p>
        Required for safe automatic page turns. Enter the first measure on each
        PDF page. Pages are 1-based and include covers; no pagination is guessed
        from MusicXML.
      </p>
      <div className="form-grid">
        <label>
          First measure on page
          <input
            type="number"
            min="0"
            value={mapMeasure}
            onChange={(e) => setMapMeasure(Number(e.target.value))}
          />
        </label>
        <label>
          PDF page
          <input
            type="number"
            min="1"
            value={mapPage}
            onChange={(e) => setMapPage(Number(e.target.value))}
          />
        </label>
      </div>
      <div className="button-row">
        <Button
          className="secondary"
          onClick={() =>
            setMapping((m) =>
              [
                ...m.filter((p) => p.measure !== mapMeasure),
                { measure: mapMeasure, pdf_page: mapPage },
              ].sort((a, b) => a.measure - b.measure),
            )
          }
        >
          Add / update page link
        </Button>
        <Button
          className="primary"
          disabled={busy}
          onClick={() =>
            void run(() =>
              api(
                `/pieces/${piece}/pages`,
                json(
                  "PUT",
                  mapping.map(({ measure, pdf_page }) => ({
                    measure,
                    pdf_page,
                  })),
                ),
              ),
            )
          }
        >
          Save page map
        </Button>
      </div>
      {mapping.map((m) => (
        <div className="map-row" key={m.measure}>
          <span>
            Measure {m.measure} → PDF page {m.pdf_page}
          </span>
          <Button
            className="secondary"
            onClick={() =>
              setMapping((rows) => rows.filter((r) => r.measure !== m.measure))
            }
          >
            Remove link
          </Button>
        </div>
      ))}
    </div>
  );
}
