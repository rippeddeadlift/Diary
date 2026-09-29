import { useEffect, useRef, useState } from 'react'
import { Archive, Check, FolderOpen, HardDrive, LoaderCircle, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  getBackupExportStatus,
  getLatestBackup,
  importBackup,
  saveBackupToMedia,
  startBackupExport,
  type LatestBackup,
} from '@/api/backup'

export function SettingsPage() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [backupFile, setBackupFile] = useState<File | null>(null)
  const [confirmReplace, setConfirmReplace] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [exportProgress, setExportProgress] = useState({ filesDone: 0, totalFiles: 0 })
  const [exportError, setExportError] = useState<string | null>(null)
  const [exportResult, setExportResult] = useState<string | null>(null)
  const [latestBackup, setLatestBackup] = useState<LatestBackup | null>(null)
  const [backupStatusError, setBackupStatusError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)

  async function refreshLatestBackup() {
    try {
      setLatestBackup(await getLatestBackup())
      setBackupStatusError(null)
    } catch (reason) {
      setLatestBackup(null)
      setBackupStatusError(reason instanceof Error ? reason.message : 'Der Backup-Status konnte nicht geladen werden.')
    }
  }

  useEffect(() => {
    void refreshLatestBackup()
  }, [])

  async function createBackup() {
    setExporting(true)
    setExportError(null)
    setExportResult(null)
    setExportProgress({ filesDone: 0, totalFiles: 0 })
    try {
      const { jobId } = await startBackupExport()
      while (true) {
        const status = await getBackupExportStatus(jobId)
        setExportProgress({ filesDone: status.filesDone, totalFiles: status.totalFiles })
        if (status.status === 'error') throw new Error(status.error ?? 'Das ZIP konnte nicht erstellt werden.')
        if (status.status === 'ready') break
        await new Promise((resolve) => window.setTimeout(resolve, 500))
      }
      const saved = await saveBackupToMedia(jobId)
      setExportResult(saved.path)
      await refreshLatestBackup()
    } catch (reason) {
      setExportError(reason instanceof Error ? reason.message : 'Das Backup konnte nicht erstellt werden.')
    } finally {
      setExporting(false)
    }
  }

  async function restoreBackup() {
    if (!backupFile || !confirmReplace) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const restored = await importBackup(backupFile)
      setResult(`Wiederhergestellt: ${restored.files} Dateien (${formatBytes(restored.unpackedBytes)}). Lade die Seite neu, damit alle Bereiche die Daten neu laden.`)
      setBackupFile(null)
      setConfirmReplace(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Das Backup konnte nicht wiederhergestellt werden.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-8">
      <header className="border-b pb-5">
        <h1 className="text-2xl font-semibold">Einstellungen</h1>
      </header>

      <section className="space-y-5 border-b pb-8" aria-labelledby="backup-heading">
        <div className="flex items-start gap-3">
          <Archive className="mt-1 h-5 w-5 shrink-0 text-muted-foreground" />
          <div>
            <h2 id="backup-heading" className="text-lg font-medium">Datensicherung</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Das ZIP enthält den gesamten lokalen <code>data/</code>-Ordner und wird im konfigurierten Medienordner gespeichert.
            </p>
          </div>
        </div>

        {latestBackup?.valid && latestBackup.createdAt ? (
          <p role="status" className="flex items-center gap-2 text-sm font-medium text-green-700">
            <Check className="h-4 w-4" /> Backup gemacht am {formatBackupDate(latestBackup.createdAt)}
          </p>
        ) : backupStatusError ? (
          <p role="alert" className="text-sm text-destructive">{backupStatusError}</p>
        ) : (
          <p className="text-sm text-muted-foreground">Kein gültiges Backup gefunden.</p>
        )}

        <Button type="button" onClick={() => void createBackup()} disabled={busy || exporting}>
          {exporting ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> : <HardDrive className="mr-2 h-4 w-4" />}
          {exporting ? 'ZIP wird erstellt…' : 'Backup im Medienordner speichern'}
        </Button>
        {exporting ? (
          <div role="status" className="max-w-xl space-y-2 text-sm text-muted-foreground">
            <p>
              {exportProgress.totalFiles > 0
                ? `${exportProgress.filesDone.toLocaleString()} von ${exportProgress.totalFiles.toLocaleString()} Dateien archiviert`
                : 'Daten werden gezählt…'}
            </p>
            <progress
              max={Math.max(exportProgress.totalFiles, 1)}
              value={exportProgress.filesDone}
              aria-label="Backup-Fortschritt"
              className="h-2 w-full accent-primary"
            />
          </div>
        ) : null}
        {exportError ? <p role="alert" className="text-sm text-destructive">{exportError}</p> : null}
        {exportResult ? <p role="status" className="text-sm text-muted-foreground">Gespeichert: {exportResult}</p> : null}
      </section>

      <section className="space-y-5" aria-labelledby="restore-heading">
        <div>
          <h2 id="restore-heading" className="text-lg font-medium">Backup wiederherstellen</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Der aktuelle <code>data/</code>-Ordner wird ersetzt. Der externe Medienordner bleibt unverändert.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={fileInputRef}
            id="backup-file"
            type="file"
            accept=".zip,application/zip"
            disabled={busy}
            aria-label="ZIP-Datei auswählen"
            onChange={(event) => {
              setBackupFile(event.target.files?.[0] ?? null)
              setConfirmReplace(false)
              setError(null)
              setResult(null)
            }}
            className="hidden"
          />
          <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()} disabled={busy}>
            <FolderOpen className="mr-2 h-4 w-4" />
            {backupFile ? 'ZIP-Datei ändern' : 'ZIP-Datei auswählen'}
          </Button>
          <span className="min-w-0 truncate text-sm text-muted-foreground" title={backupFile?.name}>
            {backupFile ? `${backupFile.name} · ${formatBytes(backupFile.size)}` : 'Keine Datei ausgewählt'}
          </span>
        </div>

        <label className="flex max-w-2xl items-start gap-3 text-sm">
          <input
            type="checkbox"
            checked={confirmReplace}
            disabled={busy || !backupFile}
            onChange={(event) => setConfirmReplace(event.target.checked)}
            className="mt-0.5 h-4 w-4 accent-primary"
          />
          <span>Ich bestätige, dass die vorhandenen Daten durch den Inhalt des ZIP-Backups ersetzt werden.</span>
        </label>

        <Button type="button" onClick={() => void restoreBackup()} disabled={busy || !backupFile || !confirmReplace}>
          {busy ? <LoaderCircle className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
          {busy ? 'Wird wiederhergestellt…' : 'Backup wiederherstellen'}
        </Button>

        {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
        {result ? <p role="status" className="flex items-start gap-2 text-sm text-green-700"><Check className="mt-0.5 h-4 w-4 shrink-0" />{result}</p> : null}
      </section>
    </div>
  )
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`
}

function formatBackupDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'unbekannt'
  const day = String(date.getDate()).padStart(2, '0')
  const month = String(date.getMonth() + 1).padStart(2, '0')
  return `${day}.${month}.${date.getFullYear()}`
}