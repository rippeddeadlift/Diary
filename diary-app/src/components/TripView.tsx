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
      <div className='flex justify-between items-center'>
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
          <h2 className="truncate text-lg font-semibold">{trip.meta.title}</h2>
        </div>

        <div className="text-sm text-muted-foreground sm:text-center">
          {typeof trip.meta.distanceKm === 'number' ? <span>{trip.meta.distanceKm.toFixed(1)} km</span> : null}
          {typeof trip.meta.durationMin === 'number' ? <span> · ⏱ {trip.meta.durationMin} min</span> : null}
          {typeof trip.meta.avgKmh === 'number' ? <span> · Ø {trip.meta.avgKmh.toFixed(1)} km/h</span> : null}
          {typeof trip.meta.maxKmh === 'number' ? <span> · max {trip.meta.maxKmh.toFixed(1)} km/h</span> : null}
        </div>

        <div className="text-sm text-muted-foreground sm:text-right">{formatDateEU(trip.meta.date)}</div>
      </div>

      {err ? <div className="text-sm text-destructive whitespace-pre-wrap">{err}</div> : null}

      <div className="grid grid-cols-1 gap-3">
        <GpxMap trip={trip} />
        <Notes trip={trip} />
      </div>
    </div>
  )
}
