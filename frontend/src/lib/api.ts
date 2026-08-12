export const API_BASE = "https://garmin-training-app.onrender.com";

export type Summary = {
  sessions: number;
  total_km: number;
  hours: number;
  calories: number;
  vo2max: number;
};

export type WeeklyPoint = {
  week: string;
  activity_type: string;
  total_hours: number;
  total_km: number;
  sessions: number;
};
export type Vo2Point = { date: string; vo2max: number };
export type HrDistributionPoint = { date: string; activity_type: string; avg_hr: number };
export type DashboardFilters = {
  activityType?: string;
  startDate?: string;
  endDate?: string;
};

export type Activity = {
  activity_id: string | number;
  activity_name: string;
  activity_type: string;
  start_time_local: string;
  distance_km: number | null;
  duration_minutes: number | null;
  avg_hr: number | null;
  max_hr: number | null;
  calories: number | null;
  training_load: number | null;
  vo2max: number | null;
  pace_min_per_km: number | null;
};

function buildPath(path: string, filters?: DashboardFilters) {
  if (!filters) {
    return path;
  }

  const params = new URLSearchParams();
  if (filters.activityType) {
    params.set("activity_type", filters.activityType);
  }
  if (filters.startDate) {
    params.set("start_date", filters.startDate);
  }
  if (filters.endDate) {
    params.set("end_date", filters.endDate);
  }

  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

async function getJson<T>(path: string, filters?: DashboardFilters): Promise<T> {
  const res = await fetch(`${API_BASE}${buildPath(path, filters)}`);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return (await res.json()) as T;
}

export const fetchSummary = (filters?: DashboardFilters) => getJson<Summary>("/api/summary", filters);
export const fetchWeekly = (filters?: DashboardFilters) => getJson<WeeklyPoint[]>("/api/weekly", filters);
export const fetchVo2maxTrend = (filters?: DashboardFilters) =>
  getJson<Vo2Point[]>("/api/vo2max_trend", filters);
export const fetchHrDistribution = (filters?: DashboardFilters) =>
  getJson<HrDistributionPoint[]>("/api/hr_distribution", filters);
export const fetchActivityTypes = () => getJson<string[]>("/api/activity_types");
export const fetchActivities = (filters?: DashboardFilters) =>
  getJson<Activity[]>("/api/activities", filters);

export type TokenUsage = {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
};

export type ChatResult = {
  content: string;
  usage?: TokenUsage;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export async function sendChat({
  message,
  history,
}: {
  message: string;
  history: ChatMessage[];
}): Promise<ChatResult> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  const data = (await res.json()) as { response?: string; usage?: TokenUsage };
  return {
    content: data.response ?? "No response.",
    usage: data.usage,
  };
}
