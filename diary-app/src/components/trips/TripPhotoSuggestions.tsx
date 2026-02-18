import { useEffect, useState } from 'react'
import type { Trip } from '@/data/trips'
import type { GalleryItem } from '@/types/photos'
import { suggestPhotos } from '@/api/photos'

export function TripPhotoSuggestions({ trip }: { trip: Trip }) {
  const [items, setItems] = useState<GalleryItem[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    ;(async () => {
      setBusy(true)
      setErr(null)
      try {
        const out = await suggestPhotos({ date: trip.meta.date, limit: 120 })
        setItems(out)
      } catch (e: any) {
        setErr(e?.message ?? String(e))
        setItems([])
      } finally {
        setBusy(false)
      }
    })()
  }, [trip.meta.date])

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-3">
        <div className="text-sm font-medium">Fotos</div>
        <div className="text-xs text-muted-foreground">
          {busy ? 'Lade…' : `${items.length} am ${trip.meta.date}`}
        </div>
      </div>

      {err ? <div className="text-sm text-destructive">{err}</div> : null}

      {items.length ? (
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">
          {items.map((it) => {
            const src = (it.thumbExists && it.thumbUrl) ? it.thumbUrl : it.url
            return (
              <a
                key={it.path}
                href={it.url}
                target="_blank"
                rel="noreferrer"
                className="block overflow-hidden rounded-md border bg-muted/20"
                title={it.path}
              >
                <img src={src} className="h-24 w-full object-cover" loading="lazy" />
              </a>
            )
          })}
        </div>
      ) : (
        <div className="text-sm text-muted-foreground">Keine Vorschläge gefunden.</div>
      )}
    </div>
  )
}
