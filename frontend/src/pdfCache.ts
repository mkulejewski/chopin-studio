import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
// Keep the current and previous volume warm when switching library/practice views.
const documents = new Map<string, pdfjs.PDFDocumentLoadingTask>();
export function preloadScore(id: string, filename: string) {
  const key = `${id}:${filename}`;
  let task = documents.get(key);
  if (!task) {
    task = pdfjs.getDocument(`/api/volumes/${id}/pdf`);
    documents.set(key, task);
    const owned = task;
    void task.promise.catch(() => {
      if (documents.get(key) === owned) documents.delete(key);
    });
    while (documents.size > 2) {
      const oldest = documents.keys().next().value!;
      const old = documents.get(oldest)!;
      documents.delete(oldest);
      void old.destroy().catch(() => {});
    }
  }
  return task.promise;
}
