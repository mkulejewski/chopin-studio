import type { Analysis } from "./analysis";
import type { PassagePoint } from "./passages";
import type { PerformanceTake } from "./practice";

type ComparisonSide = {
  segment: PerformanceTake;
  analysis: Analysis["result"];
};
export type TakeComparison = {
  left: ComparisonSide;
  right: ComparisonSide;
  aligned: {
    status: string;
    notice: string;
    points: {
      measure: number | null;
      beat: number;
      left: PassagePoint;
      right: PassagePoint;
    }[];
  };
  notice: string;
};
