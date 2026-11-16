export const SCORE_SHARE_KEY = "chopin-learning-score-share";
export const DEFAULT_SCORE_SHARE = 2 / 3;
export function clampScoreShare(value: number, width = 0) {
  const available = Math.max(1, width - 12);
  const minimum = width
    ? Math.max(0.35, Math.min(220, width * 0.4) / available)
    : 0.35;
  const maximum = width
    ? Math.min(0.8, 1 - Math.min(240, width * 0.4) / available)
    : 0.8;
  return Math.max(minimum, Math.min(maximum, value));
}
export function savedScoreShare() {
  try {
    const saved = localStorage.getItem(SCORE_SHARE_KEY);
    const value = saved === null ? DEFAULT_SCORE_SHARE : Number(saved);
    return Number.isFinite(value)
      ? clampScoreShare(value)
      : DEFAULT_SCORE_SHARE;
  } catch {
    return DEFAULT_SCORE_SHARE;
  }
}
