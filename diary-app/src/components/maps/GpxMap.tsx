import { useEffect, useState } from 'react'
import type { Trip } from '../../data/trips'
import { loadTripGpx } from '../../data/trips'
import { LeafletMap } from './LeafletMap'

function buildTripStats(trip: Trip): string {
  const parts: string[] = []
  if (typeof trip.meta.distanceKm === 'number') parts.push(`${trip.meta.distanceKm.toFixed(1)} km`)
  if (typeof trip.meta.durationMin === 'number') parts.push(`⏱ ${trip.meta.durationMin} min`)
  if (typeof trip.meta.avgKmh === 'number') parts.push(`Ø ${trip.meta.avgKmh.toFixed(1)} km/h`)
  if (typeof trip.meta.maxKmh === 'number') parts.push(`max ${trip.meta.maxKmh.toFixed(1)} km/h`)
  return parts.join(' · ')
}

export function GpxMap({ trip }: { trip: Trip }) {
  const [gpxText, setGpxText] = useState<string>('')
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    ;(async () => {
      try {
        setErr(null)
        setGpxText(await loadTripGpx(trip))
      } catch (e: any) {
        setErr(e?.message ?? String(e))
      }
    })()
  }, [trip])

  if (err) return <div style={{ color: 'crimson' }}>{err}</div>
  if (!gpxText) {
    return (
      <div style={{ border: '1px solid rgba(0,0,0,0.12)', borderRadius: 12, padding: 14, background: 'white' }}>
        Karte…
      </div>
    )
  }

  return <LeafletMap gpxText={gpxText} stats={buildTripStats(trip)} />
}
