import type { Dispatch, SetStateAction } from "react";
import { ReasonDictation } from "../ReasonDictation";
import { TouchButton as Button } from "../TouchButton";
import { noteName, noteNumber } from "./format";
import type { NoteError } from "./types";

type Props = {
  dictatingReason: boolean;
  rule: NoteError;
  action: string;
  replacement: string;
  onError: (error: unknown) => void;
  run: (
    path: string,
    body?: unknown,
    method?: string,
  ) => Promise<boolean | undefined>;
  fixReference: boolean;
  setRule: Dispatch<SetStateAction<NoteError | null>>;
  setAction: Dispatch<SetStateAction<string>>;
  setReplacement: Dispatch<SetStateAction<string>>;
  busy: boolean;
  reason: string;
  setReason: Dispatch<SetStateAction<string>>;
  setDictatingReason: Dispatch<SetStateAction<boolean>>;
};

export function NoteRuleEditor({
  dictatingReason,
  rule,
  action,
  replacement,
  onError,
  run,
  fixReference,
  setRule,
  setAction,
  setReplacement,
  busy,
  reason,
  setReason,
  setDictatingReason,
}: Props) {
  return (
    <form
      className="learning-card"
      onSubmit={async (e) => {
        e.preventDefault();
        if (dictatingReason) return;
        let pitch = rule.pitch;
        try {
          if (action === "replace") pitch = noteNumber(replacement);
        } catch (error) {
          onError(error);
          return;
        }
        if (
          await run(
            fixReference ? "/corrections" : "/variants",
            fixReference
              ? {
                  note_id: rule.id,
                  replacement,
                  reason,
                }
              : {
                  note_id: rule.id,
                  action,
                  pitch,
                  reason,
                },
          )
        )
          setRule(null);
      }}
    >
      <h2>
        {fixReference ? "Fix reference note" : "Overrule"} {rule.name} in
        measure {rule.measure}
      </h2>
      <p>
        {fixReference
          ? "Correct this exact note occurrence in the local Learning reference. Future attempts and staff comparisons will use the corrected pitch. The source PDF and old takes remain unchanged."
          : "This changes only this note occurrence in your personal Learning edition. The printed score and original reference remain intact."}{" "}
        The affected chunk and its later connections will need fresh attempts.
      </p>
      {!fixReference && (
        <label>
          Personal choice
          <select value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="omit">Omit this note</option>
            <option value="replace">Play a different note</option>
          </select>
        </label>
      )}
      {action === "replace" && (
        <label>
          Replacement note
          <input
            required
            value={replacement}
            onChange={(e) => setReplacement(e.target.value)}
            placeholder="e.g. F#4"
          />
        </label>
      )}
      {action === "replace" && (
        <div
          className="learning-note-suggestions"
          role="group"
          aria-label="Nearby replacement notes"
        >
          <span>Nearby pitches</span>
          <div>
            {[-2, -1, 1, 2]
              .map((offset) => rule.pitch + offset)
              .filter((pitch) => pitch >= 0 && pitch <= 127)
              .map((pitch) => (
                <Button
                  key={pitch}
                  type="button"
                  disabled={busy}
                  aria-label={`Use ${noteName(pitch)} as replacement`}
                  aria-pressed={replacement === noteName(pitch)}
                  onClick={() => setReplacement(noteName(pitch))}
                >
                  {noteName(pitch)}
                </Button>
              ))}
          </div>
        </div>
      )}
      <label>
        Reason
        <textarea
          required
          disabled={dictatingReason || busy}
          maxLength={1000}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder={
            fixReference
              ? "For example: the printed score restores E flat here."
              : "For example: omit this inner tone to fit my hand."
          }
        />
      </label>
      <ReasonDictation
        key={`${rule.id}:${fixReference}`}
        disabled={busy}
        onText={setReason}
        onActiveChange={setDictatingReason}
      />
      <div className="learning-controls">
        <Button
          className="primary"
          disabled={busy || dictatingReason || !reason.trim()}
          type="submit"
        >
          {fixReference
            ? "Save reference correction"
            : "Save personal note rule"}
        </Button>
        <Button type="button" onClick={() => setRule(null)}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
