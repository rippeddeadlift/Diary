import { useEffect, useState } from 'react'
import type { Trip } from '../../data/trips'
import { loadTripGpx } from '../../data/trips'
import { LeafletMap } from './LeafletMap'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

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

  return (
    <Card className="overflow-hidden">
      <CardHeader className="py-2">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <CardTitle className="text-base">GPX-Route</CardTitle>
          {gpxText ? <div className="text-xs text-muted-foreground">{buildTripStats(trip)}</div> : null}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {gpxText ? (
          <LeafletMap gpxText={gpxText} />
        ) : (
          <div className="p-4 text-sm text-muted-foreground">Karte…</div>
        )}
      </CardContent>
    </Card>
  )
}
