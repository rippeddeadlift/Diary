import { useMemo, useState } from 'react'
import type { Trip } from '@/data/trips'
import { TripList } from '@/components/TripList'
import { TripView } from '@/components/TripView'
import { TripsImportCard } from '@/components/trips/TripsImportCard'
import { Badge } from '@/components/ui/badge'

type ToursView = { kind: 'list' } | { kind: 'trip'; trip: Trip }

type Activity = 'all' | 'cycling' | 'running' | 'hiking' | 'skiing'

function tripHasActivity(t: Trip, activity: Exclude<Activity, 'all'>): boolean {
  return (t.meta.tags || []).includes(activity)
}

export function ToursPage({ trips, onReload }: { trips: Trip[]; onReload: () => Promise<void> }) {
  const [view, setView] = useState<ToursView>({ kind: 'list' })
  const [activity, setActivity] = useState<Activity>('all')

  const visibleTrips = useMemo(() => {
    if (activity === 'all') return trips
    return trips.filter((t) => tripHasActivity(t, activity))
  }, [activity, trips])

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

      <div className="flex flex-wrap gap-2">
        {(
          [
            { key: 'all', label: 'Alle' },
            { key: 'cycling', label: 'cycling' },
            { key: 'running', label: 'running' },
            { key: 'hiking', label: 'hiking' },
            { key: 'skiing', label: 'skiing' }
          ] as const
        ).map((it) => (
          <button key={it.key} type="button" onClick={() => setActivity(it.key)} className="rounded-md">
            <Badge variant={activity === it.key ? 'default' : 'secondary'}>{it.label}</Badge>
          </button>
        ))}
      </div>

      <TripList trips={visibleTrips} onOpen={(trip) => setView({ kind: 'trip', trip })} />
    </div>
  )
}
