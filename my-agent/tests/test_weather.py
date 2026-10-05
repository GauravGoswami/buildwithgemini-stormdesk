"""Unit tests for weather tools."""

import pytest
from app.tools.weather import check_weather_at_loss, find_storm_reports, haversine_miles


def test_check_weather_at_loss():
    # Test for Houston Derecho loss date 2024-05-16
    res = check_weather_at_loss(29.79, -95.399, "2024-05-16")
    assert "error" not in res
    assert res["loss_date"] == "2024-05-16"
    assert isinstance(res["max_gust_mph"], (int, float))
    assert isinstance(res["precipitation_sum"], (int, float))
    assert isinstance(res["weather_code"], int)
    assert isinstance(res["hail_code"], bool)
    assert isinstance(res["windiest_day_in_window"], bool)
    assert isinstance(res["window_max_gust_mph"], (int, float))


def test_haversine_miles():
    # Houston (29.7604, -95.3698) to Dallas (32.7767, -96.7970) is ~225-240 miles
    dist = haversine_miles(29.7604, -95.3698, 32.7767, -96.7970)
    assert 220 < dist < 250


def test_find_storm_reports():
    res = find_storm_reports(29.79, -95.399, "2024-05-16", radius_miles=25.0)
    assert "error" not in res
    assert res["date"] == "2024-05-16"
    assert res["radius_miles"] == 25.0
    assert isinstance(res["reports"], list)
    assert len(res["reports"]) > 0

    first_rep = res["reports"][0]
    assert "id" in first_rep
    assert "type" in first_rep
    assert "location" in first_rep
    assert "county" in first_rep
    assert "magnitude" in first_rep
    assert "magnitude_type" in first_rep
    assert "distance_miles" in first_rep
    assert "narrative" in first_rep
    assert len(first_rep["narrative"]) <= 200

    # Ensure reports are sorted nearest first
    distances = [r["distance_miles"] for r in res["reports"]]
    assert distances == sorted(distances)

    # Check nearest_hail_miles
    assert "nearest_hail_miles" in res
