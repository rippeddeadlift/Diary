import { useEffect, useMemo, useState } from 'react'
import { GpxMap } from './maps/GpxMap'
import { Notes } from './content/Notes'
import { TripPhotoSuggestions } from '@/components/trips/TripPhotoSuggestions'
import type { Trip } from '../data/trips'
import { Button } from './ui/button'
import { formatDateEU } from '@/lib/date'
import { trashTrips, updateTripMeta } from '@/api/trips'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger
} from '@/components/ui/alert-dialog'
import { Switch } from '@/components/ui/switch'
import { TagChips } from '@/components/photos/TagChips'
import { TRIP_ACTIVITY_TAGS } from '@/data/tripTagConfig'

function ensureSingleActivity(tags: string[]): string[] {
  const activities = new Set(TRIP_ACTIVITY_TAGS as unknown as string[])
  const chosen = tags.find((t) => activities.has(t))
  const rest = tags.filter((t) => !activities.has(t))
  return chosen ? [chosen, ...rest] : rest
}

export function TripView({
  trip,
  onBack,
  onDeleted
}: {
  trip: Trip
  onBack: () => void
  onDeleted: () => Promise<void>
}) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const [editMode, setEditMode] = useState(false)
  const [title, setTitle] = useState(trip.meta.title)
  const [tags, setTags] = useState<string[]>(trip.meta.tags || [])

  // Reset local state when switching trips
  useEffect(() => {
    setEditMode(false)
    setTitle(trip.meta.title)
    setTags(trip.meta.tags || [])
    setErr(null)
  }, [trip.id])

  // Debounced autosave while edit mode is on
  useEffect(() => {
    if (!editMode) return

    const normalizedTags = ensureSingleActivity(tags)
    if (normalizedTags.join('|') !== tags.join('|')) {
      setTags(normalizedTags)
      return
    }

    const handle = setTimeout(() => {
      ;(async () => {
        try {
          await updateTripMeta({ id: trip.id, title: title.trim() || trip.meta.title, tags: normalizedTags })
        } catch (e: any) {
          setErr(e?.message ?? String(e))
        }
      })()
    }, 650)

    return () => clearTimeout(handle)
  }, [editMode, title, tags, trip.id, trip.meta.title])

  const tripView = useMemo(() => ({ ...trip, meta: { ...trip.meta, title, tags } }), [trip, title, tags])

  return (
    <div className="grid gap-3">
      <div className="flex justify-between items-center">
        <Button variant="outline" size="sm" onClick={onBack}>
          ← zurück
        </Button>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive" size="sm" disabled={busy}>
              Löschen
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Tour in den Papierkorb verschieben?</AlertDialogTitle>
              <AlertDialogDescription>
                Der Trip-Ordner wird nach <code>data/trips/_trash/…</code> verschoben. Du kannst ihn später wiederherstellen.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={busy}>Abbrechen</AlertDialogCancel>
              <AlertDialogAction
                disabled={busy}
                onClick={async () => {
                  setErr(null)
                  setBusy(true)
                  try {
                    await trashTrips([trip.id])
                    await onDeleted()
                  } catch (e: any) {
                    setErr(e?.message ?? String(e))
                  } finally {
                    setBusy(false)
                  }
                }}
              >
                In Papierkorb
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      <div className="grid grid-cols-[1fr] gap-1 sm:grid-cols-[1fr_auto_1fr] sm:items-baseline">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-semibold">{tripView.meta.title}</h2>
        </div>

        <div className="text-sm text-muted-foreground sm:text-center">
          {typeof tripView.meta.distanceKm === 'number' ? <span>{tripView.meta.distanceKm.toFixed(1)} km</span> : null}
          {typeof tripView.meta.durationMin === 'number' ? <span> · ⏱ {tripView.meta.durationMin} min</span> : null}
          {typeof tripView.meta.avgKmh === 'number' ? <span> · Ø {tripView.meta.avgKmh.toFixed(1)} km/h</span> : null}
          {typeof tripView.meta.maxKmh === 'number' ? <span> · max {tripView.meta.maxKmh.toFixed(1)} km/h</span> : null}
        </div>

        <div className="text-sm text-muted-foreground sm:text-right">{formatDateEU(tripView.meta.date)}</div>
      </div>

      {/* You said you already moved this under the map; keep simple here */}
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs text-muted-foreground">Bearbeiten</div>
        <Switch checked={editMode} onCheckedChange={setEditMode} />
      </div>

      {editMode ? (
        <div className="space-y-3 rounded-lg border bg-muted/20 p-3">
          <div className="space-y-2">
            <div className="text-xs text-muted-foreground">Titel</div>
            <input
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <div className="text-xs text-muted-foreground">Aktivität</div>
            <TagChips
              options={TRIP_ACTIVITY_TAGS}
              value={tags}
              onChange={(next) => setTags(ensureSingleActivity(next))}
            />
          </div>
        </div>
      ) : null}

      {err ? <div className="text-sm text-destructive whitespace-pre-wrap">{err}</div> : null}

      <div className="grid grid-cols-1 gap-3">
        <GpxMap trip={tripView} />
        <TripPhotoSuggestions trip={tripView} />
        <Notes trip={tripView} />
      </div>
    </div>
  )
}
