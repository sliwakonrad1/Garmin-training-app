import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { useMemo, useState } from "react";
import type { DateRange } from "react-day-picker";
import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, Clock, Flame, Gauge, Route as RouteIcon } from "lucide-react";

import { TimeRangeControls } from "@/components/time-range-controls";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  fetchActivityGroups,
  fetchCardiacDrift,
  fetchEfficiencyScatter,
  fetchEfficiencyTrend,
  fetchHrDistribution,
  fetchSummary,
  fetchVo2maxTrend,
  fetchWeekly,
  type DashboardFilters,
  type CardiacDriftPoint,
  type EfficiencyScatterPoint,
  type EfficiencyPoint,
} from "@/lib/api";
import type { RelativeUnit } from "@/lib/time-range";
import {
  formatActivityLabel,
  formatNumberDynamic,
  getActivityColor,
  type DynamicNumberFormatOptions,
} from "@/lib/utils";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Dashboard — Garmin AI Trainer" },
      {
        name: "description",
        content:
          "Filtered training KPIs, weekly time by activity, VO2max trend and heart-rate trends.",
      },
      { property: "og:title", content: "Dashboard — Garmin AI Trainer" },
      {
        property: "og:description",
        content:
          "Filtered training KPIs, weekly time by activity, VO2max trend and heart-rate trends.",
      },
    ],
  }),
  component: Dashboard,
});

const GREEN = "#22c55e";
const GRID_COLOR = "rgba(255,255,255,0.07)";
const AXIS_COLOR = "#8b8b8b";

function formatCompactTick(value: number) {
  return formatNumberDynamic(value, {
    maximumFractionDigits: 0,
    compactMaximumFractionDigits: 1,
  });
}

function EmptyChartState() {
  return (
    <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
      No data for the current filters.
    </div>
  );
}

function KpiCard({
  label,
  value,
  unit,
  formatOptions,
  icon: Icon,
  loading,
}: {
  label: string;
  value?: number | undefined;
  unit?: string | undefined;
  formatOptions?: DynamicNumberFormatOptions;
  icon: typeof Activity;
  loading: boolean;
}) {
  const formattedValue = formatNumberDynamic(value, formatOptions);

  return (
    <Card className="border-border/60 bg-card">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </CardTitle>
        <Icon className="size-4 text-primary" />
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-20" />
        ) : (
          <p className="text-3xl font-semibold tabular-nums">
            {formattedValue}
            {unit && value !== null && value !== undefined ? (
              <span className="ml-1 text-sm text-muted-foreground">{unit}</span>
            ) : null}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

const tooltipStyle = {
  backgroundColor: "hsl(0 0% 12%)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 8,
  color: "#fafafa",
  fontSize: 12,
};

function EfficiencyTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ payload: EfficiencyPoint }>;
  label?: string;
}) {
  if (!active || !payload?.length) {
    return null;
  }

  const point = payload[0].payload;

  return (
    <div style={tooltipStyle} className="space-y-1 p-3">
      <p className="font-medium">{point.activity_name}</p>
      <p>{label}</p>
      <p>
        Efficiency:{" "}
        {formatNumberDynamic(point.efficiency, {
          maximumFractionDigits: 2,
          minimumFractionDigits: 2,
        })}
      </p>
      <p>
        Distance:{" "}
        {formatNumberDynamic(point.distance_km, {
          maximumFractionDigits: 1,
          minimumFractionDigits: 1,
        })}{" "}
        km
      </p>
      <p>HR: {formatNumberDynamic(point.avg_hr, { maximumFractionDigits: 0 })} bpm</p>
      <p>
        Temperature:{" "}
        {formatNumberDynamic(point.temperature, {
          maximumFractionDigits: 1,
          minimumFractionDigits: 1,
        })}
        °C
      </p>
      <p>
        Elevation gain: {formatNumberDynamic(point.elevation_gain, { maximumFractionDigits: 0 })} m
        ({formatNumberDynamic(point.elevation_per_100m, { maximumFractionDigits: 1 })} m / 100 m)
      </p>
    </div>
  );
}

function EfficiencyScatterTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: EfficiencyScatterPoint }>;
}) {
  if (!active || !payload?.length) {
    return null;
  }

  const point = payload[0].payload;

  return (
    <div style={tooltipStyle} className="space-y-1 p-3">
      <p className="font-medium">{point.activity_name}</p>
      <p>{point.date}</p>
      <p>
        Efficiency:{" "}
        {formatNumberDynamic(point.efficiency, {
          maximumFractionDigits: 2,
          minimumFractionDigits: 2,
        })}
      </p>
      <p>
        Distance: {formatNumberDynamic(point.distance_km, { maximumFractionDigits: 1 })} km
      </p>
      <p>HR: {formatNumberDynamic(point.avg_hr, { maximumFractionDigits: 0 })} bpm</p>
      <p>
        Temperature: {formatNumberDynamic(point.temperature, { maximumFractionDigits: 1 })}°C
      </p>
      <p>
        Elevation gain: {formatNumberDynamic(point.elevation_gain, { maximumFractionDigits: 0 })} m
      </p>
    </div>
  );
}

type ScatterMetric = "distance_km" | "temperature" | "elevation_per_100m";

const scatterConfig: Record<ScatterMetric, { label: string; unit: string }> = {
  distance_km: { label: "Distance", unit: "km" },
  temperature: { label: "Temperature", unit: "°C" },
  elevation_per_100m: { label: "Elevation gain", unit: "m / 100 m" },
};

function interpolateGreen(date: string, oldestDate: string, newestDate: string) {
  const oldest = new Date(oldestDate).getTime();
  const newest = new Date(newestDate).getTime();
  const current = new Date(date).getTime();
  const ratio = newest === oldest ? 1 : (current - oldest) / (newest - oldest);
  const from = [187, 247, 208];
  const to = [34, 197, 94];
  const color = from.map((channel, index) => Math.round(channel + (to[index] - channel) * ratio));
  return `rgb(${color.join(", ")})`;
}

function CardiacDriftTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ payload: CardiacDriftPoint }>;
  label?: string;
}) {
  if (!active || !payload?.length) {
    return null;
  }

  const point = payload[0].payload;

  return (
    <div style={tooltipStyle} className="space-y-1 p-3">
      <p className="font-medium">{label}</p>
      <p>
        Cardiac drift:{" "}
        {formatNumberDynamic(point.hr_drift_pct, {
          maximumFractionDigits: 1,
          minimumFractionDigits: 1,
        })}
        %
      </p>
      <p>
        Duration:{" "}
        {formatNumberDynamic(point.duration_minutes, {
          maximumFractionDigits: 0,
        })}{" "}
        min
      </p>
      <p>
        Distance:{" "}
        {formatNumberDynamic(point.distance_km, {
          maximumFractionDigits: 1,
          minimumFractionDigits: 1,
        })}{" "}
        km
      </p>
    </div>
  );
}

function Dashboard() {
  const [activityType, setActivityType] = useState("all");
  const [dateRange, setDateRange] = useState<DateRange | undefined>();
  const [relativeValue, setRelativeValue] = useState("");
  const [relativeUnit, setRelativeUnit] = useState<RelativeUnit>("weeks");
  const [scatterMetric, setScatterMetric] = useState<ScatterMetric>("distance_km");

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

  const activityGroups = useQuery({
    queryKey: ["activity_groups"],
    queryFn: fetchActivityGroups,
  });
  const summary = useQuery({
    queryKey: ["summary", ...queryScope],
    queryFn: () => fetchSummary(filters),
  });
  const weekly = useQuery({
    queryKey: ["weekly", ...queryScope],
    queryFn: () => fetchWeekly(filters),
  });
  const vo2 = useQuery({
    queryKey: ["vo2max_trend", ...queryScope],
    queryFn: () => fetchVo2maxTrend(filters),
  });
  const efficiency = useQuery({
    queryKey: ["efficiency_trend", ...queryScope],
    queryFn: () => fetchEfficiencyTrend(filters),
  });
  const efficiencyScatter = useQuery({
    queryKey: ["efficiency_scatter", ...queryScope],
    queryFn: () => fetchEfficiencyScatter(filters),
  });
  const cardiacDrift = useQuery({
    queryKey: ["cardiac_drift", ...queryScope],
    queryFn: () => fetchCardiacDrift(filters),
  });
  const hrDistribution = useQuery({
    queryKey: ["hr_distribution", ...queryScope],
    queryFn: () => fetchHrDistribution(filters),
  });

  const s = summary.data;
  const weeklyActivityTypes = useMemo(
    () =>
      Array.from(
        new Set((weekly.data ?? []).map((point) => point.activity_type).filter(Boolean)),
      ).sort(),
    [weekly.data],
  );
  const weeklySeries = useMemo(() => {
    const rows = new Map<string, Record<string, number | string>>();

    for (const point of weekly.data ?? []) {
      const row = rows.get(point.week) ?? { week: point.week };
      row[point.activity_type] = point.total_hours;
      rows.set(point.week, row);
    }

    return Array.from(rows.values()).sort((left, right) =>
      String(left.week).localeCompare(String(right.week)),
    );
  }, [weekly.data]);
  const hrActivityTypes = useMemo(
    () =>
      Array.from(
        new Set((hrDistribution.data ?? []).map((point) => point.activity_type).filter(Boolean)),
      ).sort(),
    [hrDistribution.data],
  );
  const hrSeries = useMemo(() => {
    const rows = new Map<string, Record<string, number | string>>();

    for (const point of hrDistribution.data ?? []) {
      const row = rows.get(point.date) ?? { date: point.date };
      row[point.activity_type] = point.avg_hr;
      rows.set(point.date, row);
    }

    return Array.from(rows.values()).sort((left, right) =>
      String(left.date).localeCompare(String(right.date)),
    );
  }, [hrDistribution.data]);
  const efficiencySeries = useMemo(
    () => [...(efficiency.data ?? [])].sort((left, right) => left.date.localeCompare(right.date)),
    [efficiency.data],
  );
  const scatterSeries = useMemo(() => {
    const points = [...(efficiencyScatter.data ?? [])].sort(
      (left, right) => left[scatterMetric] - right[scatterMetric],
    );
    if (points.length < 2) {
      return points.map((point) => ({ ...point, trend: point.efficiency }));
    }

    const count = points.length;
    const averageX = points.reduce((sum, point) => sum + point[scatterMetric], 0) / count;
    const averageY = points.reduce((sum, point) => sum + point.efficiency, 0) / count;
    const denominator = points.reduce(
      (sum, point) => sum + (point[scatterMetric] - averageX) ** 2,
      0,
    );
    const slope =
      denominator === 0
        ? 0
        : points.reduce(
            (sum, point) =>
              sum + (point[scatterMetric] - averageX) * (point.efficiency - averageY),
            0,
          ) / denominator;
    const intercept = averageY - slope * averageX;

    return points.map((point) => ({
      ...point,
      trend: slope * point[scatterMetric] + intercept,
    }));
  }, [efficiencyScatter.data, scatterMetric]);
  const scatterDateRange = useMemo(() => {
    const dates = (efficiencyScatter.data ?? []).map((point) => point.date).sort();
    return { oldest: dates[0] ?? "", newest: dates[dates.length - 1] ?? "" };
  }, [efficiencyScatter.data]);
  const cardiacDriftSeries = useMemo(
    () => [...(cardiacDrift.data ?? [])].sort((left, right) => left.date.localeCompare(right.date)),
    [cardiacDrift.data],
  );
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
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Your training at a glance</p>
      </div>

      <Card className="border-border/60 bg-card">
        <CardHeader>
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-[220px_minmax(260px,340px)_1fr_auto] lg:items-end">
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Activity type
            </p>
            <Select value={activityType} onValueChange={setActivityType}>
              <SelectTrigger>
                <SelectValue placeholder="All activities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All activities</SelectItem>
                {(activityGroups.data ?? []).flatMap(({ group, activity_types }) => [
                  <SelectItem key={group} value={group}>
                    {formatActivityLabel(group)}
                  </SelectItem>,
                  ...activity_types
                    .filter((type) => type !== group)
                    .map((type) => (
                      <SelectItem key={type} value={type}>
                        &nbsp;&nbsp;{formatActivityLabel(type)}
                      </SelectItem>
                    )),
                ])}
              </SelectContent>
            </Select>
          </div>

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

      {summary.isError ? (
        <p className="text-sm text-destructive">Could not load summary from the training API.</p>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <KpiCard
          label="Sessions"
          value={s?.sessions}
          formatOptions={{ maximumFractionDigits: 0, compactMaximumFractionDigits: 1 }}
          icon={Activity}
          loading={summary.isLoading}
        />
        <KpiCard
          label="Total km"
          value={s?.total_km}
          unit="km"
          formatOptions={{ maximumFractionDigits: 1, compactMaximumFractionDigits: 1 }}
          icon={RouteIcon}
          loading={summary.isLoading}
        />
        <KpiCard
          label="Hours"
          value={s?.hours}
          unit="h"
          formatOptions={{ maximumFractionDigits: 1, compactMaximumFractionDigits: 1 }}
          icon={Clock}
          loading={summary.isLoading}
        />
        <KpiCard
          label="Calories"
          value={s?.calories}
          unit="kcal"
          formatOptions={{ maximumFractionDigits: 0, compactMaximumFractionDigits: 1 }}
          icon={Flame}
          loading={summary.isLoading}
        />
        <KpiCard
          label="VO2max"
          value={s?.vo2max}
          formatOptions={{ maximumFractionDigits: 1, minimumFractionDigits: 1 }}
          icon={Gauge}
          loading={summary.isLoading}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-border/60 bg-card">
          <CardHeader>
            <CardTitle className="text-base">Weekly time spent by activity type</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            {weekly.isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : weeklySeries.length === 0 ? (
              <EmptyChartState />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weeklySeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
                  <XAxis
                    dataKey="week"
                    stroke={AXIS_COLOR}
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    stroke={AXIS_COLOR}
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={formatCompactTick}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    cursor={{ fill: "rgba(255,255,255,0.04)" }}
                    formatter={(value: number, name: string) => [
                      `${formatNumberDynamic(Number(value), {
                        maximumFractionDigits: 1,
                        compactMaximumFractionDigits: 1,
                      })} h`,
                      formatActivityLabel(name),
                    ]}
                  />
                  <Legend
                    formatter={(value) => formatActivityLabel(String(value))}
                    wrapperStyle={{ fontSize: 12 }}
                  />
                  {weeklyActivityTypes.map((type) => (
                    <Bar
                      key={type}
                      dataKey={type}
                      name={type}
                      stackId="weekly-time"
                      fill={getActivityColor(type)}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card">
          <CardHeader>
            <CardTitle className="text-base">VO2max trend</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px]">
            {vo2.isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : (vo2.data ?? []).length === 0 ? (
              <EmptyChartState />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={vo2.data ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
                  <XAxis
                    dataKey="date"
                    stroke={AXIS_COLOR}
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    stroke={AXIS_COLOR}
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                    domain={["auto", "auto"]}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    formatter={(value: number) => [
                      formatNumberDynamic(Number(value), {
                        maximumFractionDigits: 1,
                        minimumFractionDigits: 1,
                      }),
                      "VO2max",
                    ]}
                  />
                  <Line
                    type="monotone"
                    dataKey="vo2max"
                    stroke={GREEN}
                    strokeWidth={2}
                    dot={{ r: 3, fill: GREEN }}
                    activeDot={{ r: 5 }}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 bg-card">
        <CardHeader>
          <CardTitle className="text-base">Running Efficiency per Session</CardTitle>
          <p className="text-sm text-muted-foreground">higher = better form</p>
        </CardHeader>
        <CardContent className="h-[300px]">
          {efficiency.isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : efficiencySeries.length === 0 ? (
            <EmptyChartState />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={efficiencySeries}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke={AXIS_COLOR}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke={AXIS_COLOR}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  domain={["auto", "auto"]}
                />
                <Tooltip content={<EfficiencyTooltip />} />
                <Line
                  type="monotone"
                  dataKey="efficiency"
                  stroke={GREEN}
                  strokeWidth={2}
                  dot={{ r: 3, fill: GREEN }}
                  activeDot={{ r: 5 }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/60 bg-card">
        <CardHeader className="gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-base">Efficiency vs Conditions</CardTitle>
            <p className="text-sm text-muted-foreground">newer sessions use brighter green</p>
          </div>
          <Tabs
            value={scatterMetric}
            onValueChange={(value) => setScatterMetric(value as ScatterMetric)}
          >
            <TabsList>
              <TabsTrigger value="distance_km">Distance</TabsTrigger>
              <TabsTrigger value="temperature">Temperature</TabsTrigger>
              <TabsTrigger value="elevation_per_100m">Elevation</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent className="h-[340px]">
          {efficiencyScatter.isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : scatterSeries.length === 0 ? (
            <EmptyChartState />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={scatterSeries}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
                <XAxis
                  type="number"
                  dataKey={scatterMetric}
                  name={scatterConfig[scatterMetric].label}
                  unit={scatterConfig[scatterMetric].unit}
                  stroke={AXIS_COLOR}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  domain={["auto", "auto"]}
                />
                <YAxis
                  type="number"
                  dataKey="efficiency"
                  stroke={AXIS_COLOR}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  domain={["auto", "auto"]}
                />
                <Tooltip content={<EfficiencyScatterTooltip />} />
                <Scatter dataKey="efficiency" fill={GREEN}>
                  {scatterSeries.map((point) => (
                    <Cell
                      key={`${point.date}-${point.activity_name}-${point.efficiency}`}
                      fill={interpolateGreen(point.date, scatterDateRange.oldest, scatterDateRange.newest)}
                    />
                  ))}
                </Scatter>
                <Line
                  type="linear"
                  dataKey="trend"
                  stroke="#f8fafc"
                  strokeWidth={2}
                  dot={false}
                  activeDot={false}
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/60 bg-card">
        <CardHeader>
          <CardTitle className="text-base">Cardiac Drift Trend</CardTitle>
          <p className="text-sm text-muted-foreground">lower = better aerobic endurance</p>
        </CardHeader>
        <CardContent className="h-[300px]">
          {cardiacDrift.isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : cardiacDriftSeries.length === 0 ? (
            <EmptyChartState />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={cardiacDriftSeries}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke={AXIS_COLOR}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke={AXIS_COLOR}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  domain={["auto", "auto"]}
                  tickFormatter={(value) => `${value}%`}
                />
                <Tooltip content={<CardiacDriftTooltip />} />
                <ReferenceLine
                  y={5}
                  stroke={GREEN}
                  strokeDasharray="3 3"
                  label={{ value: "Good zone: 5%", fill: GREEN, fontSize: 12 }}
                />
                <ReferenceLine
                  y={8}
                  stroke="#ef4444"
                  strokeDasharray="3 3"
                  label={{ value: "Needs work: 8%", fill: "#ef4444", fontSize: 12 }}
                />
                <Line
                  type="monotone"
                  dataKey="hr_drift_pct"
                  stroke={GREEN}
                  strokeWidth={2}
                  dot={{ r: 3, fill: GREEN }}
                  activeDot={{ r: 5 }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/60 bg-card">
        <CardHeader>
          <CardTitle className="text-base">Average HR by activity type</CardTitle>
        </CardHeader>
        <CardContent className="h-[300px]">
          {hrDistribution.isLoading ? (
            <Skeleton className="h-full w-full" />
          ) : hrSeries.length === 0 ? (
            <EmptyChartState />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hrSeries}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke={AXIS_COLOR}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke={AXIS_COLOR}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  domain={["auto", "auto"]}
                />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(value: number, name: string) => [
                    `${formatNumberDynamic(Number(value), { maximumFractionDigits: 0 })} bpm`,
                    formatActivityLabel(name),
                  ]}
                />
                <Legend
                  formatter={(value) => formatActivityLabel(String(value))}
                  wrapperStyle={{ fontSize: 12 }}
                />
                {hrActivityTypes.map((type) => (
                  <Line
                    key={type}
                    type="monotone"
                    dataKey={type}
                    name={type}
                    stroke={getActivityColor(type)}
                    strokeWidth={2}
                    dot={{ r: 2 }}
                    activeDot={{ r: 4 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
