import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { TouchButton as Button } from "./TouchButton";
export function SymbolicPreview({
  pieceId,
  referenceId,
  onError,
}: {
  pieceId?: string;
  referenceId?: string;
  onError: (e: unknown) => void;
}) {
  const target = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(0.8),
    [message, setMessage] = useState("Loading symbolic reference…");
  useEffect(() => {
    let cancelled = false;
    let display: any = null;
    const render = async () => {
      try {
        let id = referenceId;
        if (!id) {
          const refs = await api<any[]>(`/pieces/${pieceId}/references`);
          id = refs.find(
            (r) => r.quality !== "rejected" && r.filename.endsWith(".musicxml"),
          )?.id;
        }
        if (!id) {
          setMessage("No MusicXML source is available for this piece.");
          return;
        }
        const response = await fetch(`/api/references/${id}/musicxml`);
        if (!response.ok) throw new Error("MusicXML preview unavailable");
        const xml = await response.text();
        const { OpenSheetMusicDisplay } = await import("opensheetmusicdisplay");
        if (cancelled || !target.current) return;
        target.current.replaceChildren();
        display = new OpenSheetMusicDisplay(target.current, {
          autoResize: true,
          backend: "svg",
          drawingParameters: "compacttight",
        });
        display.Zoom = zoom;
        await display.load(xml);
        if (!cancelled) {
          display.render();
          setMessage(
            "Provisional symbolic edition — compare with your printed score. Source rendering does not include JSON analysis corrections.",
          );
        }
      } catch (e) {
        if (!cancelled) {
          setMessage("Symbolic preview could not be rendered.");
          onError(e);
        }
      }
    };
    void render();
    return () => {
      cancelled = true;
      display?.clear();
    };
  }, [pieceId, referenceId, zoom]);
  return (
    <div className="symbolic-preview">
      <div className="symbolic-toolbar">
        <span>{message}</span>
        <Button
          className="secondary"
          aria-label="Zoom symbolic score out"
          onClick={() => setZoom((z) => Math.max(0.4, z - 0.1))}
        >
          −
        </Button>
        <Button
          className="secondary"
          aria-label="Zoom symbolic score in"
          onClick={() => setZoom((z) => Math.min(1.5, z + 0.1))}
        >
          +
        </Button>
      </div>
      <div ref={target} />
    </div>
  );
}
