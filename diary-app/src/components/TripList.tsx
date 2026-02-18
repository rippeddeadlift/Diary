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
              {t.meta.preview?.points?.length ? (
                <RoutePreview points={t.meta.preview.points} bbox={t.meta.preview.bbox} className="mb-3" />
              ) : null}
              <CardTitle className="text-base">{t.meta.title}</CardTitle>
              <CardDescription className="flex flex-wrap items-center gap-2">
                <span>{formatDateEU(t.meta.date)}</span>
                {typeof t.meta.distanceKm === 'number' ? <Badge variant="secondary">{t.meta.distanceKm.toFixed(1)} km</Badge> : null}
                {typeof t.meta.durationMin === 'number' ? (
                  <Badge variant="outline">⏱ {formatDurationMin(t.meta.durationMin)}</Badge>
                ) : null}
              </CardDescription>

              {t.meta.tags?.length ? (
                <div className="mt-2 flex flex-wrap gap-1">
                  {t.meta.tags.map((tag) => (
                    <Badge key={tag} variant="default">
                      {tag}
                    </Badge>
                  ))}
                </div>
              ) : null}
            </CardHeader>
          </Card>
      ))}
    </div>
  )
}
