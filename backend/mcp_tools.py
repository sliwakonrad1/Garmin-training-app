import pandas as pd
import os
import re
from datetime import datetime
from typing import Callable, Optional, Tuple

# Global dataframe — loaded once at startup, refreshed on demand
_df = None
_weekly_df = None
_loaded_at = None
_data_loader: Optional[Callable[..., Tuple[pd.DataFrame, pd.DataFrame]]] = None

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

ACTIVITY_DETAIL_FIELDS = [
    "activity_name",
    "activity_type",
    "start_time_local",
    "distance_km",
    "duration_minutes",
    "moving_duration_minutes",
    "elapsed_duration_minutes",
    "pace",
    "avg_speed_kmh",
    "max_speed_kmh",
    "avg_hr",
    "max_hr",
    "calories",
    "steps",
    "training_load",
    "aerobic_training_effect",
    "anaerobic_training_effect",
    "training_effect_label",
    "difference_body_battery",
    "vo2max",
    "elevation_gain_m",
    "elevation_loss_m",
    "min_elevation_m",
    "max_elevation_m",
    "average_running_cadence_spm",
    "max_running_cadence_spm",
    "average_biking_cadence_rpm",
    "max_biking_cadence_rpm",
    "average_power_w",
    "max_power_w",
    "normalized_power_w",
    "average_stride_length_m",
    "average_vertical_oscillation_cm",
    "average_ground_contact_time_ms",
    "average_vertical_ratio_percent",
    "moderate_intensity_minutes",
    "vigorous_intensity_minutes",
    "heart_rate_zone_1_minutes",
    "heart_rate_zone_2_minutes",
    "heart_rate_zone_3_minutes",
    "heart_rate_zone_4_minutes",
    "heart_rate_zone_5_minutes",
    "fastest_1km_seconds",
    "fastest_5km_seconds",
    "fastest_10km_seconds",
    "total_sets",
    "active_sets",
    "total_reps",
    "exercise_sets",
    "location_name",
]


def configure_data_loader(loader: Callable[..., Tuple[pd.DataFrame, pd.DataFrame]]):
    """Use the application's live data loader for all coach tools."""
    global _data_loader
    _data_loader = loader


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
        "calories": 0,
        "training_load": 0,
        "vo2max": 0,
        "elevation_gain_m": 0,
    }
    for column, default_value in required_defaults.items():
        if column not in result.columns:
            result[column] = default_value
    return result


def activity_detail_records(dataframe: pd.DataFrame, limit=20):
    """Return useful training metrics while omitting account and device metadata."""
    details = dataframe.sort_values("start_time_local", ascending=False).head(limit).copy()
    if "pace_min_per_km" in details.columns:
        details["pace"] = details["pace_min_per_km"].apply(format_pace)
    aliases = {
        "movingDuration": ("moving_duration_minutes", 1 / 60),
        "elapsedDuration": ("elapsed_duration_minutes", 1 / 60),
        "maxSpeed": ("max_speed_kmh", 3.6),
        "aerobicTrainingEffect": ("aerobic_training_effect", 1),
        "anaerobicTrainingEffect": ("anaerobic_training_effect", 1),
        "trainingEffectLabel": ("training_effect_label", 1),
        "differenceBodyBattery": ("difference_body_battery", 1),
        "elevationGain": ("elevation_gain_m", 1),
        "elevationLoss": ("elevation_loss_m", 1),
        "minElevation": ("min_elevation_m", 1),
        "maxElevation": ("max_elevation_m", 1),
        "averageRunningCadenceInStepsPerMinute": ("average_running_cadence_spm", 1),
        "maxRunningCadenceInStepsPerMinute": ("max_running_cadence_spm", 1),
        "averageBikingCadenceInRevPerMinute": ("average_biking_cadence_rpm", 1),
        "maxBikingCadenceInRevPerMinute": ("max_biking_cadence_rpm", 1),
        "avgPower": ("average_power_w", 1),
        "maxPower": ("max_power_w", 1),
        "normPower": ("normalized_power_w", 1),
        "avgStrideLength": ("average_stride_length_m", 1),
        "avgVerticalOscillation": ("average_vertical_oscillation_cm", 1),
        "avgGroundContactTime": ("average_ground_contact_time_ms", 1),
        "avgVerticalRatio": ("average_vertical_ratio_percent", 1),
        "moderateIntensityMinutes": ("moderate_intensity_minutes", 1),
        "vigorousIntensityMinutes": ("vigorous_intensity_minutes", 1),
        "hrTimeInZone_1": ("heart_rate_zone_1_minutes", 1 / 60),
        "hrTimeInZone_2": ("heart_rate_zone_2_minutes", 1 / 60),
        "hrTimeInZone_3": ("heart_rate_zone_3_minutes", 1 / 60),
        "hrTimeInZone_4": ("heart_rate_zone_4_minutes", 1 / 60),
        "hrTimeInZone_5": ("heart_rate_zone_5_minutes", 1 / 60),
        "fastestSplit_1000": ("fastest_1km_seconds", 1),
        "fastestSplit_5000": ("fastest_5km_seconds", 1),
        "fastestSplit_10000": ("fastest_10km_seconds", 1),
        "totalSets": ("total_sets", 1),
        "activeSets": ("active_sets", 1),
        "totalReps": ("total_reps", 1),
        "summarizedExerciseSets": ("exercise_sets", 1),
        "locationName": ("location_name", 1),
    }
    for source, (target, multiplier) in aliases.items():
        if source in details.columns and target not in details.columns:
            if multiplier == 1:
                details[target] = details[source]
            else:
                details[target] = pd.to_numeric(details[source], errors="coerce") * multiplier

    available = [field for field in ACTIVITY_DETAIL_FIELDS if field in details.columns]
    records = []
    for row in details[available].to_dict(orient="records"):
        record = {}
        for key, value in row.items():
            if value is None:
                continue
            if hasattr(value, "tolist"):
                value = value.tolist()
            if not isinstance(value, (list, dict)) and pd.isna(value):
                continue
            if isinstance(value, pd.Timestamp):
                value = value.strftime("%Y-%m-%d %H:%M")
            elif isinstance(value, float):
                value = round(value, 2)
            record[key] = value
        records.append(record)
    return records


def format_pace(value):
    if value is None or pd.isna(value) or value <= 0:
        return None
    total_seconds = round(float(value) * 60)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d} min/km"


def load_data(force_refresh=False):
    """Load CSV data. Refreshes if data is older than 1 hour."""
    global _df, _weekly_df, _loaded_at
    if _data_loader is not None:
        return _data_loader(force_refresh=force_refresh)

    now = datetime.now()
    if _df is None or force_refresh or (now - _loaded_at).seconds > 3600:
        _df = pd.read_csv(os.path.join(DATA_DIR, "activities-3.csv"))
        _df = normalize_activity_dataframe(_df)
        _df["start_time_local"] = pd.to_datetime(_df["start_time_local"], errors="coerce")
        _df["distance_km"]      = pd.to_numeric(_df["distance_km"], errors="coerce").fillna(0)
        _df["duration_minutes"] = pd.to_numeric(_df["duration_minutes"], errors="coerce").fillna(0)
        _df["avg_hr"]           = pd.to_numeric(_df["avg_hr"], errors="coerce").fillna(0)
        _df["calories"]         = pd.to_numeric(_df["calories"], errors="coerce").fillna(0)
        _df["training_load"]    = pd.to_numeric(_df["training_load"], errors="coerce").fillna(0)
        _df["vo2max"]           = pd.to_numeric(_df["vo2max"], errors="coerce").fillna(0)
        _df["elevation_gain_m"] = pd.to_numeric(_df["elevation_gain_m"], errors="coerce").fillna(0)

        _weekly_df = pd.read_csv(os.path.join(DATA_DIR, "weekly_summary.csv"))
        _weekly_df["week"] = pd.to_datetime(_weekly_df["week"], errors="coerce")
        _weekly_df["total_training_load"] = pd.to_numeric(_weekly_df["total_training_load"], errors="coerce").fillna(0)
        _weekly_df["total_distance_km"]   = pd.to_numeric(_weekly_df["total_distance_km"], errors="coerce").fillna(0)
        _weekly_df["session_count"]       = pd.to_numeric(_weekly_df["session_count"], errors="coerce").fillna(0)

        _loaded_at = now
        print("Data reloaded at " + str(now))
    return _df, _weekly_df


def get_activities_last_month():
    """Returns training summary for last calendar month."""
    df, _ = load_data()
    now = pd.Timestamp.now()
    start = (now - pd.DateOffset(months=1)).replace(day=1)
    end = now.replace(day=1) - pd.Timedelta(days=1)
    data = df[(df["start_time_local"] >= start) & (df["start_time_local"] <= end)]
    running = data[data["activity_type"] == "running"]
    cycling = data[data["activity_type"].str.contains("cycling", case=False, na=False)]
    strength = data[data["activity_type"] == "strength_training"]
    return {
        "period": start.strftime("%B %Y"),
        "total_sessions": len(data),
        "running_sessions": len(running),
        "running_km": round(float(running["distance_km"].sum()), 1),
        "cycling_km": round(float(cycling["distance_km"].sum()), 1),
        "strength_sessions": len(strength),
        "avg_hr": round(float(data[data["avg_hr"] > 0]["avg_hr"].mean()), 0) if len(data) > 0 else 0,
        "total_calories": int(data["calories"].sum()),
        "total_training_load": round(float(data["training_load"].sum()), 0),
        "activities": activity_detail_records(data),
    }


def get_activities_this_week():
    """Returns training summary for current week."""
    df, _ = load_data()
    now = pd.Timestamp.now()
    week_start = now - pd.Timedelta(days=now.dayofweek)
    week_start = week_start.replace(hour=0, minute=0, second=0)
    data = df[df["start_time_local"] >= week_start]
    return {
        "week_start": week_start.strftime("%Y-%m-%d"),
        "total_sessions": len(data),
        "total_km": round(float(data["distance_km"].sum()), 1),
        "total_minutes": round(float(data["duration_minutes"].sum()), 0),
        "total_calories": int(data["calories"].sum()),
        "activity_types": data["activity_type"].value_counts().to_dict(),
        "activities": activity_detail_records(data),
    }


def get_last_n_days(days=30):
    """Returns training summary for last N days."""
    df, _ = load_data()
    now = pd.Timestamp.now()
    start = now - pd.Timedelta(days=days)
    data = df[df["start_time_local"] >= start]
    running = data[data["activity_type"] == "running"]
    return {
        "period_days": days,
        "total_sessions": len(data),
        "running_km": round(float(running["distance_km"].sum()), 1),
        "running_sessions": len(running),
        "avg_hr": round(float(data[data["avg_hr"] > 0]["avg_hr"].mean()), 0) if len(data) > 0 else 0,
        "avg_vo2max": round(float(data[data["vo2max"] > 0]["vo2max"].mean()), 1) if len(data) > 0 else 0,
        "total_calories": int(data["calories"].sum()),
        "total_training_load": round(float(data["training_load"].sum()), 0),
        "activities": activity_detail_records(data),
    }


def get_training_load_trend(weeks=8):
    """Returns weekly training load trend for last N weeks."""
    df, _ = load_data()
    now = pd.Timestamp.now()
    start = now - pd.Timedelta(weeks=weeks)
    data = df[df["start_time_local"] >= start].copy()
    data["week"] = data["start_time_local"].dt.to_period("W").astype(str)
    weekly = data.groupby("week").agg(
        sessions=("activity_id", "count"),
        km=("distance_km", "sum"),
        load=("training_load", "sum"),
    ).reset_index()
    weekly["km"] = weekly["km"].round(1)
    weekly["load"] = weekly["load"].round(0)
    return weekly.to_dict(orient="records")


def get_vo2max_progress():
    """Returns VO2max trend over time."""
    df, _ = load_data()
    vo2 = df[df["vo2max"] > 0].sort_values("start_time_local")
    if len(vo2) < 2:
        return {"message": "Not enough VO2max data recorded yet."}
    first = float(vo2.iloc[0]["vo2max"])
    last = float(vo2.iloc[-1]["vo2max"])
    peak = float(vo2["vo2max"].max())
    return {
        "first_recorded": round(first, 1),
        "current": round(last, 1),
        "peak": round(peak, 1),
        "change_total": round(last - first, 1),
        "trend": "improving" if last > first else "declining" if last < first else "stable",
        "data_points": len(vo2),
    }


def get_activity_breakdown():
    """Returns all-time breakdown by activity type."""
    df, _ = load_data()
    breakdown = df.groupby("activity_type").agg(
        sessions=("activity_id", "count"),
        total_km=("distance_km", "sum"),
        avg_hr=("avg_hr", "mean"),
        total_calories=("calories", "sum"),
        total_load=("training_load", "sum"),
    ).reset_index()
    breakdown["total_km"] = breakdown["total_km"].round(1)
    breakdown["avg_hr"] = breakdown["avg_hr"].round(0)
    breakdown["total_calories"] = breakdown["total_calories"].astype(int)
    breakdown["total_load"] = breakdown["total_load"].round(0)
    return breakdown.sort_values("sessions", ascending=False).to_dict(orient="records")


def get_recent_activities(n=10):
    """Returns last N activities with full details."""
    df, _ = load_data()
    return activity_detail_records(df, n)


def get_coaching_context():
    """Returns a balanced snapshot for open-ended coaching questions."""
    df, _ = load_data()
    dated = df.dropna(subset=["start_time_local"])
    if dated.empty:
        return {"message": "No training activities are available."}

    latest_date = dated["start_time_local"].max().normalize()
    recent_start = latest_date - pd.Timedelta(days=27)
    recent = dated[
        (dated["start_time_local"] >= recent_start)
        & (dated["start_time_local"] < latest_date + pd.Timedelta(days=1))
    ].copy()
    weekly = recent.assign(
        week=recent["start_time_local"].dt.to_period("W").dt.start_time
    ).groupby("week").agg(
        sessions=("activity_id", "count"),
        distance_km=("distance_km", "sum"),
        duration_minutes=("duration_minutes", "sum"),
        training_load=("training_load", "sum"),
    ).reset_index()
    weekly["week"] = weekly["week"].dt.strftime("%Y-%m-%d")
    weekly["distance_km"] = weekly["distance_km"].round(1)
    weekly["duration_minutes"] = weekly["duration_minutes"].round(0)
    weekly["training_load"] = weekly["training_load"].round(0)

    return {
        "data_through": latest_date.strftime("%Y-%m-%d"),
        "recent_period": {
            "start_date": recent_start.strftime("%Y-%m-%d"),
            "end_date": latest_date.strftime("%Y-%m-%d"),
        },
        "recent_summary": {
            "total_sessions": len(recent),
            "total_km": round(float(recent["distance_km"].sum()), 1),
            "total_minutes": round(float(recent["duration_minutes"].sum()), 0),
            "total_training_load": round(float(recent["training_load"].sum()), 0),
            "activity_types": recent["activity_type"].value_counts().to_dict(),
        },
        "weekly_trend": weekly.to_dict(orient="records"),
        "latest_activities": get_recent_activities(12),
        "vo2max_progress": get_vo2max_progress(),
        "personal_bests": get_personal_bests(),
    }


def get_activities_by_date_range(start_date=None, end_date=None):
    """Returns a training summary for an explicit date range."""
    df, _ = load_data()
    start = pd.to_datetime(start_date, errors="coerce") if start_date else None
    end = pd.to_datetime(end_date, errors="coerce") if end_date else None
    if start is None or pd.isna(start) or end is None or pd.isna(end):
        raise ValueError("A valid start_date and end_date are required.")

    data = df[
        (df["start_time_local"] >= start)
        & (df["start_time_local"] < end + pd.Timedelta(days=1))
    ].copy()
    running = data[data["activity_type"] == "running"]
    activity_types = data["activity_type"].value_counts().to_dict()
    return {
        "period": {
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
        },
        "total_sessions": len(data),
        "total_km": round(float(data["distance_km"].sum()), 1),
        "running_km": round(float(running["distance_km"].sum()), 1),
        "total_minutes": round(float(data["duration_minutes"].sum()), 0),
        "avg_hr": (
            round(float(data[data["avg_hr"] > 0]["avg_hr"].mean()), 0)
            if not data[data["avg_hr"] > 0].empty
            else 0
        ),
        "total_calories": int(data["calories"].sum()),
        "total_training_load": round(float(data["training_load"].sum()), 0),
        "activity_types": activity_types,
        "activities_returned": min(len(data), 20),
        "activities": activity_detail_records(data),
    }


def get_personal_bests():
    """Returns personal best performances."""
    df, _ = load_data()
    running = df[df["activity_type"] == "running"]
    cycling = df[df["activity_type"].str.contains("cycling", case=False, na=False)]
    result = {}
    if len(running) > 0:
        longest_run = running.loc[running["distance_km"].idxmax()]
        result["longest_run_km"] = round(float(longest_run["distance_km"]), 1)
        result["longest_run_date"] = longest_run["start_time_local"].strftime("%Y-%m-%d")
        fastest_pace = running[running["distance_km"] > 5]
        if len(fastest_pace) > 0:
            best_pace_idx = (fastest_pace["duration_minutes"] / fastest_pace["distance_km"]).idxmin()
            best = fastest_pace.loc[best_pace_idx]
            result["best_pace"] = format_pace(
                best["duration_minutes"] / best["distance_km"]
            )
    if len(cycling) > 0:
        longest_ride = cycling.loc[cycling["distance_km"].idxmax()]
        result["longest_ride_km"] = round(float(longest_ride["distance_km"]), 1)
    vo2_data = df[df["vo2max"] > 0]
    if len(vo2_data) > 0:
        result["peak_vo2max"] = round(float(vo2_data["vo2max"].max()), 1)
    return result

def get_cardiac_drift_trend(weeks=8):
    """Returns cardiac drift trend for long runs over last N weeks."""
    df, _ = load_data()
    now = pd.Timestamp.now()

    long_runs = df[
        (df["activity_type"] == "running") &
        (df["start_time_local"] >= now - pd.Timedelta(weeks=weeks)) &
        (df["duration_minutes"] >= 30) &
        (df["avg_hr"] > 0)
    ].copy()

    if long_runs.empty:
        return {"message": "No long runs found in this period"}

    long_runs["hr_drift"] = (
        (long_runs["max_hr"] - long_runs["avg_hr"]) /
        long_runs["avg_hr"] * 100
    ).round(1)

    long_runs["date"] = long_runs["start_time_local"].dt.strftime("%Y-%m-%d")

    recent_avg = round(float(long_runs["hr_drift"].tail(5).mean()), 1)
    older_avg  = round(float(long_runs["hr_drift"].head(5).mean()), 1)
    trend = "improving" if recent_avg < older_avg else "declining" if recent_avg > older_avg else "stable"

    return {
        "drift_trend": trend,
        "recent_avg_drift_pct": recent_avg,
        "older_avg_drift_pct": older_avg,
        "interpretation": (
            "Lower drift = better aerobic endurance. "
            "Under 5% is excellent, 5-8% is good, above 8% means aerobic base needs work."
        ),
        "sessions": long_runs[["date", "hr_drift", "avg_hr", "max_hr", "duration_minutes", "distance_km"]]
                    .fillna(0).to_dict(orient="records")
    }

# Tool registry — maps tool names to functions and descriptions
TOOLS = {
    "get_coaching_context": {
        "fn": get_coaching_context,
        "description": "Use for: open-ended coaching, planning next week, recovery, pacing, recommendations, or questions not covered by another tool"
    },
    "get_activities_by_date_range": {
        "fn": get_activities_by_date_range,
        "description": "Use for: a named month or year, a specific date, or an explicit date range"
    },
    "get_activities_last_month": {
        "fn": get_activities_last_month,
        "description": "Use for: last month, previous month, monthly stats, past 1 month"
    },
    "get_activities_this_week": {
        "fn": get_activities_this_week,
        "description": "Use for: this week, current week, this past week"
    },
    "get_last_n_days": {
        "fn": get_last_n_days,
        "description": "Use for: last N days, past N days, past N weeks, past N months, past N years (any time range: 1-365 days)"
    },
    "get_training_load_trend": {
        "fn": get_training_load_trend,
        "description": "Use for: training load trend over time, weekly load pattern, overtraining risk, progression"
    },
    "get_vo2max_progress": {
        "fn": get_vo2max_progress,
        "description": "Use for: VO2max progress, fitness level, aerobic capacity change, peak fitness"
    },
    "get_activity_breakdown": {
        "fn": get_activity_breakdown,
        "description": "Use for: activity type breakdown, running vs cycling vs strength, how many of each type"
    },
    "get_recent_activities": {
        "fn": get_recent_activities,
        "description": "Use for: recent workouts, last N activities, latest sessions, what I did recently"
    },
    "get_personal_bests": {
        "fn": get_personal_bests,
        "description": "Use for: personal bests, records, longest run, fastest pace, peak performances"
    },
    "get_cardiac_drift_trend": {
    "fn": get_cardiac_drift_trend,
    "description": "Use when asked about cardiac drift, aerobic decoupling, endurance, long run quality"
},
}


def select_tool(question: str) -> str:
    """Simple keyword-based tool selector as fallback."""
    q = question.lower()
    month_names = [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    ]
    if any(month in q for month in month_names) or re.search(r"\b20\d{2}\b|\d{4}-\d{2}-\d{2}", q):
        return "get_activities_by_date_range"
    if any(w in q for w in ["last month", "previous month", "monthly"]):
        return "get_activities_last_month"
    if any(w in q for w in ["this week", "current week"]):
        return "get_activities_this_week"
    if any(w in q for w in ["last 7", "last 14", "last 30", "last 60", "last 90", "past week", "past month"]):
        return "get_last_n_days"
    if any(w in q for w in ["training load", "overtraining", "load trend"]):
        return "get_training_load_trend"
    if any(w in q for w in ["vo2max", "fitness", "aerobic", "cardio"]):
        return "get_vo2max_progress"
    if any(w in q for w in ["breakdown", "how many", "total", "running vs", "types"]):
        return "get_activity_breakdown"
    if any(w in q for w in ["recent", "last session", "latest", "yesterday"]):
        return "get_recent_activities"
    if any(w in q for w in ["best", "record", "pb", "fastest", "longest"]):
        return "get_personal_bests"
    return "get_coaching_context"