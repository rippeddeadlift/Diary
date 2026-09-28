import { FitnessPage } from './fitness/fitness-page'
import { MoviesPage } from './movies/movies-page'
import { PhotosPage } from './photos/photos-page'
import { TripsPage } from './trips/TripsPage'

export const FEATURES = {
  photos: { label: 'Fotos', component: PhotosPage },
  trips: { label: 'Touren', component: TripsPage },
  fitness: { label: 'Fitness', component: FitnessPage },
  movies: { label: 'Filme', component: MoviesPage },
} as const

export type FeatureId = keyof typeof FEATURES
export type Page = 'home' | FeatureId

export const FEATURE_ITEMS = (Object.keys(FEATURES) as FeatureId[]).map((id) => ({
  id,
  label: FEATURES[id].label,
}))