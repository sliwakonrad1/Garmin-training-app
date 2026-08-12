import { subDays, subMonths, subWeeks, subYears } from "date-fns";
import type { DateRange } from "react-day-picker";

export const RELATIVE_UNITS = ["days", "weeks", "months", "years"] as const;
export type RelativeUnit = (typeof RELATIVE_UNITS)[number];

export function buildRelativeDateRange(amount: number, unit: RelativeUnit): DateRange {
  const to = new Date();

  switch (unit) {
    case "days":
      return { from: subDays(to, amount), to };
    case "weeks":
      return { from: subWeeks(to, amount), to };
    case "months":
      return { from: subMonths(to, amount), to };
    case "years":
      return { from: subYears(to, amount), to };
  }
}
