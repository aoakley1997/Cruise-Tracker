#!/usr/bin/env python3
"""Fetch Quantum of the Seas' latest verified MyShipTracking AIS position.
Never publish guessed coordinates, and never overwrite a newer report.
"""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MMSI = 311000267
OUTPUT = Path("ship-position.json")
URL = f"https://api.myshiptracking.com/api/v2/vessel?mmsi={MMSI}&response=simple"

def utc_timestamp(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00").replace(" ", "T"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        age = (datetime.now(timezone.utc) - dt).total_seconds()
        if age < -300 or age > 86400 * 7:
            return None
        return dt.isoformat().replace("+00:00", "Z")
    except (ValueError, TypeError):
        return None

def normalise(payload):
    if not isinstance(payload, dict) or payload.get("status") != "success":
        return None
    data = payload.get("data")
    if isinstance(data, list):
        data = data[0] if len(data) == 1 else None
    if not isinstance(data, dict):
        return None
    try:
        if int(data.get("mmsi")) != MMSI:
            return None
        lat = float(data["lat"])
        lon = float(data["lng"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
            return None
    except (TypeError, ValueError, KeyError):
        return None
    timestamp = utc_timestamp(data.get("received"))
    if not timestamp:
        return None
    def numeric(value, lower, upper):
        try:
            number = float(value)
            return round(number, 1) if lower <= number < upper else None
        except (TypeError, ValueError):
            return None
    return {
        "mmsi": MMSI, "lat": lat, "lon": lon,
        "speedKnots": numeric(data.get("speed"), 0, 102.3),
        "courseDegrees": numeric(data.get("course"), 0, 360),
        "reportedAt": timestamp, "source": "MyShipTracking"
    }

def main():
    key = os.getenv("MYSHIPTRACKING_API_KEY")
    if not key:
        print("MyShipTracking fallback not configured; AISStream remains available.")
        return
    request = urllib.request.Request(URL, headers={
        "Authorization": "Bearer " + key,
        "Accept": "application/json",
        "User-Agent": "FamilyCruiseTracker/1.0"
    })
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print("Fallback API unavailable:", type(exc).__name__)
        return
    position = normalise(payload)
    if not position:
        print("No verified MyShipTracking position available.")
        return
    if OUTPUT.exists():
        try:
            current = json.loads(OUTPUT.read_text())
            if current.get("mmsi") == MMSI and current.get("reportedAt", "") >= position["reportedAt"]:
                print("Existing AIS report is as new or newer; retaining it.")
                return
        except (ValueError, OSError):
            pass
    OUTPUT.write_text(json.dumps(position, indent=2) + "\n")
    print("Saved verified MyShipTracking position:", position["reportedAt"])

if __name__ == "__main__":
    main()
