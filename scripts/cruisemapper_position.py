#!/usr/bin/env python3
"""Fetch permitted CruiseMapper public AIS position for Quantum of the Seas.

Only publish a position when the page explicitly identifies a recent AIS report.
The timestamp is inferred from the site's relative-age text, so record provenance.
"""
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

URL = "https://www.cruisemapper.com/ships/Quantum-Of-The-Seas-802"
MMSI = 311000267
OUT = Path("ship-position.json")

class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)

def extract(page, fetched_at):
    if "Quantum" not in page or "311000267" not in page or "9549463" not in page:
        return None
    match = re.search(r'"shipCurrentPositionMap"\s*:\s*\{([^}]{1,500})\}', page)
    if not match:
        print("No shipCurrentPositionMap object.")
        return None
    try:
        mapdata = json.loads("{" + match.group(1) + "}")
        lat, lon = float(mapdata["lat"]), float(mapdata["lon"])
    except (ValueError, TypeError, KeyError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        return None
    parser = Text()
    parser.feed(page)
    readable = re.sub(r"\s+", " ", unescape(" ".join(parser.parts)))
    # Require the explicit AIS age text. Never use page-fetch time as report time.
    age = re.search(
        r"AIS\s+position\s+was\s+last\s+reported\s+"
        r"(\d{1,3})\s+(seconds?|minutes?|hours?|days?)\s+ago",
        readable, re.I,
    )
    if not age:
        print("No trustworthy AIS age label on page.")
        return None
    n, unit = int(age.group(1)), age.group(2).lower()
    seconds = n * (1 if unit.startswith("second") else 60 if unit.startswith("minute") else 3600 if unit.startswith("hour") else 86400)
    # Reject stale positions. Relative age is rounded by the website, so subtract
    # an extra minute for conservative timestamp ordering.
    if seconds > 3600:
        print("CruiseMapper position too old:", n, unit)
        return None
    observed = fetched_at - timedelta(seconds=seconds + 60)
    return {
        "mmsi": MMSI,
        "lat": lat,
        "lon": lon,
        "speedKnots": None,
        "courseDegrees": None,
        "reportedAt": observed.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": "CruiseMapper (AIS; approximate timestamp)",
    }

def main():
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Mozilla/5.0 (compatible; FamilyAtSea/1.0; authorised family cruise tracker)",
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            page = response.read(2_000_000).decode("utf-8", "replace")
            fetched_at = datetime.now(timezone.utc)
    except Exception as exc:
        print("CruiseMapper unavailable:", type(exc).__name__, str(exc)[:150])
        return
    result = extract(page, fetched_at)
    if not result:
        print("No qualifying CruiseMapper position; keeping existing data.")
        return
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text())
            if old.get("mmsi") == MMSI and old.get("reportedAt", "") >= result["reportedAt"]:
                print("Existing AIS position is newer; keeping it.")
                return
        except (OSError, ValueError):
            pass
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print("Updated verified CruiseMapper position:", result["lat"], result["lon"], result["reportedAt"])

if __name__ == "__main__":
    main()
