export type BackupImportResult = {
  ok: boolean
  files: number
  unpackedBytes: number
}

export type BackupExportStatus = {
  jobId: string
  status: 'running' | 'ready' | 'error'
  filesDone: number
  totalFiles: number
  error: string | null
}

export type LatestBackup = {
  valid: boolean
  createdAt: string | null
  filename: string | null
}

export async function getLatestBackup(): Promise<LatestBackup> {
  const response = await fetch('/api/backup/status')
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail ?? 'Der Backup-Status konnte nicht geladen werden.')
  }
  return payload as LatestBackup
}

export async function startBackupExport(): Promise<{ jobId: string }> {
  const response = await fetch('/api/backup/export', { method: 'POST' })
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail ?? 'Das Backup konnte nicht gestartet werden.')
  }
  return payload as { jobId: string }
}

export async function getBackupExportStatus(jobId: string): Promise<BackupExportStatus> {
  const response = await fetch(`/api/backup/export/${encodeURIComponent(jobId)}`)
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail ?? 'Der Backup-Status konnte nicht geladen werden.')
  }
  return payload as BackupExportStatus
}

export function getBackupDownloadUrl(jobId: string): string {
  return `/api/backup/export/${encodeURIComponent(jobId)}/download`
}

export async function saveBackupToMedia(jobId: string): Promise<{ path: string }> {
  const response = await fetch(`/api/backup/export/${encodeURIComponent(jobId)}/save-to-media`, { method: 'POST' })
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail ?? 'Das Backup konnte nicht im Medienordner gespeichert werden.')
  }
  return payload as { path: string }
}

export async function importBackup(file: File): Promise<BackupImportResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('confirm_replace', 'true')

  const response = await fetch('/api/backup/import', { method: 'POST', body: form })
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail ?? 'Das Backup konnte nicht wiederhergestellt werden.')
  }
  return payload as BackupImportResult
}