import { expect, test } from "@playwright/test";
import { writeFile } from "node:fs/promises";
import { scorePdf } from "./pdf-fixture";

test("repeated score navigation reuses the PDF and records workload measurements", async ({
  page,
}, info) => {
  test.setTimeout(90000);
  const settings = await (await page.request.get("/api/settings")).json();
  await page.request.put("/api/settings", {
    data: { ...settings, live_enabled: false },
  });
  await page.request.post("/api/volumes/nocturnes/pdf", {
    multipart: {
      file: {
        name: "synthetic-navigation-profile.pdf",
        mimeType: "application/pdf",
        buffer: scorePdf(12, true),
      },
    },
  });
  const library = await (await page.request.get("/api/library")).json();
  const piece = library.pieces.find((p: { id: string }) => p.id === "n9-1");
  await page.request.put("/api/pieces/n9-1", {
    data: { ...piece, start_page: 1, end_page: 12 },
  });
  await page.request.put("/api/pieces/n9-1/view", {
    data: { page: 1, zoom: 1, two_pages: false, crop: 0 },
  });
  await page.addInitScript(() => localStorage.setItem("chopin-piece", "n9-1"));
  let requests = 0;
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (request.url().endsWith("/api/volumes/nocturnes/pdf")) requests++;
  });
  await page.goto("/");
  await expect(
    page.getByLabel("Score PDF page 1", { exact: true }),
  ).toBeVisible();
  const samples: { milliseconds: number; jsHeapBytes: number | null }[] = [];
  for (let cycle = 0; cycle < 2; cycle++) {
    const start = Date.now();
    for (let number = 1; number <= 12; number++) {
      await page.getByLabel("First displayed page").fill(String(number));
      await expect(
        page.getByLabel(`Score PDF page ${number}`, { exact: true }),
      ).toBeVisible();
    }
    samples.push({
      milliseconds: Date.now() - start,
      jsHeapBytes: await page.evaluate(() => {
        const memory = (
          performance as Performance & { memory?: { usedJSHeapSize: number } }
        ).memory;
        return memory?.usedJSHeapSize ?? null;
      }),
    });
  }
  expect(requests).toBe(1);
  await expect(page.locator(".paper-pair canvas")).toHaveCount(2);
  expect(errors).toEqual([]);
  const payloads: Record<string, number> = {};
  for (const piece_id of ["e25-1", "p53", "n15-1"]) {
    expect(
      (
        await page.request.post("/api/learning/selection", {
          data: { piece_id },
        })
      ).ok(),
    ).toBeTruthy();
    const response = await page.request.get(`/api/learning/${piece_id}`);
    expect(response.ok()).toBeTruthy();
    payloads[piece_id] = (await response.body()).byteLength;
  }
  const output = info.outputPath("synthetic-rendering-profile.json");
  await writeFile(
    output,
    JSON.stringify(
      {
        viewport: page.viewportSize(),
        cycles: samples,
        pdfRequests: requests,
        learningSnapshotBytes: payloads,
        notice:
          "Chromium JS heap is descriptive; GPU/canvas/process RAM and long-session growth are not inferred. Cache eviction and cancellation have separate unit tests.",
      },
      null,
      2,
    ),
  );
  await info.attach("synthetic-rendering-profile", {
    path: output,
    contentType: "application/json",
  });
});
