import { test, expect } from "@playwright/test";

test("Library distinguishes reviewed counterparts from provisional sources", async ({
  page,
}) => {
  await page.route("**/api/library", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    data.pieces = data.pieces.map((piece: any) =>
      piece.id === "p28-4"
        ? {
            ...piece,
            reference_count: 2,
            verified_reference_count: 1,
            provisional_reference_count: 1,
          }
        : piece,
    );
    await route.fulfill({ response, json: data });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Library", exact: true }).click();
  await page.getByRole("textbox", { name: "Search pieces" }).fill("28");
  const card = page.locator('[data-piece-id="p28-4"]');
  await expect(
    card.getByText("1 verified · 1 provisional", { exact: true }),
  ).toBeVisible();
  const label = await card
    .getByText("1 verified · 1 provisional", { exact: true })
    .boundingBox();
  const bounds = await card.boundingBox();
  expect(label!.x).toBeGreaterThanOrEqual(bounds!.x);
  expect(label!.x + label!.width).toBeLessThanOrEqual(
    bounds!.x + bounds!.width,
  );
  expect(label!.x + label!.width).toBeLessThanOrEqual(
    page.viewportSize()!.width,
  );
});
