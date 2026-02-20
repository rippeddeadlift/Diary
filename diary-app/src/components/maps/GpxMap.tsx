import { useEffect, useState } from 'react'
import type { Trip } from '../../data/trips'
import { loadTripGpx } from '../../data/trips'
import { LeafletMap } from './LeafletMap'
import { Card, CardContent } from '@/components/ui/card'

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
    <Card className="overflow-hidden z-0">
      <CardContent className="p-0">
        {gpxText ? <LeafletMap gpxText={gpxText} /> : <div className="p-4 text-sm text-muted-foreground">Karte…</div>}
      </CardContent>
    </Card>
  )
}
