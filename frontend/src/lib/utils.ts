import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const DEFAULT_ACTIVITY_COLOR = "#22c55e";
const ACTIVITY_COLOR_PALETTE = [
  "#22c55e",
  "#3b82f6",
  "#f97316",
  "#a855f7",
  "#14b8a6",
  "#eab308",
  "#ec4899",
  "#06b6d4",
] as const;

const ACTIVITY_COLOR_OVERRIDES: Record<string, string> = {
  running: "#22c55e",
  hiking: "#3b82f6",
  strength_training: "#f97316",
  cycling: "#a855f7",
  walking: "#14b8a6",
  trail_running: "#eab308",
  cardio: "#ec4899",
  swimming: "#06b6d4",
};

export type DynamicNumberFormatOptions = {
  maximumFractionDigits?: number;
  minimumFractionDigits?: number;
  compactMaximumFractionDigits?: number;
};

function normalizeActivityType(activityType: string) {
  return activityType.trim().toLowerCase().replace(/[\s-]+/g, "_");
}

export function formatActivityLabel(activityType?: string | null) {
  if (!activityType) {
    return "Unknown";
  }

  return normalizeActivityType(activityType)
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function getActivityColor(activityType?: string | null) {
  if (!activityType) {
    return DEFAULT_ACTIVITY_COLOR;
  }

  const normalized = normalizeActivityType(activityType);
  const configuredColor = ACTIVITY_COLOR_OVERRIDES[normalized];
  if (configuredColor) {
    return configuredColor;
  }

  const hash = Array.from(normalized).reduce((total, character) => total + character.charCodeAt(0), 0);
  return ACTIVITY_COLOR_PALETTE[hash % ACTIVITY_COLOR_PALETTE.length] ?? DEFAULT_ACTIVITY_COLOR;
}

export function formatNumberDynamic(
  value: number | null | undefined,
  {
    maximumFractionDigits = 0,
    minimumFractionDigits = 0,
    compactMaximumFractionDigits = 1,
  }: DynamicNumberFormatOptions = {},
) {
  if (value === null || value === undefined) {
    return "—";
  }

  const absValue = Math.abs(value);
  if (absValue >= 1000) {
    return new Intl.NumberFormat(undefined, {
      notation: "compact",
      compactDisplay: "short",
      maximumFractionDigits: compactMaximumFractionDigits,
    }).format(value);
  }

  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits,
    minimumFractionDigits,
  }).format(value);
}

export function formatDistance(value?: number | null) {
  if (value === null || value === undefined || value <= 0) return "—";
  return `${value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} km`;
}

export function formatPace(value?: number | null) {
  if (value === null || value === undefined || !Number.isFinite(value) || value <= 0) return "—";
  const totalSeconds = Math.round(value * 60);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")} min/km`;
}
