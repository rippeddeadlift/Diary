export type TripIndex = {
  version: number
  trips: { id: string; path: string }[]
}

export type TripMeta = {
  id: string
  title: string
  date: string 
  tags?: string[]
  distanceKm?: number
  durationMin?: number
  preview?: {
    bbox: [number, number, number, number] // [minLat, minLon, maxLat, maxLon]
    points: [number, number][] // [lat, lon] sampled
  }
  gpx?: string // filename (relative to trip folder)
  notes?: string // filename (relative to trip folder)
}
