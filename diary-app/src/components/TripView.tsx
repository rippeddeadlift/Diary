import { GpxMap } from './maps/GpxMap'
import { Notes } from './content/Notes'
import type { Trip } from '../data/trips'

export function TripView({ trip, onBack }: { trip: Trip; onBack: () => void }) {
  return (
    <div style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <button onClick={onBack}>← zurück</button>
        <h2 style={{ margin: 0 }}>{trip.meta.title}</h2>
        <span style={{ opacity: 0.7 }}>{trip.meta.date}</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12 }}>
        <GpxMap trip={trip} />
        <Notes trip={trip} />
      </div>
    </div>
  )
}
