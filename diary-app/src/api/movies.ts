export type MovieItem = {
  path: string
  title: string
  url: string
  posterUrl: string
}

export type MovieLibrary = {
  folder: string | null
  count: number
  items: MovieItem[]
  cancelled?: boolean
}

async function requestMovies(path: string, init?: RequestInit): Promise<MovieLibrary> {
  const response = await fetch(path, init)
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail ?? 'Die Filmbibliothek konnte nicht geladen werden.')
  }
  return payload as MovieLibrary
}

export function listMovies(): Promise<MovieLibrary> {
  return requestMovies('/api/movies')
}

export function setMovieFolder(path: string): Promise<MovieLibrary> {
  return requestMovies('/api/movies/folder', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  })
}

export function pickMovieFolder(): Promise<MovieLibrary> {
  return requestMovies('/api/movies/pick-folder', { method: 'POST' })
}

export async function openMovie(path: string): Promise<void> {
  const response = await fetch('/api/movies/open', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  })
  if (!response.ok) {
    const payload = await response.json()
    throw new Error(payload.detail ?? 'Der Film konnte nicht im lokalen Player geöffnet werden.')
  }
}