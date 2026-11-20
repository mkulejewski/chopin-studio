import { expect, test } from "@playwright/test";
import { scorePdf } from "./pdf-fixture";

test("choose a certification range, inspect live MIDI and review a paused take", async ({
  page,
}) => {
  const piece = "e25-1";
  const base = `/api/score-certification/${piece}`;
  await page.request.post("/api/learning/selection", {
    data: { piece_id: piece },
  });
  await page.request.post("/api/volumes/etudes/pdf", {
    multipart: {
      file: {
        name: "synthetic.pdf",
        mimeType: "application/pdf",
        buffer: scorePdf(3),
      },
    },
  });

  const take = {
    id: "synthetic-certification",
    session_id: "synthetic-certification",
    created: "2026-11-19T10:00:00Z",
    status: "recording",
    revision: "synthetic",
    notice: null,
    origin: "certification",
    start_measure: 1,
    end_measure: 25,
    through_pause: false,
    correction_count: 1,
  };
  const state = {
    title: "Aeolian Harp",
    revision: take.revision,
    ready: true,
    notice: "",
    volume_id: "etudes",
    first_page: 1,
    last_page: 3,
    measures: [
      { number: 0, pdf_page: 1 },
      { number: 1, pdf_page: 2 },
      { number: 25, pdf_page: 3 },
      { number: 49, pdf_page: 3 },
    ],
    learned_end: 25,
    correction_measures: [25],
    takes: [] as (typeof take)[],
  };
  await page.route(`**${base}{,/**}`, async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/start")) {
      expect(route.request().postDataJSON()).toEqual({
        start_measure: 1,
        end_measure: 25,
        include_corrections: true,
      });
      state.takes = [take];
    }
    if (path.endsWith("/live"))
      return route.fulfill({ json: { played_count: 3, recent: [60, 65, 67] } });
    if (path.endsWith("/pause")) {
      take.status = "saved";
      take.through_pause = true;
    }
    if (path.endsWith("/review")) {
      return route.fulfill({
        json: {
          played_count: 3,
          matched_count: 2,
          missing_count: 1,
          extra_count: 1,
          pause_endpoint: {
            measure: 1,
            attack: 3,
            partial_measure: true,
            partial_attack: false,
          },
          measures: [
            {
              number: 1,
              pdf_page: 2,
              key_fifths: 0,
              attacks: [
                {
                  beat: "0",
                  expected: [
                    { id: "m1:1", pitch: 60, staff: 1, played_index: 0 },
                  ],
                  extra: [],
                },
                {
                  beat: "1",
                  expected: [
                    { id: "m1:2", pitch: 64, staff: 1, played_index: null },
                  ],
                  extra: [{ pitch: 65, played_index: 1 }],
                  suggestion: "replace",
                },
                {
                  beat: "2",
                  expected: [
                    { id: "m1:3", pitch: 67, staff: 1, played_index: 2 },
                  ],
                  extra: [],
                },
              ],
            },
          ],
        },
      });
    }
    return route.fulfill({ json: state });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Library", exact: true }).click();
  await expect(
    page
      .locator('[data-piece-id="n9-1"]')
      .getByRole("button", { name: "Score certification" }),
  ).toHaveCount(0);
  await page
    .locator(`[data-piece-id="${piece}"]`)
    .getByRole("button", { name: "Score certification", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Score certification" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Use learned range" }).click();
  await expect(page.getByRole("combobox", { name: "Through" })).toHaveValue(
    "25",
  );
  await page.getByRole("combobox", { name: "From" }).selectOption("49");
  await expect(
    page.getByRole("button", { name: "Start certification take" }),
  ).toBeDisabled();
  await page.getByRole("combobox", { name: "From" }).selectOption("1");
  await page
    .getByRole("checkbox", { name: /Include saved Learning score corrections/ })
    .check();
  await page.getByRole("button", { name: "Start certification take" }).click();
  await expect(page.getByLabel("Latest captured pitches")).toHaveText(
    "C4, F4, G4",
  );
  await expect(
    page.getByRole("img", { name: "Played notes on staves" }).locator("svg"),
  ).toBeVisible();
  const pause = page.getByRole("button", {
    name: "Pause and review up to here",
  });
  const bounds = (await pause.boundingBox())!;
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(
    page.viewportSize()!.width,
  );
  await pause.click();
  await expect(page.getByText(/through attack 3/)).toBeVisible();
  await expect(page.getByText("Matched C4 (upper staff)")).toBeVisible();
  await expect(page.getByText("Reference only E4 (upper staff)")).toHaveClass(
    "certification-difference",
  );
  await expect(
    page.getByText("Replace E4 (upper staff) with F4."),
  ).toBeVisible();
  const notation = page.getByRole("img", {
    name: "Expected and played notes on staves",
  });
  await expect(notation.locator("svg")).toBeVisible();
  await expect(notation.locator('[fill="#C1273D" i]').first()).toBeAttached();

  await page.getByRole("button", { name: "Learning", exact: true }).click();
  await expect(
    page.getByRole("combobox", { name: "Learning piece" }),
  ).toHaveValue(piece);
  const link = page.getByRole("button", {
    name: "Score certification",
    exact: true,
  });
  await expect(link).toBeHidden();
  await page.getByText("Score tools", { exact: true }).click();
  await link.click();
  await expect(
    page.getByRole("heading", { name: "Certification review" }),
  ).toBeVisible();
});

test("show all hand-entered corrections together and navigate by measure", async ({
  page,
}) => {
  await page.route("**/api/score-certification/e25-1", (route) =>
    route.fulfill({
      json: {
        title: "Aeolian Harp",
        revision: "synthetic",
        ready: false,
        notice: "Source scan unavailable",
        volume_id: "etudes",
        first_page: 1,
        last_page: 2,
        measures: [
          { number: 0, pdf_page: 1 },
          { number: 6, pdf_page: 1 },
          { number: 25, pdf_page: 2 },
        ],
        learned_end: 25,
        correction_measures: [6, 25, 25],
        takes: [
          {
            id: "manual",
            status: "saved",
            origin: "corrections",
            session_id: null,
            revision: "synthetic",
            start_measure: 0,
            end_measure: 25,
            through_pause: false,
            correction_count: 3,
            manual_measures: [
              {
                number: 6,
                key_fifths: 0,
                attacks: [
                  [{ id: "m6:s1:g0:n0", pitch: 67, staff: 1 }],
                  [{ id: "m6:s2:g21:n0", pitch: 64, staff: 2 }],
                  [{ id: "m6:s2:g22:n0", pitch: 48, staff: 2 }],
                ],
              },
              {
                number: 25,
                key_fifths: 0,
                attacks: [
                  [{ id: "m25:s1:g9:n0", pitch: 64, staff: 1 }],
                  [{ id: "m25:s2:g10:n0", pitch: 55, staff: 2 }],
                  [{ id: "m25:s1:g11:n0", pitch: 72, staff: 1 }],
                ],
              },
            ],
            manual_corrections: [
              {
                note_id: "m6:s2:g21:n0",
                measure: 6,
                staff: 2,
                original_pitch: 64,
                pitch: 63,
                spelling: { step: "E", alter: -1, octave: 4 },
              },
              {
                note_id: "m25:s1:g9:n0",
                measure: 25,
                staff: 1,
                original_pitch: 64,
                pitch: 69,
                spelling: { step: "A", alter: 0, octave: 4 },
              },
              {
                note_id: "m25:s2:g10:n0",
                measure: 25,
                staff: 2,
                original_pitch: 55,
                pitch: 56,
                spelling: { step: "A", alter: -1, octave: 3 },
              },
            ],
          },
        ],
      },
    }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Library", exact: true }).click();
  await page
    .locator('[data-piece-id="e25-1"]')
    .getByRole("button", { name: "Score certification", exact: true })
    .click();
  const review = page.getByRole("region", { name: "Certification review" });
  await expect(review.getByText("Lower staff · E4 → E♭4")).toBeVisible();
  await expect(
    page.getByText(/Play verbatim from your copy of the Paderewski edition/),
  ).toBeVisible();
  const notation = review.getByRole("img", {
    name: "Full measure with original and corrected notes on staves",
  });
  const redNoteheads = notation.locator('.vf-notehead [fill="#C1273D" i]');
  await expect(redNoteheads).toHaveCount(2);
  await expect(notation.locator('[fill="#7A827F" i]').first()).toBeAttached();
  const next = review.getByRole("button", { name: "Next changed measure" });
  const previous = review.getByRole("button", {
    name: "Previous changed measure",
  });
  await expect(review.getByRole("status")).toHaveText(
    "Measure 6 · 1 difference",
  );
  await next.click();
  await expect(review.getByRole("status")).toHaveText(
    "Measure 25 · 2 differences",
  );
  await expect(review.getByText("Upper staff · E4 → A4")).toBeVisible();
  await expect(review.getByText("Lower staff · G3 → A♭3")).toBeVisible();
  await expect(redNoteheads).toHaveCount(4);
  await expect(notation.locator('[fill="#7A827F" i]').first()).toBeAttached();
  await next.click();
  await expect(review.getByRole("status")).toHaveText(
    "Measure 6 · 1 difference",
  );
  await previous.click();
  await expect(review.getByRole("status")).toHaveText(
    "Measure 25 · 2 differences",
  );
  await review.getByRole("combobox", { name: "Measure" }).selectOption("6");
  await expect(review.getByRole("status")).toHaveText(
    "Measure 6 · 1 difference",
  );
  await expect(review.getByRole("link", { name: "Download MIDI" })).toHaveCount(
    0,
  );
  await expect(review.getByText("Comparing the saved MIDI…")).toHaveCount(0);
});
