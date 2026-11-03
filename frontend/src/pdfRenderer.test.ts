import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { PDFDocumentProxy } from "pdfjs-dist";
import { PdfRenderer } from "./pdfRenderer";

function fixture() {
  const calls: number[] = [];
  const failures = new Set<number>();
  let hold: number | null = null;
  let finish: (() => void) | undefined;
  const doc = {
    getPage: vi.fn(async (page: number) => ({
      getViewport: ({ scale }: { scale: number }) => ({
        width: 600 * scale,
        height: 800 * scale,
      }),
      cleanup: vi.fn(),
      render: () => {
        calls.push(page);
        let reject!: (error: Error) => void;
        const promise = new Promise<void>((resolve, fail) => {
          reject = fail;
          if (failures.has(page)) fail(new Error("Broken page"));
          else if (hold === page) finish = resolve;
          else resolve();
        });
        return { promise, cancel: () => reject(new Error("cancelled")) };
      },
    })),
  } as unknown as PDFDocumentProxy;
  return {
    renderer: new PdfRenderer(doc),
    calls,
    failures,
    hold: (page: number) => {
      hold = page;
    },
    finish: () => finish?.(),
  };
}

beforeEach(() => {
  vi.stubGlobal("document", {
    createElement: () => ({
      width: 0,
      height: 0,
      style: {},
      getContext: () => ({}),
    }),
  });
});
afterEach(() => vi.unstubAllGlobals());

describe("PDF rendering queue", () => {
  it("prepares four following pages and reuses overlapping spreads", async () => {
    const { renderer, calls } = fixture();
    const ready = vi.fn();
    renderer.request(1, 12, true, 600, 800, 1, ready, vi.fn());
    await vi.waitFor(() => expect(calls).toEqual([1, 2, 3, 4, 5, 6]));
    renderer.request(2, 12, true, 600, 800, 1, ready, vi.fn());
    await vi.waitFor(() => expect(ready).toHaveBeenCalledTimes(2));
    expect(ready.mock.calls[1][0].images).toHaveLength(2);
    expect(calls.filter((p) => p === 2 || p === 3)).toEqual([2, 3]);
    renderer.dispose();
  });

  it("commits a spread only after both pages finish and cancels obsolete work", async () => {
    const f = fixture();
    f.hold(2);
    const old = vi.fn(),
      next = vi.fn(),
      failed = vi.fn();
    f.renderer.request(1, 8, true, 600, 800, 1, old, failed);
    await vi.waitFor(() => expect(f.calls).toEqual([1, 2]));
    expect(old).not.toHaveBeenCalled();
    f.renderer.request(3, 8, true, 600, 800, 1, next, failed);
    await vi.waitFor(() => expect(next).toHaveBeenCalledOnce());
    expect(old).not.toHaveBeenCalled();
    expect(failed).not.toHaveBeenCalled();
    f.renderer.dispose();
  });

  it("reports failed foreground pages and retries without clearing successful cached pages", async () => {
    const f = fixture();
    f.failures.add(2);
    const ready = vi.fn(),
      failed = vi.fn();
    f.renderer.request(1, 2, true, 600, 800, 1, ready, failed);
    await vi.waitFor(() => expect(failed).toHaveBeenCalledOnce());
    expect(ready).not.toHaveBeenCalled();
    f.failures.clear();
    f.renderer.request(1, 2, true, 600, 800, 1, ready, failed);
    await vi.waitFor(() => expect(ready).toHaveBeenCalledOnce());
    expect(f.calls).toEqual([1, 2, 2]);
    f.renderer.dispose();
  });

  it("bounds high-resolution prefetch memory while retaining the nearest pages", async () => {
    const f = fixture();
    const ready = vi.fn();
    f.renderer.request(1, 20, true, 3000, 4000, 2, ready, vi.fn());
    await vi.waitFor(() => expect(f.calls).toHaveLength(4));
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(f.calls).toEqual([1, 2, 3, 4]);
    expect(
      ready.mock.calls[0][0].images[0].width *
        ready.mock.calls[0][0].images[0].height,
    ).toBeLessThanOrEqual(4 * 1024 * 1024);
    f.renderer.dispose();
  });
});
