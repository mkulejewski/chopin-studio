import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
type Entry = { task: pdfjs.PDFDocumentLoadingTask; users: number };
// Two warm volumes; documents in use by a viewer cannot be evicted.
const documents = new Map<string, Entry>();
function trim() {
  while (documents.size > 2) {
    const oldest = [...documents.keys()].find(
      (key) => !documents.get(key)!.users,
    );
    if (!oldest) break;
    const old = documents.get(oldest)!;
    documents.delete(oldest);
    void old.task.destroy().catch(() => {});
  }
}
function acquire(id: string, filename: string, retain: boolean) {
  const key = `${id}:${filename}`;
  let entry = documents.get(key);
  if (!entry) {
    entry = { task: pdfjs.getDocument(`/api/volumes/${id}/pdf`), users: 0 };
    const owned = entry;
    void entry.task.promise.catch(() => {
      if (documents.get(key) === owned) documents.delete(key);
    });
  }
  if (retain) entry.users++;
  // Refresh access order, including hits to an older cached document.
  documents.delete(key);
  documents.set(key, entry);
  trim();
  return entry;
}
export function preloadScore(id: string, filename: string) {
  return acquire(id, filename, false).task.promise;
}
export function retainScore(id: string, filename: string) {
  const entry = acquire(id, filename, true);
  let released = false;
  return {
    promise: entry.task.promise,
    release() {
      if (released) return;
      released = true;
      entry.users--;
      trim();
    },
  };
}
