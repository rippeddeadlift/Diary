import { useState } from 'react'
import type { Trip } from '@/data/trips'
import { TripList } from '@/components/TripList'
import { TripView } from '@/components/TripView'

type ToursView = { kind: 'list' } | { kind: 'trip'; trip: Trip }

export function ToursPage({ trips }: { trips: Trip[] }) {
  const [view, setView] = useState<ToursView>({ kind: 'list' })

  if (view.kind === 'trip') {
    return <TripView trip={view.trip} onBack={() => setView({ kind: 'list' })} />
  }

  return <TripList trips={trips} onOpen={(trip) => setView({ kind: 'trip', trip })} />
}
