// Original generated blank score-navigation fixture; no third-party sheet music.
export function scorePdf(pages = 3, coloured = false): Buffer {
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    `<< /Type /Pages /Kids [${Array.from({ length: pages }, (_, i) => `${3 + i * 2} 0 R`).join(" ")}] /Count ${pages} >>`,
  ];
  for (let i = 0; i < pages; i++) {
    const content = coloured
      ? `${(i + 1) / (pages + 1)} 0.2 0.4 rg 0 0 600 800 re f`
      : "";
    objects.push(
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Contents ${4 + i * 2} 0 R >>`,
    );
    objects.push(
      `<< /Length ${Buffer.byteLength(content)} >>\nstream\n${content}\nendstream`,
    );
  }
  let text = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((object, i) => {
    offsets.push(Buffer.byteLength(text));
    text += `${i + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xref = Buffer.byteLength(text);
  text += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  offsets
    .slice(1)
    .forEach(
      (offset) => (text += `${offset.toString().padStart(10, "0")} 00000 n \n`),
    );
  text += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(text);
}
