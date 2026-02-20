import { useCallback, useEffect, useState } from 'react'
import type { Trip } from '@/data/trips'
import type { GalleryItem } from '@/types/photos'
import { suggestPhotos, trashPhotos } from '@/api/photos'
import { GalleryGrid } from '../photos/GalleryGrid'
import { PhotoViewerDialog } from '../photos/PhotoViewerDialog'
import { useBulkTagging } from '@/hooks/useBulkTagging'
import { BulkTagDialog } from '../photos/BulkTagDialog'
import { useBulkSelection } from '@/hooks/useBulkSelection'
import { SelectionBar } from '../photos/SelectionBar'

export function TripPhotoSuggestions({ trip }: { trip: Trip }) {
  const [items, setItems] = useState<GalleryItem[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [viewerIndex, setViewerIndex] = useState<number | null>(null)
  const [bulkOpen, setBulkOpen] = useState(false)

  const { selectionMode, selectedPaths, toggleSelected, clearSelected, selectAllFiltered } = useBulkSelection()

  const loadSuggestions = useCallback(async () => {
    setBusy(true)
    setErr(null)
    setLoaded(false)
    try {
      const out = await suggestPhotos({ date: trip.meta.date, limit: 120 })
      setItems(out)
    } catch {
      setItems([])
    } finally {
      setBusy(false)
      setLoaded(true)
    }
  }, [trip.meta.date])

  useEffect(() => {
    void loadSuggestions()
  }, [loadSuggestions])

  const { busy: bulkBusy, error: bulkErr, bulkStateOf, toggleBulk } = useBulkTagging({
    gallery: items,
    selectedPaths,
    reload: loadSuggestions
  })

  // If nothing was found (or error), keep TripView clean: render nothing.
  if (loaded && !busy && items.length === 0) return null

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-3">
        <div className="text-sm font-medium">Fotos</div>
        <div className="text-xs text-muted-foreground">{busy ? 'Lade…' : `${items.length} am ${trip.meta.date}`}</div>
      </div>

      {items.length > 0 && (
        <>
          <GalleryGrid
            items={items}
            onSelect={(it) => setViewerIndex(items.findIndex((x) => x.path === it.path))}
            selectionMode={selectionMode}
            selected={selectedPaths}
            onToggleSelect={toggleSelected}
          />

          {viewerIndex !== null && (
            <PhotoViewerDialog
              items={items}
              index={viewerIndex}
              onChangeIndex={setViewerIndex}
              onClose={() => setViewerIndex(null)}
            />
          )}

          {selectionMode ? (
            <>
              <SelectionBar
                count={selectedPaths.size}
                onSelectAll={() => selectAllFiltered(items)}
                onClear={clearSelected}
                onShare={async () => {
                  const paths = Array.from(selectedPaths)
                  if (paths.length === 0) return

                  const nameFromPath = (p: string) => p.split('/').pop() || 'photo'

                  const MAX_DIRECT = 20
                  const itemsByPath = new Map(items.map((it) => [it.path, it] as const))
                  const selectedItems = paths.map((p) => itemsByPath.get(p)).filter(Boolean) as GalleryItem[]

                  async function fetchFile(it: GalleryItem) {
                    const res = await fetch(it.url)
                    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
                    const blob = await res.blob()
                    return new File([blob], nameFromPath(it.path), { type: blob.type || 'image/jpeg' })
                  }

                  const nav: any = navigator

                  if (selectedItems.length <= MAX_DIRECT && nav?.share) {
                    try {
                      const files: File[] = []
                      for (const it of selectedItems) files.push(await fetchFile(it))
                      await nav.share({ files, title: `Fotos (${files.length})` })
                      return
                    } catch {
                      // fall through to zip
                    }
                  }

                  try {
                    const { zipSync } = await import('fflate')
                    const entries: Record<string, Uint8Array> = {}
                    for (const it of selectedItems) {
                      const res = await fetch(it.url)
                      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
                      const buf = new Uint8Array(await res.arrayBuffer())
                      entries[nameFromPath(it.path)] = buf
                    }
                    const zipped = zipSync(entries, { level: 0 })
                    const blob = new Blob([zipped.slice().buffer], { type: 'application/zip' })
                    const objUrl = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = objUrl
                    a.download = `fotos_${new Date().toISOString().slice(0, 10)}.zip`
                    document.body.appendChild(a)
                    a.click()
                    a.remove()
                    window.setTimeout(() => URL.revokeObjectURL(objUrl), 1000)
                  } catch (e: any) {
                    alert(e?.message ?? String(e))
                  }
                }}
                onTrash={async () => {
                  const paths = Array.from(selectedPaths)
                  if (paths.length === 0) return

                  try {
                    await trashPhotos(paths)
                  } catch (e: any) {
                    alert(e?.message ?? String(e))
                    return
                  }

                  clearSelected()
                  setBulkOpen(false)
                  await loadSuggestions()
                }}
                onOpenTags={() => setBulkOpen(true)}
                onDone={() => {
                  clearSelected()
                  setBulkOpen(false)
                }}
              />

              <BulkTagDialog
                open={bulkOpen}
                onOpenChange={setBulkOpen}
                count={selectedPaths.size}
                busy={bulkBusy}
                error={bulkErr}
                bulkStateOf={bulkStateOf}
                onToggle={toggleBulk}
              />
            </>
          ) : null}
        </>
      )}
    </div>
  )
}