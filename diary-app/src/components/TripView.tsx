import { useState } from 'react'
import { GpxMap } from './maps/GpxMap'
import { Notes } from './content/Notes'
import type { Trip } from '../data/trips'
import { Button } from './ui/button'
import { formatDateEU } from '@/lib/date'
import { trashTrips } from '@/api/trips'
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
  return (
    <div className="grid gap-3">
      <div>
        <Button variant="outline" size="sm" onClick={onBack}>
          ← zurück
        </Button>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-lg font-semibold">
            {trip.meta.title}
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              {typeof trip.meta.distanceKm === 'number' ? `${trip.meta.distanceKm.toFixed(1)} km` : ''}
              {typeof trip.meta.durationMin === 'number' ? ` · ⏱ ${trip.meta.durationMin} min` : ''}
              {typeof trip.meta.avgKmh === 'number' ? ` · Ø ${trip.meta.avgKmh.toFixed(1)} km/h` : ''}
              {typeof trip.meta.maxKmh === 'number' ? ` · max ${trip.meta.maxKmh.toFixed(1)} km/h` : ''}
            </span>
          </h2>
          <div className="mt-1 text-sm text-muted-foreground">{formatDateEU(trip.meta.date)}</div>
        </div>

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

      {err ? <div className="text-sm text-destructive whitespace-pre-wrap">{err}</div> : null}

      <div className="grid grid-cols-1 gap-3">
        <GpxMap trip={trip} />
        <Notes trip={trip} />
      </div>
    </div>
  )
}
