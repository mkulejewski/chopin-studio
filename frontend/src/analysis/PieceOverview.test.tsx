import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { PieceOverview } from "./PieceOverview";
import type { PassageData, PassagePoint } from "../types/passages";

function point(
  measure: number | null,
  velocity = 70,
  time: number | null = 1,
): PassagePoint {
  return {
    index: measure ?? 0,
    measure,
    beat: measure ?? 0,
    time,
    bpm: 120,
    velocity,
    duration_ratio: null,
    pedal: null,
    release_velocity: null,
    missing: [],
    extra: [],
    dynamics: [],
    voices: {},
    voicing: [],
    notes: [],
  };
}
function render(points: PassagePoint[], trusted = true) {
  const data: PassageData = {
    reference_id: "synthetic",
    trusted,
    notice: "Synthetic analysis",
    points,
    voices: [],
    target: {},
    release: {
      status: "unavailable",
      count: 0,
      distinct_values: 0,
      notice: "",
    },
  };
  return renderToStaticMarkup(
    <PieceOverview data={data} onMeasure={() => {}} />,
  );
}

describe("whole-piece overview", () => {
  it("includes every measure of a long take rather than a note page", () => {
    const html = render(Array.from({ length: 181 }, (_, i) => point(i + 1)));
    expect(html).toContain("Showing measures 1–181");
    expect(html.match(/aria-label="Review measure /g)).toHaveLength(181);
    expect(html).toContain('class="overview-chart"');
    expect(html).toContain(">30 BPM</text>");
    expect(html).toContain(">60 BPM</text>");
    expect(html).toContain(">90 BPM</text>");
    expect(html).toContain(">120 BPM</text>");
  });

  it("breaks curves at unavailable bars and excludes unlocated/unmatched measurements", () => {
    const html = render([
      point(10, 60),
      point(10, 80),
      point(12, 90, null),
      point(13, 100),
      point(null, 127),
    ]);
    const paths = [...html.matchAll(/<path d="([^"]*)"/g)].map(
      (match) => match[1],
    );
    // Tempo and velocity have two disconnected points; pedal stays absent.
    expect(paths[0].match(/M/g)).toHaveLength(2);
    expect(paths[1].match(/M/g)).toHaveLength(2);
    expect(paths[1]).not.toContain("L");
    expect(html).toContain("mean 70.0, range 60.0–80.0");
    expect(html).not.toContain("mean 127.0");
    expect(paths[2].trim()).toBe("");
    expect(html).toContain("Showing measures 10–13");
  });

  it("retains capture/alignment uncertainty and handles historical analyses", () => {
    expect(render([point(1)], false)).toContain(
      "Alignment or capture needs review",
    );
    expect(render([point(null)])).toContain("Analyse this activity again");
  });
});
