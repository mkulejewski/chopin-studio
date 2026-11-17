import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  Columns2,
  Crop,
  Maximize,
  Minimize,
  Minus,
  Plus,
  Scan,
  X,
} from "lucide-react";
import type { PDFDocumentProxy } from "pdfjs-dist";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";
import { api, json, type Piece, type Settings, type Volume } from "./api";
import { retainScore } from "./pdfCache";
import { PdfRenderer } from "./pdfRenderer";
import { usePageFollowing } from "./score/usePageFollowing";
import { useScoreFullscreen } from "./score/useScoreFullscreen";
import { useScoreGestures } from "./score/useScoreGestures";
import { SymbolicPreview } from "./SymbolicPreview";
import { TouchButton } from "./TouchButton";

export function Score({
  learningMode = false,
  fullscreenTarget,
  controlsHost,
  concealed = false,
  concealedContent,
  requestedPage,
  piece,
  volume,
  settings,
  onLibrary,
  onClear,
  onFullscreenHost,
  fullscreenControls,
  onAutoTurnChange,
  command,
  automaticCommand,
  onError,
  onToggle,
}: {
  learningMode?: boolean;
  fullscreenTarget?: RefObject<HTMLDivElement | null>;
  controlsHost?: HTMLElement | null;
  concealed?: boolean;
  concealedContent?: ReactNode;
  requestedPage?: number;
  piece: Piece | null;
  volume: Volume | undefined;
  settings: Settings;
  onLibrary: () => void;
  onClear: () => void;
  onFullscreenHost?: (element: HTMLElement | null) => void;
  fullscreenControls?: ReactNode;
  onAutoTurnChange: (enabled: boolean) => Promise<void>;
  command: {
    id: number;
    action: string;
    page?: number;
    piece_id?: string;
    actions?: { action: string }[];
  } | null;
  automaticCommand: {
    id: number;
    action: string;
    page?: number;
    piece_id?: string;
  } | null;
  onError: (e: unknown) => void;
  onToggle: () => void;
}) {
  const shell = useRef<HTMLDivElement>(null);
  const pageMarginX = learningMode ? 16 : 64;
  const pageMarginY = learningMode ? 16 : 32;
  const [savingTurns, setSavingTurns] = useState(false);
  const { scoreFull, scoreFullscreen } = useScoreFullscreen(
    shell,
    fullscreenTarget,
    onFullscreenHost,
    onError,
  );
  const [doc, setDoc] = useState<PDFDocumentProxy | null>(null);
  const [page, setPage] = useState(1),
    [zoom, setZoom] = useState(1),
    [two, setTwo] = useState(false),
    [crop, setCrop] = useState(0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [loading, setLoading] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [renderError, setRenderError] = useState("");
  const [retry, setRetry] = useState(0);
  const [presented, setPresented] = useState<{
    page: number;
    two: boolean;
  } | null>(null);
  const renderer = useMemo(() => (doc ? new PdfRenderer(doc) : null), [doc]);
  useEffect(() => () => renderer?.dispose(), [renderer]);
  const [showXml, setShowXml] = useState(false);
  const [calibrating, setCalibrating] = useState(false),
    [mapMeasure, setMapMeasure] = useState(1),
    [mapSaving, setMapSaving] = useState(false),
    [mapNotice, setMapNotice] = useState("");
  const savePageLink = async () => {
    if (
      !piece ||
      rendering ||
      renderError ||
      presented?.page !== page ||
      !Number.isInteger(mapMeasure) ||
      mapMeasure < 0
    )
      return;
    setMapSaving(true);
    try {
      const mapping = await api<{ measure: number; pdf_page: number }[]>(
        `/pieces/${piece.id}/pages`,
      );
      // Preserve all other page links; replace this page's former calibration.
      const next = mapping.filter(
        (m) => m.pdf_page !== page && m.measure !== mapMeasure,
      );
      next.push({ measure: mapMeasure, pdf_page: page });
      await api(
        `/pieces/${piece.id}/pages`,
        json(
          "PUT",
          next.map(({ measure, pdf_page }) => ({ measure, pdf_page })),
        ),
      );
      setMapNotice(`Saved: measure ${mapMeasure} starts PDF page ${page}.`);
    } catch (e) {
      onError(e);
    } finally {
      setMapSaving(false);
    }
  };
  const container = useRef<HTMLDivElement>(null);
  // Resize the already displayed bitmap synchronously; PDF rasterisation can
  // finish later without making fullscreen wait for a new high-resolution page.
  const fitCanvases = () => {
    const box = container.current?.getBoundingClientRect();
    if (!box) return;
    const elements = [canvas.current, canvas2.current].filter(
      (element): element is HTMLCanvasElement => !!element && !element.hidden,
    );
    for (const element of elements) {
      const aspect =
        Number(element.dataset.aspect) || element.width / element.height;
      const height = Math.min(
        Math.max(1, box.width - pageMarginX) / elements.length / aspect,
        Math.max(1, box.height - pageMarginY),
      );
      element.style.width = `${aspect * height}px`;
      element.style.height = `${height}px`;
    }
  };
  const [viewportSize, setViewportSize] = useState("");
  useEffect(() => {
    const element = container.current;
    if (!element) return;
    let timer: ReturnType<typeof setTimeout>;
    const observer = new ResizeObserver(([entry]) => {
      fitCanvases();
      clearTimeout(timer);
      const size = `${Math.round(entry.contentRect.width)},${Math.round(entry.contentRect.height)}`;
      timer = setTimeout(() => setViewportSize(size), 120);
    });
    observer.observe(element);
    return () => {
      clearTimeout(timer);
      observer.disconnect();
    };
  }, []);
  const canvas = useRef<HTMLCanvasElement>(null),
    canvas2 = useRef<HTMLCanvasElement>(null);
  const loaded = useRef("");
  const end = Math.min(
    piece?.end_page || doc?.numPages || 1,
    doc?.numPages || 1,
  );
  const start = piece?.start_page || 1;
  const lastManualTurn = useRef(0);
  const turn = (direction: number) => {
    lastManualTurn.current = Date.now();
    setPage((p) => Math.max(start, Math.min(end, p + direction)));
    setPan({ x: 0, y: 0 });
  };
  useEffect(() => {
    setDoc(null);
    setPresented(null);
    setRenderError("");
    setCalibrating(false);
    setMapNotice("");
    setShowXml(false);
    loaded.current = "";
    setPan({ x: 0, y: 0 });
    setLoading(false);
    if (!piece || !volume?.filename) return;
    let cancelled = false;
    const view = JSON.parse(piece.view || "{}");
    setPage(
      Math.max(
        piece.start_page || 1,
        Math.min(
          piece.end_page || volume.pages || 1,
          learningMode
            ? view.page || piece.start_page || 1
            : piece.start_page || 1,
        ),
      ),
    );
    setZoom(view.zoom || 1);
    setTwo(view.two_pages || false);
    setCrop(view.crop || 0);
    setLoading(true);
    const retained = retainScore(volume.id, volume.filename);
    retained.promise
      .then((d) => {
        if (!cancelled) {
          setDoc(d);
          loaded.current = piece.id;
        }
      })
      .catch((e) => {
        if (!cancelled) onError(e);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      retained.release();
      // Shared document stays warm across navigation.
    };
  }, [piece?.id, volume?.filename]);
  useEffect(() => {
    if (requestedPage === undefined) return;
    setPage(Math.max(start, Math.min(end, requestedPage)));
    setPan({ x: 0, y: 0 });
  }, [requestedPage, start, end]);
  useEffect(() => {
    if (concealed) setPresented(null);
  }, [concealed]);
  useEffect(() => {
    // Warm the assigned pages even during hidden recall. PdfRenderer paints
    // detached canvases; the score stays absent from the recall DOM.
    if (!renderer || showXml) return;
    const box = container.current?.getBoundingClientRect();
    if (!box || box.width <= 64 || box.height <= 32) return;
    setRendering(true);
    setRenderError("");
    return renderer.request(
      page,
      end,
      two,
      Math.floor((box.width - pageMarginX) / (two ? 2 : 1)),
      Math.floor(box.height - pageMarginY),
      window.devicePixelRatio || 1,
      ({ page: renderedPage, images }) => {
        if (concealed) {
          setRendering(false);
          return;
        }
        // Commit both completed pages in one browser task. Never draw a PDF
        // directly onto a visible canvas or clear the previous spread early.
        images.forEach((image, i) => {
          const element = i === 0 ? canvas.current : canvas2.current;
          if (!element) return;
          element.width = image.width;
          element.height = image.height;
          // Use PDF proportions rather than rounded raster dimensions, keeping
          // geometry identical when the sharper bitmap replaces the preview.
          element.dataset.aspect = String(
            parseFloat(image.style.width) / parseFloat(image.style.height),
          );
          element.hidden = false;
          element.getContext("2d")!.drawImage(image, 0, 0);
        });
        if (canvas2.current) canvas2.current.hidden = images.length !== 2;
        fitCanvases();
        setPresented({ page: renderedPage, two: images.length === 2 });
        setRendering(false);
      },
      (error) => {
        setRendering(false);
        setRenderError(
          `Could not display page ${page}${two && page < end ? `–${page + 1}` : ""}. ${error instanceof Error ? error.message : String(error)}`,
        );
      },
      start,
    );
  }, [
    renderer,
    page,
    two,
    start,
    end,
    viewportSize,
    showXml,
    retry,
    concealed,
  ]);
  useEffect(() => {
    if (!piece || loaded.current !== piece.id) return;
    const timer = setTimeout(() => {
      void api(
        `/pieces/${piece.id}/view`,
        json("PUT", { page, zoom, two_pages: two, crop }),
      ).catch(onError);
    }, 500);
    return () => clearTimeout(timer);
  }, [piece?.id, page, zoom, two, crop]);
  useEffect(() => {
    if (!command || command.action === "go") return;
    for (const item of command.actions || [command]) {
      if (item.action === "next") turn(1);
      else if (item.action === "previous") turn(-1);
      else if (item.action === "toggle_two") setTwo((value) => !value);
    }
  }, [command?.id]);
  usePageFollowing({
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
  });
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (
        ["INPUT", "TEXTAREA", "SELECT"].includes(
          (e.target as HTMLElement).tagName,
        )
      )
        return;
      if (e.key === "ArrowRight") turn(1);
      if (e.key === "ArrowLeft") turn(-1);
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [start, end, two]);
  const { down, move, up, cancel } = useScoreGestures({
    enabled: !!doc,
    zoom,
    pan,
    settings,
    setZoom,
    setPan,
    turn,
    onToggle,
  });
  const scoreTools = (
    <div className="score-tools">
      {scoreFull && fullscreenControls}
      <div className="tool-group">
        {!learningMode && (
          <TouchButton
            disabled={!doc}
            className={calibrating ? "selected" : ""}
            onClick={() => {
              setCalibrating(!calibrating);
              setMapNotice("");
            }}
          >
            Calibrate page
          </TouchButton>
        )}
        <TouchButton
          aria-label="First score page"
          title="Go to the first page of the current piece"
          disabled={!doc || page <= start}
          onClick={() => {
            lastManualTurn.current = Date.now();
            setPage(start);
            setPan({ x: 0, y: 0 });
          }}
        >
          <ChevronsLeft size={19} />
          {learningMode ? (
            <span className="learning-wide-label">First page</span>
          ) : (
            "First page"
          )}
        </TouchButton>
        <TouchButton
          aria-label="Previous page"
          disabled={!doc || page <= start}
          onClick={() => turn(-1)}
        >
          <ChevronLeft />
        </TouchButton>
        <span>
          {doc
            ? `${page}${two && page < end ? "–" + (page + 1) : ""} / ${end}`
            : "No score open"}
        </span>
        <label className="page-jump">
          {learningMode ? "Page" : "Start page"}
          <input
            aria-label="First displayed page"
            type="number"
            min={start}
            max={end}
            value={page}
            disabled={!doc}
            onChange={(e) => {
              const value = Number(e.target.value);
              if (value >= start && value <= end) {
                lastManualTurn.current = Date.now();
                setPage(value);
                setPan({ x: 0, y: 0 });
              }
            }}
          />
        </label>
        <TouchButton
          aria-label="Next page"
          disabled={!doc || page >= end}
          onClick={() => turn(1)}
        >
          <ChevronRight />
        </TouchButton>
      </div>
      <div className="tool-group">
        {!learningMode && (
          <TouchButton
            aria-label="Automatic page turns"
            aria-pressed={!!settings.live_auto_turn}
            className={settings.live_auto_turn ? "selected" : ""}
            disabled={savingTurns}
            onClick={() => {
              setSavingTurns(true);
              void onAutoTurnChange(!settings.live_auto_turn)
                .catch(onError)
                .finally(() => setSavingTurns(false));
            }}
          >
            Auto turns: {settings.live_auto_turn ? "on" : "off"}
          </TouchButton>
        )}
        <TouchButton
          aria-label="Zoom out"
          disabled={!doc}
          onClick={() => setZoom((z) => Math.max(0.5, z - 0.2))}
        >
          <Minus size={19} />
        </TouchButton>
        <span>{Math.round(zoom * 100)}%</span>
        <TouchButton
          aria-label="Zoom in"
          disabled={!doc}
          onClick={() => setZoom((z) => Math.min(4, z + 0.2))}
        >
          <Plus size={19} />
        </TouchButton>
        <TouchButton
          aria-label="Fit to page"
          disabled={!doc}
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
        >
          <Scan size={19} />
          {learningMode ? (
            <span className="learning-wide-label">Fit page</span>
          ) : (
            "Fit page"
          )}
        </TouchButton>
        <TouchButton
          aria-label={
            scoreFull ? "Exit score fullscreen" : "Enter score fullscreen"
          }
          title="Show only the score and its page controls in fullscreen"
          onClick={scoreFullscreen}
        >
          {scoreFull ? <Minimize size={19} /> : <Maximize size={19} />}
          {learningMode
            ? scoreFull
              ? "Exit"
              : "Fullscreen"
            : scoreFull
              ? "Exit score fullscreen"
              : "Score fullscreen"}
        </TouchButton>
        <TouchButton
          aria-label="Two-page view"
          aria-pressed={two}
          title={two ? "Show one page" : "Show two pages (smaller notation)"}
          className={two ? "selected" : ""}
          disabled={!doc}
          onClick={() => setTwo(!two)}
        >
          <Columns2 size={19} />
          {learningMode && (two ? "Two pages" : "One page")}
        </TouchButton>
        <TouchButton
          aria-label="Crop margins"
          className={crop ? "selected" : ""}
          disabled={!doc}
          onClick={() => setCrop((c) => (c ? 0 : 0.05))}
        >
          <Crop size={19} />
        </TouchButton>
        {!learningMode && piece && (
          <TouchButton
            aria-label="Clear score"
            title="Hide the score and return to free practice"
            onClick={onClear}
          >
            <X size={19} />
            Clear score
          </TouchButton>
        )}
      </div>
    </div>
  );
  return (
    <div className="score-shell" ref={shell}>
      <div
        className={`score-stage ${showXml ? "xml-stage" : ""}`}
        ref={container}
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={up}
        onPointerCancel={cancel}
      >
        {concealed ? (
          concealedContent
        ) : showXml && piece ? (
          <SymbolicPreview pieceId={piece.id} onError={onError} />
        ) : doc ? (
          <div
            className="paper-pair"
            style={{
              transform: `translate(${pan.x}px,${pan.y}px) scale(${zoom})`,
              clipPath: crop ? `inset(${crop * 100}%)` : undefined,
            }}
          >
            <canvas
              ref={canvas}
              hidden={!presented}
              aria-label={
                presented
                  ? `Score PDF page ${presented.page}`
                  : "Loading score page"
              }
            />
            <canvas
              ref={canvas2}
              hidden={!presented?.two}
              aria-label={
                presented?.two
                  ? `Score PDF page ${presented.page + 1}`
                  : "Next score page"
              }
            />
          </div>
        ) : (
          <div className="empty-score">
            <div className="score-monogram">𝄞</div>
            <span className="eyebrow">YOUR SPACE TO PLAY</span>
            <h2>
              {loading
                ? "Opening your score…"
                : piece
                  ? `${piece.title} in ${piece.musical_key}`
                  : "Let the music begin."}
            </h2>
            <p>
              {piece
                ? "Import your own Paderewski PDF to read it here. Recording works with or without a score."
                : "Choose a piece from your library, or simply start recording. No naming. No setup between pieces."}
            </p>
            <TouchButton className="primary" onClick={onLibrary}>
              <BookOpen size={19} />
              Open score library
            </TouchButton>
            {!learningMode && piece?.reference_count ? (
              <TouchButton
                className="secondary"
                onClick={() => setShowXml(true)}
              >
                Read provisional MusicXML
              </TouchButton>
            ) : null}
            <small>Your recordings stay on this computer.</small>
          </div>
        )}
      </div>
      {doc && !showXml && !concealed && (rendering || renderError) && (
        <div
          className="score-render-status"
          role={renderError ? "alert" : "status"}
        >
          {renderError ||
            `Preparing page ${page}${two && page < end ? `–${page + 1}` : ""}…`}
          {renderError && (
            <TouchButton
              className="secondary"
              onClick={() => setRetry((n) => n + 1)}
            >
              Retry pages
            </TouchButton>
          )}
        </div>
      )}
      {!learningMode && calibrating && doc && (
        <div className="page-calibration">
          <label>
            First measure on displayed PDF page {page}
            <input
              aria-label="Page calibration measure"
              type="number"
              min="0"
              step="1"
              value={mapMeasure}
              onChange={(e) => {
                setMapMeasure(Number(e.target.value));
                setMapNotice("");
              }}
            />
          </label>
          <TouchButton
            className="secondary"
            disabled={
              mapSaving ||
              rendering ||
              !!renderError ||
              presented?.page !== page ||
              !Number.isInteger(mapMeasure) ||
              mapMeasure < 0
            }
            onClick={() => void savePageLink()}
          >
            Save this page link
          </TouchButton>
          <small>
            {mapNotice ||
              "Navigate to each page and enter its first measure. PDF pages include covers; use your displayed edition's measure numbers."}
          </small>
        </div>
      )}
      {controlsHost ? createPortal(scoreTools, controlsHost) : scoreTools}
    </div>
  );
}
