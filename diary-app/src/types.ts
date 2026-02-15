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
  gpx?: string // filename (relative to trip folder)
  notes?: string // filename (relative to trip folder)
}
