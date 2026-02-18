export type PhotoLocation = { lat: number; lon: number } | null

export type GalleryItem = {
  path: string
  url: string
  hasSidecar: boolean

  thumbUrl?: string | null
  thumbExists?: boolean

  people?: string[]
  tags?: string[]
  createdAt?: string | null
  location?: PhotoLocation
  missing?: boolean
}

export type GalleryResponse = { ok: boolean; items: GalleryItem[] }
