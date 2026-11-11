import { describe, expect, it } from "vitest";
import { buildComparisonMusicXml, SCORE_COLORS } from "./comparisonScore";
import type { NoteGroup } from "./AnalysisEvidence";

const passage: NoteGroup[] = [
  {
    measure: 12,
    beat: 44,
    time: 2,
    expected: [48, 60, 64],
    observed: [48, 60, 65],
    score_notes: [
      { pitch: 48, duration: 2, staff: 2 },
      { pitch: 60, duration: 0.5, staff: 1 },
      { pitch: 64, duration: 0.5, staff: 1 },
    ],
  },
  {
    measure: 13,
    beat: 45,
    time: null,
    expected: [67],
    observed: [],
    score_notes: [{ pitch: 67, duration: 1 / 3, staff: 1 }],
  },
];

describe("comparison score compilation", () => {
  it("distinguishes played errors from missing reference pitches on shared grand staves", () => {
    const xml = buildComparisonMusicXml(passage, "overlay");
    expect(xml.match(/<part id=/g)).toHaveLength(1);
    expect(xml).toContain("<staves>2</staves>");
    expect(xml).toContain('<measure number="12"');
    expect(xml).toContain(
      `<notehead color="${SCORE_COLORS.error}">diamond</notehead>`,
    );
    expect(xml).toContain(
      `<notehead color="${SCORE_COLORS.error}">x</notehead>`,
    );
    expect(xml).toContain("<staff>2</staff>");
    expect(xml).toContain("<actual-notes>3</actual-notes>");
    expect(xml).toContain('<tie type="start"/>');
    expect(xml).toContain('<tie type="stop"/>');
  });
  it("can compile the actual pitch set independently of the expected pitch set", () => {
    const played = buildComparisonMusicXml(passage, "played");
    expect(played).toContain("<step>F</step>");
    expect(played).not.toContain("<step>E</step>");
    expect(played).not.toContain("<step>G</step>");
    const reference = buildComparisonMusicXml(passage, "reference");
    expect(reference).toContain("<step>E</step>");
    expect(reference).not.toContain("<step>F</step>");
    expect(reference).not.toContain(">x</notehead>");
  });
  it("aligns both complete pitch layers within one stacked score", () => {
    const xml = buildComparisonMusicXml(passage, "stacked");
    expect(xml.match(/<part id=/g)).toHaveLength(2);
    expect(xml.match(/<measure number="12"/g)).toHaveLength(2);
    expect(xml).toContain("<part-name>Reference</part-name>");
    expect(xml).toContain("<part-name>Played</part-name>");
  });
  it("keeps historical onset-only comparisons usable and rejects an empty passage", () => {
    expect(
      buildComparisonMusicXml(
        [{ measure: null, time: null, expected: [61], observed: [61] }],
        "overlay",
      ),
    ).toContain("<alter>1</alter>");
    expect(() => buildComparisonMusicXml([], "overlay")).toThrow(
      "No score groups",
    );
  });
});

it("uses blue for musical uncertainty and keeps strict pitch differences red", () => {
  const xml = buildComparisonMusicXml(passage, "overlay", "musical");
  expect(xml).toContain(SCORE_COLORS.review);
  expect(xml).not.toContain(SCORE_COLORS.error);
  const withContext = structuredClone(passage);
  withContext[0].musical_context = {
    expected: {
      "64": {
        severity: "review",
        reason: "variant",
        explanation: "Possible edition variant",
      },
    },
    observed: {
      "65": {
        severity: "error",
        reason: "wrong_pitch",
        explanation: "Likely pitch error",
      },
    },
  };
  const coloured = buildComparisonMusicXml(withContext, "overlay", "musical");
  expect(coloured).toContain(SCORE_COLORS.review);
  expect(coloured).toContain(SCORE_COLORS.error);
  const strict = buildComparisonMusicXml(withContext, "overlay", "strict");
  expect(strict).toContain(SCORE_COLORS.error);
  expect(strict).not.toContain(SCORE_COLORS.review);
});

it("keeps bass-reference notes and their octave adaptations on the bass staff", () => {
  const groups: NoteGroup[] = [
    {
      measure: 1,
      beat: 0,
      time: 0,
      expected: [60, 69],
      observed: [72, 69],
      score_notes: [
        { pitch: 60, duration: 1, staff: 1, part: 1, display_staff: 2 },
        { pitch: 69, duration: 1, staff: 1, part: 0, display_staff: 1 },
      ],
    },
  ];
  const xml = buildComparisonMusicXml(groups, "played");
  const notes = xml.match(/<note\b[\s\S]*?<\/note>/g)!;
  expect(notes.find((n) => n.includes("<step>C</step>"))).toContain(
    "<staff>2</staff>",
  );
  expect(notes.find((n) => n.includes("<step>A</step>"))).toContain(
    "<staff>1</staff>",
  );
  const reference = buildComparisonMusicXml(groups, "reference").match(
    /<note\b[\s\S]*?<\/note>/g,
  )!;
  expect(reference.find((n) => n.includes("<step>C</step>"))).toContain(
    "<staff>2</staff>",
  );
});

function beamPassage(
  durations: number[],
  grouping?: (i: number) => string | null,
  beatGroupSize = 1,
): NoteGroup[] {
  let beat = 0;
  return durations.map((duration, i) => {
    const group: NoteGroup = {
      measure: 1,
      beat,
      time: i,
      expected: [60 + i],
      observed: [60 + i],
      score_notes: [
        {
          pitch: 60 + i,
          duration,
          staff: 1,
          measure_start: 0,
          beat_group_size: beatGroupSize,
          beaming_source: grouping ? "reference" : "meter",
          beam_group: grouping?.(i),
        },
      ],
    };
    beat += duration;
    return group;
  });
}

it("uses source beam groups instead of joining every short note in a measure", () => {
  const xml = buildComparisonMusicXml(
    beamPassage([0.5, 0.5, 0.5, 0.5], (i) => (i < 3 ? "source-a" : null)),
    "overlay",
  );
  expect(xml.match(/<beam number="1">begin<\/beam>/g)).toHaveLength(2);
  expect(xml.match(/<beam number="1">continue<\/beam>/g)).toHaveLength(2);
  expect(xml.match(/<beam number="1">end<\/beam>/g)).toHaveLength(2);
  const lastNotes = xml
    .match(/<note\b[\s\S]*?<\/note>/g)!
    .filter(
      (n) => n.includes("<step>D</step>") && n.includes("<alter>1</alter>"),
    );
  expect(lastNotes).toHaveLength(2);
  expect(lastNotes.every((n) => !n.includes("<beam"))).toBe(true);
});

it("groups compound beats and short-note beams while leaving quarter notes separate", () => {
  const compound = buildComparisonMusicXml(
    beamPassage([0.5, 0.5, 0.5, 0.5, 0.5, 0.5], undefined, 1.5),
    "reference",
  );
  expect(compound.match(/<beam number="1">begin<\/beam>/g)).toHaveLength(2);
  expect(compound.match(/<beam number="1">continue<\/beam>/g)).toHaveLength(2);
  const mixed = buildComparisonMusicXml(
    beamPassage([0.25, 0.25, 0.5, 1]),
    "reference",
  );
  expect(mixed).toContain('<beam number="2">begin</beam>');
  expect(mixed).toContain('<beam number="2">end</beam>');
  const quarter = mixed
    .match(/<note\b[\s\S]*?<\/note>/g)!
    .find((n) => n.includes("<type>quarter</type>"))!;
  expect(quarter).not.toContain("<beam");
});

it("keeps pending live notes grey and neutral played-only input ungraded", () => {
  const pending: NoteGroup[] = [
    {
      measure: 1,
      beat: 0,
      time: null,
      expected: [60],
      observed: [],
      live_missing: [],
    },
  ];
  expect(buildComparisonMusicXml(pending, "overlay", "strict")).not.toContain(
    SCORE_COLORS.error,
  );
  const missed = [{ ...pending[0], live_missing: [60] }];
  expect(buildComparisonMusicXml(missed, "overlay", "strict")).toContain(
    SCORE_COLORS.error,
  );
  const played: NoteGroup[] = [
    {
      measure: 1,
      beat: 0,
      time: null,
      expected: [],
      observed: [61],
      live_neutral: [61],
    },
  ];
  expect(buildComparisonMusicXml(played, "played", "strict")).not.toContain(
    SCORE_COLORS.error,
  );
});
