export const pitches = [
  60, 64, 67, 62, 69, 65, 71, 63, 68, 66, 73, 70, 72, 75, 74, 77, 76, 79, 78,
  81,
];
export function musicXml(): Buffer {
  const names = ["C", "C", "D", "D", "E", "F", "F", "G", "G", "A", "A", "B"];
  const sharps = new Set([1, 3, 6, 8, 10]);
  const notes = [...pitches, ...pitches];
  let measures = "";
  for (let i = 0; i < notes.length; i += 4) {
    const group = notes
      .slice(i, i + 4)
      .map(
        (p) =>
          `<note><pitch><step>${names[p % 12]}</step>${sharps.has(p % 12) ? "<alter>1</alter>" : ""}<octave>${Math.floor(p / 12) - 1}</octave></pitch><duration>1</duration><type>quarter</type></note>`,
      )
      .join("");
    measures += `<measure number="${i / 4 + 1}">${i === 0 ? "<attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>" : ""}${group}</measure>`;
  }
  return Buffer.from(
    `<score-partwise version="4.0"><work><work-title>Original synthetic navigation fixture</work-title></work><part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list><part id="P1">${measures}</part></score-partwise>`,
  );
}
function variable(n: number) {
  const bytes = [n & 127];
  while ((n >>= 7)) bytes.unshift((n & 127) | 128);
  return Buffer.from(bytes);
}
export function midiFixture(): Buffer {
  const events: Buffer[] = [Buffer.from([0, 255, 81, 3, 7, 161, 32])];
  const notes = [...pitches, ...pitches];
  for (let repeat = 0; repeat < 2; repeat++)
    for (let i = 0; i < notes.length; i++) {
      events.push(
        variable(repeat && i === 0 ? 7680 : i ? 48 : 0),
        Buffer.from([144, notes[i], 80]),
        variable(144),
        Buffer.from([128, notes[i], 0]),
      );
    }
  events.push(Buffer.from([0, 255, 47, 0]));
  const track = Buffer.concat(events);
  const header = Buffer.from("4d546864000000060000000101e0", "hex");
  const chunk = Buffer.alloc(8);
  chunk.write("MTrk");
  chunk.writeUInt32BE(track.length, 4);
  return Buffer.concat([header, chunk, track]);
}
