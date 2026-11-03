import { test, expect } from "@playwright/test";
import { scorePdf } from "./pdf-fixture";

test("cached spreads contain both rendered pages and advance one page through rapid turns and resize", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const settings = await (await page.request.get("/api/settings")).json();
  await page.request.put("/api/settings", {
    data: { ...settings, live_enabled: false },
  });
  expect(
    (
      await page.request.post("/api/volumes/nocturnes/pdf", {
        multipart: {
          file: {
            name: "coloured-pages.pdf",
            mimeType: "application/pdf",
            buffer: scorePdf(10, true),
          },
        },
      })
    ).ok(),
  ).toBeTruthy();
  const library = await (await page.request.get("/api/library")).json();
  const piece = library.pieces.find((p: any) => p.id === "n9-1");
  await page.request.put("/api/pieces/n9-1", {
    data: { ...piece, start_page: 1, end_page: 10 },
  });
  await page.request.put("/api/pieces/n9-1/view", {
    data: { page: 1, zoom: 1, two_pages: true, crop: 0 },
  });
  await page.addInitScript(() => localStorage.setItem("chopin-piece", "n9-1"));
  await page.goto("/");
  const spread = async (first: number) => {
    for (const number of [first, first + 1].filter((n) => n <= 10)) {
      const canvas = page.getByLabel(`Score PDF page ${number}`, {
        exact: true,
      });
      await expect(canvas).toBeVisible();
      // Verify actual pixels, not just the presence of a blank canvas.
      await expect
        .poll(() =>
          canvas.evaluate((el: HTMLCanvasElement) => {
            const p = el
              .getContext("2d")!
              .getImageData(el.width / 2, el.height / 2, 1, 1).data;
            return Array.from(p);
          }),
        )
        .toEqual([Math.round((number / 11) * 255), 51, 102, 255]);
    }
  };
  await spread(1);
  await page.getByRole("button", { name: "Next page", exact: true }).tap();
  await spread(2);
  await page.getByRole("button", { name: "Previous page", exact: true }).tap();
  await spread(1);
  for (let i = 0; i < 5; i++) await page.keyboard.press("ArrowRight");
  await spread(6);
  await page.setViewportSize({ width: 1100, height: 850 });
  await spread(6);
  await page.getByLabel("First displayed page").fill("10");
  await expect(
    page.getByLabel("Score PDF page 10", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".paper-pair canvas:visible")).toHaveCount(1);
  await page.screenshot({
    path: `/tmp/chopin-cached-pages-${test.info().project.name}.png`,
  });
  expect(errors).toEqual([]);
  await page.request.put("/api/settings", { data: settings });
});
