export type PhotoLocation = { lat: number; lon: number } | null

export type GalleryItem = {
  path: string
  url: string
  thumbUrl?: string | null
  hasSidecar: boolean
  createdAt?: string | null
  location?: PhotoLocation
  missing?: boolean
}

export type GalleryResponse = { ok: boolean; items: GalleryItem[] }
