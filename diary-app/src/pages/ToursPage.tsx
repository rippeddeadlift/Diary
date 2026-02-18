import { useMemo, useState } from 'react'
import type { Trip } from '@/data/trips'
import { TripList } from '@/components/TripList'
import { TripView } from '@/components/TripView'
import { TripsImportCard } from '@/components/trips/TripsImportCard'
import { Switch } from '@/components/ui/switch'

type ToursView = { kind: 'list' } | { kind: 'trip'; trip: Trip }

const MIN_DURATION_MIN = 20
const MIN_DIST_KM: Record<string, number> = {
  cycling: 10,
  running: 3,
  hiking: 2
}

function passesDefaultTourFilter(t: Trip): boolean {
  // Duration gate (if missing, keep visible)
  if (typeof t.meta.durationMin === 'number' && t.meta.durationMin < MIN_DURATION_MIN) return false

  const tags = t.meta.tags || []
  const dist = t.meta.distanceKm

  // If we know the activity type AND the distance, enforce per-type thresholds.
  if (typeof dist === 'number') {
    for (const [tag, minKm] of Object.entries(MIN_DIST_KM)) {
      if (tags.includes(tag) && dist < minKm) return false
    }
  }

  return true
}

export function ToursPage({ trips, onReload }: { trips: Trip[]; onReload: () => Promise<void> }) {
  const [view, setView] = useState<ToursView>({ kind: 'list' })
  const [showAll, setShowAll] = useState(false)

  const visibleTrips = useMemo(() => {
    if (showAll) return trips
    return trips.filter(passesDefaultTourFilter)
  }, [showAll, trips])

  if (view.kind === 'trip') {
    return (
      <TripView
        trip={view.trip}
        onBack={() => setView({ kind: 'list' })}
        onDeleted={async () => {
          await onReload()
          setView({ kind: 'list' })
        }}
      />
    )
  }

  return (
    <div className="space-y-4">
      <TripsImportCard onImported={onReload} />

      <div className="flex items-center justify-between gap-3">
        <div className="text-sm text-muted-foreground">
          {showAll ? 'Alle Aktivitäten' : `Touren (≥ ${MIN_DURATION_MIN} min, cycling ≥ ${MIN_DIST_KM.cycling} km, running ≥ ${MIN_DIST_KM.running} km, hiking ≥ ${MIN_DIST_KM.hiking} km)`}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <span>Kurz anzeigen</span>
          <Switch checked={showAll} onCheckedChange={setShowAll} />
        </label>
      </div>

      <TripList trips={visibleTrips} onOpen={(trip) => setView({ kind: 'trip', trip })} />
    </div>
  )
}
