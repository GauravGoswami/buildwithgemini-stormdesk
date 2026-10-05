"""Weather tools backed by Open-Meteo archive API and Firestore storm reports."""

from datetime import datetime, timedelta
import json
import math
import time
import urllib.request

from google.cloud.firestore_v1.base_query import FieldFilter
from app.db import db


def check_weather_at_loss(lat: float, lon: float, loss_date: str) -> dict:
    """Check historical weather data around a loss date using Open-Meteo archive API.

    Args:
        lat: Latitude of the loss location.
        lon: Longitude of the loss location.
        loss_date: Date of loss in 'YYYY-MM-DD' format.

    Returns:
        Dict containing loss-day max gust (mph), precipitation (mm), weather code,
        hail_code boolean, windiest_day_in_window boolean, and window max gust (mph).
    """
    try:
        lat = float(lat)
        lon = float(lon)
        dt = datetime.strptime(loss_date, "%Y-%m-%d")
    except (ValueError, TypeError) as e:
        return {"error": f"Invalid inputs for check_weather_at_loss: {str(e)}"}

    start_date = (dt - timedelta(days=3)).strftime("%Y-%m-%d")
    end_date = (dt + timedelta(days=3)).strftime("%Y-%m-%d")

    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}&"
        f"start_date={start_date}&end_date={end_date}&"
        f"daily=wind_gusts_10m_max,precipitation_sum,weather_code&"
        f"wind_speed_unit=mph&timezone=America/Chicago"
    )

    data = None
    last_error = None
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "StormDesk/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except Exception as e:
            last_error = e
            if attempt == 0:
                time.sleep(1)

    if not data or "daily" not in data:
        return {"error": f"Failed to fetch weather data: {str(last_error)}"}

    daily = data["daily"]
    times = daily.get("time", [])
    gusts = daily.get("wind_gusts_10m_max", [])
    precips = daily.get("precipitation_sum", [])
    codes = daily.get("weather_code", [])

    if loss_date not in times:
        return {"error": f"loss_date {loss_date} not found in weather response."}

    idx = times.index(loss_date)
    loss_day_gust = gusts[idx] if idx < len(gusts) else None
    loss_day_precip = precips[idx] if idx < len(precips) else None
    loss_day_code = codes[idx] if idx < len(codes) else None

    valid_gusts = [g for g in gusts if g is not None]
    window_max_gust = max(valid_gusts) if valid_gusts else loss_day_gust

    hail_code = int(loss_day_code) in (96, 99) if loss_day_code is not None else False
    windiest_day_in_window = (
        loss_day_gust is not None
        and window_max_gust is not None
        and loss_day_gust >= window_max_gust
    )

    return {
        "loss_date": loss_date,
        "max_gust_mph": loss_day_gust,
        "precipitation_sum": loss_day_precip,
        "weather_code": loss_day_code,
        "hail_code": hail_code,
        "windiest_day_in_window": windiest_day_in_window,
        "window_max_gust_mph": window_max_gust,
    }


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great Circle distance between two points in miles using Haversine formula."""
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def find_storm_reports(
    lat: float, lon: float, date: str, radius_miles: float = 25.0
) -> dict:
    """Find NOAA storm reports near a location for a given date from Firestore.

    Args:
        lat: Latitude of location.
        lon: Longitude of location.
        date: Date in 'YYYY-MM-DD' format.
        radius_miles: Maximum search radius in miles (default 25.0).

    Returns:
        Dict containing 'reports' within radius (nearest first) and 'nearest_hail_miles'
        across ALL reports on that date (or None if no hail reports).
    """
    try:
        lat = float(lat)
        lon = float(lon)
        radius_miles = float(radius_miles)
    except (ValueError, TypeError) as e:
        return {"error": f"Invalid coordinates or radius: {str(e)}"}

    query = db.collection("storm_reports").where(filter=FieldFilter("date", "==", date))
    docs = query.stream()

    reports = []
    hail_distances = []

    for doc in docs:
        data = doc.to_dict()
        r_lat = data.get("lat")
        r_lon = data.get("lon")
        if r_lat is None or r_lon is None:
            continue

        try:
            r_lat = float(r_lat)
            r_lon = float(r_lon)
        except (ValueError, TypeError):
            continue

        dist = haversine_miles(lat, lon, r_lat, r_lon)

        report_type = str(data.get("type", ""))
        if report_type.lower() == "hail" or "hail" in report_type.lower():
            hail_distances.append(dist)

        if dist <= radius_miles:
            narrative = str(data.get("narrative") or "")
            reports.append({
                "id": str(data.get("id") or doc.id),
                "type": report_type,
                "location": data.get("location"),
                "county": data.get("county"),
                "magnitude": data.get("magnitude"),
                "magnitude_type": data.get("magnitude_type"),
                "distance_miles": round(dist, 1),
                "narrative": narrative[:200],
            })

    reports.sort(key=lambda r: r["distance_miles"])
    nearest_hail_miles = round(min(hail_distances), 1) if hail_distances else None

    return {
        "date": date,
        "radius_miles": radius_miles,
        "reports": reports,
        "nearest_hail_miles": nearest_hail_miles,
    }
