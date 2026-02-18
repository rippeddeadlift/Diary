import { useState } from 'react'
import type { Trip } from '@/data/trips'
import { TripList } from '@/components/TripList'
import { TripView } from '@/components/TripView'
import { TripsImportCard } from '@/components/trips/TripsImportCard'

type ToursView = { kind: 'list' } | { kind: 'trip'; trip: Trip }

export function ToursPage({ trips, onReload }: { trips: Trip[]; onReload: () => Promise<void> }) {
  const [view, setView] = useState<ToursView>({ kind: 'list' })

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
      <TripList trips={trips} onOpen={(trip) => setView({ kind: 'trip', trip })} />
    </div>
  )
}
