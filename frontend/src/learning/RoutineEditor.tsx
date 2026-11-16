import type { Dispatch, SetStateAction } from "react";
import { TouchButton as Button } from "../TouchButton";
import { range } from "./format";
import type { Config, Snapshot } from "./types";

type Props = {
  chunkText: string;
  data: Snapshot;
  run: (
    path: string,
    body?: unknown,
    method?: string,
  ) => Promise<boolean | undefined>;
  setEditing: Dispatch<SetStateAction<boolean>>;
  onError: (error: unknown) => void;
  config: Config;
  setConfig: Dispatch<SetStateAction<Config | null>>;
  setChunkText: Dispatch<SetStateAction<string>>;
  busy: boolean;
};

export function RoutineEditor({
  chunkText,
  data,
  run,
  setEditing,
  onError,
  config,
  setConfig,
  setChunkText,
  busy,
}: Props) {
  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        try {
          const chunks = chunkText.split(",").map((text) => {
            const match = /^\s*(\d+)\s*-\s*(\d+)\s*$/.exec(text);
            if (!match)
              throw new Error("Use comma-separated ranges, such as 0-2, 3-4.");
            const start = Number(match[1]),
              end = Number(match[2]);
            return {
              start,
              end,
              focus:
                data.profile.chunks.find(
                  (c) => c.start <= start && c.end >= start,
                )?.focus ||
                "Study this passage and connect it to the preceding material.",
            };
          });
          if (await run("", { config, chunks }, "PUT")) setEditing(false);
        } catch (error) {
          onError(error);
        }
      }}
    >
      <div className="learning-config">
        {(["visible", "hidden", "connections"] as const).map((key) => (
          <label key={key}>
            {key === "visible"
              ? "Visible repetitions"
              : key === "hidden"
                ? "Hidden repetitions"
                : "Connection repetitions"}
            <input
              type="number"
              min={1}
              max={20}
              required
              value={config[key]}
              onChange={(e) =>
                setConfig({
                  ...config,
                  [key]: Number(e.target.value),
                })
              }
            />
          </label>
        ))}
      </div>
      {!data.automatic_ready && (
        <p>
          Automatic finish and mistake restart await complete digital note
          review. Finish manually and assess your recall against the scan.
        </p>
      )}
      <label className="learning-checkbox">
        <input
          type="checkbox"
          checked={config.auto_restart_on_mistake}
          disabled={!data.automatic_ready}
          onChange={(e) =>
            setConfig({
              ...config,
              auto_restart_on_mistake: e.target.checked,
            })
          }
        />
        Automatically restart takes on mistakes
      </label>
      <p className="muted">
        Restarts after a definite pitch or note-order mismatch once all keys are
        released. Pauses and unfinished passages do not trigger a restart. MIDI
        is saved and your streak stays unchanged.
      </p>
      <label className="learning-checkbox">
        <input
          type="checkbox"
          checked={config.auto_finish}
          disabled={!data.automatic_ready}
          onChange={(e) =>
            setConfig({ ...config, auto_finish: e.target.checked })
          }
        />
        Automatically finish a complete correct attempt
      </label>
      <label className="learning-checkbox">
        <input
          type="checkbox"
          checked={config.auto_continue}
          onChange={(e) =>
            setConfig({ ...config, auto_continue: e.target.checked })
          }
        />
        Start the next attempt after a two-second review
      </label>
      <label>
        Chunk ranges (printed measures)
        <textarea
          required
          value={chunkText}
          onChange={(e) => setChunkText(e.target.value)}
        />
      </label>
      <p>
        Cover every measure once, in order. Keep boundaries within these
        sections:{" "}
        {data.lesson.sections.map((s) => range(s.start, s.end)).join(", ")}.
        Changing chunks restarts progression and preserves attempt history.
        Changing repetition settings restarts the current streak.
      </p>
      <div className="learning-controls">
        <Button disabled={busy} className="primary" type="submit">
          Save routine
        </Button>
        <Button type="button" onClick={() => setEditing(false)}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
