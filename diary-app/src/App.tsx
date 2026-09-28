import { useState } from 'react'
import { PhotosPage } from '@/features/photos/PhotosPage'
import { MenuPage } from '@/features/MenuPage'
import { FitnessPage } from '@/features/fitness/FitnessPage'
import { TripsPage } from '@/features/trips/TripsPage'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { Toaster } from 'sonner'
import { Layout } from './components/layout'

type Page = 'menu' | 'photos' | 'trips' | 'fitness'

export default function App() {
  const [page, setPage] = useState<Page>('menu')

  const goPhotos = () => setPage('photos')
  const goTrips = () => setPage('trips')
  const goFitness = () => setPage('fitness')

  return (
    <ErrorBoundary>
      <Layout page={page} setPage={setPage}>
        {page === 'menu' ? (
          <MenuPage onTrips={goTrips} onPhotos={goPhotos} onFitness={goFitness} />
        ) : page === 'photos' ? (
          <PhotosPage />
        ) : page === 'fitness' ? (
          <FitnessPage />
        ) : (
          <TripsPage />
        )}
      </Layout>
      <Toaster />
    </ErrorBoundary>
  )
}