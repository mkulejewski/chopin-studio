import type { OpenSheetMusicDisplay } from "opensheetmusicdisplay";
import { useEffect, useRef, useState } from "react";
import type { ComparisonMode } from "./comparisonJudgement";
import { buildComparisonMusicXml, type ScoreView } from "./comparisonScore";
import { TouchButton as Button } from "./TouchButton";
import type { NoteGroup } from "./types/analysis";

export function ScoreComparison({
  groups,
  allGroups,
  mode,
  title,
  fifths = 0,
}: {
  groups: NoteGroup[];
  allGroups: NoteGroup[];
  mode: ComparisonMode;
  title: string;
  fifths?: number;
}) {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<ScoreView>("overlay");
  const [zoom, setZoom] = useState(0.9);
  const [status, setStatus] = useState("");
  const [width, setWidth] = useState(760);
  const frame = useRef<HTMLDivElement>(null);
  const target = useRef<HTMLDivElement>(null);
  const [downloadUrl, setDownloadUrl] = useState("");
  const [exporting, setExporting] = useState(false);
  const [exportStatus, setExportStatus] = useState("");
  const exportController = useRef<AbortController | null>(null);
  useEffect(
    () => () => {
      exportController.current?.abort();
      exportController.current = null;
    },
    [],
  );
  const exportPdf = async () => {
    const controller = new AbortController();
    exportController.current = controller;
    setExporting(true);
    setExportStatus("Preparing full comparison PDF…");
    try {
      const { compileComparisonPdf } = await import("./comparisonPdf");
      const { blob, pages } = await compileComparisonPdf({
        groups: allGroups,
        view,
        mode,
        title,
        fifths,
        signal: controller.signal,
        onProgress: (text) => {
          if (exportController.current === controller) setExportStatus(text);
        },
      });
      controller.signal.throwIfAborted();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${title.replace(/[^a-zA-Z0-9_-]+/g, "-").slice(0, 90)}-${mode}-${view}.pdf`;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setExportStatus(
        `Downloaded full comparison PDF · ${pages} ${pages === 1 ? "page" : "pages"}.`,
      );
    } catch (error) {
      if (!controller.signal.aborted)
        setExportStatus(
          `PDF export failed: ${error instanceof Error ? error.message : String(error)}`,
        );
    } finally {
      if (exportController.current === controller) {
        exportController.current = null;
        setExporting(false);
      }
    }
  };
  // Identical polling results must not trigger repeated engravings.
  const signature = JSON.stringify(groups);
  const [xml, setXml] = useState("");
  useEffect(() => {
    if (!open) return;
    try {
      setXml(
        buildComparisonMusicXml(JSON.parse(signature), view, mode, fifths),
      );
    } catch {
      setXml("");
      setStatus(
        "This passage cannot be notated. The piano roll and discrepancy list remain available.",
      );
    }
  }, [signature, view, open, mode, fifths]);
  useEffect(() => {
    if (!xml) return;
    const url = URL.createObjectURL(
      new Blob([xml], { type: "application/vnd.recordare.musicxml+xml" }),
    );
    setDownloadUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [xml]);
  useEffect(() => {
    if (!open || !frame.current) return;
    const observer = new ResizeObserver(([entry]) =>
      setWidth(Math.max(760, Math.round(entry.contentRect.width))),
    );
    observer.observe(frame.current);
    return () => observer.disconnect();
  }, [open]);
  useEffect(() => {
    if (!open || !xml) return;
    let cancelled = false;
    let display: OpenSheetMusicDisplay | undefined;
    setStatus("Engraving comparison…");
    const render = async () => {
      try {
        const { OpenSheetMusicDisplay } = await import("opensheetmusicdisplay");
        if (cancelled || !target.current) return;
        // Each render owns its own detached child until load completes. An old
        // asynchronous load must never clear or commit over a newer score.
        const container = document.createElement("div");
        container.style.width = `${width}px`;
        display = new OpenSheetMusicDisplay(container, {
          backend: "svg",
          autoResize: false,
          drawingParameters: "compacttight",
          drawTitle: false,
          drawComposer: false,
          drawPartNames: view === "stacked",
          coloringEnabled: true,
          colorStemsLikeNoteheads: true,
          autoBeam: false,
          drawMeasureNumbers: true,
          drawMeasureNumbersOnlyAtSystemStart: false,
          useXMLMeasureNumbers: true,
          drawTimeSignatures: false,
        });
        display.EngravingRules.SetWantedStemDirectionByXml = true;
        display.Zoom = zoom;
        await display.load(xml);
        if (cancelled || !target.current) return;
        target.current.replaceChildren(container);
        display.render();
        setStatus("Score comparison ready.");
      } catch {
        if (!cancelled) {
          target.current?.replaceChildren();
          setStatus(
            "Notation could not be rendered. Try another passage or use the piano roll below.",
          );
        }
      }
    };
    void render();
    return () => {
      cancelled = true;
      display?.clear();
    };
  }, [open, xml, zoom, width, view]);
  return (
    <section className="score-comparison" aria-label="Staff score comparison">
      <h3>Staff score comparison</h3>
      <p>
        Compare the reference and your aligned pitches as staff notation, with
        colour-coded pitch differences.
      </p>
      <Button
        className="secondary"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        {open ? "Hide staff comparison" : "Render score comparison"}
      </Button>
      {open && (
        <>
          <p className="muted">
            Your pitches are placed on the reference beats and note lengths so
            both layers align. This is a pitch comparison, not a transcription
            of your rhythm. Source key signatures and note spelling are retained
            when available; other spellings follow the piece's key. Voices are
            regenerated; rests, grace notes and engraving may differ from the
            source edition. Durations are rounded to conventional note values;
            meter is omitted. Only the current page of note groups is shown.
          </p>
          {!groups.every((g) => g.score_notes?.length) && (
            <p className="muted">
              This older analysis has no source note lengths. Note lengths are
              estimated from score onset spacing; analyse this activity again to
              include the reference durations.
            </p>
          )}
          <div className="button-row">
            <label>
              Score comparison layout
              <select
                value={view}
                onChange={(e) => setView(e.target.value as ScoreView)}
              >
                <option value="overlay">Overlay on the same staves</option>
                <option value="stacked">Reference above played</option>
                <option value="reference">Reference only</option>
                <option value="played">Played notes only</option>
              </select>
            </label>
            <Button
              className="secondary"
              aria-label="Zoom comparison score out"
              disabled={zoom <= 0.5}
              onClick={() => setZoom((z) => Math.max(0.5, z - 0.1))}
            >
              −
            </Button>
            <Button
              className="secondary"
              aria-label="Zoom comparison score in"
              disabled={zoom >= 1.4}
              onClick={() => setZoom((z) => Math.min(1.4, z + 0.1))}
            >
              +
            </Button>
            {downloadUrl && (
              <a
                className="button secondary"
                href={downloadUrl}
                download={`pitch-comparison-${view}.musicxml`}
              >
                Download comparison MusicXML
              </a>
            )}
          </div>
          <div className="button-row">
            <Button
              className="secondary"
              disabled={exporting}
              onClick={() => void exportPdf()}
            >
              Download full comparison PDF
            </Button>
            {exporting && (
              <Button
                className="secondary"
                onClick={() => {
                  exportController.current?.abort();
                  exportController.current = null;
                  setExporting(false);
                  setExportStatus("PDF export cancelled.");
                }}
              >
                Cancel PDF export
              </Button>
            )}
          </div>
          <p className="muted">
            PDF includes all {allGroups.length} note groups in this activity,
            using the selected layout and comparison method, including measures
            hidden by the screen filter.
          </p>
          {!!exportStatus && (
            <p className="pdf-export-status" aria-live="polite">
              {exportStatus}
            </p>
          )}
          <div className="note-legend">
            <span>Reference: grey, stems up · played: dark, stems down</span>
            <span className="score-error">
              Red:{" "}
              {mode === "strict"
                ? "strict reference differences"
                : "likely pitch/chord errors"}
            </span>
            {mode === "musical" && (
              <span className="score-review">
                Blue: adaptation or uncertainty
              </span>
            )}
            <span>◆ Expected but absent · × Extra played pitch</span>
          </div>
          <p role="status">{status}</p>
          <div ref={frame} className="staff-comparison-scroll">
            <div
              ref={target}
              role="img"
              aria-label="Compiled reference and played note comparison"
            />
          </div>
        </>
      )}
    </section>
  );
}
