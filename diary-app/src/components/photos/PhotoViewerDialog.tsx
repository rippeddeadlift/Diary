import { useEffect, useMemo, useState } from 'react'
import type { GalleryItem } from '@/types/photos'
import { parseCsvList, toCsvList } from '@/lib/tags'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { PhotoPointMap } from '@/components/maps/PhotoPointMap'
import { Button } from '@/components/ui/button'

type Sidecar = {
  people: string[]
  tags: string[]
  caption: string
}

export function PhotoViewerDialog({ item, onClose }: { item: GalleryItem | null; onClose: () => void }) {
  const [people, setPeople] = useState<string[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [caption, setCaption] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const path = item?.path

  useEffect(() => {
    if (!path) return

    ;(async () => {
      try {
        setErr(null)
        const res = await fetch(`/api/photos/sidecar?path=${encodeURIComponent(path)}`)
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
        const json = (await res.json()) as { ok: boolean; sidecar: Sidecar }
        setPeople(json.sidecar?.people ?? [])
        setTags(json.sidecar?.tags ?? [])
        setCaption(json.sidecar?.caption ?? '')
      } catch (e: any) {
        setErr(e?.message ?? String(e))
      }
    })()
  }, [path])

  const people = useMemo(() => parseCsvList(peopleStr), [peopleStr])
  const tags = useMemo(() => parseCsvList(tagsStr), [tagsStr])

  async function onSave() {
    if (!path) return
    setBusy(true)
    setErr(null)
    try {
      const res = await fetch('/api/photos/sidecar', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ path, people, tags, caption })
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`${res.status} ${res.statusText}: ${text}`)
      }
    } catch (e: any) {
      setErr(e?.message ?? String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={!!item} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="p-0">
        {item ? (
          <div className="grid max-h-[90vh] grid-cols-1 overflow-auto sm:grid-cols-2">
            <div className="p-4">
              <div className="overflow-hidden rounded-md border bg-muted">
                <img src={item.url} alt={item.path} className="block h-auto w-full object-contain" />
              </div>

              <div className="mt-4 space-y-2">
                <DialogHeader>
                  <DialogTitle className="text-base">Tags</DialogTitle>
                </DialogHeader>

                <label className="block text-xs text-muted-foreground">People (klein, Komma getrennt)</label>
                <input
                  value={peopleStr}
                  onChange={(e) => setPeopleStr(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  placeholder="person1, person2, ..."
                />

                <label className="block text-xs text-muted-foreground">Tags (Komma getrennt)</label>
                <input
                  value={tagsStr}
                  onChange={(e) => setTagsStr(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  placeholder="family, nature, cycling"
                />

                <label className="block text-xs text-muted-foreground">Caption</label>
                <textarea
                  value={caption}
                  onChange={(e) => setCaption(e.target.value)}
                  className="min-h-[80px] w-full rounded-md border bg-background px-3 py-2 text-sm"
                  placeholder="Kurze Notiz…"
                />

                <div className="flex items-center gap-2">
                  <Button onClick={onSave} disabled={busy}>
                    {busy ? 'Speichern…' : 'Speichern'}
                  </Button>
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
                  <div className="overflow-hidden rounded-md border">
                    <PhotoPointMap lat={item.location.lat} lon={item.location.lon} />
                  </div>
                  <div className="font-mono text-xs text-muted-foreground">
                    {item.location.lat.toFixed(6)}, {item.location.lon.toFixed(6)}
                  </div>
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
