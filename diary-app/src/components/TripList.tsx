import type { Trip } from '../data/trips'
import { Badge } from '@/components/ui/badge'
import { formatDateEU } from "@/lib/date"

import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { RoutePreview } from '@/components/trips/RoutePreview'

function formatDurationMin(min: number): string {
  if (!Number.isFinite(min) || min <= 0) return ''
  const h = Math.floor(min / 60)
  const m = min % 60
  if (h <= 0) return `${m} min`
  return `${h}:${String(m).padStart(2, '0')} h`
}

export function TripList({ trips, onOpen }: { trips: Trip[]; onOpen: (t: Trip) => void }) {
  if (trips.length === 0) return <div className="text-muted-foreground">Noch leer. Lege eine Tour im Ordner trips/ an…</div>

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {trips.map((t) => (
          <Card key={t.id} onClick={() => onOpen(t)} className="cursor-pointer text-left transition hover:bg-muted/30 hover:shadow-sm">
            <CardHeader>
              <div className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-1">
                <CardTitle className="text-base">{t.meta.title}</CardTitle>

                {t.meta.preview?.points?.length ? (
                  <RoutePreview
                    points={t.meta.preview.points}
                    bbox={t.meta.preview.bbox}
                    className="row-span-3 flex h-full w-40 items-center justify-center rounded-md bg-background/0"
                  />
                ) : null}

                <div className="text-sm text-muted-foreground">{formatDateEU(t.meta.date)}</div>

                <div className="mt-2 flex flex-wrap items-center gap-2">
                {(t.meta.tags || []).slice(0, 3).map((tag) => (
                  <Badge key={tag} variant="default">
                    {tag}
                  </Badge>
                ))}
                {(t.meta.tags?.length || 0) > 3 ? (
                  <Badge variant="secondary">+{(t.meta.tags?.length || 0) - 3}</Badge>
                ) : null}

                {typeof t.meta.distanceKm === 'number' ? (
                  <Badge variant="secondary">{t.meta.distanceKm.toFixed(1)} km</Badge>
                ) : null}

                {typeof t.meta.durationMin === 'number' ? (
                  <Badge variant="outline">⏱ {formatDurationMin(t.meta.durationMin)}</Badge>
                ) : null}
                </div>
              </div>
            </CardHeader>
          </Card>
      ))}
    </div>
  )
}
