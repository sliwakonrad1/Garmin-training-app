import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { useMemo, useState } from "react";
import type { DateRange } from "react-day-picker";

import { TimeRangeControls } from "@/components/time-range-controls";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  fetchActivities,
  fetchActivityBreakdown,
  fetchActivityGroups,
  type DashboardFilters,
} from "@/lib/api";
import type { RelativeUnit } from "@/lib/time-range";
import { formatActivityLabel, formatDistance, formatPace, getActivityColor } from "@/lib/utils";

export const Route = createFileRoute("/activities")({
  head: () => ({
    meta: [
      { title: "Activities — Garmin AI Trainer" },
      {
        name: "description",
        content: "Browse and filter every logged training session with distance, HR and load.",
      },
      { property: "og:title", content: "Activities — Garmin AI Trainer" },
      {
        property: "og:description",
        content: "Browse and filter every logged training session with distance, HR and load.",
      },
    ],
  }),
  component: Activities,
});

function formatValue(value: number | null, maximumFractionDigits: number) {
  if (value === null || value === 0) return "";

  return value.toLocaleString(undefined, {
    maximumFractionDigits,
    minimumFractionDigits: maximumFractionDigits,
  });
}

function Activities() {
  const [activityType, setActivityType] = useState("all");
  const [dateRange, setDateRange] = useState<DateRange | undefined>();
  const [relativeValue, setRelativeValue] = useState("");
  const [relativeUnit, setRelativeUnit] = useState<RelativeUnit>("weeks");
  const filters = useMemo<DashboardFilters>(() => {
    const startDate = dateRange?.from ? format(dateRange.from, "yyyy-MM-dd") : undefined;
    const endDate = dateRange?.to
      ? format(dateRange.to, "yyyy-MM-dd")
      : dateRange?.from
        ? format(dateRange.from, "yyyy-MM-dd")
        : undefined;
    return {
      activityType: activityType === "all" ? undefined : activityType,
      startDate,
      endDate,
    };
  }, [activityType, dateRange]);
  const queryScope = [
    filters.activityType ?? "all",
    filters.startDate ?? "all",
    filters.endDate ?? "all",
  ];
  const { data, isLoading, isError } = useQuery({
    queryKey: ["activities", ...queryScope],
    queryFn: () => fetchActivities(filters),
  });
  const activityGroups = useQuery({
    queryKey: ["activity_groups"],
    queryFn: fetchActivityGroups,
  });
  const activityBreakdown = useQuery({
    queryKey: ["activity_breakdown", ...queryScope],
    queryFn: () => fetchActivityBreakdown(filters),
  });
  const rows = data ?? [];
  const hasActiveFilters = Boolean(filters.activityType || filters.startDate || filters.endDate);

  const clearFilters = () => {
    setActivityType("all");
    setDateRange(undefined);
    setRelativeValue("");
    setRelativeUnit("weeks");
  };

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Activities</h1>
        <p className="text-sm text-muted-foreground">{rows.length} sessions</p>
      </div>

      <Card className="border-border/60 bg-card">
        <CardHeader>
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-[minmax(260px,340px)_1fr_auto] lg:items-end">
          <TimeRangeControls
            dateRange={dateRange}
            setDateRange={setDateRange}
            relativeValue={relativeValue}
            setRelativeValue={setRelativeValue}
            relativeUnit={relativeUnit}
            setRelativeUnit={setRelativeUnit}
          />
          <Button
            variant="ghost"
            onClick={clearFilters}
            disabled={!hasActiveFilters && !relativeValue}
          >
            Clear filters
          </Button>
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-2">
        {["all", ...(activityGroups.data ?? []).map(({ group }) => group)].map((type) => {
          const color = type === "all" ? undefined : getActivityColor(type);
          const selected = activityType === type;
          return (
            <Button
              key={type}
              size="sm"
              variant={type === "all" && selected ? "default" : "outline"}
              className="rounded-full"
              style={
                color
                  ? {
                      borderColor: `${color}80`,
                      backgroundColor: selected ? color : `${color}1A`,
                      color: selected ? "#fff" : color,
                    }
                  : undefined
              }
              onClick={() => setActivityType(type)}
            >
              {type === "all" ? "All" : formatActivityLabel(type)}
            </Button>
          );
        })}
      </div>

      {activityType !== "all" ? (
        <div className="flex flex-wrap gap-2">
          {(activityGroups.data ?? [])
            .find(({ group }) => group === activityType)
            ?.activity_types.filter((type) => type !== activityType)
            .map((type) => (
              <Button
                key={type}
                size="sm"
                variant="outline"
                className="rounded-full"
                onClick={() => setActivityType(type)}
              >
                {formatActivityLabel(type)}
              </Button>
            ))}
        </div>
      ) : null}

      {activityType === "all" && activityBreakdown.data?.length ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {activityBreakdown.data.map((group) => (
            <Button
              key={group.activity_group}
              variant="outline"
              className="h-auto justify-start p-4 text-left"
              onClick={() => setActivityType(group.activity_group)}
            >
              <span>
                <span className="block font-medium">
                  {formatActivityLabel(group.activity_group)}
                </span>
                <span className="block text-xs text-muted-foreground">
                  {group.sessions} sessions · {formatDistance(group.total_km)}
                </span>
                <span className="block text-xs text-muted-foreground">
                  {group.total_hours.toFixed(1)} h · load {group.total_load.toFixed(0)}
                </span>
              </span>
            </Button>
          ))}
        </div>
      ) : null}

      <Card className="border-border/60 bg-card">
        <CardContent className="p-0">
          {isError ? (
            <p className="p-6 text-sm text-destructive">Could not load activities.</p>
          ) : isLoading ? (
            <div className="space-y-2 p-6">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Date</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead className="text-right">Distance</TableHead>
                  <TableHead className="text-right">Pace</TableHead>
                  <TableHead className="text-right">Duration</TableHead>
                  <TableHead className="text-right">HR</TableHead>
                  <TableHead className="text-right">kcal</TableHead>
                  <TableHead className="text-right">Load</TableHead>
                  <TableHead className="text-right">VO2max</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((a, i) => (
                  <TableRow key={a.activity_id ?? `${a.start_time_local}-${i}`}>
                    <TableCell className="whitespace-nowrap text-muted-foreground">
                      {a.start_time_local}
                    </TableCell>
                    <TableCell>
                      <span
                        className="rounded-full px-2 py-0.5 text-xs font-medium"
                        style={{
                          backgroundColor: `${getActivityColor(a.activity_type)}1A`,
                          color: getActivityColor(a.activity_type),
                        }}
                      >
                        {formatActivityLabel(a.activity_type)}
                      </span>
                    </TableCell>
                    <TableCell className="font-medium">{a.activity_name}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatDistance(a.distance_km)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right tabular-nums">
                      {formatPace(a.pace_min_per_km)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatValue(a.duration_minutes, 0)}
                      {a.duration_minutes ? " min" : ""}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatValue(a.avg_hr, 0)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatValue(a.calories, 0)}
                    </TableCell>
                    <TableCell className="text-right font-semibold tabular-nums text-primary">
                      {formatValue(a.training_load, 1)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatValue(a.vo2max, 1)}
                    </TableCell>
                  </TableRow>
                ))}
                {rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="py-10 text-center text-muted-foreground">
                      No activities found.
                    </TableCell>
                  </TableRow>
                ) : null}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
