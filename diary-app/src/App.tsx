import { useMemo, useState } from 'react'
import { ThemeToggle } from './components/ThemeToggle'
import { Button } from '@/components/ui/button'
import { PhotosPage } from '@/features/photos/PhotosPage'
import { MenuPage } from '@/pages/MenuPage'
import { FitnessPage } from '@/pages/FitnessPage'
import { TripsPage } from '@/features/trips/TripsPage'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { Toaster } from 'sonner'

type Page = 'menu' | 'photos' | 'trips' | 'fitness'

export default function App() {
  // ALT: trips und error State komplett entfernt
  const [page, setPage] = useState<Page>('menu')

  // ALT: useEffect und reloadTrips komplett entfernt

  const subtitle = useMemo(() => {
    if (page === 'menu') return 'Menü'
    if (page === 'photos') return 'Fotos'
    if (page === 'trips') return 'Touren'
    return 'Fitness'
  }, [page])

  const goMenu = () => setPage('menu')
  const goPhotos = () => setPage('photos')
  const goTrips = () => setPage('trips')
  const goFitness = () => setPage('fitness')

  const isMenu = page === 'menu'

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-background text-foreground">
        <div className={isMenu ? "flex min-h-screen flex-col overflow-hidden" : "mx-auto min-h-screen max-w-5xl p-6"}>
          <header className={isMenu ? "flex items-center justify-between gap-3 px-6 py-4" : "mb-6 flex items-center justify-between gap-3"}>
            <div className="flex items-baseline gap-3">
              <h1 className="text-xl font-semibold">Tagebuch</h1>
              <span className="text-sm text-muted-foreground">{subtitle}</span>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={goMenu}>
                Home
              </Button>
              <Toaster />
              <ThemeToggle />
            </div>
          </header>

         {page === 'menu' ? (
        <MenuPage onTrips={goTrips} onPhotos={goPhotos} onFitness={goFitness} />
      ) : page === 'photos' ? (
        <PhotosPage />
      ) : page === 'fitness' ? (
        <FitnessPage />
      ) : (
        <TripsPage />
      )}
        </div>
      </div>
    </ErrorBoundary>
  )
}