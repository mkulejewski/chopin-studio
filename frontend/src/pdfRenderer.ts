import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist";

type Image = { canvas: HTMLCanvasElement; bytes: number };
export type Spread = {
  page: number;
  images: HTMLCanvasElement[];
};
const MEMORY_LIMIT = 64 * 1024 * 1024;
const PIXEL_LIMIT = 4 * 1024 * 1024;

/** One renderer per viewer: detached canvases, serialized work, bounded LRU. */
export class PdfRenderer {
  private cache = new Map<string, Image>();
  private bytes = 0;
  private generation = 0;
  private active?: RenderTask;
  private queue: Promise<void> = Promise.resolve();

  constructor(private doc: PDFDocumentProxy) {}

  request(
    page: number,
    end: number,
    two: boolean,
    width: number,
    height: number,
    ratio: number,
    ready: (spread: Spread) => void,
    failed: (error: unknown) => void,
  ) {
    const generation = ++this.generation;
    this.active?.cancel();
    const current = () => generation === this.generation;
    ratio = Math.min(ratio || 1, 2);
    const size = `${width}:${height}:${ratio}`;
    const visible = two && page < end ? [page, page + 1] : [page];
    // Retain one previous page and prepare four pages beyond the visible spread.
    const wanted = new Set(
      Array.from({ length: visible.length + 5 }, (_, i) => page - 1 + i)
        .filter((p) => p > 0 && p <= end)
        .map((p) => `${size}:${p}`),
    );
    const protectedKeys = new Set(visible.map((p) => `${size}:${p}`));
    const release = (key: string) => {
      const image = this.cache.get(key)!;
      this.bytes -= image.bytes;
      image.canvas.width = image.canvas.height = 0;
      this.cache.delete(key);
    };
    const render = async (p: number, background = false) => {
      const key = `${size}:${p}`;
      const cached = this.cache.get(key);
      if (cached) {
        this.cache.delete(key);
        this.cache.set(key, cached);
        return cached.canvas;
      }
      const pdfPage = await this.doc.getPage(p);
      if (!current()) return null;
      const base = pdfPage.getViewport({ scale: 1 });
      const fit = Math.min(width / base.width, height / base.height);
      let scale = fit * ratio;
      scale = Math.min(
        scale,
        Math.sqrt(PIXEL_LIMIT / (base.width * base.height)),
      );
      const viewport = pdfPage.getViewport({ scale });
      const bytes =
        Math.max(1, Math.floor(viewport.width)) *
        Math.max(1, Math.floor(viewport.height)) *
        4;
      // Preserve the closest prefetched pages if the memory budget is exhausted.
      if (background && this.bytes + bytes > MEMORY_LIMIT) return null;
      while (this.bytes + bytes > MEMORY_LIMIT) {
        const victim = [...this.cache.keys()].find(
          (k) => !protectedKeys.has(k),
        );
        if (!victim) break;
        release(victim);
      }
      const canvas = document.createElement("canvas");
      canvas.style.width = `${base.width * fit}px`;
      canvas.style.height = `${base.height * fit}px`;
      canvas.width = Math.max(1, Math.floor(viewport.width));
      canvas.height = Math.max(1, Math.floor(viewport.height));
      const task = pdfPage.render({
        canvasContext: canvas.getContext("2d")!,
        viewport,
      });
      this.active = task;
      task.onContinue = (resume: () => void) => {
        setTimeout(() => (current() ? resume() : task.cancel()), 0);
      };
      try {
        await task.promise;
        if (!current()) {
          canvas.width = canvas.height = 0;
          return null;
        }
        this.cache.set(key, { canvas, bytes });
        this.bytes += bytes;
        return canvas;
      } catch (error) {
        canvas.width = canvas.height = 0;
        throw error;
      } finally {
        if (this.active === task) this.active = undefined;
        pdfPage.cleanup();
      }
    };
    this.queue = this.queue
      .catch(() => {})
      .then(async () => {
        if (!current()) return;
        for (const key of this.cache.keys()) if (!wanted.has(key)) release(key);
        try {
          const images: HTMLCanvasElement[] = [];
          for (const p of visible) {
            const image = await render(p);
            if (!image || !current()) return;
            images.push(image);
          }
          ready({ page, images });
        } catch (error) {
          if (current()) failed(error);
          return;
        }
        for (
          let p = visible[visible.length - 1] + 1;
          p <= Math.min(end, visible[visible.length - 1] + 4);
          p++
        ) {
          // Yield between pages so controls and recording UI remain responsive.
          await new Promise((resolve) => setTimeout(resolve, 0));
          if (!current()) return;
          try {
            if (!(await render(p, true))) return;
          } catch {
            /* Foreground navigation retries failed prefetches. */
          }
        }
      });
    return () => {
      if (current()) {
        ++this.generation;
        this.active?.cancel();
      }
    };
  }

  dispose() {
    ++this.generation;
    this.active?.cancel();
    for (const { canvas } of this.cache.values())
      canvas.width = canvas.height = 0;
    this.cache.clear();
    this.bytes = 0;
  }
}
