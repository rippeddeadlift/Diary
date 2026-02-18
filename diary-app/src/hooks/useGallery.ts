import { useCallback, useEffect, useState } from 'react'
import type { GalleryItem } from '@/types/photos'
import { listGallery } from '@/api/photos'

export function useGallery() {
  const [items, setItems] = useState<GalleryItem[]>([])
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      setError(null)
      setItems(await listGallery())
    } catch (e: any) {
      setError(e?.message ?? String(e))
    }
  }, [])

  useEffect(() => {
    reload()
  }, [reload])

  return { items, error, reload }
}
