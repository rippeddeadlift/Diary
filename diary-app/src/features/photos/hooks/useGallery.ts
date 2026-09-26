import { useCallback, useEffect, useRef, useState } from 'react'
import { listGallery } from '@/api/photos'
import type { GalleryItem } from '@/types/photos'

const PAGE = 48
const NEXT_PAGE = 120

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
      let before = first.items[first.items.length - 1]?.path
      let hasMore = true
      while (hasMore && before) {
        const page = await listGallery({ before, limit: NEXT_PAGE })
        if (gen.current !== id) return
        if (page.items.length === 0) break
        before = page.items[page.items.length - 1]?.path
        hasMore = page.hasMore
        setItems((prev) => {
          const seen = new Set(prev.map((it) => it.path))
          return [...prev, ...page.items.filter((it) => !seen.has(it.path))]
        })
        if (page.total != null) setTotal(page.total)
      }
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
