import { useEffect, useMemo, useState } from 'react'
import { loadTrips, type Trip } from './data/trips'
import { TripList } from './components/TripList'
import { TripView } from './components/TripView'
import { ThemeToggle } from './components/ThemeToggle'
import { Button } from '@/components/ui/button'
import { HomePage } from '@/pages/HomePage'
import { PhotosPage } from '@/pages/PhotosPage'

type Page = 'home' | 'tours' | 'photos'

type View = { kind: 'list' } | { kind: 'trip'; trip: Trip }

export default function App() {
  const [trips, setTrips] = useState<Trip[]>([])
  const [error, setError] = useState<string | null>(null)

  const [page, setPage] = useState<Page>('home')
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

  const subtitle = useMemo(() => {
    if (page === 'home') return 'Start'
    if (page === 'tours') return 'Touren'
    return 'Fotos'
  }, [page])

  function openTrip(trip: Trip) {
    setPage('tours')
    setView({ kind: 'trip', trip })
  }

  function goHome() {
    setPage('home')
    setView({ kind: 'list' })
  }

  function goTours() {
    setPage('tours')
    setView({ kind: 'list' })
  }

  function goPhotos() {
    setPage('photos')
    setView({ kind: 'list' })
  }

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
        <header className="mb-6 flex items-center justify-between gap-3">
          <div className="flex items-baseline gap-3">
            <h1 className="text-xl font-semibold">Tagebuch</h1>
            <span className="text-sm text-muted-foreground">{subtitle}</span>
          </div>

          <div className="flex items-center gap-2">
            <Button variant={page === 'home' ? 'default' : 'outline'} size="sm" onClick={goHome}>
              Home
            </Button>
            <Button variant={page === 'tours' ? 'default' : 'outline'} size="sm" onClick={goTours}>
              Touren
            </Button>
            <Button variant={page === 'photos' ? 'default' : 'outline'} size="sm" onClick={goPhotos}>
              Fotos
            </Button>
            <ThemeToggle />
          </div>
        </header>

        {page === 'home' ? (
          <HomePage trips={trips} onOpenTrip={openTrip} />
        ) : page === 'photos' ? (
          <PhotosPage />
        ) : view.kind === 'list' ? (
          <TripList trips={trips} onOpen={openTrip} />
        ) : (
          <TripView trip={view.trip} onBack={goTours} />
        )}
      </div>
    </div>
  )
}
