from typing import Iterable

import pandas as pd

ACTIVITY_GROUPS = {
    "running": ["running", "trail_running", "treadmill_running", "track_running"],
    "cycling": [
        "cycling",
        "road_biking",
        "indoor_cycling",
        "mountain_biking",
        "gravel_cycling",
        "virtual_ride",
        "bike",
    ],
    "strength": ["strength_training", "gym", "fitness_equipment", "weight_training"],
    "hiking": ["hiking", "walking", "mountaineering"],
    "swimming": ["swimming", "open_water_swimming", "pool_swimming"],
    "other": [],
}


def normalize_activity_type(activity_type: object) -> str:
    return str(activity_type or "").strip().lower().replace("-", "_").replace(" ", "_")


def get_parent_type(activity_type: object) -> str:
    normalized = normalize_activity_type(activity_type)
    for parent, children in ACTIVITY_GROUPS.items():
        if normalized in children:
            return parent
    return "other"


def activity_type_mask(dataframe: pd.DataFrame, activity_type: str) -> pd.Series:
    normalized = normalize_activity_type(activity_type)
    values = dataframe["activity_type"].map(normalize_activity_type)
    if normalized in ACTIVITY_GROUPS:
        if normalized == "other":
            known_types = {
                child for children in ACTIVITY_GROUPS.values() for child in children
            }
            return ~values.isin(known_types)
        return values.isin(ACTIVITY_GROUPS[normalized])
    return values == normalized


def activity_group_statistics(dataframe: pd.DataFrame) -> list[dict]:
    data = dataframe.copy()
    data["activity_group"] = data["activity_type"].map(get_parent_type)
    grouped = data.groupby("activity_group", as_index=False).agg(
        sessions=("activity_id", "count"),
        total_km=("distance_km", "sum"),
        total_hours=("duration_minutes", lambda value: value.sum() / 60),
        total_calories=("calories", "sum"),
        total_load=("training_load", "sum"),
    )
    grouped["total_km"] = grouped["total_km"].round(1)
    grouped["total_hours"] = grouped["total_hours"].round(1)
    grouped["total_calories"] = grouped["total_calories"].round(0).astype(int)
    grouped["total_load"] = grouped["total_load"].round(0)
    return grouped.sort_values("sessions", ascending=False).to_dict(orient="records")


def available_activity_groups(activity_types: Iterable[object]) -> list[dict]:
    available = {normalize_activity_type(activity_type) for activity_type in activity_types}
    known_types = {child for children in ACTIVITY_GROUPS.values() for child in children}
    groups = []
    for group, children in ACTIVITY_GROUPS.items():
        members = (
            sorted(available - known_types)
            if group == "other"
            else [child for child in children if child in available]
        )
        if members:
            groups.append({"group": group, "activity_types": members})
    return groups
