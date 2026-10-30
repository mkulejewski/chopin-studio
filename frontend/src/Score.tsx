import { SymbolicPreview } from "./SymbolicPreview";
import { TouchButton } from "./TouchButton";
import { useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import type { PDFDocumentProxy } from "pdfjs-dist";
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Minus,
  Plus,
  Scan,
  Columns2,
  Crop,
} from "lucide-react";
import { api, json, type Piece, type Settings, type Volume } from "./api";
pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export function Score({
  piece,
  volume,
  settings,
  onLibrary,
  command,
  onError,
  onToggle,
}: {
  piece: Piece | null;
  volume: Volume | undefined;
  settings: Settings;
  onLibrary: () => void;
  command: {
    id: number;
    action: string;
    page?: number;
    piece_id?: string;
  } | null;
  onError: (e: unknown) => void;
  onToggle: () => void;
}) {
  const [doc, setDoc] = useState<PDFDocumentProxy | null>(null);
  const [page, setPage] = useState(1),
    [zoom, setZoom] = useState(1),
    [two, setTwo] = useState(false),
    [crop, setCrop] = useState(0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [loading, setLoading] = useState(false);
  const [showXml, setShowXml] = useState(false);
  const container = useRef<HTMLDivElement>(null);
  const [viewportSize, setViewportSize] = useState("");
  useEffect(() => {
    const element = container.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      setViewportSize(
        `${Math.round(entry.contentRect.width)},${Math.round(entry.contentRect.height)}`,
      );
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  const canvas = useRef<HTMLCanvasElement>(null),
    canvas2 = useRef<HTMLCanvasElement>(null);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const gesture = useRef({
    x: 0,
    y: 0,
    at: 0,
    distance: 0,
    zoom: 1,
    pan: { x: 0, y: 0 },
    multi: false,
  });
  const lastTap = useRef(0);
  const loaded = useRef("");
  const end = Math.min(
    piece?.end_page || doc?.numPages || 1,
    doc?.numPages || 1,
  );
  const start = piece?.start_page || 1;
  const lastManualTurn = useRef(0);
  const turn = (direction: number) => {
    lastManualTurn.current = Date.now();
    setPage((p) =>
      Math.max(start, Math.min(end, p + direction * (two ? 2 : 1))),
    );
    setPan({ x: 0, y: 0 });
  };
  useEffect(() => {
    setDoc(null);
    setShowXml(false);
    loaded.current = "";
    setPan({ x: 0, y: 0 });
    if (!piece || !volume?.filename) return;
    let cancelled = false;
    const view = JSON.parse(piece.view || "{}");
    setPage(
      Math.max(
        piece.start_page || 1,
        Math.min(
          piece.end_page || volume.pages || 1,
          view.page || piece.start_page || 1,
        ),
      ),
    );
    setZoom(view.zoom || 1);
    setTwo(view.two_pages || false);
    setCrop(view.crop || 0);
    setLoading(true);
    const task = pdfjs.getDocument(`/api/volumes/${volume.id}/pdf`);
    task.promise
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
      void task.destroy();
    };
  }, [piece?.id, volume?.filename]);
  useEffect(() => {
    if (!doc) return;
    let cancelled = false;
    const tasks: pdfjs.RenderTask[] = [];
    const render = async (p: number, element: HTMLCanvasElement | null) => {
      if (!element || p > end) return;
      const pdfPage = await doc.getPage(p);
      if (cancelled) return;
      const viewport = pdfPage.getViewport({ scale: 1 });
      const box = container.current?.getBoundingClientRect();
      const width = ((box?.width || 900) - 64) / (two ? 2 : 1),
        height = (box?.height || 700) - 32;
      const scale =
        Math.min(width / viewport.width, height / viewport.height) *
        Math.min(window.devicePixelRatio || 1, 2);
      const actual = pdfPage.getViewport({ scale });
      element.width = actual.width;
      element.height = actual.height;
      element.style.width = `${actual.width / Math.min(window.devicePixelRatio || 1, 2)}px`;
      element.style.height = `${actual.height / Math.min(window.devicePixelRatio || 1, 2)}px`;
      const task = pdfPage.render({
        canvasContext: element.getContext("2d")!,
        viewport: actual,
      });
      tasks.push(task);
      await task.promise;
    };
    Promise.all([
      render(page, canvas.current),
      two ? render(page + 1, canvas2.current) : Promise.resolve(),
    ]).catch((e) => {
      if (e.name !== "RenderingCancelledException") onError(e);
    });
    return () => {
      cancelled = true;
      tasks.forEach((t) => t.cancel());
    };
  }, [doc, page, two, end, viewportSize]);
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
    if (!command) return;
    if (
      command.action === "go" &&
      command.piece_id === piece?.id &&
      command.page &&
      Date.now() - lastManualTurn.current > 10000
    ) {
      setPage(Math.max(start, Math.min(end, command.page)));
      setPan({ x: 0, y: 0 });
    } else if (command.action === "next") turn(1);
    else if (command.action === "previous") turn(-1);
  }, [command?.id]);
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
  const down = (e: React.PointerEvent) => {
    if (!doc) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.current.size === 1)
      gesture.current = {
        x: e.clientX,
        y: e.clientY,
        at: Date.now(),
        distance: 0,
        zoom,
        pan,
        multi: false,
      };
    if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()];
      gesture.current.distance = Math.hypot(a.x - b.x, a.y - b.y);
      gesture.current.zoom = zoom;
      gesture.current.multi = true;
    }
  };
  const move = (e: React.PointerEvent) => {
    if (!pointers.current.has(e.pointerId)) return;
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.current.size === 2 && settings.pinch) {
      const [a, b] = [...pointers.current.values()];
      setZoom(
        Math.max(
          0.5,
          Math.min(
            4,
            (gesture.current.zoom * Math.hypot(a.x - b.x, a.y - b.y)) /
              Math.max(gesture.current.distance, 1),
          ),
        ),
      );
    } else if (
      pointers.current.size === 1 &&
      zoom > 1.05 &&
      !gesture.current.multi
    )
      setPan({
        x: gesture.current.pan.x + e.clientX - gesture.current.x,
        y: gesture.current.pan.y + e.clientY - gesture.current.y,
      });
  };
  const up = (e: React.PointerEvent) => {
    const g = gesture.current;
    const dx = e.clientX - g.x,
      dy = e.clientY - g.y;
    pointers.current.delete(e.pointerId);
    if (g.multi) return;
    if (
      zoom <= 1.05 &&
      settings.swipe &&
      Math.abs(dx) > 75 &&
      Math.abs(dx) > Math.abs(dy) * 1.8 &&
      Date.now() - g.at < 900
    )
      turn(dx < 0 ? 1 : -1);
    else if (Math.hypot(dx, dy) < 14) {
      if (Date.now() - lastTap.current < 320 && settings.double_tap) {
        setZoom((z) => (z > 1.05 ? 1 : 1.5));
        setPan({ x: 0, y: 0 });
        lastTap.current = 0;
      } else {
        lastTap.current = Date.now();
        if (settings.tap_overlay) onToggle();
      }
    }
  };
  return (
    <div className="score-shell">
      <div
        className={`score-stage ${showXml ? "xml-stage" : ""}`}
        ref={container}
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={up}
        onPointerCancel={(e) => {
          pointers.current.delete(e.pointerId);
          gesture.current.multi = true;
        }}
      >
        {showXml && piece ? (
          <SymbolicPreview pieceId={piece.id} onError={onError} />
        ) : doc ? (
          <div
            className="paper-pair"
            style={{
              transform: `translate(${pan.x}px,${pan.y}px) scale(${zoom})`,
              clipPath: crop ? `inset(${crop * 100}%)` : undefined,
            }}
          >
            <canvas ref={canvas} aria-label={`Score PDF page ${page}`} />
            {two && page < end && (
              <canvas ref={canvas2} aria-label={`Score PDF page ${page + 1}`} />
            )}
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
            {piece?.reference_count ? (
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
      <div className="score-tools">
        <div className="tool-group">
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
          <TouchButton
            aria-label="Next page"
            disabled={!doc || page >= end}
            onClick={() => turn(1)}
          >
            <ChevronRight />
          </TouchButton>
        </div>
        <div className="tool-group">
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
          </TouchButton>
          <TouchButton
            aria-label="Two-page view"
            className={two ? "selected" : ""}
            disabled={!doc}
            onClick={() => setTwo(!two)}
          >
            <Columns2 size={19} />
          </TouchButton>
          <TouchButton
            aria-label="Crop margins"
            className={crop ? "selected" : ""}
            disabled={!doc}
            onClick={() => setCrop((c) => (c ? 0 : 0.05))}
          >
            <Crop size={19} />
          </TouchButton>
        </div>
      </div>
    </div>
  );
}
