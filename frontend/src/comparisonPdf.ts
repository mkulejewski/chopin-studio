import type { NoteGroup } from "./AnalysisEvidence";
import type { ComparisonMode } from "./comparisonJudgement";
import { buildComparisonMusicXml, type ScoreView } from "./comparisonScore";

const VIEW_NAMES: Record<ScoreView, string> = {
  overlay: "Overlaid reference and played notes",
  stacked: "Reference above played notes",
  reference: "Reference notes",
  played: "Played notes",
};

/** Render the complete activity independently of screen pagination and filters. */
export async function compileComparisonPdf({
  groups,
  view,
  mode,
  title,
  fifths = 0,
  signal,
  onProgress,
}: {
  groups: NoteGroup[];
  view: ScoreView;
  mode: ComparisonMode;
  title: string;
  fifths?: number;
  signal: AbortSignal;
  onProgress: (message: string) => void;
}): Promise<{ blob: Blob; pages: number }> {
  signal.throwIfAborted();
  onProgress(`Compiling all ${groups.length} score groups…`);
  const xml = buildComparisonMusicXml(groups, view, mode, fifths);
  const [{ OpenSheetMusicDisplay }, { jsPDF }] = await Promise.all([
    import("opensheetmusicdisplay"),
    import("jspdf"),
  ]);
  await import("svg2pdf.js");
  signal.throwIfAborted();
  const host = document.createElement("div");
  // It must have real layout and visible SVG styles for engraving and vector
  // conversion, while remaining outside the user's viewport.
  host.style.cssText =
    "position:fixed;left:-20000px;top:0;width:1000px;pointer-events:none;background:white;";
  host.setAttribute("aria-hidden", "true");
  document.body.append(host);
  const display = new OpenSheetMusicDisplay(host, {
    backend: "svg",
    autoResize: false,
    pageFormat: "A4_P",
    drawingParameters: "compacttight",
    drawTitle: false,
    drawComposer: false,
    drawPartNames: view === "stacked",
    coloringEnabled: true,
    colorStemsLikeNoteheads: true,
    autoBeam: false,
    drawTimeSignatures: false,
    drawMeasureNumbers: false,
  });
  try {
    display.EngravingRules.SetWantedStemDirectionByXml = true;
    display.Zoom = 0.9;
    await display.load(xml);
    signal.throwIfAborted();
    display.render();
    display.renderRemaining();
    const pages = Array.from(host.querySelectorAll("svg")).filter(
      (svg) => !svg.parentElement?.closest("svg"),
    );
    if (!pages.length) throw new Error("No engraved pages were produced.");
    const pdf = new jsPDF({
      orientation: "portrait",
      unit: "mm",
      format: "a4",
      compress: true,
    });
    pdf.setProperties({
      title: `${title} - ${mode} comparison`,
      author: "Chopin Studio",
      subject: VIEW_NAMES[view],
    });
    for (let i = 0; i < pages.length; i++) {
      signal.throwIfAborted();
      onProgress(`Preparing PDF page ${i + 1} of ${pages.length}…`);
      if (i > 0) pdf.addPage();
      const svg = pages[i];
      const box = svg.viewBox.baseVal;
      const width =
        box.width || Number.parseFloat(svg.getAttribute("width") || "0");
      const height =
        box.height || Number.parseFloat(svg.getAttribute("height") || "0");
      if (!(width > 0 && height > 0))
        throw new Error("Invalid engraved page dimensions.");
      const scale = Math.min(190 / width, 246 / height);
      const drawnWidth = width * scale;
      await pdf.svg(svg, {
        x: (210 - drawnWidth) / 2,
        y: 36,
        width: drawnWidth,
        height: height * scale,
      });
      signal.throwIfAborted();
      // svg2pdf changes text spacing while fitting SVG labels. Reset it for
      // the report's own header/footer rather than inheriting engraving state.
      pdf.setCharSpace(0);
      pdf.setLineHeightFactor(1.15);
      pdf.setFont("helvetica", "bold");
      pdf.setFontSize(11);
      pdf.setTextColor(37, 62, 50);
      const titleLines = (pdf.splitTextToSize(title, 190) as string[]).slice(
        0,
        2,
      );
      pdf.text(titleLines, 10, 9);
      pdf.setFont("helvetica", "normal");
      pdf.setFontSize(8);
      pdf.text(
        `${mode === "strict" ? "Strict digital reference" : "Musical context"} | ${VIEW_NAMES[view]} | Entire activity: ${groups.length} groups`,
        10,
        21,
      );
      pdf.setTextColor(193, 39, 61);
      if (mode === "strict")
        pdf.text("Red: exact reference differences.", 10, 26);
      else {
        const redLegend = "Red: likely pitch/chord errors.";
        pdf.text(redLegend, 10, 26);
        const blueX = 12 + pdf.getTextWidth(redLegend);
        pdf.setTextColor(35, 100, 180);
        pdf.text("Blue: possible adaptation or uncertainty.", blueX, 26);
      }
      pdf.setTextColor(80, 80, 80);
      pdf.setFontSize(7.5);
      pdf.text(
        "Reference grey; played dark. Diamond: absent reference pitch; x: extra played pitch. Rhythm aligned to reference.",
        10,
        31,
      );
      pdf.text(
        `Chopin Studio | ${i + 1} / ${pages.length} | Note values and engraving simplified; musical judgements require review.`,
        10,
        291,
      );
      // Let the browser paint progress and handle cancellation between pages.
      await new Promise<void>((resolve) => setTimeout(resolve, 0));
    }
    signal.throwIfAborted();
    return { blob: pdf.output("blob"), pages: pages.length };
  } finally {
    display.clear();
    host.remove();
  }
}
