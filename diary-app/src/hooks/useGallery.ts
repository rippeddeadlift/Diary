import { useCallback, useEffect, useState } from 'react'
import type { GalleryItem, GalleryResponse } from '@/types/photos'

export function useGallery() {
  const [items, setItems] = useState<GalleryItem[]>([])
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      setError(null)
      const res = await fetch('/api/photos/inbox/all')
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      const json = (await res.json()) as GalleryResponse
      setItems(json.items ?? [])
    } catch (e: any) {
      setError(e?.message ?? String(e))
    }
  }, [])

  useEffect(() => {
    reload()
  }, [reload])

  return { items, error, reload }
}
