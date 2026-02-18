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
import { BulkTagChips, type BulkState } from '@/components/photos/BulkTagChips'
import { PEOPLE, TAGS } from '@/data/tagConfig'

export function PhotosPage() {
  const { items: gallery, error: galleryErr, reload: loadGallery } = useGallery()

  const [selected, setSelected] = useState<GalleryItem | null>(null)

  const [selectionMode, setSelectionMode] = useState(false)
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set())

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

  async function applyBulkPatch(patch: {
    addPeople?: string[]
    removePeople?: string[]
    addTags?: string[]
    removeTags?: string[]
  }) {
    const paths = Array.from(selectedPaths)
    if (paths.length === 0) return

    const res = await fetch('/api/photos/sidecar/bulk', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ paths, ...patch })
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(`${res.status} ${res.statusText}: ${text}`)
    }
    await loadGallery()
  }

  function bulkStateOf(opt: string, kind: 'people' | 'tags'): BulkState {
    const paths = Array.from(selectedPaths)
    if (paths.length === 0) return 'off'

    let yes = 0
    for (const p of paths) {
      const it = gallery.find((g) => g.path === p)
      const arr = kind === 'people' ? it?.people ?? [] : it?.tags ?? []
      if (arr.includes(opt)) yes += 1
    }

    if (yes === 0) return 'off'
    if (yes === paths.length) return 'on'
    return 'mixed'
  }

  async function onToggleBulk(opt: string, current: BulkState, kind: 'people' | 'tags') {
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

  function toggleSelected(it: GalleryItem) {
    setSelectedPaths((prev) => {
      const next = new Set(prev)
      if (next.has(it.path)) next.delete(it.path)
      else next.add(it.path)
      return next
    })
  }

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
              <Button variant={selectionMode ? 'default' : 'outline'} size="sm" onClick={() => {
                setSelectionMode((v) => !v)
                setSelectedPaths(new Set())
              }}>
                {selectionMode ? 'Auswahl an' : 'Auswählen'}
              </Button>

              <Button variant="outline" size="sm" onClick={() => setFiltersOpen((v) => !v)}>
                <Filter className="mr-2 h-4 w-4" /> Filter
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {selectionMode ? (
            <div className="space-y-3 rounded-lg border bg-muted/20 p-3">
              <div className="text-xs text-muted-foreground">
                Auswahl: {selectedPaths.size} Foto(s). Chip klicken → setzt bei allen ausgewählten auf an/aus (gemischt wird „an“).
              </div>

              <div className="space-y-2">
                <div className="text-xs text-muted-foreground">People</div>
                <BulkTagChips
                  options={PEOPLE}
                  stateOf={(opt) => bulkStateOf(opt, 'people')}
                  onToggle={(opt, st) => void onToggleBulk(opt, st, 'people')}
                />
              </div>

              <div className="space-y-2">
                <div className="text-xs text-muted-foreground">Tags</div>
                <BulkTagChips
                  options={TAGS}
                  stateOf={(opt) => bulkStateOf(opt, 'tags')}
                  onToggle={(opt, st) => void onToggleBulk(opt, st, 'tags')}
                />
              </div>
            </div>
          ) : null}
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
              onSelect={setSelected}
              selectionMode={selectionMode}
              selected={selectedPaths}
              onToggleSelect={toggleSelected}
            />
          )}
        </CardContent>
      </Card>

      <PhotoViewerDialog
        item={selected}
        onClose={() => {
          setSelected(null)
          // viewer interactions may have updated sidecars; keep gallery fresh
          void loadGallery()
        }}
      />
    </div>
  )
}
