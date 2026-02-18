import { useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { GalleryItem } from '@/types/photos'
import { useGallery } from '@/hooks/useGallery'
import { GalleryGrid } from '@/components/photos/GalleryGrid'
import { PhotoViewerDialog } from '@/components/photos/PhotoViewerDialog'
import { PhotoUploadCard } from '@/components/photos/PhotoUploadCard'
import { Button } from '@/components/ui/button'
import { Filter } from 'lucide-react'
import { TagChips } from '@/components/photos/TagChips'
import { BulkTagDialog } from '@/components/photos/BulkTagDialog'
import { SelectionBar } from '@/components/photos/SelectionBar'
import { useBulkSelection } from '@/hooks/useBulkSelection'
import { useBulkTagging } from '@/hooks/useBulkTagging'
import { PEOPLE, TAGS } from '@/data/tagConfig'
import { trashPhotos } from '@/api/photos'

export function PhotosPage() {
  const { items: gallery, error: galleryErr, reload: loadGallery } = useGallery()

  const [viewerIndex, setViewerIndex] = useState<number | null>(null)
  const [bulkOpen, setBulkOpen] = useState(false)

  const { selectionMode, selectedPaths, toggleSelected, clearSelected, selectAllFiltered } = useBulkSelection()

  const { busy: bulkBusy, error: bulkErr, bulkStateOf, toggleBulk } = useBulkTagging({
    gallery,
    selectedPaths,
    reload: loadGallery
  })

  const [filtersOpen, setFiltersOpen] = useState(false)
  const [peopleFilter, setPeopleFilter] = useState<string[]>([])
  const [tagFilter, setTagFilter] = useState<string[]>([])
  const [untaggedOnly, setUntaggedOnly] = useState(false)

  const filtered = useMemo(() => {
    return gallery.filter((it) => {
      const people = it.people ?? []
      const tags = it.tags ?? []

      if (untaggedOnly && (people.length > 0 || tags.length > 0)) return false

      // AND semantics: all selected people/tags must be present
      for (const p of peopleFilter) if (!people.includes(p)) return false
      for (const t of tagFilter) if (!tags.includes(t)) return false

      return true
    })
  }, [gallery, peopleFilter, tagFilter, untaggedOnly])

  return (
    <div className="space-y-4">
      <PhotoUploadCard onUploaded={loadGallery} />
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">Galerie</CardTitle>
              <div className="text-xs text-muted-foreground">
                {filtered.length} / {gallery.length} Fotos
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setFiltersOpen((v) => !v)}>
                <Filter className="mr-2 h-4 w-4" /> Filter
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {filtersOpen ? (
            <div className="space-y-4 rounded-lg border bg-muted/20 p-3">
              <div className="space-y-2">
                <div className="text-xs text-muted-foreground">People</div>
                <TagChips options={PEOPLE} value={peopleFilter} onChange={setPeopleFilter} />
              </div>

              <div className="space-y-2">
                <div className="text-xs text-muted-foreground">Tags</div>
                <TagChips options={TAGS} value={tagFilter} onChange={setTagFilter} />
              </div>

              <div>
                <button
                  type="button"
                  onClick={() => setUntaggedOnly((v) => !v)}
                  className="text-sm text-muted-foreground underline"
                >
                  {untaggedOnly ? '✓ Nur ungetaggte (an)' : 'Nur ungetaggte'}
                </button>
              </div>
            </div>
          ) : null}
          {galleryErr ? <div className="text-sm text-destructive">{galleryErr}</div> : null}

          {filtered.length === 0 ? (
            <div className="text-sm text-muted-foreground">Keine Fotos gefunden (Filter?).</div>
          ) : (
            <GalleryGrid
              items={filtered}
              onSelect={(it) => setViewerIndex(filtered.findIndex((x) => x.path === it.path))}
              selectionMode={selectionMode}
              selected={selectedPaths}
              onToggleSelect={toggleSelected}
            />
          )}
        </CardContent>
      </Card>

      <PhotoViewerDialog
        items={filtered}
        index={viewerIndex}
        onChangeIndex={setViewerIndex}
        onClose={() => {
          setViewerIndex(null)
          // viewer interactions may have updated sidecars; keep gallery fresh
          void loadGallery()
        }}
      />

      {selectionMode ? (
        <>
          <SelectionBar
            count={selectedPaths.size}
            onSelectAll={() => selectAllFiltered(filtered)}
            onClear={clearSelected}
            onTrash={async () => {
              const paths = Array.from(selectedPaths)
              if (paths.length === 0) return

              try {
                await trashPhotos(paths)
              } catch (e: any) {
                // TODO: unify with app-wide toast later
                alert(e?.message ?? String(e))
                return
              }

              clearSelected()
              setBulkOpen(false)
              await loadGallery()
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
    </div>
  )
}
