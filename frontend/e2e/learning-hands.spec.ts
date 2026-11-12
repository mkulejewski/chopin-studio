import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

const base = "/api/learning/e25-1";

test("Learning selects hands, isolates live reference notes and restores both-hands progress", async ({
  page,
}) => {
  test.skip(
    !process.env.CHOPIN_LEARNING_PDF,
    "Needs the reviewed score in the isolated test library.",
  );
  await page.request.post(base + "/pause");
  await page.request.put(base + "/hand", { data: { hand: "both" } });
  await page.request.post(base + "/restart");
  await page.request.post("/api/volumes/etudes/pdf", {
    multipart: {
      file: {
        name: "paderewski_etudes.pdf",
        mimeType: "application/pdf",
        buffer: readFileSync(process.env.CHOPIN_LEARNING_PDF!),
      },
    },
  });
  await page.request.put(base, {
    data: {
      config: {
        visible: 2,
        hidden: 1,
        connections: 1,
        auto_continue: false,
        auto_finish: false,
      },
    },
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Learning", exact: true }).click();
  const hands = page.getByRole("combobox", {
    name: "Practice hands",
    exact: true,
  });
  await expect(hands).toHaveValue("both");
  const initial = await (await page.request.get(base)).json();
  await hands.selectOption("right");
  await expect
    .poll(
      async () => (await (await page.request.get(base)).json()).profile.hand,
    )
    .toBe("right");
  await page
    .getByRole("button", { name: "Start attempt", exact: true })
    .click();
  await expect(hands).toBeDisabled();
  let state = await (await page.request.get(base)).json();
  expect(state.active.target.hand).toBe("right");
  let projection = await (
    await page.request.get(base + `/attempts/${state.active.id}/staves`)
  ).json();
  expect(
    projection.groups.flatMap((g: any) => g.score_notes).length,
  ).toBeGreaterThan(0);
  expect(
    projection.groups
      .flatMap((g: any) => g.score_notes)
      .every((n: any) => n.staff === 1),
  ).toBe(true);
  await page
    .getByRole("button", { name: "Pause learning", exact: true })
    .click();
  await expect(hands).toBeEnabled();
  await hands.selectOption("left");
  await expect
    .poll(
      async () => (await (await page.request.get(base)).json()).profile.hand,
    )
    .toBe("left");
  await page
    .getByRole("button", { name: "Start attempt", exact: true })
    .click();
  state = await (await page.request.get(base)).json();
  expect(state.active.target.hand).toBe("left");
  projection = await (
    await page.request.get(base + `/attempts/${state.active.id}/staves`)
  ).json();
  const left = projection.groups.flatMap((g: any) => g.score_notes);
  expect(left.length).toBeGreaterThan(0);
  expect(left.every((n: any) => n.staff === 2)).toBe(true);
  await page
    .getByRole("button", { name: "Enter score fullscreen", exact: true })
    .click();
  await expect
    .poll(() => page.evaluate(() => !!document.fullscreenElement))
    .toBe(true);
  await expect
    .poll(() => page.locator(".learning-staves svg").count())
    .toBeGreaterThan(0);
  if (test.info().project.name === "full-hd") {
    const staves = await page.locator(".learning-staves-scroll").boundingBox();
    expect(staves!.y + staves!.height).toBeLessThanOrEqual(
      page.viewportSize()!.height,
    );
  }
  await page.screenshot({
    path: test.info().outputPath("left-hand-fullscreen.png"),
  });
  await page
    .getByRole("button", { name: "Pause learning", exact: true })
    .click();
  await expect(hands).toBeEnabled();
  await hands.selectOption("both");
  await expect
    .poll(
      async () => (await (await page.request.get(base)).json()).profile.hand,
    )
    .toBe("both");
  state = await (await page.request.get(base)).json();
  expect(state.profile.stage_index).toBe(initial.profile.stage_index);
  expect(state.profile.completed).toEqual(initial.profile.completed);
  expect(state.profile.streak).toBe(initial.profile.streak);
});
