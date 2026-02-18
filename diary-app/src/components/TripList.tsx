import type { Trip } from '../data/trips'
import { Badge } from '@/components/ui/badge'
import { formatDateEU } from "@/lib/date"

import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

function inferTypeLabel(tags: string[] | undefined, title: string | undefined): string | null {
  const t = `${(title || '').toLowerCase()} ${(tags || []).join(' ').toLowerCase()}`
  if (/(cycling|bike|bicycle|rad|fahrrad|radtour|gravel|rennrad)/.test(t)) return 'Rad'
  if (/(hiking|hike|wandern|wanderung|spaziergang)/.test(t)) return 'Wandern'
  return null
}

export function TripList({ trips, onOpen }: { trips: Trip[]; onOpen: (t: Trip) => void }) {
  if (trips.length === 0) return <div className="text-muted-foreground">Noch leer. Lege eine Tour im Ordner trips/ an…</div>

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {trips.map((t) => (
          <Card key={t.id} onClick={() => onOpen(t)} className="cursor-pointer text-left transition hover:bg-muted/30 hover:shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">{t.meta.title}</CardTitle>
              <CardDescription className="flex flex-wrap items-center gap-2">
                {inferTypeLabel(t.meta.tags, t.meta.title) ? (
                  <Badge variant="outline">{inferTypeLabel(t.meta.tags, t.meta.title)}</Badge>
                ) : null}
                <span>{formatDateEU(t.meta.date)}</span>
                {typeof t.meta.distanceKm === 'number' ? <Badge variant="secondary">{t.meta.distanceKm.toFixed(1)} km</Badge> : null}
                {t.meta.gpx ? <Badge variant="outline">GPX</Badge> : null}
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
