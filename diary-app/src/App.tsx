import { useEffect, useState } from 'react'
import { loadTrips, type Trip } from './data/trips'
import { TripList } from './components/TripList'
import { TripView } from './components/TripView'
import { ThemeToggle } from './components/ThemeToggle'

type View = { kind: 'list' } | { kind: 'trip'; trip: Trip }

export default function App() {
  const [trips, setTrips] = useState<Trip[]>([])
  const [error, setError] = useState<string | null>(null)
  const [view, setView] = useState<View>({ kind: 'list' })

  useEffect(() => {
    ;(async () => {
      try {
        setError(null)
        setTrips(await loadTrips())
      } catch (e: any) {
        setError(e?.message ?? String(e))
      }
    })()
  }, [])

  if (error) {
    return (
      <div className="min-h-screen p-6">
        <div className="mx-auto max-w-3xl">
          <h1 className="text-xl font-semibold">Tagebuch</h1>
          <p className="mt-1 text-sm text-muted-foreground">Lokale Touren-Übersicht</p>

          <pre className="mt-4 whitespace-pre-wrap rounded-lg bg-black p-4 text-sm text-white">{error}</pre>
          <p className="mt-3 text-sm text-muted-foreground">
            Tipp: Stelle sicher, dass der Dev-Server den Ordner <code>../trips</code> sehen kann.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-5xl p-6">
        <header className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-baseline gap-3">
            <h1 className="text-xl font-semibold">Tagebuch</h1>
            <span className="text-sm text-muted-foreground">Lokale Touren-Übersicht</span>
          </div>
          <ThemeToggle />
        </header>

        {view.kind === 'list' ? (
          <TripList trips={trips} onOpen={(trip) => setView({ kind: 'trip', trip })} />
        ) : (
          <TripView trip={view.trip} onBack={() => setView({ kind: 'list' })} />
        )}
      </div>
    </div>
  )
}
