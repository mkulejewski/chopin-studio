import { useEffect, useState } from "react";
import { api, json, type Piece, type Settings } from "./api";
import { TouchButton as Button } from "./TouchButton";
export function LivePanel({
  pieces,
  settings,
  onSettings,
  onChoose,
  onPage,
  onError,
}: {
  pieces: Piece[];
  settings: Settings;
  onSettings: (s: Settings) => void;
  onChoose: (p: Piece) => void;
  onPage: (command: any) => void;
  onError: (e: unknown) => void;
}) {
  const [live, setLive] = useState<any>(null),
    [open, setOpen] = useState(false);
  useEffect(() => {
    if (!settings.live_enabled) {
      setLive(null);
      return;
    }
    let previous = 0;
    const poll = async () => {
      try {
        const value = await api("/live");
        setLive(value);
        if (value.page_request && value.page_request.id > previous) {
          previous = value.page_request.id;
          onPage({ action: "go", ...value.page_request });
        }
      } catch (e) {
        onError(e);
      }
    };
    void poll();
    const timer = setInterval(poll, 1100);
    return () => clearInterval(timer);
  }, [settings.live_enabled, settings.live_auto_turn, settings.live_piece_id]);
  const save = async (s: Settings) => {
    const previous = settings;
    onSettings(s);
    try {
      await api("/settings", json("PUT", s));
    } catch (e) {
      onSettings(previous);
      onError(e);
    }
  };
  const recognised = pieces.find((p) => p.id === live?.piece_id);
  return (
    <div className="live-panel">
      <div className="live-summary">
        <span>
          {settings.live_enabled ? (
            <>
              <strong>Live recognition · experimental</strong>{" "}
              {recognised
                ? recognised.catalogue_path
                : live?.label || "Listening for a phrase…"}
              {live?.stable && live?.measure != null
                ? ` · measure ${live.measure}`
                : ""}
              {live?.confidence
                ? ` · similarity ${live.confidence.toFixed(2)}`
                : ""}
            </>
          ) : (
            "Live recognition & score following are off"
          )}
        </span>
        <Button className="secondary" onClick={() => setOpen(!open)}>
          Live controls
        </Button>
        {recognised && (
          <Button className="secondary" onClick={() => onChoose(recognised)}>
            Open recognised piece
          </Button>
        )}
      </div>
      {open && (
        <div className="live-options">
          <label className="toggle-row">
            Enable live piece recognition
            <input
              type="checkbox"
              checked={!!settings.live_enabled}
              onChange={(e) =>
                void save({ ...settings, live_enabled: e.target.checked })
              }
            />
          </label>
          <label>
            Manual following override
            <select
              value={settings.live_piece_id || ""}
              onChange={(e) =>
                void save({
                  ...settings,
                  live_piece_id: e.target.value || null,
                })
              }
            >
              <option value="">Recognise across available references</option>
              {pieces
                .filter((p) => p.reference_count > 0)
                .map((p) => (
                  <option value={p.id} key={p.id}>
                    {p.catalogue_path}
                  </option>
                ))}
            </select>
          </label>
          <label className="toggle-row">
            Allow confident automatic page turns
            <input
              type="checkbox"
              checked={!!settings.live_auto_turn}
              onChange={(e) =>
                void save({ ...settings, live_auto_turn: e.target.checked })
              }
            />
          </label>
          <p className="muted">
            Requires a verified reference, three consistent matches, and an
            explicit measure/page map. Manual page navigation pauses automatic
            turns for 10 seconds. Unknown material and ambiguous matches do not
            turn pages. Recording remains independent.
          </p>
        </div>
      )}
    </div>
  );
}
