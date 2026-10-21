#!/usr/bin/env python3
"""Read-only diagnostic of permitted CruiseMapper public ship page.

Never writes ship-position.json. Reports whether usable coordinates can be
identified, without treating map viewport coordinates as vessel coordinates.
"""
import re
import urllib.request
from html import unescape

URL = "https://www.cruisemapper.com/ships/Quantum-Of-The-Seas-802"
req = urllib.request.Request(URL, headers={
    "User-Agent": "Mozilla/5.0 (compatible; FamilyAtSea/1.0; authorised family cruise tracker)",
    "Accept": "text/html,application/xhtml+xml",
})
try:
    with urllib.request.urlopen(req, timeout=25) as resp:
        html = resp.read(2_000_000).decode("utf-8", "replace")
        print("HTTP:", resp.status, "HTML bytes:", len(html))
except Exception as exc:
    print("CruiseMapper fetch unavailable:", type(exc).__name__, str(exc)[:240])
    raise SystemExit(0)

print("Ship identity:", "Quantum" in html, "MMSI:", "311000267" in html)
for key in ["latitude", "longitude", "lat", "lng", "lon", "position", "vesselfinder", "ais"]:
    print("Occurrences", key, len(re.findall(r"(?i)\b" + re.escape(key) + r"\b", html)))
# Inspect only short sanitized excerpts, not full page HTML or tokens.
patterns = [
    r'(?i)(?:latitude|longitude|lat|lng|lon)\s*["\\\']?\s*[:=]\s*["\\\']?-?\d{1,3}\.\d+',
    r'(?i)(?:mmsi|imo)\s*["\\\']?\s*[:=]\s*["\\\']?\d{7,9}',
]
for pattern in patterns:
    matches = list(re.finditer(pattern, html))
    print("Coordinate/identity candidate count:", len(matches))
    for match in matches[:12]:
        excerpt = unescape(html[max(0, match.start()-75):match.end()+75])
        excerpt = re.sub(r"[\r\n\t]+", " ", excerpt)
        print("Candidate:", excerpt[:230])

# Examine timestamp labels in the same page; never treat the fetch time as AIS time.
print("Timestamp diagnostics:")
time_patterns = [
    r"(?i)(?:last\\s+reported|last\\s+updated|last\\s+seen|received|reported|updated|position\\s+time|ais\\s+time)[^<>\\n]{0,110}",
    r"\\b20\\d{2}-\\d{2}-\\d{2}[T ]\\d{2}:\\d{2}(?::\\d{2})?(?:Z|[+-]\\d{2}:?\\d{2})?",
    r"(?i)(?:timestamp|lastUpdate|lastPosition|positionDate|updatedAt|reportedAt)[\\\"']?\\s*[:=]\\s*[\\\"']?[^,}<>]{1,90}",
]
for pattern in time_patterns:
    matches = list(re.finditer(pattern, html))
    print("Timestamp pattern matches:", len(matches))
    for match in matches[:12]:
        excerpt = unescape(html[max(0, match.start()-55):match.end()+55])
        excerpt = re.sub(r"[\\r\\n\\t]+", " ", excerpt)
        print("Time candidate:", excerpt[:230])


print("Speed and course diagnostics:")
for pattern in [
    r"(?i)(?:speed|knots?|\\bkn\\b|km/h|course|heading|rotation)[^<>\\n]{0,100}",
    r"(?i)\\b\\d{1,2}(?:\\.\\d+)?\\s*(?:kn|knots|km/h)\\b",
]:
    matches = list(re.finditer(pattern, html))
    print("Motion matches:", len(matches))
    for match in matches[:15]:
        excerpt = unescape(html[max(0, match.start()-65):match.end()+65])
        excerpt = re.sub(r"[\\r\\n\\t]+", " ", excerpt)
        print("Motion candidate:", excerpt[:230])

print("Diagnostic complete. No map data modified.")
