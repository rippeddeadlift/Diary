import { useEffect, useMemo, useState } from 'react'
import { loadTrips, type Trip } from './data/trips'
import { ThemeToggle } from './components/ThemeToggle'
import { Button } from '@/components/ui/button'
import { HomePage } from '@/pages/HomePage'
import { PhotosPage } from '@/pages/PhotosPage'
import { MenuPage } from '@/pages/MenuPage'
import { FitnessPage } from '@/pages/FitnessPage'
import { ToursPage } from '@/pages/ToursPage'
import { ErrorBoundary } from '@/components/ErrorBoundary'

type Page = 'menu' | 'home' | 'photos' | 'tours' | 'fitness'

export default function App() {
  const [trips, setTrips] = useState<Trip[]>([])
  const [error, setError] = useState<string | null>(null)

  const [page, setPage] = useState<Page>('menu')

  async function reloadTrips() {
    setError(null)
    setTrips(await loadTrips())
  }

  useEffect(() => {
    ;(async () => {
      try {
        await reloadTrips()
      } catch (e: any) {
        setError(e?.message ?? String(e))
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const subtitle = useMemo(() => {
    if (page === 'menu') return 'Menü'
    if (page === 'home') return 'Start'
    if (page === 'photos') return 'Fotos'
    if (page === 'tours') return 'Touren'
    return 'Fitness'
  }, [page])

  function goMenu() {
    setPage('menu')
  }
  function goPhotos() {
    setPage('photos')
  }
  function goTours() {
    setPage('tours')
  }
  function goFitness() {
    setPage('fitness')
  }

  if (error) {
    return (
      <div className="min-h-screen p-6">
        <div className="mx-auto max-w-3xl">
          <h1 className="text-xl font-semibold">Tagebuch</h1>
          <p className="mt-1 text-sm text-muted-foreground">Lokale Touren-Übersicht</p>

          <pre className="mt-4 whitespace-pre-wrap rounded-lg bg-black p-4 text-sm text-white">{error}</pre>
          <p className="mt-3 text-sm text-muted-foreground">
            Tipp: Stelle sicher, dass der Dev-Server den Ordner <code>../data/trips</code> sehen kann.
          </p>
        </div>
      </div>
    )
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-5xl p-6">
        <header className="mb-6 flex items-center justify-between gap-3">
          <div className="flex items-baseline gap-3">
            <h1 className="text-xl font-semibold">Tagebuch</h1>
            <span className="text-sm text-muted-foreground">{subtitle}</span>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={goMenu}>
              Home
            </Button>
            <ThemeToggle />
          </div>
        </header>

        {page === 'menu' ? (
          <MenuPage onTours={goTours} onPhotos={goPhotos} onFitness={goFitness} />
        ) : page === 'home' ? (
          <HomePage trips={trips} onOpenTrip={() => setPage('tours')} />
        ) : page === 'photos' ? (
          <PhotosPage />
        ) : page === 'fitness' ? (
          <FitnessPage />
        ) : (
          <ToursPage trips={trips} onReload={reloadTrips} />
        )}
      </div>
      </div>
    </ErrorBoundary>
  )
}
