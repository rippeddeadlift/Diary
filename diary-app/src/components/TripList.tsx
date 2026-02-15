import type { Trip } from '../data/trips'
import { Badge } from '@/components/ui/badge'
import { formatDateEU } from "@/lib/date"

import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function TripList({ trips, onOpen }: { trips: Trip[]; onOpen: (t: Trip) => void }) {
  if (trips.length === 0) return <div className="text-muted-foreground">Noch leer. Lege eine Tour im Ordner trips/ an…</div>

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {trips.map((t) => (
        <button key={t.id} onClick={() => onOpen(t)} className="text-left">
          <Card key={t.id} onClick={() => onOpen(t)} className="text-left transition hover:shadow-md">
            <CardHeader>
              <CardTitle className="text-base">{t.meta.title}</CardTitle>
              <CardDescription className="flex items-center gap-2">
                <span>{formatDateEU(t.meta.date)}</span>
                {typeof t.meta.distanceKm === 'number' ? <Badge variant="secondary">{t.meta.distanceKm.toFixed(1)} km</Badge> : null}
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
        </button>
      ))}
    </div>
  )
}
