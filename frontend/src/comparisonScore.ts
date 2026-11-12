import {
  comparisonJudgement,
  type ComparisonMode,
} from "./comparisonJudgement";
import type { NoteGroup } from "./AnalysisEvidence";

export type ScoreView = "overlay" | "stacked" | "reference" | "played";
export const SCORE_COLORS = {
  reference: "#7A827F",
  played: "#253E32",
  error: "#C1273D",
  review: "#2364B4",
};
const DIVISIONS = 480;
const escapeXml = (value: string) =>
  value.replace(
    /[&<>"']/g,
    (c) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&apos;",
      })[c]!,
  );

export type PitchSpelling = { step: string; alter: number; octave: number };

export function spellPitch(pitch: number, fifths = 0): PitchSpelling {
  const names =
    fifths < 0
      ? ["C", "D", "D", "E", "E", "F", "G", "G", "A", "A", "B", "B"]
      : ["C", "C", "D", "D", "E", "F", "F", "G", "G", "A", "A", "B"];
  const altered = [1, 3, 6, 8, 10].includes(pitch % 12);
  return {
    step: names[pitch % 12],
    alter: altered ? (fifths < 0 ? -1 : 1) : 0,
    octave: Math.floor(pitch / 12) - 1,
  };
}

function pitchXml(
  pitch: number,
  fifths: number,
  spelling?: PitchSpelling | null,
) {
  const p = spelling || spellPitch(pitch, fifths);
  return `<pitch><step>${p.step}</step><alter>${p.alter}</alter><octave>${p.octave}</octave></pitch>`;
}

// Split arbitrary source durations into conventional values, tied when needed.
// The 1/12-quarter grid accommodates straight sixteenths and common triplets.
function rhythm(
  ticks: number,
): { ticks: number; type: string; dotted?: boolean; triplet?: boolean }[] {
  if (!Number.isFinite(ticks) || ticks > DIVISIONS * 64)
    throw new Error("Note duration is outside the supported comparison range.");
  const values = [
    { ticks: 1920, type: "whole" },
    { ticks: 1440, type: "half", dotted: true },
    { ticks: 960, type: "half" },
    { ticks: 720, type: "quarter", dotted: true },
    { ticks: 480, type: "quarter" },
    { ticks: 360, type: "eighth", dotted: true },
    { ticks: 320, type: "quarter", triplet: true },
    { ticks: 240, type: "eighth" },
    { ticks: 160, type: "eighth", triplet: true },
    { ticks: 120, type: "16th" },
    { ticks: 80, type: "16th", triplet: true },
    { ticks: 40, type: "32nd", triplet: true },
  ];
  const result: typeof values = [];
  let remaining = Math.max(40, Math.round(ticks / 40) * 40);
  while (remaining > 0) {
    const value = values.find((v) => v.ticks <= remaining)!;
    result.push(value);
    remaining -= value.ticks;
  }
  return result;
}

type ScoreNote = {
  pitch: number;
  spelling?: PitchSpelling | null;
  start: number;
  duration: number;
  staff: number;
  layer: "reference" | "played";
  error: boolean;
  review: boolean;
  sourceVoice?: string;
  beamGroup?: string | null;
  beamingSource?: string | null;
  beatGroupSize?: number | null;
  measureStart?: number | null;
  tieFrom?: boolean;
  tieTo?: boolean;
};
type Bar = {
  label: number | null;
  start: number;
  end: number;
  notes: ScoreNote[];
  timing: { beat: number; ratio: number }[];
};

function comparisonBars(groups: NoteGroup[], mode: ComparisonMode): Bar[] {
  const bars: Bar[] = [];
  groups.forEach((g, index) => {
    const beat = Number.isFinite(g.beat) ? g.beat! : index;
    const next = groups[index + 1];
    const nextBeat =
      next && Number.isFinite(next.beat) && next.beat! > beat
        ? next.beat!
        : undefined;
    const fallback = Math.max(
      0.25,
      ...(g.score_notes?.map((n) => Math.min(4, n.duration || 0.25)) || [1]),
    );
    if (!bars.length || bars[bars.length - 1].label !== g.measure)
      bars.push({
        label: g.measure,
        start: beat,
        end: beat,
        notes: [],
        timing: [],
      });
    const bar = bars[bars.length - 1];
    if (mode === "musical" && g.timing_review)
      bar.timing.push({ beat, ratio: g.timing_review.ratio });
    const slot = nextBeat ? Math.min(4, nextBeat - beat) : fallback;
    bar.end = Math.max(bar.end, beat + slot);
    const source = g.score_notes?.length
      ? g.score_notes
      : g.expected.map((pitch) => ({
          pitch,
          duration: slot,
          staff: pitch < 60 ? 2 : 1,
        }));
    const resolvedStaff = (note: (typeof source)[number]) => {
      const enriched = note as NonNullable<NoteGroup["score_notes"]>[number];
      return enriched.display_staff === 2
        ? 2
        : enriched.display_staff === 1
          ? 1
          : enriched.staff === 2
            ? 2
            : enriched.staff === 1
              ? 1
              : enriched.pitch < 60
                ? 2
                : 1;
    };
    const matchingSource = (pitch: number) => {
      const exact = source.find((n) => n.pitch === pitch);
      const nearest = [...source].sort(
        (a, b) => Math.abs(a.pitch - pitch) - Math.abs(b.pitch - pitch),
      )[0];
      const octave = [...source]
        .filter((n) => n.pitch % 12 === pitch % 12)
        .sort(
          (a, b) => Math.abs(a.pitch - pitch) - Math.abs(b.pitch - pitch),
        )[0];
      return exact || octave || nearest;
    };
    const beamMetadata = (note?: (typeof source)[number]) => {
      const n = note as
        NonNullable<NoteGroup["score_notes"]>[number] | undefined;
      return {
        spelling: n?.spelling,
        sourceVoice: n?.voice ? `${n.part ?? 0}:${n.voice}` : undefined,
        beamGroup: n?.beam_group,
        beamingSource: n?.beaming_source,
        beatGroupSize: n?.beat_group_size,
        measureStart: n?.measure_start,
      };
    };
    for (const note of source)
      bar.notes.push({
        pitch: note.pitch,
        start: beat,
        duration: Math.max(1 / 12, note.duration || slot),
        staff: resolvedStaff(note),
        ...beamMetadata(note),
        layer: "reference",
        error: g.live_missing
          ? g.live_missing.includes(note.pitch)
          : !g.observed.includes(note.pitch),
        review:
          comparisonJudgement(g, note.pitch, "expected", mode).severity ===
          "review",
      });
    for (const pitch of g.observed) {
      const same = source.find((n) => n.pitch === pitch);
      const reference = matchingSource(pitch);
      bar.notes.push({
        pitch,
        start: beat,
        duration: Math.max(1 / 12, same?.duration || slot),
        staff: reference ? resolvedStaff(reference) : pitch < 60 ? 2 : 1,
        ...beamMetadata(reference),
        spelling: same ? beamMetadata(same).spelling : undefined,
        layer: "played",
        error: !g.expected.includes(pitch) && !g.live_neutral?.includes(pitch),
        review:
          comparisonJudgement(g, pitch, "observed", mode).severity === "review",
      });
    }
  });
  bars.forEach((bar, i) => {
    if (bars[i + 1]) bar.end = bars[i + 1].start;
  });
  // Source ties crossing a measure become tied notes in the following bar.
  for (let i = 0; i < bars.length - 1; i++) {
    const bar = bars[i];
    for (const note of [...bar.notes]) {
      const end = note.start + note.duration;
      if (end > bar.end + 0.001) {
        bars[i + 1].notes.push({
          ...note,
          start: bar.end,
          duration: end - bar.end,
          tieFrom: true,
        });
        note.duration = bar.end - note.start;
        note.tieTo = true;
      }
    }
  }
  return bars;
}

function voiceXml(
  notes: ScoreNote[],
  start: number,
  length: number,
  voice: number,
  fifths: number,
) {
  const chords: ScoreNote[][] = [];
  for (const note of notes) {
    const previous = chords[chords.length - 1];
    if (
      previous &&
      Math.abs(previous[0].start - note.start) < 0.001 &&
      Math.abs(previous[0].duration - note.duration) < 0.001
    )
      previous.push(note);
    else chords.push([note]);
  }
  const events = chords.flatMap((chord) => {
    let at = Math.round(((chord[0].start - start) * DIVISIONS) / 40) * 40;
    const segments = rhythm(chord[0].duration * DIVISIONS);
    return segments.map((segment, i) => {
      const note = chord[0];
      const size =
        note.beatGroupSize && note.beatGroupSize > 0 ? note.beatGroupSize : 1;
      const key =
        note.beamingSource === "reference"
          ? note.beamGroup
            ? `source:${note.beamGroup}`
            : null
          : `beat:${Math.floor((note.start - (note.measureStart ?? start)) / size + 0.0001)}`;
      const event = {
        chord,
        segment,
        i,
        total: segments.length,
        at,
        key,
        beams:
          segment.type === "eighth"
            ? 1
            : segment.type === "16th"
              ? 2
              : segment.type === "32nd"
                ? 3
                : 0,
      };
      at += segment.ticks;
      return event;
    });
  });
  let cursor = 0;
  let xml = "";
  events.forEach((event, index) => {
    const { chord, segment, i, total, at, key, beams } = event;
    if (at > cursor)
      xml += `<forward><duration>${at - cursor}</duration><voice>${voice}</voice><staff>${chord[0].staff}</staff></forward>`;
    if (at < cursor)
      xml += `<backup><duration>${cursor - at}</duration></backup>`;
    const previous = events[index - 1],
      next = events[index + 1];
    const joinsPrevious =
      !!key &&
      previous?.key === key &&
      (key.startsWith("source:") ||
        Math.abs(previous.at + previous.segment.ticks - at) < 1);
    const joinsNext =
      !!key &&
      next?.key === key &&
      (key.startsWith("source:") || Math.abs(at + segment.ticks - next.at) < 1);
    let beamXml = "";
    for (let level = 1; level <= beams; level++) {
      const before = joinsPrevious && previous.beams >= level;
      const after = joinsNext && next.beams >= level;
      const value =
        before && after
          ? "continue"
          : after
            ? "begin"
            : before
              ? "end"
              : level > 1 && joinsNext && next.beams
                ? "forward hook"
                : level > 1 && joinsPrevious && previous.beams
                  ? "backward hook"
                  : null;
      if (value) beamXml += `<beam number="${level}">${value}</beam>`;
    }
    chord.forEach((note, j) => {
      const color = note.error
        ? note.review
          ? SCORE_COLORS.review
          : SCORE_COLORS.error
        : note.layer === "reference"
          ? SCORE_COLORS.reference
          : SCORE_COLORS.played;
      const missing = note.layer === "reference" && note.error,
        extra = note.layer === "played" && note.error;
      xml += `<note color="${color}">${j > 0 ? "<chord/>" : ""}${pitchXml(note.pitch, fifths, note.spelling)}<duration>${segment.ticks}</duration>${i > 0 || note.tieFrom ? '<tie type="stop"/>' : ""}${i < total - 1 || note.tieTo ? '<tie type="start"/>' : ""}<voice>${voice}</voice><type>${segment.type}</type>${segment.dotted ? "<dot/>" : ""}${segment.triplet ? "<time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>" : ""}<stem>${note.layer === "reference" ? "up" : "down"}</stem><notehead color="${color}">${extra ? "x" : missing ? "diamond" : "normal"}</notehead><staff>${note.staff}</staff>${j === 0 ? beamXml : ""}${total > 1 || note.tieFrom || note.tieTo ? `<notations>${i > 0 || note.tieFrom ? '<tied type="stop"/>' : ""}${i < total - 1 || note.tieTo ? '<tied type="start"/>' : ""}</notations>` : ""}</note>`;
    });
    cursor = at + segment.ticks;
  });
  if (cursor < length)
    xml += `<forward><duration>${length - cursor}</duration><voice>${voice}</voice></forward>`;
  return { xml, cursor: Math.max(cursor, length) };
}

/** Regenerated pitch comparison, with played notes placed on reference beats.
 * It intentionally does not transcribe performance timing or certify errors.
 */
export function buildComparisonMusicXml(
  groups: NoteGroup[],
  view: ScoreView,
  mode: ComparisonMode = "strict",
  fifths = 0,
): string {
  const bars = comparisonBars(groups, mode);
  if (!bars.length) throw new Error("No score groups available for notation.");
  const parts =
    view === "stacked" ? (["reference", "played"] as const) : [view];
  const partList = parts
    .map(
      (layer, i) =>
        `<score-part id="P${i + 1}"><part-name>${layer === "reference" ? "Reference" : layer === "played" ? "Played" : "Comparison"}</part-name><part-abbreviation>${layer === "reference" ? "Ref." : layer === "played" ? "Played" : ""}</part-abbreviation></score-part>`,
    )
    .join("");
  const content = parts
    .map(
      (layer, part) =>
        `<part id="P${part + 1}">${bars
          .map((bar, index) => {
            const length = Math.max(
              40,
              Math.round(((bar.end - bar.start) * DIVISIONS) / 40) * 40,
            );
            const notes = bar.notes.filter(
              (n) => layer === "overlay" || n.layer === layer,
            );
            // Allocate simultaneous/overlapping notes to independent voices. A shared
            // MusicXML layout then aligns both layers; independent engravings would not.
            const lanes: ScoreNote[][] = [];
            for (const note of [...notes].sort(
              (a, b) => a.start - b.start || a.pitch - b.pitch,
            )) {
              let lane = lanes.find(
                (l) =>
                  l[0].staff === note.staff &&
                  l[0].layer === note.layer &&
                  l[0].sourceVoice === note.sourceVoice &&
                  (l[l.length - 1].start + l[l.length - 1].duration <=
                    note.start + 0.001 ||
                    (Math.abs(l[l.length - 1].start - note.start) < 0.001 &&
                      Math.abs(l[l.length - 1].duration - note.duration) <
                        0.001)),
              );
              if (!lane) {
                lane = [];
                lanes.push(lane);
              }
              lane.push(note);
            }
            let body = `<attributes><divisions>${DIVISIONS}</divisions>${index === 0 ? `<key><fifths>${fifths}</fifths></key><time><senza-misura/></time><staves>2</staves><clef number="1"><sign>G</sign><line>2</line></clef><clef number="2"><sign>F</sign><line>4</line></clef>` : ""}</attributes>`;
            body += `<direction placement="above"><direction-type><words font-size="10">m. ${escapeXml(String(bar.label ?? "?"))}</words></direction-type><staff>1</staff></direction>`;
            for (const timing of bar.timing)
              body += `<direction placement="above"><direction-type><words color="${SCORE_COLORS.review}" font-size="10">Timing review (${timing.ratio}x)</words></direction-type><offset>${Math.round((timing.beat - bar.start) * DIVISIONS)}</offset><staff>1</staff></direction>`;
            if (!lanes.length)
              body += `<note><rest measure="yes"/><duration>${length}</duration><voice>1</voice><staff>1</staff></note>`;
            lanes.forEach((lane, i) => {
              const rendered = voiceXml(lane, bar.start, length, i + 1, fifths);
              body += rendered.xml;
              if (i < lanes.length - 1)
                body += `<backup><duration>${rendered.cursor}</duration></backup>`;
            });
            return `<measure number="${escapeXml(String(bar.label ?? index + 1))}" implicit="no">${body}</measure>`;
          })
          .join("")}</part>`,
    )
    .join("");
  return `<?xml version="1.0" encoding="utf-8"?><score-partwise version="4.0"><work><work-title>${mode === "strict" ? "Strict reference" : "Musical context"} pitch comparison</work-title></work><part-list>${partList}</part-list>${content}</score-partwise>`;
}
