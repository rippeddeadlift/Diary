import { useMemo, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { UploadResult } from '@/types/uploads'
import { uploadPhotos, uploadZip } from '@/api/photos'
import { chunkArray } from '@/lib/chunk'
import { UploadProgress } from '@/components/photos/UploadProgress'

export function PhotoUploadCard({ onUploaded }: { onUploaded: () => Promise<void> }) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<FileList | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [result, setResult] = useState<UploadResult | null>(null)
  const [uploaded, setUploaded] = useState(0)
  const [dupSkipped, setDupSkipped] = useState(0)
  const batchSize = 150;
  const fileCount = useMemo(() => (files ? files.length : 0), [files])
  const singleZip = useMemo(() => {
    if (!files || files.length !== 1) return null
    const f = files[0]
    return f.name.toLowerCase().endsWith('.zip') ? f : null
  }, [files])

  async function onUpload() {
    if (!files || files.length === 0) return

    setBusy(true)
    setErr(null)
    setResult(null)
    setUploaded(0)
    setDupSkipped(0)

    try {
      // ZIP mode (exactly one .zip selected)
      if (singleZip) {
        const json = await uploadZip(singleZip)
        setResult(json)
        setFiles(null)
        await onUploaded()
        return
      }

      // image mode
      const all = Array.from(files)
      const batches = chunkArray(all, batchSize)

      let totalSaved = 0
      let totalDup = 0
      let last: UploadResult | null = null

      for (let i = 0; i < batches.length; i++) {
        try {
          const batch = batches[i]
          const json = await uploadPhotos(batch)
          last = json
          totalSaved += json.count ?? 0
          totalDup += json.duplicatesSkipped ?? 0

          setUploaded((i + 1) * batchSize > all.length ? all.length : (i + 1) * batchSize)
          setDupSkipped(totalDup)
        } catch (err) {
          console.error(`Batch ${i} fehlgeschlagen:`, err);
          continue;
        }

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

  return (
    <Card>
      <CardHeader>
        <CardTitle>Fotos – Upload</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Upload landet in <code>data/photos/inbox/YYYY-MM-DD_HHMM/</code>. Für jedes Bild wird automatisch ein <code>.json</code>{' '}
          Sidecar angelegt.
        </p>

        {/* Versteckte Inputs */}
        <div className="hidden">
          <input
            type="file"
            accept="image/*,.zip,application/zip"
            multiple
            ref={fileInputRef}
            onChange={(e) => setFiles(e.target.files)}
          />
          <input
            type="file"
            multiple
            {...{ webkitdirectory: '' } as React.InputHTMLAttributes<HTMLInputElement>}
            ref={folderInputRef}
            onChange={(e) => {
              const rawFiles = e.target.files;
              if (!rawFiles || rawFiles.length === 0) return;

              // Erlaubte Endungen
              const allowedExts = ['.jpg', '.jpeg', '.png', '.heic', '.heif'];

              // Filtere nach Dateiendung statt MIME-Type
              const validFiles = Array.from(rawFiles).filter((f) => {
                const name = f.name.toLowerCase();
                return allowedExts.some(ext => name.endsWith(ext));
              });

              if (validFiles.length === 0) {
                alert("Keine unterstützten Medien (Bilder/Videos) in diesem Ordner gefunden.");
                return;
              }

              const dt = new DataTransfer();
              validFiles.forEach((f) => dt.items.add(f));

              setFiles(dt.files);

              // Input zurücksetzen, damit dieselbe Auswahl nochmal getriggert werden kann
              e.target.value = "";
            }}
          />
        </div>

        {/* Sichtbare UI */}
        <div className="flex flex-col gap-3 rounded-md border p-4 bg-muted/50">
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={busy}
            >
              Dateien / ZIP wählen
            </Button>

            <Button
              variant="outline"
              onClick={() => folderInputRef.current?.click()}
              disabled={busy}
            >
              Ordner wählen
            </Button>
          </div>

          {fileCount > 0 && (
            <div className="text-sm font-medium">
              Ausgewählt: {singleZip ? singleZip.name : `${fileCount} Bilder`}
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={onUpload} disabled={busy || fileCount === 0} className="w-full sm:w-auto">
            {busy ? 'Upload…' : singleZip ? 'ZIP importieren' : `Upload starten (${fileCount})`}
          </Button>
        </div>

        {busy ? <UploadProgress done={uploaded} total={fileCount} duplicates={dupSkipped} /> : null}

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
            {typeof (result as any).skippedNonImages === 'number' && (result as any).skippedNonImages > 0 ? (
              <div className="mt-1 text-xs text-muted-foreground">Nicht-Bilder übersprungen: {(result as any).skippedNonImages}</div>
            ) : null}
            {Array.isArray((result as any).errors) && (result as any).errors.length ? (
              <div className="mt-1 text-xs text-muted-foreground">Fehler: {(result as any).errors.length}</div>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
