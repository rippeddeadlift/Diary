import type { Trip } from '@/data/trips'
import { TripList } from '@/components/TripList'

export function HomePage({ trips, onOpenTrip }: { trips: Trip[]; onOpenTrip: (t: Trip) => void }) {
  const recent = trips.slice(0, 3)

  return (
    <div className="space-y-6">
      <section>
        <h2 className="text-lg font-semibold">Zuletzt</h2>
        <p className="text-sm text-muted-foreground">Die letzten Touren aus deinem Archiv.</p>

        <div className="mt-3">
          <TripList trips={recent} onOpen={onOpenTrip} />
        </div>
      </section>

      <section className="rounded-xl border bg-card p-4 text-card-foreground">
        <h3 className="font-semibold">Neue Tour hinzufügen</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Lege einen neuen Ordner unter <code>trips/</code> an (mit <code>meta.json</code>, <code>route.gpx</code>, optional
          <code>notes.md</code> und <code>photos/</code>) und ergänze <code>trips/index.json</code>.
        </p>
      </section>
    </div>
  )
}
