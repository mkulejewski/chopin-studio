import type { Piece } from "./api";

const units = [
  "zero",
  "one",
  "two",
  "three",
  "four",
  "five",
  "six",
  "seven",
  "eight",
  "nine",
  "ten",
  "eleven",
  "twelve",
  "thirteen",
  "fourteen",
  "fifteen",
  "sixteen",
  "seventeen",
  "eighteen",
  "nineteen",
];
const tens = [
  "twenty",
  "thirty",
  "forty",
  "fifty",
  "sixty",
  "seventy",
  "eighty",
  "ninety",
];
function tokens(text: string, keepLabels = false): string[] {
  const words = text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\bop\b/g, "opus")
    .replace(/\bno\b/g, "number")
    .replace(/\b(please|the|in|chopin|by)\b/g, " ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .split(/\s+/);
  const result: string[] = [];
  for (let i = 0; i < words.length; i++) {
    const unit = units.indexOf(words[i]);
    const ten = tens.indexOf(words[i]);
    if (ten >= 0) {
      const next = units.indexOf(words[i + 1]);
      result.push(String((ten + 2) * 10 + (next > 0 && next < 10 ? next : 0)));
      if (next > 0 && next < 10) i++;
    } else
      result.push(
        unit >= 0
          ? String(unit)
          : ["opus", "number"].includes(words[i])
            ? words[i]
            : words[i].replace(/s$/, ""),
      );
  }
  return result.filter(
    (word) => word && (keepLabels || !["opus", "number"].includes(word)),
  );
}

export function resolveVoiceCommand(
  transcript: string,
  pieces: Piece[],
): { piece: Piece; message?: never } | { message: string; piece?: never } {
  const command = transcript.trim().replace(/[.!?]+$/, "");
  const match = command.match(
    /^(?:please\s+)?(?:open|show|load)(?:\s+score\s+for)?\s+(.+)$/i,
  );
  if (!match) return { message: "Say “Open Nocturne Opus Nine Number One”." };
  const query = tokens(match[1]);
  if (!query.length)
    return { message: "Please include the piece name and opus number." };
  const labelled = tokens(match[1], true);
  const numericField = (words: string[], label: string) => {
    const index = words.indexOf(label);
    return index >= 0 && /^\d+$/.test(words[index + 1] || "")
      ? words[index + 1]
      : undefined;
  };
  const matches = pieces.filter((piece) => {
    const catalogue = tokens(`opus ${piece.opus}`, true);
    for (const label of ["opus", "number"]) {
      const requested = numericField(labelled, label);
      if (requested && requested !== numericField(catalogue, label))
        return false;
    }
    const candidate = new Set(
      tokens(
        `${piece.title} ${piece.genre} ${piece.opus} ${piece.musical_key}`,
      ),
    );
    return query.every((word) => candidate.has(word));
  });
  if (matches.length === 1) return { piece: matches[0] };
  if (!matches.length)
    return {
      message: `No library piece matches “${match[1]}”. Try its title, opus and number.`,
    };
  return {
    message: `“${match[1]}” matches ${matches.length} pieces. Include the opus, number or key.`,
  };
}
