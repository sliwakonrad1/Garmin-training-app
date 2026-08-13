import unittest
from unittest.mock import patch

import pandas as pd

import main
import mcp_tools


class AiCoachDateParsingTests(unittest.TestCase):
    def test_named_month_with_year(self):
        self.assertEqual(
            main.parse_explicit_date_range("How was my training in June 2025?"),
            {"start_date": "2025-06-01", "end_date": "2025-06-30"},
        )

    def test_explicit_date_range(self):
        self.assertEqual(
            main.parse_explicit_date_range("Compare 2026-05-01 to 2026-05-14"),
            {"start_date": "2026-05-01", "end_date": "2026-05-14"},
        )

    @patch("main.pd.Timestamp.now", return_value=pd.Timestamp("2026-08-10"))
    def test_named_month_without_year_uses_most_recent_occurrence(self, _):
        self.assertEqual(
            main.parse_explicit_date_range("What happened in December?"),
            {"start_date": "2025-12-01", "end_date": "2025-12-31"},
        )


class AiCoachDataTests(unittest.TestCase):
    def test_efficiency_scatter_normalizes_garmin_elevation_gain(self):
        activities = main.normalize_activity_dataframe(
            pd.DataFrame(
                {
                    "activity_id": [1],
                    "activity_name": ["Hilly run"],
                    "activity_type": ["running"],
                    "start_time_local": pd.to_datetime(["2026-08-05"]),
                    "distance_km": [10.0],
                    "avg_hr": [140.0],
                    "avg_speed_kmh": [12.0],
                    "elevationGain": [250.0],
                }
            )
        )

        with patch("main.get_df", return_value=(activities, pd.DataFrame())):
            result = main.get_efficiency_scatter()

        self.assertEqual(result[0]["elevation_gain"], 250.0)
        self.assertEqual(result[0]["elevation_per_100m"], 2.5)

    def test_efficiency_charts_prefer_weather_temperature_columns(self):
        activities = pd.DataFrame(
            {
                "activity_id": [1],
                "activity_name": ["Warm run"],
                "activity_type": ["running"],
                "start_time_local": pd.to_datetime(["2026-08-05"]),
                "distance_km": [10.0],
                "avg_hr": [140.0],
                "avg_speed_kmh": [12.0],
                "weather_temp_mean": [23.4],
                "min_temp_c": [4.0],
                "max_temp_c": [5.0],
            }
        )

        with patch("main.get_df", return_value=(activities, pd.DataFrame())):
            trend = main.get_efficiency_trend()
            scatter = main.get_efficiency_scatter()

        self.assertEqual(trend[0]["temperature"], 23.4)
        self.assertEqual(scatter[0]["temperature"], 23.4)

    def test_activity_group_filter_includes_all_running_variants(self):
        activities = main.normalize_activity_dataframe(
            pd.DataFrame(
                {
                    "activity_id": [1, 2, 3],
                    "activity_type": ["running", "trail_running", "cycling"],
                    "start_time_local": pd.to_datetime(["2026-08-01", "2026-08-02", "2026-08-03"]),
                    "distance_km": [5.0, 10.0, 20.0],
                }
            )
        )

        with patch("main.get_df", return_value=(activities, pd.DataFrame())):
            result = main.get_summary(activity_type="running")

        self.assertEqual(result["sessions"], 2)
        self.assertEqual(result["total_km"], 15.0)

    def test_coach_criteria_filters_aggregate_type_location_and_period(self):
        activities = pd.DataFrame(
            {
                "activity_id": [1, 2, 3],
                "activity_type": ["trail_running", "running", "cycling"],
                "activity_name": ["Alpine trail", "City run", "Alpine ride"],
                "location_name": ["Alps", "City", "Alps"],
                "start_time_local": pd.to_datetime(["2026-06-10", "2026-06-11", "2026-06-12"]),
                "distance_km": [12.0, 8.0, 50.0],
                "duration_minutes": [90.0, 40.0, 180.0],
                "avg_hr": [140.0, 145.0, 130.0],
                "max_hr": [160.0, 165.0, 155.0],
                "calories": [800, 500, 1200],
                "training_load": [100.0, 60.0, 150.0],
                "vo2max": [50.0, 50.0, 50.0],
            }
        )
        mcp_tools.configure_data_loader(lambda force_refresh=False: (activities, pd.DataFrame()))

        result = mcp_tools.get_activities_by_criteria(
            "How much trail running did I do in the Alps in June 2026?",
            start_date="2026-06-01",
            end_date="2026-06-30",
        )

        self.assertEqual(result["total_sessions"], 1)
        self.assertEqual(result["matched_activity_groups"], ["running"])
        self.assertEqual(result["matched_locations"], ["Alps"])
        self.assertEqual(result["total_km"], 12.0)

    def test_date_range_tool_uses_configured_backend_loader(self):
        activities = pd.DataFrame(
            {
                "activity_id": [1, 2],
                "activity_type": ["running", "cycling"],
                "start_time_local": pd.to_datetime(["2026-06-10", "2026-07-10"]),
                "distance_km": [10.0, 20.0],
                "duration_minutes": [60.0, 90.0],
                "avg_hr": [140.0, 130.0],
                "calories": [600, 700],
                "training_load": [80.0, 90.0],
            }
        )
        weekly = pd.DataFrame()
        calls = []

        def loader(force_refresh=False):
            calls.append(force_refresh)
            return activities, weekly

        mcp_tools.configure_data_loader(loader)
        result = mcp_tools.get_activities_by_date_range("2026-06-01", "2026-06-30")

        self.assertEqual(calls, [False])
        self.assertEqual(result["total_sessions"], 1)
        self.assertEqual(result["running_km"], 10.0)

    def test_open_question_uses_general_coaching_context(self):
        self.assertEqual(
            mcp_tools.select_tool("How should I structure next week?"),
            "get_coaching_context",
        )

    def test_coaching_context_is_anchored_to_latest_available_data(self):
        activities = pd.DataFrame(
            {
                "activity_id": [1, 2, 3],
                "activity_name": ["June run", "July ride", "August run"],
                "activity_type": ["running", "cycling", "running"],
                "start_time_local": pd.to_datetime(
                    ["2026-06-01", "2026-07-20", "2026-08-08"]
                ),
                "distance_km": [10.0, 20.0, 8.0],
                "duration_minutes": [60.0, 90.0, 45.0],
                "avg_hr": [140.0, 130.0, 145.0],
                "calories": [600, 700, 500],
                "training_load": [80.0, 90.0, 70.0],
                "vo2max": [50.0, 51.0, 52.0],
                "elevation_gain_m": [10.0, 20.0, 5.0],
                "averageRunningCadenceInStepsPerMinute": [170.0, None, 176.0],
                "hrTimeInZone_3": [600.0, 300.0, 720.0],
                "ownerFullName": ["Private", "Private", "Private"],
            }
        )
        mcp_tools.configure_data_loader(lambda force_refresh=False: (activities, pd.DataFrame()))

        result = mcp_tools.get_coaching_context()

        self.assertEqual(result["data_through"], "2026-08-08")
        self.assertEqual(result["recent_period"]["start_date"], "2026-07-12")
        self.assertEqual(result["recent_summary"]["total_sessions"], 2)
        latest = result["latest_activities"][0]
        self.assertEqual(latest["average_running_cadence_spm"], 176.0)
        self.assertEqual(latest["heart_rate_zone_3_minutes"], 12.0)
        self.assertNotIn("ownerFullName", latest)
        self.assertEqual(mcp_tools.format_pace(5.499), "5:30 min/km")

    @patch("main.get_df")
    def test_activities_endpoint_filters_dates_and_returns_pace(self, get_df):
        activities = pd.DataFrame(
            {
                "activity_id": [1, 2],
                "activity_name": ["Older run", "Filtered run"],
                "activity_type": ["running", "running"],
                "start_time_local": pd.to_datetime(["2026-06-10", "2026-08-05"]),
                "distance_km": [10.0, 5.0],
                "duration_minutes": [55.0, 25.0],
                "avg_hr": [140.0, 145.0],
                "max_hr": [160.0, 165.0],
                "calories": [600, 350],
                "training_load": [80.0, 60.0],
                "vo2max": [50.0, 51.0],
            }
        )
        get_df.return_value = (activities, pd.DataFrame())

        result = main.get_activities(
            start_date="2026-08-01", end_date="2026-08-31"
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["activity_name"], "Filtered run")
        self.assertEqual(result[0]["pace_min_per_km"], 5.0)


if __name__ == "__main__":
    unittest.main()
