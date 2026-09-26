import { useCallback, useEffect, useRef, useState } from 'react'
import { listGallery } from '@/api/photos'
import type { GalleryItem } from '@/types/photos'

const PAGE = 48

export function useGallery() {
  const [items, setItems] = useState<GalleryItem[]>([])
  const [total, setTotal] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const gen = useRef(0)

  const reload = useCallback(async () => {
    const id = ++gen.current
    setLoading(true)
    setError(null)
    try {
      const first = await listGallery({ offset: 0, limit: PAGE })
      if (gen.current !== id) return
      if (first.items.length > 0) {
        setItems(first.items)
        setTotal(first.total)
        setLoading(false)
      }

      if (!first.hasMore) return

      setLoadingMore(true)
      // One full request writes the path/date cache and replaces the provisional pages.
      const all = await listGallery()
      if (gen.current !== id) return
      setItems(all.items)
      setTotal(all.total)
    } catch (e) {
      if (gen.current !== id) return
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      if (gen.current === id) {
        setLoading(false)
        setLoadingMore(false)
      }
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  return { items, total, loading, loadingMore, error, reload }
}
