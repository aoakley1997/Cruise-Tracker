#!/usr/bin/env python3
"""Collect real AIS position reports for Quantum of the Seas.
No synthetic or estimated coordinates are published.
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import websockets

MMSI = 311000267
OUTPUT = Path("ship-position.json")
URL = "wss://stream.aisstream.io/v0/stream"

def parse_report(message):
    if message.get("MessageType") != "PositionReport":
        return None
    meta = message.get("MetaData") or {}
    if int(meta.get("MMSI") or 0) != MMSI:
        return None
    pos = (message.get("Message") or {}).get("PositionReport") or {}
    lat, lon = pos.get("Latitude"), pos.get("Longitude")
    if not isinstance(lat, (float, int)) or not isinstance(lon, (float, int)):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        return None
    ts = meta.get("time_utc")
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    if not (0 <= (datetime.now(timezone.utc) - dt).total_seconds() < 86400):
        return None
    speed = pos.get("Sog")
    course = pos.get("Cog")
    return {
        "mmsi": MMSI, "lat": float(lat), "lon": float(lon),
        "speedKnots": round(float(speed), 1) if isinstance(speed, (int, float)) and 0 <= speed < 102.3 else None,
        "courseDegrees": round(float(course), 1) if isinstance(course, (int, float)) and 0 <= course < 360 else None,
        "reportedAt": dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "AISStream"
    }

async def run():
    key = os.environ.get("AISSTREAM_API_KEY")
    if not key:
        raise SystemExit("AISSTREAM_API_KEY secret not configured")
    newest = None
    if OUTPUT.exists():
        try:
            existing = json.loads(OUTPUT.read_text())
            if existing.get("mmsi") == MMSI:
                newest = existing
        except (ValueError, OSError):
            pass
    try:
        async with websockets.connect(URL, open_timeout=20, ping_interval=20) as ws:
            await ws.send(json.dumps({"APIKey": key, "BoundingBoxes": [[[-90, -180], [90, 180]]], "FiltersShipMMSI": [str(MMSI)]}))
            deadline = asyncio.get_running_loop().time() + 215
            while asyncio.get_running_loop().time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=min(25, max(1, deadline - asyncio.get_running_loop().time())))
                    p = parse_report(json.loads(raw))
                    if p and (newest is None or p["reportedAt"] > newest.get("reportedAt", "")):
                        newest = p
                        OUTPUT.write_text(json.dumps(newest, indent=2) + "\n")
                        print("Received verified AIS report at", p["reportedAt"])
                except asyncio.TimeoutError:
                    continue
    except Exception as exc:
        print("AIS stream unavailable:", type(exc).__name__, str(exc)[:180])
    if newest is None:
        print("No verified AIS report available; no file created.")
    else:
        print("Latest verified report:", newest["reportedAt"])

if __name__ == "__main__":
    asyncio.run(run())
