import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { PhotoPointMap } from '@/components/maps/PhotoPointMap'

type UploadResult = {
  ok: boolean
  batch?: string
  count?: number
  saved?: Array<{ file: string; sidecar: string; originalName?: string }>
}

type GalleryItem = {
  path: string
  url: string
  hasSidecar: boolean
  createdAt?: string | null
  location?: { lat: number; lon: number } | null
  missing?: boolean
}

function formatDateTimeEU(iso?: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const yyyy = d.getFullYear()
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${dd}.${mm}.${yyyy} ${hh}:${mi}`
}

export function PhotosPage() {
  const [files, setFiles] = useState<FileList | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [result, setResult] = useState<UploadResult | null>(null)

  const [gallery, setGallery] = useState<GalleryItem[]>([])
  const [galleryErr, setGalleryErr] = useState<string | null>(null)

  const [selected, setSelected] = useState<GalleryItem | null>(null)

  const fileCount = useMemo(() => (files ? files.length : 0), [files])

  async function loadGallery() {
    try {
      setGalleryErr(null)
      const res = await fetch('/api/photos/inbox/all')
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      const json = (await res.json()) as { ok: boolean; items: GalleryItem[] }
      setGallery(json.items ?? [])
    } catch (e: any) {
      setGalleryErr(e?.message ?? String(e))
    }
  }

  useEffect(() => {
    loadGallery()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function onUpload() {
    if (!files || files.length === 0) return

    setBusy(true)
    setErr(null)
    setResult(null)

    try {
      const fd = new FormData()
      for (const f of Array.from(files)) fd.append('files', f)

      const res = await fetch('/api/photos/upload', {
        method: 'POST',
        body: fd
      })

      if (!res.ok) {
        const text = await res.text()
        throw new Error(`${res.status} ${res.statusText}: ${text}`)
      }

      const json = (await res.json()) as UploadResult
      setResult(json)
      setFiles(null)
      await loadGallery()
    } catch (e: any) {
      setErr(e?.message ?? String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Fotos – Upload</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Upload landet in <code>data/photos/inbox/YYYY-MM-DD_HHMM/</code>. Für jedes Bild wird automatisch ein{' '}
            <code>.json</code> Sidecar angelegt.
          </p>

          <input type="file" accept="image/*" multiple onChange={(e) => setFiles(e.target.files)} />

          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={onUpload} disabled={busy || fileCount === 0}>
              {busy ? 'Upload…' : `Upload (${fileCount})`}
            </Button>
            <Button variant="outline" onClick={loadGallery} disabled={busy}>
              Reload Galerie
            </Button>
          </div>

          {err ? <div className="text-sm text-destructive">{err}</div> : null}

          {result?.ok ? (
            <div className="rounded-lg border p-3 text-sm">
              <div>
                Gespeichert: <code>{result.batch}</code>
              </div>
              <div>Anzahl: {result.count}</div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Galerie</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {galleryErr ? <div className="text-sm text-destructive">{galleryErr}</div> : null}

          {gallery.length === 0 ? (
            <div className="text-sm text-muted-foreground">Noch keine Fotos gefunden. (Oder Backend läuft nicht.)</div>
          ) : (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
              {gallery.map((it) => (
                <button
                  type="button"
                  key={it.path}
                  onClick={() => setSelected(it)}
                  className="overflow-hidden rounded-lg border bg-muted text-left"
                >
                  <img
                    src={it.url}
                    alt={it.path}
                    loading="lazy"
                    className="block aspect-square w-full object-cover"
                  />
                  <div className="flex items-center justify-between gap-2 p-2 text-xs text-muted-foreground">
                    <span>{it.hasSidecar ? 'taggable' : 'no json'}</span>
                    {it.createdAt ? <span className="font-mono">{formatDateTimeEU(it.createdAt)}</span> : null}
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent className="p-0">
          {selected ? (
            <div className="grid max-h-[90vh] grid-cols-1 overflow-auto sm:grid-cols-2">
              <div className="p-4">
                <div className="overflow-hidden rounded-md border bg-muted">
                  <img src={selected.url} alt={selected.path} className="block h-auto w-full object-contain" />
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  <div className="font-mono break-all">{selected.path}</div>
                  {selected.createdAt ? <div>{formatDateTimeEU(selected.createdAt)}</div> : null}
                </div>
              </div>

              <div className="border-t p-4 sm:border-l sm:border-t-0">
                <DialogHeader>
                  <DialogTitle className="text-base">Ort</DialogTitle>
                </DialogHeader>
                {selected.location ? (
                  <div className="mt-3 space-y-2">
                    <div className="overflow-hidden rounded-md border">
                      <PhotoPointMap lat={selected.location.lat} lon={selected.location.lon} />
                    </div>
                    <div className="font-mono text-xs text-muted-foreground">
                      {selected.location.lat.toFixed(6)}, {selected.location.lon.toFixed(6)}
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
    </div>
  )
}
