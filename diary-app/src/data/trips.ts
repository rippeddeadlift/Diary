import type { TripIndex, TripMeta } from '../types'

export type Trip = { id: string; path: string; meta: TripMeta }

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${url}`)
  return (await res.json()) as T
}

export async function loadTrips(): Promise<Trip[]> {
  const idx = await fetchJson<TripIndex>('/tours/index.json')
  const loaded: Trip[] = []
  for (const t of idx.trips) {
    const meta = await fetchJson<TripMeta>(`/tours/${t.path}/meta.json`)
    loaded.push({ ...t, meta })
  }
  loaded.sort((a, b) => b.meta.date.localeCompare(a.meta.date))
  return loaded
}

export async function loadTripNotes(trip: Trip): Promise<string> {
  if (!trip.meta.notes) return ''
  const res = await fetch(`/tours/${trip.path}/${trip.meta.notes}`)
  if (!res.ok) throw new Error(`Cannot load notes for ${trip.id}`)
  return await res.text()
}

export async function loadTripGpx(trip: Trip): Promise<string> {
  if (!trip.meta.gpx) return ''
  const res = await fetch(`/tours/${trip.path}/${trip.meta.gpx}`)
  if (!res.ok) throw new Error(`Cannot load GPX for ${trip.id}`)
  return await res.text()
}
