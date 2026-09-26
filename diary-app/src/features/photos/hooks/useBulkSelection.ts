import { useState } from 'react'
import type { GalleryItem } from '@/types/photos'

export function useBulkSelection() {
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set())

  const selectionMode = selectedPaths.size > 0

  function clearAll() {
    setSelectedPaths(new Set())
  }

  function toggleSelected(it: GalleryItem) {
    setSelectedPaths((prev) => {
      const next = new Set(prev)
      if (next.has(it.path)) next.delete(it.path)
      else next.add(it.path)
      return next
    })
  }

  function clearSelected() {
    clearAll()
  }

  function selectAllFiltered(items: GalleryItem[]) {
    setSelectedPaths(new Set(items.map((x) => x.path)))
  }

  return {
    selectionMode,
    selectedPaths,
    toggleSelected,
    clearSelected,
    selectAllFiltered
  }
}
