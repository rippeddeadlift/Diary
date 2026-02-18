import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { UploadResult } from '@/types/uploads'
import { uploadPhotos, uploadZip } from '@/api/photos'
import { chunkArray } from '@/lib/chunk'
import { UploadProgress } from '@/components/photos/UploadProgress'

export function PhotoUploadCard({ onUploaded }: { onUploaded: () => Promise<void> }) {
  const [files, setFiles] = useState<FileList | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [result, setResult] = useState<UploadResult | null>(null)
  const [uploaded, setUploaded] = useState(0)
  const [dupSkipped, setDupSkipped] = useState(0)
  const [zipFile, setZipFile] = useState<File | null>(null)

  const fileCount = useMemo(() => (files ? files.length : 0), [files])

  async function onUpload() {
    if (!files || files.length === 0) return

    setBusy(true)
    setErr(null)
    setResult(null)
    setUploaded(0)
    setDupSkipped(0)

    try {
      const all = Array.from(files)
      const batches = chunkArray(all, 25)

      let totalSaved = 0
      let totalDup = 0
      let last: UploadResult | null = null

      for (let i = 0; i < batches.length; i++) {
        const batch = batches[i]
        const json = await uploadPhotos(batch)
        last = json
        totalSaved += json.count ?? 0
        totalDup += json.duplicatesSkipped ?? 0

        setUploaded((i + 1) * 25 > all.length ? all.length : (i + 1) * 25)
        setDupSkipped(totalDup)
      }

      setResult({ ok: true, batch: last?.batch, count: totalSaved, duplicatesSkipped: totalDup })
      setFiles(null)
      await onUploaded()
    } catch (e: any) {
      setErr(e?.message ?? String(e))
    } finally {
      setBusy(false)
    }
  }

  async function onUploadZip() {
    if (!zipFile) return
    setBusy(true)
    setErr(null)
    setResult(null)
    setUploaded(0)
    setDupSkipped(0)

    try {
      const json = await uploadZip(zipFile)
      setResult(json)
      setZipFile(null)
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

        {busy ? <UploadProgress done={uploaded} total={fileCount} duplicates={dupSkipped} /> : null}

        <div className="mt-3 space-y-2">
          <div className="text-xs text-muted-foreground">Oder ZIP hochladen (jpg/jpeg/png/webp)</div>
          <input
            type="file"
            accept=".zip,application/zip"
            onChange={(e) => setZipFile(e.target.files?.[0] ?? null)}
            disabled={busy}
          />
          <div>
            <Button onClick={onUploadZip} disabled={busy || !zipFile} variant="secondary">
              {busy ? 'Upload…' : 'ZIP hochladen'}
            </Button>
          </div>
        </div>

        {err ? <div className="text-sm text-destructive">{err}</div> : null}

        {result?.ok ? (
          <div className="rounded-lg border p-3 text-sm">
            <div>
              Gespeichert: <code>{result.batch}</code>
            </div>
            <div>Anzahl: {result.count}</div>
            {typeof (result as any).duplicatesSkipped === 'number' && (result as any).duplicatesSkipped > 0 ? (
              <div className="mt-1 text-xs text-muted-foreground">Duplikate übersprungen: {(result as any).duplicatesSkipped}</div>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
