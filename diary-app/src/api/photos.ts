import type { GalleryResponse, GalleryItem } from '@/types/photos'
import type { UploadResult } from '@/types/uploads'

export type Sidecar = {
  people: string[]
  tags: string[]
  caption: string
}

function errText(res: Response, bodyText?: string) {
  const extra = bodyText ? `: ${bodyText}` : ''
  return `${res.status} ${res.statusText}${extra}`
}

export async function listGallery(): Promise<GalleryItem[]> {
  const res = await fetch('/api/photos/inbox/all')
  if (!res.ok) throw new Error(errText(res))
  const json = (await res.json()) as GalleryResponse
  return json.items ?? []
}

export async function getSidecar(path: string): Promise<Sidecar> {
  const res = await fetch(`/api/photos/sidecar?path=${encodeURIComponent(path)}`)
  if (!res.ok) throw new Error(errText(res))
  const json = (await res.json()) as { ok: boolean; sidecar: Sidecar }
  return json.sidecar
}

export async function updateSidecar(req: { path: string; people: string[]; tags: string[] }) {
  const res = await fetch('/api/photos/sidecar', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ ...req, caption: '' })
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(errText(res, text))
  }
}

export async function bulkUpdate(req: {
  paths: string[]
  addPeople?: string[]
  removePeople?: string[]
  addTags?: string[]
  removeTags?: string[]
}) {
  const res = await fetch('/api/photos/sidecar/bulk', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(req)
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(errText(res, text))
  }
}

export async function trashPhotos(paths: string[]) {
  const res = await fetch('/api/photos/trash', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ paths })
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(errText(res, text))
  }
}

export async function uploadPhotos(files: FileList | File[]): Promise<UploadResult> {
  const fd = new FormData()
  for (const f of Array.from(files) ) fd.append('files', f)

  const res = await fetch('/api/photos/upload', {
    method: 'POST',
    body: fd
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(errText(res, text))
  }

  return (await res.json()) as UploadResult
}
