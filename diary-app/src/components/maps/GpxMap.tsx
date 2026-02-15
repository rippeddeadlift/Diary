import { useEffect, useState } from 'react'
import type { Trip } from '../../data/trips'
import { loadTripGpx } from '../../data/trips'
import { LeafletMap } from './LeafletMap'

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

  return <LeafletMap gpxText={gpxText} />
}
