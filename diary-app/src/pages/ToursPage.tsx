import { useMemo, useState } from 'react'
import type { Trip } from '@/data/trips'
import { TripList } from '@/components/TripList'
import { TripView } from '@/components/TripView'
import { TripsImportCard } from '@/components/trips/TripsImportCard'
import { FilterBar } from '@/components/FilterBar'
import { TRIP_ACTIVITY_TAGS, type TripActivityTag } from '@/data/tagConfig'

type ToursView = { kind: 'list' } | { kind: 'trip'; trip: Trip }

type Activity = 'all' | 'unknown' | TripActivityTag

type SortKey = 'date_desc' | 'distance_desc' | 'duration_desc' | 'avg_desc' | 'max_desc'

function tripHasActivity(t: Trip, activity: Exclude<Activity, 'all'>): boolean {
  if (activity === 'unknown') return (t.meta.tags || []).length === 0
  return (t.meta.tags || []).includes(activity)
}

function compareMaybeNumberDesc(a: number | undefined, b: number | undefined): number {
  const aa = typeof a === 'number' && Number.isFinite(a) ? a : null
  const bb = typeof b === 'number' && Number.isFinite(b) ? b : null
  if (aa === null && bb === null) return 0
  if (aa === null) return 1
  if (bb === null) return -1
  return bb - aa
}

function compareTrips(a: Trip, b: Trip, sort: SortKey): number {
  if (sort === 'distance_desc') {
    const c = compareMaybeNumberDesc(a.meta.distanceKm, b.meta.distanceKm)
    return c !== 0 ? c : b.meta.date.localeCompare(a.meta.date)
  }
  if (sort === 'duration_desc') {
    const c = compareMaybeNumberDesc(a.meta.durationMin, b.meta.durationMin)
    return c !== 0 ? c : b.meta.date.localeCompare(a.meta.date)
  }
  if (sort === 'avg_desc') {
    const c = compareMaybeNumberDesc(a.meta.avgKmh, b.meta.avgKmh)
    return c !== 0 ? c : b.meta.date.localeCompare(a.meta.date)
  }
  if (sort === 'max_desc') {
    const c = compareMaybeNumberDesc(a.meta.maxKmh, b.meta.maxKmh)
    return c !== 0 ? c : b.meta.date.localeCompare(a.meta.date)
  }
  // default: newest first
  return b.meta.date.localeCompare(a.meta.date)
}

export function ToursPage({ trips, onReload }: { trips: Trip[]; onReload: () => Promise<void> }) {
  const [view, setView] = useState<ToursView>({ kind: 'list' })
  const [activity, setActivity] = useState<Activity>('all')
  const [sort, setSort] = useState<SortKey>('date_desc')

  const visibleTrips = useMemo(() => {
    const filtered = activity === 'all' ? trips : trips.filter((t) => tripHasActivity(t, activity))
    const sorted = [...filtered].sort((a, b) => compareTrips(a, b, sort))
    return sorted
  }, [activity, sort, trips])

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

      <FilterBar
        chips={[
          { key: 'all', label: 'Alle' },
          ...TRIP_ACTIVITY_TAGS.map((t) => ({ key: t, label: t })),
          { key: 'unknown', label: 'unknown' }
        ]}
        activeChip={activity}
        onChipChange={setActivity}
        sorts={[
          { key: 'date_desc', label: 'Neueste' },
          { key: 'distance_desc', label: 'Distanz' },
          { key: 'duration_desc', label: 'Dauer' },
          { key: 'avg_desc', label: 'Ø km/h' },
          { key: 'max_desc', label: 'max km/h' }
        ]}
        activeSort={sort}
        onSortChange={setSort}
        onReset={() => {
          setActivity('all')
          setSort('date_desc')
        }}
      />

      <TripList trips={visibleTrips} onOpen={(trip) => setView({ kind: 'trip', trip })} />
    </div>
  )
}
