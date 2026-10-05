#!/usr/bin/env python3
import csv
import gzip
import json
import math
import os
import re
import urllib.request

BASE_URL = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
CENTER_LAT = 29.76
CENTER_LON = -95.37
MAX_RADIUS_MILES = 100.0

def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8  # Radius of earth in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_latest_details_file_url():
    req = urllib.request.Request(BASE_URL, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req).read().decode("utf-8")
    matches = re.findall(r"StormEvents_details-ftp_v1\.0_d2024_c[0-9]+\.csv\.gz", html)
    if not matches:
        raise ValueError("No 2024 details CSV file found on NOAA server.")
    newest = sorted(list(set(matches)))[-1]
    return BASE_URL + newest, newest

def main():
    file_url, filename = get_latest_details_file_url()
    print(f"Downloading {filename} from {file_url}...")
    
    local_gz_path = os.path.join("/tmp", filename)
    if not os.path.exists(local_gz_path):
        urllib.request.urlretrieve(file_url, local_gz_path)
        print(f"Downloaded to {local_gz_path}")
    else:
        print(f"Using cached file at {local_gz_path}")

    reports = []
    counts_by_date = {}
    counts_by_type = {}

    with gzip.open(local_gz_path, "rt", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            state = (row.get("STATE") or "").upper()
            if state not in ["TEXAS", "LOUISIANA"]:
                continue
            
            yearmonth = str(row.get("BEGIN_YEARMONTH") or "")
            if yearmonth != "202405":
                continue
            
            try:
                begin_day = int(row.get("BEGIN_DAY") or 0)
            except ValueError:
                continue
            
            if not (15 <= begin_day <= 21):
                continue
            
            lat_str = row.get("BEGIN_LAT") or ""
            lon_str = row.get("BEGIN_LON") or ""
            if not lat_str.strip() or not lon_str.strip():
                continue
            
            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except ValueError:
                continue
            
            dist = haversine_miles(lat, lon, CENTER_LAT, CENTER_LON)
            if dist > MAX_RADIUS_MILES:
                continue
            
            # Format date
            date_str = f"2024-05-{begin_day:02d}"
            event_type = row.get("EVENT_TYPE") or "Unknown"
            
            # Magnitude & type
            mag_raw = row.get("MAGNITUDE")
            mag = float(mag_raw) if mag_raw and mag_raw.strip() else None
            
            mag_type_raw = row.get("MAGNITUDE_TYPE")
            mag_type = mag_type_raw.strip() if mag_type_raw and mag_type_raw.strip() else None
            
            narrative_raw = row.get("EVENT_NARRATIVE") or ""
            narrative = narrative_raw[:300]
            
            record = {
                "id": str(row.get("EVENT_ID")),
                "date": date_str,
                "time": str(row.get("BEGIN_TIME") or ""),
                "type": event_type,
                "county": row.get("CZ_NAME") or "",
                "location": row.get("BEGIN_LOCATION") or "",
                "magnitude": mag,
                "magnitude_type": mag_type,
                "lat": lat,
                "lon": lon,
                "damage_property": row.get("DAMAGE_PROPERTY") or "",
                "narrative": narrative
            }
            
            reports.append(record)
            
            counts_by_date[date_str] = counts_by_date.get(date_str, 0) + 1
            counts_by_type[event_type] = counts_by_type.get(event_type, 0) + 1

    # Save output
    output_paths = [
        "stormdesk-kit/data/storm_reports.json",
        "my-agent/stormdesk-kit/data/storm_reports.json"
    ]
    
    for path in output_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(reports, f, indent=2)
        print(f"Saved {len(reports)} records to {path}")

    # Copy script to my-agent/scripts as well
    os.makedirs("my-agent/scripts", exist_ok=True)
    with open("my-agent/scripts/build_storm_reports.py", "w", encoding="utf-8") as f:
        with open("scripts/build_storm_reports.py", "r", encoding="utf-8") as f_in:
            f.write(f_in.read())

    print("\n--- Summary ---")
    print(f"Total storm reports found: {len(reports)}\n")
    
    print("Counts by Date:")
    for d in sorted(counts_by_date.keys()):
        print(f"  {d}: {counts_by_date[d]}")
        
    print("\nCounts by Event Type:")
    for t in sorted(counts_by_type.keys()):
        print(f"  {t}: {counts_by_type[t]}")

if __name__ == "__main__":
    main()
