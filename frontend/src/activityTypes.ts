export const activityTypes: Record<string, string> = {
  unknown: "Unidentified material",
  partial: "Partial attempt",
  exercise: "Partial exercise",
  full_exercise: "Full-piece exercise",
  complete: "Complete performance",
};
export const activityLabel = (kind: string) => activityTypes[kind] || kind;
