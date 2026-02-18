import { useState } from 'react'
import type { GalleryItem } from '@/types/photos'

export function useBulkSelection() {
  const [selectionMode, setSelectionMode] = useState(false)
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set())

  function toggleSelectionMode() {
    setSelectionMode((v) => !v)
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
    setSelectedPaths(new Set())
  }

  function selectAllFiltered(items: GalleryItem[]) {
    setSelectedPaths(new Set(items.map((x) => x.path)))
  }

  return {
    selectionMode,
    setSelectionMode,
    toggleSelectionMode,
    selectedPaths,
    toggleSelected,
    clearSelected,
    selectAllFiltered
  }
}
