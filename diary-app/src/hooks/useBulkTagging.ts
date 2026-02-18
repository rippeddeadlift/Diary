import { useMemo, useState } from 'react'
import type { GalleryItem } from '@/types/photos'

export type BulkState = 'off' | 'on' | 'mixed'

type Patch = {
  addPeople?: string[]
  removePeople?: string[]
  addTags?: string[]
  removeTags?: string[]
}

export function useBulkTagging({
  gallery,
  selectedPaths,
  reload
}: {
  gallery: GalleryItem[]
  selectedPaths: Set<string>
  reload: () => Promise<void>
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectedList = useMemo(() => Array.from(selectedPaths), [selectedPaths])

  function bulkStateOf(opt: string, kind: 'people' | 'tags'): BulkState {
    if (selectedList.length === 0) return 'off'

    let yes = 0
    for (const p of selectedList) {
      const it = gallery.find((g) => g.path === p)
      const arr = kind === 'people' ? it?.people ?? [] : it?.tags ?? []
      if (arr.includes(opt)) yes += 1
    }

    if (yes === 0) return 'off'
    if (yes === selectedList.length) return 'on'
    return 'mixed'
  }

  async function applyBulkPatch(patch: Patch) {
    const paths = selectedList
    if (paths.length === 0) return

    setBusy(true)
    setError(null)
    try {
      const res = await fetch('/api/photos/sidecar/bulk', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ paths, ...patch })
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`${res.status} ${res.statusText}: ${text}`)
      }
      await reload()
    } catch (e: any) {
      setError(e?.message ?? String(e))
    } finally {
      setBusy(false)
    }
  }

  async function toggleBulk(opt: string, current: BulkState, kind: 'people' | 'tags') {
    // Normalize:
    // - off/mixed -> make all ON (add)
    // - on -> make all OFF (remove)
    const makeOn = current !== 'on'
    if (kind === 'people') {
      await applyBulkPatch(makeOn ? { addPeople: [opt] } : { removePeople: [opt] })
    } else {
      await applyBulkPatch(makeOn ? { addTags: [opt] } : { removeTags: [opt] })
    }
  }

  return { busy, error, bulkStateOf, applyBulkPatch, toggleBulk }
}
