/** Hide the historical arecord clean-stop diagnostic in saved-take views only.
 * Keep original metadata and every warning containing other capture errors.
 */
export function captureWarning(error?: string | null): string | null {
  if (!error) return null;
  const remaining = error.split(/;\s*/).filter((part) => {
    const lines = part
      .replace(
        /^Microphone stopped unexpectedly or reported capture errors:\s*/,
        "",
      )
      .trim()
      .split(/\r?\n/);
    const interrupted =
      /^arecord: pcm_read:\d+: read error: Interrupted system call$/;
    return !(
      lines.some((line) => interrupted.test(line.trim())) &&
      lines.every(
        (line) =>
          interrupted.test(line.trim()) ||
          /^Aborted by signal (Interrupt|Terminated)\.\.\.$/.test(line.trim()),
      )
    );
  });
  return remaining.join("; ").trim() || null;
}
