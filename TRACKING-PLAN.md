# Automatic ship tracking — implementation plan

Ship: Quantum of the Seas (MMSI 311000267)

This branch is a safe staging area. The existing deployed app has NOT been changed.

## Why there is no live data yet
AISStream provides a WebSocket stream, not a historical position endpoint. GitHub Pages cannot hold a private API key or run a persistent receiver. A scheduled GitHub Action can listen briefly but may miss reports between runs, especially offshore.

## Proposed ingestion contract
A verified backend should publish `ship-position.json` only after receiving a genuine AIS position report:
```json
{
  "mmsi": 311000267,
  "lat": -22.0,
  "lon": 165.0,
  "speedKnots": 15.2,
  "courseDegrees": 120,
  "reportedAt": "2026-10-21T00:00:00Z",
  "source": "AISStream"
}
```
The numbers above are **examples only** and must never be displayed as real vessel data.

## Safety requirements
- Never expose an AIS API key in public HTML or committed files.
- Do not overwrite a newer position with an older report.
- Display the AIS report timestamp, including when stale.
- Use ship coordinates for weather only if the report is sufficiently recent.
- Keep the planned itinerary distinct from actual AIS observations.
- Test receiving actual Quantum reports before enabling an automatic workflow.
