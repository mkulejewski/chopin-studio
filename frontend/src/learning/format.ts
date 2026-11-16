export const kindName = (kind?: string) =>
  ({
    visible: "Study with the score",
    hidden: "Recall from memory",
    connection: "Connect this section",
    cumulative: "Recall all learned sections",
    transition: "Connect the section boundary",
    assembly: "Join the larger form",
    review: "Previously learned chunks · review",
  })[kind || "visible"];
export const range = (a: number, b: number) =>
  `${a === 0 ? "Pickup" : a}${a === b ? "" : `–${b}`}`;
export const noteName = (p: number) =>
  ["C", "D♭", "D♮", "E♭", "E♮", "F", "G♭", "G", "A♭", "A♮", "B♭", "B♮"][
    p % 12
  ] +
  (Math.floor(p / 12) - 1);
export function noteNumber(name: string) {
  const match = /^([A-Ga-g])([#b♯♭♮]?)(-?\d)$/.exec(name.trim());
  if (!match) throw new Error("Enter a note such as C4, F#4 or B♭3.");
  const pitch =
    (Number(match[3]) + 1) * 12 +
    ({ C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }[match[1].toUpperCase()] ||
      0) +
    (["#", "♯"].includes(match[2])
      ? 1
      : ["b", "♭"].includes(match[2])
        ? -1
        : 0);
  if (pitch < 0 || pitch > 127)
    throw new Error("That note is outside the MIDI range.");
  return pitch;
}
