import { beforeEach, expect, it, vi } from "vitest";
const { getDocument, tasks } = vi.hoisted(() => {
  const tasks: {
    promise: Promise<object>;
    destroy: ReturnType<typeof vi.fn>;
  }[] = [];
  return {
    tasks,
    getDocument: vi.fn(() => {
      const task = {
        promise: Promise.resolve({}),
        destroy: vi.fn(async () => {}),
      };
      tasks.push(task);
      return task;
    }),
  };
});
vi.mock("pdfjs-dist", () => ({ getDocument, GlobalWorkerOptions: {} }));
beforeEach(() => {
  vi.resetModules();
  tasks.length = 0;
  getDocument.mockClear();
});

it("does not destroy the active document when other volumes are preloaded", async () => {
  const { retainScore, preloadScore } = await import("./pdfCache");
  const retained = retainScore("active", "a.pdf");
  await preloadScore("second", "b.pdf");
  await preloadScore("third", "c.pdf");
  expect(tasks[0].destroy).not.toHaveBeenCalled();
  expect(tasks[1].destroy).toHaveBeenCalledOnce();
  retained.release();
  retained.release();
  await preloadScore("fourth", "d.pdf");
  expect(tasks[0].destroy).toHaveBeenCalledOnce();
});

it("refreshes document access order on cache hits", async () => {
  const { preloadScore } = await import("./pdfCache");
  await preloadScore("a", "a.pdf");
  await preloadScore("b", "b.pdf");
  await preloadScore("a", "a.pdf");
  await preloadScore("c", "c.pdf");
  expect(getDocument).toHaveBeenCalledTimes(3);
  expect(tasks[0].destroy).not.toHaveBeenCalled();
  expect(tasks[1].destroy).toHaveBeenCalledOnce();
});
