# Refactor notes

## What changed
We split the original `src/App.tsx` (which contained list + trip view + notes + map parsing) into small components.

New files:
- `src/data/trips.ts` — data loading functions (`loadTrips`, `loadTripNotes`, `loadTripGpx`)
- `src/components/TripList.tsx` — grid/list view
- `src/components/TripView.tsx` — trip page (header + map + notes)
- `src/components/content/Notes.tsx` — loads and renders notes.md
- `src/components/maps/GpxMap.tsx` — loads route.gpx and passes to Leaflet
- `src/components/maps/LeafletMap.tsx` — Leaflet setup + GPX polyline

`src/App.tsx` is now just app state + switching between list/trip.

## How to add features
- New trip fields → extend `TripMeta` in `src/types.ts`
- Add UI → create a component in `src/components/...` and plug it into TripView or TripList
- Add new data files in a trip folder (e.g. `photos/`) → add loader in `src/data/trips.ts`

## Build note
TypeScript build required installing `@types/leaflet`.
