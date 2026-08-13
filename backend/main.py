from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import requests
import io
import os
import re
from dotenv import load_dotenv
try:
    from .mcp_tools import TOOLS, configure_data_loader, select_tool
except ImportError:
    from mcp_tools import TOOLS, configure_data_loader, select_tool

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))
load_dotenv(os.path.join(os.path.dirname(BACKEND_DIR), ".env"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HOST  = os.getenv("DATABRICKS_HOST", "").rstrip("/")
TOKEN = os.getenv("DATABRICKS_TOKEN", "")

# Cache — avoids hitting Databricks on every request
_cache = {"df": None, "weekly_df": None, "loaded_at": None}


def load_from_databricks(volume_path: str) -> pd.DataFrame:
    """Read CSV from Databricks Volume via Files REST API. Works in Community Edition."""
    if not HOST:
        raise RuntimeError("DATABRICKS_HOST is not configured.")
    if not TOKEN:
        raise RuntimeError("DATABRICKS_TOKEN is not configured.")
    headers = {"Authorization": "Bearer " + TOKEN}
    url = HOST + "/api/2.0/fs/files" + volume_path
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code == 200:
        return pd.read_csv(io.StringIO(resp.text))
    raise Exception("Databricks API " + str(resp.status_code) + ": " + resp.text[:200])


def normalize_activity_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    result = dataframe.copy()
    alias_map = {
        "activityId": "activity_id",
        "activityName": "activity_name",
        "activityType": "activity_type",
        "startTimeLocal": "start_time_local",
        "averageHR": "avg_hr",
        "maxHR": "max_hr",
        "vO2MaxValue": "vo2max",
        "activityTrainingLoad": "training_load",
        "elevationGain": "elevation_gain_m",
    }
    for source, target in alias_map.items():
        if target not in result.columns and source in result.columns:
            result[target] = result[source]

    if "distance_km" not in result.columns and "distance" in result.columns:
        result["distance_km"] = pd.to_numeric(result["distance"], errors="coerce") / 1000
    if "duration_minutes" not in result.columns and "duration" in result.columns:
        result["duration_minutes"] = pd.to_numeric(result["duration"], errors="coerce") / 60

    required_defaults = {
        "activity_id": "",
        "activity_name": "",
        "activity_type": "",
        "start_time_local": pd.NaT,
        "distance_km": 0,
        "duration_minutes": 0,
        "avg_hr": 0,
        "max_hr": 0,
        "avg_speed_kmh": 0,
        "elevation_gain_m": 0,
        "min_temp_c": None,
        "max_temp_c": None,
        "calories": 0,
        "training_load": 0,
        "vo2max": 0,
    }
    for column, default_value in required_defaults.items():
        if column not in result.columns:
            result[column] = default_value
    return result


def get_df(force_refresh=False):
    import datetime
    now = datetime.datetime.now()
    stale = _cache["loaded_at"] is None or (now - _cache["loaded_at"]).seconds > 3600

    if force_refresh or stale:
        # Try Databricks first, fall back to local CSV
        try:
            print("Trying Databricks live data...")
            df = load_from_databricks("/Volumes/garmin/raw/garmin/exports/activities-3.csv")
            weekly_df = load_from_databricks("/Volumes/garmin/raw/garmin/exports/weekly_summary.csv")
            print("Loaded from Databricks live!")
        except Exception as e:
            print("Databricks unavailable (" + str(e)[:80] + ") — falling back to local CSV")
            data_dir = os.path.join(os.path.dirname(__file__), "data")
            df = pd.read_csv(os.path.join(data_dir, "activities-3.csv"))
            weekly_df = pd.read_csv(os.path.join(data_dir, "weekly_summary.csv"))
            print("Loaded from local CSV fallback")

        df = normalize_activity_dataframe(df)
        df["start_time_local"] = pd.to_datetime(df["start_time_local"], errors="coerce")
        df["distance_km"]      = pd.to_numeric(df["distance_km"], errors="coerce").fillna(0)
        df["duration_minutes"] = pd.to_numeric(df["duration_minutes"], errors="coerce").fillna(0)
        df["avg_hr"]           = pd.to_numeric(df["avg_hr"], errors="coerce").fillna(0)
        df["max_hr"]           = pd.to_numeric(df["max_hr"], errors="coerce").fillna(0)
        df["calories"]         = pd.to_numeric(df["calories"], errors="coerce").fillna(0)
        df["training_load"]    = pd.to_numeric(df["training_load"], errors="coerce").fillna(0)
        df["vo2max"]           = pd.to_numeric(df["vo2max"], errors="coerce").fillna(0)
        df["elevation_gain_m"] = pd.to_numeric(df["elevation_gain_m"], errors="coerce").fillna(0)
        if "weather_temp_mean" in df.columns:
            df["temperature_c"] = pd.to_numeric(
                df.get("temperature_c", pd.Series([None] * len(df))), errors="coerce"
            ).fillna(pd.to_numeric(df["weather_temp_mean"], errors="coerce"))
        elif "weather_temp_max" in df.columns:
            df["temperature_c"] = pd.to_numeric(df["weather_temp_max"], errors="coerce")
        else:
            df["temperature_c"] = pd.to_numeric(
                df.get("maxTemperature", pd.Series([None] * len(df))), errors="coerce"
            )

        if "weather_wind_kmh" in df.columns:
            df["wind_kmh"] = pd.to_numeric(df["weather_wind_kmh"], errors="coerce")
        else:
            df["wind_kmh"] = None

        df["activity_group"] = df["activity_type"].apply(get_parent_type)
        weekly_df["week"]                = pd.to_datetime(weekly_df["week"], errors="coerce")
        weekly_df["total_training_load"] = pd.to_numeric(weekly_df["total_training_load"], errors="coerce").fillna(0)
        weekly_df["total_distance_km"]   = pd.to_numeric(weekly_df["total_distance_km"], errors="coerce").fillna(0)
        weekly_df["session_count"]       = pd.to_numeric(weekly_df["session_count"], errors="coerce").fillna(0)

        _cache["df"]        = df
        _cache["weekly_df"] = weekly_df
        _cache["loaded_at"] = now
        print("Ready: " + str(len(df)) + " activities loaded")

    return _cache["df"], _cache["weekly_df"]


configure_data_loader(get_df)


def parse_date_value(value, field_name):
    if not value:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise HTTPException(status_code=400, detail=field_name + " must use YYYY-MM-DD format.")
    return parsed


def filter_dataset(dataframe, date_column, start_date=None, end_date=None, activity_type=None):
    result = dataframe.copy()
    start = parse_date_value(start_date, "start_date")
    end   = parse_date_value(end_date, "end_date")
    if start is not None:
        result = result[result[date_column] >= start]
    if end is not None:
        result = result[result[date_column] < end + pd.Timedelta(days=1)]
    if activity_type and activity_type.lower() != "all":
        result = result[result["activity_type"] == activity_type]
    return result


def resolve_auto_granularity(dataframe, date_column):
    if dataframe.empty:
        return "day"
    span_days = max((dataframe[date_column].max() - dataframe[date_column].min()).days, 0)
    if span_days <= 90:
        return "day"
    if span_days <= 365:
        return "week"
    return "month"


def add_time_bucket(dataframe, date_column, granularity, label_column):
    result = dataframe.copy()
    if granularity == "month":
        bucket = result[date_column].dt.to_period("M").dt.start_time
    elif granularity == "week":
        bucket = result[date_column].dt.to_period("W").dt.start_time
    else:
        bucket = result[date_column].dt.floor("D")
    result[label_column] = bucket.dt.strftime("%Y-%m-%d")
    return result


def parse_relative_days(text: str):
    query = text.lower()
    unit_to_days = {
        "day": 1,
        "days": 1,
        "week": 7,
        "weeks": 7,
        "month": 30,
        "months": 30,
        "quarter": 90,
        "quarters": 90,
        "year": 365,
        "years": 365,
    }

    # Match explicit patterns: "last/past X unit"
    explicit = re.search(r"(?:last|past|previous)\s+(\d+)\s*(day|days|week|weeks|month|months|quarter|quarters|year|years)\b", query)
    if explicit:
        value = int(explicit.group(1))
        unit = explicit.group(2)
        return max(1, value * unit_to_days[unit])

    # Match single unit patterns: "last/past week/month/year"
    single = re.search(r"\b(?:last|past|previous)\s+(day|week|month|quarter|year)\b", query)
    if single:
        return unit_to_days[single.group(1)]

    # Match specific phrases
    if "today" in query or "yesterday" in query or "last 24" in query:
        return 1
    if "this week" in query or "past week" in query:
        return 7
    if "this month" in query or "past month" in query or "previous month" in query:
        return 30
    if "this quarter" in query or "past quarter" in query:
        return 90
    if "this year" in query or "past year" in query or "previous year" in query:
        return 365
    if "six months" in query or "6 months" in query or "half year" in query:
        return 180
    if "three months" in query or "3 months" in query or "quarter" in query:
        return 90
    if "two weeks" in query or "2 weeks" in query or "fortnight" in query:
        return 14
    
    return None


def parse_activity_count(text: str):
    query = text.lower()
    match = re.search(r"(?:last|recent|latest)\s+(\d+)\s+(?:activities|workouts|sessions)\b", query)
    if not match:
        return None
    return max(1, min(int(match.group(1)), 200))


def parse_explicit_date_range(text: str):
    query = text.lower()
    iso_dates = re.findall(r"\b(20\d{2}-\d{2}-\d{2})\b", query)
    if iso_dates:
        return {
            "start_date": iso_dates[0],
            "end_date": iso_dates[1] if len(iso_dates) > 1 else iso_dates[0],
        }

    month_numbers = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    month_match = re.search(
        r"\b(" + "|".join(month_numbers) + r")(?:\s+(20\d{2}))?\b",
        query,
    )
    if month_match:
        month = month_numbers[month_match.group(1)]
        now = pd.Timestamp.now()
        if month_match.group(2):
            year = int(month_match.group(2))
        else:
            year = now.year if month <= now.month else now.year - 1
        start = pd.Timestamp(year=year, month=month, day=1)
        end = start + pd.offsets.MonthEnd(1)
        return {
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
        }

    year_match = re.search(r"\b(20\d{2})\b", query)
    if year_match:
        year = int(year_match.group(1))
        return {
            "start_date": f"{year}-01-01",
            "end_date": f"{year}-12-31",
        }
    return None


def infer_tool_kwargs(tool_name: str, user_message: str):
    if tool_name == "get_activities_by_date_range":
        return parse_explicit_date_range(user_message) or {}
    if tool_name == "get_last_n_days":
        days = parse_relative_days(user_message)
        if days:
            return {"days": days}
        # Return empty dict to let the tool use its default
        return {}
    if tool_name == "get_training_load_trend":
        days = parse_relative_days(user_message)
        if not days:
            return {}
        weeks = max(1, (days + 6) // 7)
        return {"weeks": weeks}
    if tool_name == "get_recent_activities":
        count = parse_activity_count(user_message)
        return {"n": count} if count else {}
    return {}


@app.get("/api/summary")
def get_summary(start_date: str = None, end_date: str = None, activity_type: str = None):
    df, _ = get_df()
    filtered = filter_dataset(df, "start_time_local", start_date, end_date, activity_type)
    vo2_vals = filtered[filtered["vo2max"] > 0]["vo2max"]
    avg_vo2  = round(float(vo2_vals.mean()), 1) if len(vo2_vals) > 0 else 0
    return {
        "sessions":       len(filtered),
        "total_sessions": len(filtered),
        "total_km":       round(float(filtered["distance_km"].sum()), 1),
        "hours":          round(float(filtered["duration_minutes"].sum() / 60), 1),
        "total_hours":    round(float(filtered["duration_minutes"].sum() / 60), 1),
        "calories":       int(filtered["calories"].sum()),
        "total_calories": int(filtered["calories"].sum()),
        "vo2max":         avg_vo2,
        "avg_vo2max":     avg_vo2,
    }


@app.get("/api/activities")
def get_activities(
    limit: int = 100,
    activity_type: str = None,
    start_date: str = None,
    end_date: str = None,
):
    df, _ = get_df()
    result = filter_dataset(
        df, "start_time_local", start_date, end_date, activity_type
    )
    if "pace_min_per_km" not in result.columns:
        result = result.copy()
        result["pace_min_per_km"] = (
            result["duration_minutes"] / result["distance_km"].replace(0, pd.NA)
        )
    result = result.sort_values("start_time_local", ascending=False).head(limit)
    result["start_time_local"] = result["start_time_local"].dt.strftime("%Y-%m-%d %H:%M")
    cols = [
        "activity_id", "activity_name", "activity_type",
        "start_time_local", "distance_km", "duration_minutes",
        "avg_hr", "max_hr", "calories", "training_load", "vo2max",
        "pace_min_per_km",
    ]
    available = [c for c in cols if c in result.columns]
    return result[available].fillna(0).to_dict(orient="records")


@app.get("/api/weekly")
def get_weekly(start_date: str = None, end_date: str = None, activity_type: str = None):
    df, _ = get_df()
    filtered = filter_dataset(df, "start_time_local", start_date, end_date, activity_type)
    if filtered.empty:
        return []
    filtered = add_time_bucket(filtered, "start_time_local", "week", "week")
    agg = filtered.groupby(["week", "activity_type"], as_index=False).agg(
        total_hours=("duration_minutes", lambda v: v.sum() / 60),
        total_km=("distance_km", "sum"),
        sessions=("activity_id", "count"),
    ).sort_values(["week", "activity_type"])
    agg["total_hours"] = agg["total_hours"].round(1)
    agg["total_km"]    = agg["total_km"].round(1)
    return agg.fillna(0).to_dict(orient="records")


@app.get("/api/activity_types")
def get_activity_types():
    df, _ = get_df()
    return sorted(df["activity_type"].dropna().unique().tolist())


@app.get("/api/vo2max_trend")
def get_vo2max_trend(start_date: str = None, end_date: str = None, activity_type: str = None):
    df, _ = get_df()
    vo2 = filter_dataset(df, "start_time_local", start_date, end_date, activity_type)
    vo2 = vo2[vo2["vo2max"] > 0].sort_values("start_time_local").copy()
    if vo2.empty:
        return []
    try:
        granularity = resolve_auto_granularity(vo2, "start_time_local")
        vo2 = add_time_bucket(vo2, "start_time_local", granularity, "date")
        vo2 = vo2.groupby("date", as_index=False).agg(vo2max=("vo2max", "mean")).sort_values("date")
        vo2["vo2max"] = vo2["vo2max"].round(1)
        return vo2.to_dict(orient="records")
    except Exception as e:
        print("vo2max_trend error: " + str(e))
        return []


@app.get("/api/hr_distribution")
def get_hr_distribution(start_date: str = None, end_date: str = None, activity_type: str = None):
    df, _ = get_df()
    hr = filter_dataset(df, "start_time_local", start_date, end_date, activity_type)
    hr = hr[hr["avg_hr"] > 0][["start_time_local", "activity_type", "avg_hr"]].copy()
    if hr.empty:
        return []
    granularity = resolve_auto_granularity(hr, "start_time_local")
    hr = add_time_bucket(hr, "start_time_local", granularity, "date")
    hr = hr.groupby(["date", "activity_type"], as_index=False).agg(avg_hr=("avg_hr", "mean"))
    hr["avg_hr"] = hr["avg_hr"].round(1)
    return hr.sort_values(["date", "activity_type"]).to_dict(orient="records")


@app.get("/api/refresh")
def refresh_data():
    """Force reload live data from Databricks. Call after running the export notebook."""
    get_df(force_refresh=True)
    df, _ = get_df()
    return {"status": "refreshed", "activities_loaded": len(df)}

@app.get("/api/efficiency_trend")
def get_efficiency_trend(
    weeks: int = None,
    granularity: str = "activity",
    start_date: str = None,
    end_date: str = None,
    activity_type: str = None,
):
    """
    granularity = 'activity' → one point per run (recommended)
    granularity = 'week' → weekly average
    """
    df, _ = get_df()
    now = pd.Timestamp.now()

    running = filter_dataset(df, "start_time_local", start_date, end_date, activity_type)
    if weeks is not None and start_date is None and end_date is None:
        running = running[running["start_time_local"] >= now - pd.Timedelta(weeks=weeks)]
    running = running[
        (running["activity_type"] == "running") &
        (running["distance_km"] >= 3) &
        (running["avg_hr"] > 0) &
        (running["avg_speed_kmh"] > 0)
    ].copy()

    if running.empty:
        return []

    # Core efficiency metric
    running["efficiency"] = (running["avg_speed_kmh"] / running["avg_hr"] * 1000).round(2)

    # Normalized factors for scatter
    running["date"]          = running["start_time_local"].dt.strftime("%Y-%m-%d")
    running["distance_km"]   = running["distance_km"].round(1)
    running["elevation_gain"]= running["elevation_gain_m"].fillna(0).round(0)
    running["temperature"]   = running["min_temp_c"].fillna(
                                running["max_temp_c"]).fillna(20).round(1)
    running["activity_name"] = running["activity_name"].fillna("Run")

    if granularity == "week":
        running["week"] = running["start_time_local"].dt.to_period("W").dt.start_time.dt.strftime("%Y-%m-%d")
        result = running.groupby("week").agg(
            efficiency=("efficiency", "mean"),
            distance_km=("distance_km", "sum"),
            avg_hr=("avg_hr", "mean"),
            elevation_gain=("elevation_gain", "sum"),
            temperature=("temperature", "mean"),
            sessions=("activity_id", "count")
        ).reset_index().rename(columns={"week": "date"})
        result["efficiency"] = result["efficiency"].round(2)
        return result.to_dict(orient="records")

    # Default — one point per activity
    cols = ["date", "activity_name", "efficiency", "distance_km",
            "avg_hr", "elevation_gain", "temperature",
            "duration_minutes", "pace_min_per_km"]
    available = [c for c in cols if c in running.columns]
    return running[available].sort_values("date").fillna(0).to_dict(orient="records")

@app.get("/api/cardiac_drift")
def get_cardiac_drift(
    weeks: int = None,
    start_date: str = None,
    end_date: str = None,
    activity_type: str = None,
):
    """Cardiac drift trend for long runs — tracks aerobic endurance."""
    df, _ = get_df()
    now = pd.Timestamp.now()
    long_runs = filter_dataset(df, "start_time_local", start_date, end_date, activity_type)
    if weeks is not None and start_date is None and end_date is None:
        long_runs = long_runs[long_runs["start_time_local"] >= now - pd.Timedelta(weeks=weeks)]
    long_runs = long_runs[
        (long_runs["activity_type"] == "running") &
        (long_runs["duration_minutes"] >= 30) &
        (long_runs["avg_hr"] > 0)
    ].copy()
    if long_runs.empty:
        return []
    long_runs["hr_drift_pct"] = ((long_runs["max_hr"] - long_runs["avg_hr"]) / long_runs["avg_hr"] * 100).round(1)
    long_runs["date"] = long_runs["start_time_local"].dt.strftime("%Y-%m-%d")
    return long_runs.sort_values("start_time_local")[
        ["date", "hr_drift_pct", "avg_hr", "max_hr", "duration_minutes", "distance_km"]
    ].fillna(0).to_dict(orient="records")

@app.get("/api/efficiency_scatter")
def get_efficiency_scatter(
    start_date: str = None,
    end_date: str = None,
    activity_type: str = None,
):
    """
    Scatter data: efficiency vs distance, temperature, elevation.
    Used for multi-factor analysis chart.
    """
    df, _ = get_df()

    running = filter_dataset(df, "start_time_local", start_date, end_date, activity_type)
    running = running[
        (running["activity_type"] == "running") &
        (running["distance_km"] >= 3) &
        (running["avg_hr"] > 0) &
        (running["avg_speed_kmh"] > 0)
    ].copy()

    if running.empty:
        return []

    running["efficiency"]    = (running["avg_speed_kmh"] / running["avg_hr"] * 1000).round(2)
    running["date"]          = running["start_time_local"].dt.strftime("%Y-%m-%d")
    running["temperature"]   = running["min_temp_c"].fillna(running["max_temp_c"]).fillna(20).round(1)
    running["elevation_gain"]= running["elevation_gain_m"].fillna(0).round(0)
    running["elevation_per_100m"] = (
        running["elevation_gain_m"] / (running["distance_km"] * 10)
    ).round(1)
    running["activity_name"] = running["activity_name"].fillna("Run")

    cols = ["date", "activity_name", "efficiency",
            "distance_km", "avg_hr", "elevation_gain",
            "elevation_per_100m",
            "temperature", "duration_minutes", "pace_min_per_km",
            "avg_speed_kmh"]
    available = [c for c in cols if c in running.columns]
    return running[available].sort_values("date").fillna(0).to_dict(orient="records")

@app.post("/api/chat")
def chat(message: dict):
    user_message = str(message.get("message", "")).strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="message is required.")
    history = [
        {"role": item["role"], "content": str(item["content"])}
        for item in message.get("history", [])[-10:]
        if isinstance(item, dict)
        and item.get("role") in {"user", "assistant"}
        and item.get("content")
    ]
    try:
        from groq import Groq
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        configured_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

        def create_completion_with_fallback(**kwargs):
            model_candidates = [configured_model]
            if configured_model != "llama-3.1-8b-instant":
                model_candidates.append("llama-3.1-8b-instant")

            last_error = None
            for model_name in model_candidates:
                try:
                    return groq_client.chat.completions.create(model=model_name, **kwargs)
                except Exception as exc:
                    last_error = exc
                    error_text = str(exc)
                    is_decommissioned = (
                        "model_decommissioned" in error_text
                        or "decommissioned" in error_text.lower()
                    )
                    if not is_decommissioned:
                        raise
            raise last_error

        # Step 1 — LLM picks the best tool
        tool_descriptions = "\n".join(
            [name + ": " + info["description"] for name, info in TOOLS.items()]
        )
        tool_selection = create_completion_with_fallback(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a tool selector. Pick the single best tool name for the question.\n"
                        "Available tools:\n" + tool_descriptions + "\n"
                        "For open-ended advice, planning, recovery, pacing, or any ambiguous "
                        "question, select get_coaching_context.\n"
                        "Reply with ONLY the tool name, nothing else."
                    )
                },
                *history,
                {"role": "user", "content": user_message}
            ],
            max_tokens=50,
            temperature=0
        )

        tool_name = tool_selection.choices[0].message.content.strip()
        if tool_name not in TOOLS:
            tool_name = select_tool(user_message)

        # Step 2 — execute tool, get real data
        explicit_range = parse_explicit_date_range(user_message)
        if explicit_range:
            tool_name = "get_activities_by_date_range"
        elif any(
            phrase in user_message.lower()
            for phrase in [
                "how should",
                "what should",
                "recommend",
                "advice",
                "plan",
                "next week",
                "recovery",
                "recover",
                "pacing",
                "pace for",
            ]
        ):
            tool_name = "get_coaching_context"
        elif tool_name == "get_activities_by_date_range":
            tool_name = select_tool(user_message)
        tool_kwargs = infer_tool_kwargs(tool_name, user_message)
        print(f"[DEBUG] user_message: '{user_message}'")
        print(f"[DEBUG] selected tool: {tool_name}")
        print(f"[DEBUG] tool_kwargs: {tool_kwargs}")
        
        tool_result = TOOLS[tool_name]["fn"](**tool_kwargs)
        print(f"[DEBUG] tool_result keys: {list(tool_result.keys()) if isinstance(tool_result, dict) else type(tool_result)}")

        # Step 3 — answer using only real data
        final = create_completion_with_fallback(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert AI training coach.\n"
                        "Answer ONLY using the data below. Never invent numbers.\n"
                        "For future plans, give practical recommendations grounded in the "
                        "available history and clearly distinguish advice from recorded data.\n"
                        "The detailed activity records come from activities-3, not the weekly "
                        "summary. Use their cadence, power, heart-rate zones, training effects, "
                        "elevation, splits, and strength-set fields when relevant.\n"
                        "Do not focus on a calendar month unless the user asked about it.\n"
                        "Be specific and concise, max 150 words.\n\n"
                        "DATA (" + tool_name + "):\n" + str(tool_result)
                    )
                },
                *history,
                {"role": "user", "content": user_message}
            ]
        )
        return {
            "response": final.choices[0].message.content,
            "data_source": tool_name
        }

    except Exception as e:
        return {"response": "AI coach unavailable: " + str(e)}

# Activity type grouping — parent → children
ACTIVITY_GROUPS = {
    "running": ["running", "trail_running", "treadmill_running", "track_running"],
    "cycling": ["cycling", "road_biking", "indoor_cycling", "mountain_biking",
                "gravel_cycling", "virtual_ride", "bike"],
    "strength": ["strength_training", "gym", "fitness_equipment", "weight_training"],
    "hiking": ["hiking", "walking", "mountaineering"],
    "swimming": ["swimming", "open_water_swimming", "pool_swimming"],
    "other": []  # catch-all
}

def get_parent_type(activity_type: str) -> str:
    """Maps specific activity type to parent group."""
    if not activity_type:
        return "other"
    at = str(activity_type).lower()
    for parent, children in ACTIVITY_GROUPS.items():
        if at in children or at == parent:
            return parent
    return activity_type  # keep original if no match