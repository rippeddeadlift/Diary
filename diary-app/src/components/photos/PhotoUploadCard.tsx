import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { UploadResult } from '@/types/uploads'

export function PhotoUploadCard({ onUploaded }: { onUploaded: () => Promise<void> }) {
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
      await onUploaded()
    } catch (e: any) {
      setErr(e?.message ?? String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
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
  )
}
