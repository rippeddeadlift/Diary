import { useEffect, useState } from 'react'
import { Film, FolderOpen, LoaderCircle, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { listMovies, openMovie, pickMovieFolder, setMovieFolder, type MovieLibrary } from '@/api/movies'

export function MoviesPage() {
  const [library, setLibrary] = useState<MovieLibrary>({ folder: null, count: 0, items: [] })
  const [folderPath, setFolderPath] = useState('')
  const [loading, setLoading] = useState(true)
  const [openingPath, setOpeningPath] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function loadMovies() {
    setLoading(true)
    setError(null)
    try {
      const result = await listMovies()
      setLibrary(result)
      setFolderPath(result.folder ?? '')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Die Filmbibliothek konnte nicht geladen werden.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadMovies()
  }, [])

  async function chooseFolder() {
    setLoading(true)
    setError(null)
    try {
      const result = await pickMovieFolder()
      if (!result.cancelled) {
        setLibrary(result)
        setFolderPath(result.folder ?? '')
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Der Ordner konnte nicht ausgewählt werden.')
    } finally {
      setLoading(false)
    }
  }

  async function submitFolder(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const result = await setMovieFolder(folderPath)
      setLibrary(result)
      setFolderPath(result.folder ?? '')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Der Ordnerpfad ist ungültig.')
    } finally {
      setLoading(false)
    }
  }

  async function playMovie(path: string) {
    setOpeningPath(path)
    setError(null)
    try {
      await openMovie(path)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Der Film konnte nicht im lokalen Player geöffnet werden.')
    } finally {
      setOpeningPath(null)
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b pb-5">
        <div>
          <h1 className="text-2xl font-semibold">Filmbibliothek</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {library.folder ? `${library.count} Filme` : 'Kein Filmordner ausgewählt'}
          </p>
        </div>
        <Button type="button" onClick={() => void chooseFolder()} disabled={loading}>
          {loading ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> : <FolderOpen className="mr-2 h-4 w-4" />}
          Ordner wählen
        </Button>
      </header>

      <form onSubmit={(event) => void submitFolder(event)} className="flex flex-wrap gap-2">
        <label className="sr-only" htmlFor="movie-folder-path">Ordnerpfad</label>
        <input
          id="movie-folder-path"
          value={folderPath}
          onChange={(event) => setFolderPath(event.target.value)}
          placeholder="Ordnerpfad eingeben"
          className="h-10 min-w-0 flex-1 rounded-md border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <Button type="submit" variant="outline" disabled={loading || !folderPath.trim()}>
          Pfad öffnen
        </Button>
      </form>

      {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}

      {loading && library.items.length === 0 ? (
        <div className="flex items-center gap-2 py-12 text-sm text-muted-foreground">
          <LoaderCircle className="h-4 w-4 animate-spin" /> Bibliothek wird geladen
        </div>
      ) : library.items.length > 0 ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-x-4 gap-y-6 sm:grid-cols-[repeat(auto-fill,minmax(175px,1fr))]">
          {library.items.map((movie) => (
            <button
              key={movie.path}
              type="button"
              onClick={() => void playMovie(movie.path)}
              disabled={openingPath !== null}
              title="Im lokalen Player abspielen"
              aria-label={`Im lokalen Player abspielen: ${movie.title}`}
              className="group min-w-0 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <span className="relative block aspect-[2/3] overflow-hidden rounded-md bg-muted">
                <Film className="absolute inset-0 m-auto h-10 w-10 text-muted-foreground/60" />
                <img
                  src={movie.posterUrl}
                  alt=""
                  loading="lazy"
                  onError={(event) => { event.currentTarget.style.display = 'none' }}
                  className="relative h-full w-full object-cover transition-transform duration-200 group-hover:scale-[1.03]"
                />
                <span className="absolute inset-0 flex items-center justify-center bg-black/0 text-white opacity-0 transition group-hover:bg-black/35 group-hover:opacity-100">
                  {openingPath === movie.path
                    ? <LoaderCircle className="h-10 w-10 animate-spin" />
                    : <Play className="h-10 w-10 fill-current" />}
                </span>
              </span>
              <span className="mt-2 block truncate text-sm font-medium" title={movie.title}>{movie.title}</span>
            </button>
          ))}
        </div>
      ) : (
        <div className="flex min-h-48 flex-col items-center justify-center gap-3 border-y text-center">
          <Film className="h-9 w-9 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            {library.folder ? 'Keine unterstützten Videodateien in diesem Ordner gefunden.' : 'Wähle einen Ordner mit deinen Filmen.'}
          </p>
        </div>
      )}

    </div>
  )
}