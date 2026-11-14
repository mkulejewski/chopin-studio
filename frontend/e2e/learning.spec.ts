import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { scorePdf } from "./pdf-fixture";
const base = "/api/learning/e25-1";
const config = {
  visible: 2,
  hidden: 1,
  connections: 1,
  auto_continue: true,
  auto_finish: true,
};
function midi(complete: boolean, limit?: number) {
  const b = JSON.parse(
    readFileSync(
      new URL(
        "../../backend/chopin/learning_data/aeolian_harp_etude_op25_no1.json",
        import.meta.url,
      ),
      "utf8",
    ),
  );
  const events = new Map<string, { m: number; beat: number; p: number }>();
  for (const m of b.measures.filter((m: any) => m.number <= 2))
    for (const staff of m.staves)
      for (const [pos, pitches] of staff) {
        const [n, d = "1"] = pos.split("/");
        for (const p of pitches)
          events.set(`${m.number}:${pos}:${p}`, {
            m: m.number,
            beat: Number(n) / Number(d),
            p,
          });
      }
  const notes = [...events.values()]
    .sort((a, b) => a.m - b.m || a.beat - b.beat || a.p - b.p)
    .map((e) => e.p);
  if (!complete) notes.pop();
  if (limit !== undefined) notes.splice(limit);
  const track = Buffer.from(
    notes
      .flatMap((p) => [6, 0x90, p, 64, 2, 0x80, p, 0])
      .concat([0, 0xff, 0x2f, 0]),
  );
  const size = Buffer.alloc(4);
  size.writeUInt32BE(track.length);
  return Buffer.concat([
    Buffer.from("4d546864000000060000000103e84d54726b", "hex"),
    size,
    track,
  ]);
}
async function replay(page: any, id: string) {
  expect(
    (
      await page.request.post("/api/simulation/start", {
        data: { session_id: id, speed: 8 },
      })
    ).ok(),
  ).toBeTruthy();
  await expect
    .poll(
      async () =>
        (await (await page.request.get("/api/status")).json()).simulation,
    )
    .toBe(false);
}
test("Learning refuses an unreviewed PDF and explains model analysis", async ({
  page,
}) => {
  await page.request.post(base + "/pause");
  await page.request.post("/api/volumes/etudes/pdf", {
    multipart: {
      file: {
        name: "unreviewed.pdf",
        mimeType: "application/pdf",
        buffer: scorePdf(68),
      },
    },
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Learning", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Learning", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("status").filter({ hasText: "This PDF differs" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Start attempt", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".learning canvas")).toHaveCount(0);
  await page
    .getByText("Lesson analysis & edition evidence", { exact: true })
    .click();
  await expect(
    page.getByText(/Every new proper Learning piece requires/),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Open score library", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Your score library.", exact: true }),
  ).toBeVisible();
});
test("reviewed PDF, auto advancement, peek, note overrule and saved progress", async ({
  page,
}, info) => {
  test.skip(
    !process.env.CHOPIN_LEARNING_PDF,
    "Set CHOPIN_LEARNING_PDF to the reviewed local scan.",
  );
  test.setTimeout(90000);
  await page.request.post(base + "/pause");
  expect(
    (
      await page.request.post("/api/volumes/etudes/pdf", {
        multipart: {
          file: {
            name: "paderewski_etudes.pdf",
            mimeType: "application/pdf",
            buffer: readFileSync(process.env.CHOPIN_LEARNING_PDF!),
          },
        },
      })
    ).ok(),
  ).toBeTruthy();
  await page.request.post(base + "/restart");
  const old = await (await page.request.get(base)).json();
  for (const rule of old.profile.variants)
    await page.request.post(base + "/variants", {
      data: { ...rule, action: "revoke", reason: "Reset test fixture" },
    });
  await page.request.put(base, { data: { config } });
  async function upload(complete: boolean, limit?: number) {
    return (
      await (
        await page.request.post("/api/import/midi", {
          multipart: {
            file: {
              name: "learning.mid",
              mimeType: "audio/midi",
              buffer: midi(complete, limit),
            },
          },
        })
      ).json()
    ).id;
  }
  const complete = await upload(true),
    missing = await upload(false),
    short = await upload(true, 3);
  await page.goto("/");
  await page.getByRole("button", { name: "Learning", exact: true }).click();
  await expect(
    page.getByLabel("Score PDF page 64", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: info.outputPath("visible.png"),
    fullPage: true,
  });
  // Regression: App fullscreen followed by Learning score fullscreen must keep
  // its exit button correct through polling and all notation transitions.
  await page
    .getByRole("button", { name: "Enter app fullscreen", exact: true })
    .tap();
  await page
    .getByRole("button", { name: "Enter score fullscreen", exact: true })
    .tap();
  await expect
    .poll(() => page.evaluate(() => document.fullscreenElement?.className))
    .toBe("learning-workspace");
  const workspace = page.locator(".learning-workspace");
  await workspace.evaluate((element) => {
    (element as HTMLElement).dataset.fullscreenToken = "stable";
  });
  await expect(
    page.getByRole("button", { name: "Exit score fullscreen", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Next page", exact: true }).tap();
  await expect(
    page.getByLabel("Score PDF page 65", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "First score page", exact: true })
    .tap();
  await expect(
    page.getByLabel("Score PDF page 64", { exact: true }),
  ).toBeVisible();
  const twoPages = page.getByRole("button", {
    name: "Two-page view",
    exact: true,
  });
  await expect(twoPages).toHaveAttribute("aria-pressed", "false");
  await expect(
    page.locator(".learning .paper-pair canvas:visible"),
  ).toHaveCount(1);
  const layout = await page.evaluate(() => {
    const root = document
      .querySelector(".learning-workspace")!
      .getBoundingClientRect();
    const controls = document
      .querySelector(".learning-control-panel")!
      .getBoundingClientRect();
    const score = document
      .querySelector(".learning-pdf")!
      .getBoundingClientRect();
    return {
      width: root.width,
      controlsLeft: controls.left - root.left,
      scoreRight: score.right - root.left,
      scoreWidth: score.width,
      scoreLeft: score.left - root.left,
      scoreHeight: score.height,
      height: root.height,
    };
  });
  expect(layout.scoreLeft).toBeCloseTo(0, 0);
  expect(layout.scoreWidth / (layout.width - 12)).toBeCloseTo(2 / 3, 2);
  expect(layout.controlsLeft - layout.scoreRight).toBeCloseTo(12, 0);
  expect(layout.scoreHeight).toBeGreaterThan(layout.height * 0.95);
  await expect
    .poll(() =>
      page.evaluate(() => {
        const canvas = document
          .querySelector(".learning .paper-pair canvas")!
          .getBoundingClientRect();
        const stage = document
          .querySelector(".learning .score-stage")!
          .getBoundingClientRect();
        return Math.max(
          canvas.width / stage.width,
          canvas.height / stage.height,
        );
      }),
    )
    .toBeGreaterThan(0.94);
  await twoPages.tap();
  await expect(twoPages).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.locator(".learning .paper-pair canvas:visible"),
  ).toHaveCount(2);
  await twoPages.tap();
  await expect(twoPages).toHaveAttribute("aria-pressed", "false");
  await expect(
    page.locator(".learning .paper-pair canvas:visible"),
  ).toHaveCount(1);
  await page.screenshot({ path: info.outputPath("fullscreen-visible.png") });
  await page.waitForTimeout(2200);
  await expect(
    page.getByRole("button", { name: "Exit score fullscreen", exact: true }),
  ).toBeVisible();

  await page
    .getByRole("button", { name: "Start attempt", exact: true })
    .click();
  const liveReview = page.getByRole("region", {
    name: "Review this attempt",
    exact: true,
  });
  await expect(
    liveReview.getByRole("heading", {
      name: "Live note comparison",
      exact: true,
    }),
  ).toBeVisible();
  await expect(liveReview.locator(".learning-staves svg").first()).toBeVisible({
    timeout: 15000,
  });
  await expect
    .poll(() =>
      liveReview
        .locator(".learning-staves-scroll")
        .evaluate((el) => el.scrollWidth <= el.clientWidth),
    )
    .toBe(true);
  const initialStaves = await (
    await page.request.get(
      `${base}/attempts/${(await (await page.request.get(base)).json()).active.id}/staves`,
    )
  ).json();
  expect(new Set(initialStaves.groups.map((g: any) => g.measure)).size).toBe(1);
  await replay(page, complete);
  await expect
    .poll(
      async () => (await (await page.request.get(base)).json()).profile.streak,
    )
    .toBe(1);
  await expect(
    page.getByLabel("Score PDF page 64", { exact: true }),
  ).toBeVisible();
  // Wait for the server's NEW recording, not a stale Finish button left by
  // the previous status poll during the two-second review countdown.
  await expect
    .poll(async () => (await (await page.request.get(base)).json()).active)
    .not.toBe(null);
  // Restarting that automatic take is immediate and neutral for the streak.
  const beforeRestart = (await (await page.request.get(base)).json()).active.id;
  await page.getByRole("button", { name: "Restart take", exact: true }).click();
  await expect
    .poll(async () => (await (await page.request.get(base)).json()).active.id)
    .not.toBe(beforeRestart);
  expect((await (await page.request.get(base)).json()).profile.streak).toBe(1);
  await expect(
    page.getByRole("button", { name: "Exit score fullscreen", exact: true }),
  ).toBeVisible();
  // The next visible attempt starts without leaving fullscreen or pressing Start.
  await expect(
    page.getByRole("button", { name: "Finish & evaluate", exact: true }),
  ).toBeVisible({ timeout: 12000 });
  await replay(page, complete);
  await expect(
    page.getByText("Recall from memory", { exact: true }),
  ).toBeVisible({ timeout: 15000 });
  await page.request.put(base, {
    data: { config: { ...config, auto_continue: false } },
  });
  await expect(page.locator(".learning canvas")).toHaveCount(0);
  await expect
    .poll(() => page.evaluate(() => document.fullscreenElement?.className))
    .toBe("learning-workspace");
  await expect(workspace).toHaveAttribute("data-fullscreen-token", "stable");
  await expect(
    workspace.getByRole("button", { name: "Start attempt", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Exit score fullscreen", exact: true })
    .tap();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.fullscreenElement === document.documentElement,
      ),
    )
    .toBe(true);
  await page
    .getByRole("button", { name: "Enter score fullscreen", exact: true })
    .tap();
  await expect(
    page.getByRole("button", { name: "Exit score fullscreen", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: info.outputPath("hidden.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Start attempt", exact: true })
    .click();
  await replay(page, short);
  await expect(
    liveReview.getByText("3 played attacks · played notes only", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    liveReview
      .getByRole("img", { name: "Played notes on staves", exact: true })
      .locator("svg")
      .first(),
  ).toBeVisible();
  await expect(
    liveReview.getByRole("img", {
      name: "Expected and played notes on staves",
      exact: true,
    }),
  ).toHaveCount(0);
  const hiddenAttempt = (await (await page.request.get(base)).json()).active.id;
  const hiddenNotes = await (
    await page.request.get(`${base}/attempts/${hiddenAttempt}/staves`)
  ).json();
  expect(hiddenNotes.expected_visible).toBe(false);
  expect(
    hiddenNotes.groups.every((group: any) => group.expected.length === 0),
  ).toBe(true);
  await page.getByRole("button", { name: "Restart take", exact: true }).click();
  await page
    .getByRole("button", { name: "Peek at score", exact: true })
    .click();
  await expect(
    page.getByLabel("Score PDF page 64", { exact: true }),
  ).toBeVisible();
  await replay(page, complete);
  await expect(
    page.getByRole("heading", { name: "Assisted recall", exact: true }),
  ).toBeVisible({ timeout: 15000 });
  await expect
    .poll(
      async () =>
        (await (await page.request.get(base)).json()).profile.stage_index,
    )
    .toBe(1);
  await page
    .getByRole("button", { name: "Start attempt", exact: true })
    .click();
  await replay(page, missing);
  await page
    .getByRole("button", { name: "Finish & evaluate", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Overrule error", exact: true }),
  ).toHaveCount(1);
  await page
    .getByRole("button", { name: "Count take as remembered", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Counted as remembered", exact: true }),
  ).toBeVisible();
  const accepted = (await (await page.request.get(base)).json()).history[0]
    .result;
  expect(accepted.manual_accepted).toBe(true);
  expect(accepted.passed).toBe(false);
  await expect(
    page.getByRole("button", { name: "Exit score fullscreen", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Overrule error", exact: true })
    .click();
  await page
    .getByLabel("Reason", { exact: true })
    .fill("Omit this particular tone for my hand span.");
  await page
    .getByRole("button", { name: "Save personal note rule", exact: true })
    .click();
  await expect
    .poll(
      async () =>
        (await (await page.request.get(base)).json()).profile.variants.length,
    )
    .toBe(1);
  await expect(
    page.getByText("Study with the score", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "Learning", exact: true }).click();
  await expect(
    page.getByText("Personal note rules: 1", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Enter score fullscreen", exact: true })
    .tap();
  await expect(
    page.getByRole("button", { name: "Exit score fullscreen", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Start attempt", exact: true })
    .click();
  await replay(page, missing);
  await expect
    .poll(
      async () => (await (await page.request.get(base)).json()).profile.streak,
    )
    .toBe(1);
  await page
    .getByRole("button", { name: "Start attempt", exact: true })
    .click();
  await replay(page, missing);
  await expect(
    page.getByText("Recall from memory", { exact: true }),
  ).toBeVisible({ timeout: 15000 });
  await page
    .getByRole("button", { name: "Start attempt", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Pause learning", exact: true })
    .click();
  await expect
    .poll(async () => (await (await page.request.get(base)).json()).active)
    .toBe(null);
  await expect(
    page.getByRole("button", { name: "Exit score fullscreen", exact: true }),
  ).toBeVisible();
  // Self-assessment may advance without completing the repetition quota.
  await page.getByRole("button", { name: "Next stage", exact: true }).click();
  await expect(
    page.getByText("Study with the score", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Measures 3–4", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Next stage", exact: true }).click();
  await expect(
    page.getByText("Recall from memory", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".learning canvas")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Exit score fullscreen", exact: true }),
  ).toBeVisible();
  const final = await (await page.request.get(base)).json();
  expect(final.profile.manual_advances.length).toBeGreaterThanOrEqual(2);
  await page.screenshot({ path: info.outputPath("fullscreen-hidden.png") });
  await page
    .getByRole("button", { name: "Exit score fullscreen", exact: true })
    .tap();
  await page.getByRole("button", { name: "Practice", exact: true }).click();
  await expect
    .poll(async () => (await (await page.request.get(base)).json()).active)
    .toBe(null);
  await expect
    .poll(
      async () => (await (await page.request.get("/api/status")).json()).active,
    )
    .toBe(null);
});

test("Learning divider supports drag, keyboard, saved width and reset", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Learning", exact: true }).click();
  await page
    .getByRole("button", { name: "Enter score fullscreen", exact: true })
    .click();
  const divider = page.getByRole("separator", {
    name: "Resize score and controls",
  });
  await expect(divider).toHaveAttribute("aria-valuenow", "67");
  const root = await page.locator(".learning-workspace").boundingBox();
  const handle = await divider.boundingBox();
  await page.mouse.move(
    handle!.x + handle!.width / 2,
    handle!.y + handle!.height / 2,
  );
  await page.mouse.down();
  await page.mouse.move(
    root!.x + 6 + (root!.width - 12) * 0.55,
    handle!.y + handle!.height / 2,
    { steps: 8 },
  );
  await page.mouse.up();
  await expect(divider).toHaveAttribute("aria-valuenow", "55");
  await divider.press("ArrowRight");
  await expect(divider).toHaveAttribute("aria-valuenow", "57");
  await page
    .getByRole("button", { name: "Exit score fullscreen", exact: true })
    .click();
  await page.reload();
  await page.getByRole("button", { name: "Learning", exact: true }).click();
  await page
    .getByRole("button", { name: "Enter score fullscreen", exact: true })
    .click();
  await expect(divider).toHaveAttribute("aria-valuenow", "57");
  await divider.press("Enter");
  await expect(divider).toHaveAttribute("aria-valuenow", "67");
  await page.screenshot({
    path: test.info().outputPath("score-left-resizable.png"),
  });
  await page
    .getByRole("button", { name: "Exit score fullscreen", exact: true })
    .click();
});

test("auto-restart on mistakes is optional and the routine remembers it", async ({
  page,
}) => {
  await page.request.post(base + "/pause");
  const initial = await (await page.request.get(base)).json();
  await page.request.put(base, {
    data: {
      config: { ...initial.profile.config, auto_restart_on_mistake: false },
    },
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Learning", exact: true }).click();
  const edit = page.getByRole("button", {
    name: "Edit routine & chunks",
    exact: true,
  });
  await edit.click();
  const option = page.getByRole("checkbox", {
    name: "Automatically restart takes on mistakes",
    exact: true,
  });
  await expect(option).not.toBeChecked();
  await option.check();
  await page.getByRole("button", { name: "Save routine", exact: true }).click();
  await expect(
    page.getByText(
      "Auto-restart on mistakes is on. Release all keys to restart.",
      { exact: true },
    ),
  ).toBeVisible();
  expect(
    (await (await page.request.get(base)).json()).profile.config
      .auto_restart_on_mistake,
  ).toBe(true);
  await page.reload();
  await page.getByRole("button", { name: "Learning", exact: true }).click();
  await edit.click();
  await expect(option).toBeChecked();
  await option.uncheck();
  await page.getByRole("button", { name: "Save routine", exact: true }).click();
  await expect(
    page.getByText(
      "Auto-restart on mistakes is on. Release all keys to restart.",
      { exact: true },
    ),
  ).toHaveCount(0);
});

test("review return control stays beside start in normal and score fullscreen", async ({
  page,
}, info) => {
  const learning = await (await page.request.get(base)).json();
  let reviewing = true;
  await page.route("**" + base, (route) =>
    route.fulfill({
      json: reviewing
        ? {
            ...learning,
            ready: false,
            active: null,
            pending_at: null,
            history: [],
            target: { ...learning.target, kind: "review" },
            review: { ...learning.review, active: true },
          }
        : learning,
    }),
  );
  await page.route("**" + base + "/review/leave", (route) => {
    expect(route.request().method()).toBe("POST");
    reviewing = false;
    return route.fulfill({ json: learning });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Learning", exact: true }).click();
  const controls = page.locator(".learning-target .learning-controls");
  const returnButton = controls.getByRole("button", {
    name: "Return to learning",
    exact: true,
  });
  await expect(
    controls.getByRole("button", { name: "Start review", exact: true }),
  ).toBeVisible();
  await expect(returnButton).toBeEnabled();
  expect(
    await returnButton.evaluate(
      (button) => button.previousElementSibling?.textContent,
    ),
  ).toBe("Start review");
  await page
    .getByRole("button", { name: "Enter score fullscreen", exact: true })
    .click();
  await expect
    .poll(() => page.evaluate(() => document.fullscreenElement?.className))
    .toBe("learning-workspace");
  await returnButton.scrollIntoViewIfNeeded();
  const bounds = await returnButton.boundingBox();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.y).toBeGreaterThanOrEqual(0);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(
    page.viewportSize()!.width,
  );
  expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(
    page.viewportSize()!.height,
  );
  await page.screenshot({
    path: info.outputPath("review-return-fullscreen.png"),
  });
  await returnButton.tap();
  await expect(
    controls.getByRole("button", { name: "Start attempt", exact: true }),
  ).toBeVisible();
  await expect(returnButton).toHaveCount(0);
});

test("learned-prefix review preserves the current learning assignment", async ({
  page,
}) => {
  test.skip(
    !process.env.CHOPIN_LEARNING_PDF,
    "Needs the reviewed local score and the learned-prefix fixture.",
  );
  await page.request.post(base + "/review/leave");
  const before = await (await page.request.get(base)).json();
  expect(before.review.learned_end).not.toBe(null);
  await page.goto("/");
  await page.getByRole("button", { name: "Learning", exact: true }).click();
  await page
    .getByRole("button", { name: "Enter score fullscreen", exact: true })
    .click();
  const chunkMap = page.locator(".learning-card").filter({
    has: page.getByRole("heading", { name: "Your chunk map", exact: true }),
  });
  const reviewAll = chunkMap.locator(".learning-chunks > button").first();
  await expect(reviewAll).toContainText("Review all learned");
  await expect(chunkMap.getByLabel("Include the current chunk")).toBeVisible();
  await reviewAll.click();
  await expect(
    page.getByText("Previously learned chunks · review", { exact: true }),
  ).toBeVisible();
  const reviewing = await (await page.request.get(base)).json();
  expect(reviewing.target.start).toBe(0);
  expect(reviewing.target.end).toBe(before.review.learned_end);
  expect(reviewing.active.target.kind).toBe("review");
  expect(reviewing.profile).toEqual(before.profile);
  await expect(
    page.getByRole("button", { name: "Next stage", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Finish & evaluate", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Start review", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Count take as remembered", exact: true }),
  ).toHaveCount(0);
  expect((await (await page.request.get(base)).json()).profile).toEqual(
    before.profile,
  );
  await page
    .getByRole("button", { name: "Return to learning", exact: true })
    .click();
  const after = await (await page.request.get(base)).json();
  expect(after.target).toEqual(before.target);
  expect(after.profile).toEqual(before.profile);
  expect(after.review.active).toBe(false);
  await page
    .getByRole("button", { name: "Start attempt", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Review learned chunk Pickup–2", exact: true })
    .click();
  const chunkReview = await (await page.request.get(base)).json();
  expect(chunkReview.active.target.kind).toBe("review");
  expect(chunkReview.target.start).toBe(0);
  expect(chunkReview.target.end).toBe(2);
  expect(chunkReview.profile).toEqual(before.profile);
  await page
    .getByRole("button", { name: /^Return to learning chunk / })
    .click();
  expect((await (await page.request.get(base)).json()).profile).toEqual(
    before.profile,
  );
  await expect(
    page.getByRole("button", { name: "Exit score fullscreen", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Exit score fullscreen", exact: true })
    .click();
});
