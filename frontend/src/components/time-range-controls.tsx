import { format } from "date-fns";
import { CalendarIcon } from "lucide-react";
import type { DateRange } from "react-day-picker";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { buildRelativeDateRange, RELATIVE_UNITS, type RelativeUnit } from "@/lib/time-range";
import { cn, formatActivityLabel } from "@/lib/utils";

function formatDateRangeLabel(dateRange?: DateRange) {
  if (!dateRange?.from) return "All dates";
  if (!dateRange.to) return format(dateRange.from, "MMM d, yyyy");
  return `${format(dateRange.from, "MMM d, yyyy")} - ${format(dateRange.to, "MMM d, yyyy")}`;
}

export function TimeRangeControls({
  dateRange,
  setDateRange,
  relativeValue,
  setRelativeValue,
  relativeUnit,
  setRelativeUnit,
}: {
  dateRange?: DateRange;
  setDateRange: (range: DateRange | undefined) => void;
  relativeValue: string;
  setRelativeValue: (value: string) => void;
  relativeUnit: RelativeUnit;
  setRelativeUnit: (unit: RelativeUnit) => void;
}) {
  const applyRelativeRange = () => {
    const amount = Number.parseInt(relativeValue, 10);
    if (Number.isFinite(amount) && amount > 0) {
      setDateRange(buildRelativeDateRange(amount, relativeUnit));
    }
  };

  return (
    <>
      <div className="space-y-2">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Date range
        </p>
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              className={cn(
                "w-full justify-start text-left font-normal",
                !dateRange?.from && "text-muted-foreground",
              )}
            >
              <CalendarIcon className="mr-2 size-4" />
              {formatDateRangeLabel(dateRange)}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="range"
              selected={dateRange}
              onSelect={(nextRange) => {
                setDateRange(nextRange);
                setRelativeValue("");
              }}
              numberOfMonths={2}
            />
          </PopoverContent>
        </Popover>
      </div>

      <div className="grid gap-4 sm:grid-cols-[100px_160px_auto] sm:items-end">
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Last</p>
          <Input
            type="number"
            inputMode="numeric"
            min={1}
            placeholder="12"
            value={relativeValue}
            onChange={(event) => setRelativeValue(event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Unit</p>
          <Select
            value={relativeUnit}
            onValueChange={(value) => setRelativeUnit(value as RelativeUnit)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {RELATIVE_UNITS.map((unit) => (
                <SelectItem key={unit} value={unit}>
                  {formatActivityLabel(unit)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button onClick={applyRelativeRange} disabled={!relativeValue}>
          Apply range
        </Button>
      </div>
    </>
  );
}
