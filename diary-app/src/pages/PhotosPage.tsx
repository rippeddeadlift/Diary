import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

type UploadResult = {
  ok: boolean
  batch?: string
  count?: number
  saved?: Array<{ file: string; sidecar: string; originalName?: string }>
}

export function PhotosPage() {
  const [files, setFiles] = useState<FileList | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [result, setResult] = useState<UploadResult | null>(null)

  const fileCount = useMemo(() => (files ? files.length : 0), [files])

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

          <input
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => setFiles(e.target.files)}
          />

          <div className="flex items-center gap-2">
            <Button onClick={onUpload} disabled={busy || fileCount === 0}>
              {busy ? 'Upload…' : `Upload (${fileCount})`}
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
          <CardTitle className="text-base">Später</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Nächster Schritt (nach dem MVP): Galerie + Tagging UI (people/tags/caption) direkt im Tagebuch.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
