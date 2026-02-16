import { useEffect, useMemo, useRef, useState } from 'react'
import type { GalleryItem } from '@/types/photos'
import { formatDateTimeEU } from '@/lib/format'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { PhotoPointMap } from '@/components/maps/PhotoPointMap'
import { PEOPLE, TAGS } from '@/data/tagConfig'
import { TagChips } from '@/components/photos/TagChips'
import { Switch } from '@/components/ui/switch'

type Sidecar = {
  people: string[]
  tags: string[]
  caption: string
}

function MapBlock({ lat, lon }: { lat: number; lon: number }) {
  const [showMap, setShowMap] = useState(false)

  useEffect(() => {
    const t = window.setTimeout(() => setShowMap(true), 200)
    return () => window.clearTimeout(t)
  }, [])

  return (
    <>
      <div className="overflow-hidden rounded-md border">
        {showMap ? (
          <PhotoPointMap lat={lat} lon={lon} />
        ) : (
          <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">Karte lädt…</div>
        )}
      </div>
      <div className="font-mono text-xs text-muted-foreground">
        {lat.toFixed(6)}, {lon.toFixed(6)}
      </div>
    </>
  )
}

export function PhotoViewerDialog({ item, onClose }: { item: GalleryItem | null; onClose: () => void }) {
  const [people, setPeople] = useState<string[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [showAll, setShowAll] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const initialRef = useRef<{ people: string[]; tags: string[] } | null>(null)
  const loadedRef = useRef(false)

  const path = item?.path

  useEffect(() => {
    if (!path) return

    ;(async () => {
      try {
        setErr(null)
        const res = await fetch(`/api/photos/sidecar?path=${encodeURIComponent(path)}`)
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
        const json = (await res.json()) as { ok: boolean; sidecar: Sidecar }
        const p = json.sidecar?.people ?? []
        const t = json.sidecar?.tags ?? []
        setPeople(p)
        setTags(t)
        initialRef.current = { people: p, tags: t }
        loadedRef.current = true
        // caption intentionally omitted for now
      } catch (e: any) {
        setErr(e?.message ?? String(e))
      }
    })()
  }, [path])

  const dirty = useMemo(() => {
    const init = initialRef.current
    if (!loadedRef.current || !init) return false
    const a = JSON.stringify({ people: init.people, tags: init.tags })
    const b = JSON.stringify({ people, tags })
    return a !== b
  }, [people, tags])

  async function save() {
    if (!path) return
    if (!loadedRef.current) return
    if (!dirty) return

    setBusy(true)
    setErr(null)
    try {
      const res = await fetch('/api/photos/sidecar', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ path, people, tags, caption: '' })
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`${res.status} ${res.statusText}: ${text}`)
      }
      initialRef.current = { people: [...people], tags: [...tags] }
    } catch (e: any) {
      setErr(e?.message ?? String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog
      open={!!item}
      onOpenChange={(open) => {
        if (!open) {
          // Fire-and-forget save on close (don't block UI)
          void save()
          onClose()
        }
      }}
    >
      <DialogContent className="p-0">
        {item ? (
          <div className="grid max-h-[90vh] grid-cols-1 overflow-auto sm:grid-cols-2">
            <div className="p-4">
              <div className="overflow-hidden rounded-md border bg-muted">
                <img src={item.url} alt={item.path} className="block h-auto w-full object-contain" />
              </div>

           
              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <DialogHeader>
                    <DialogTitle className="text-base">Tags</DialogTitle>
                  </DialogHeader>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">Settings</span>
                    <Switch checked={showAll} onCheckedChange={setShowAll} />
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-xs text-muted-foreground">People</div>
                  <TagChips options={PEOPLE} value={people} onChange={setPeople} hideInactive={!showAll} />
                </div>

                <div className="space-y-2">
                  <div className="text-xs text-muted-foreground">Tags</div>
                  <TagChips options={TAGS} value={tags} onChange={setTags} hideInactive={!showAll} />
                </div>

                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  {busy ? 'Speichern…' : dirty ? 'Ungespeichert (wird beim Schließen gespeichert)' : 'Gespeichert'}
                </div>

                {err ? <div className="text-sm text-destructive">{err}</div> : null}
              </div>
            </div>

            <div className="border-t p-4 sm:border-l sm:border-t-0">
              <DialogHeader>
                <DialogTitle className="text-base">Ort</DialogTitle>
              </DialogHeader>
              {item.location ? (
                <div className="mt-3 space-y-2">
                  <MapBlock lat={item.location.lat} lon={item.location.lon} />
                </div>
              ) : (
                <div className="mt-3 text-sm text-muted-foreground">Kein GPS im Foto.</div>
              )}
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
