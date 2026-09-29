import { useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { GalleryItem } from '@/types/photos'
import { useGallery } from './hooks/useGallery'
import { GalleryGrid } from './components/GalleryGrid'
import { PhotoViewerDialog } from './components/PhotoViewerDialog'
import { PhotoUploadCard } from './components/PhotoUploadCard'
import { Button } from '@/components/ui/button'
import { ArrowDownWideNarrow, Filter } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { TagChips } from './components/TagChips'
import { BulkTagDialog } from './components/BulkTagDialog'
import { SelectionBar } from './components/SelectionBar'
import { useBulkSelection } from './hooks/useBulkSelection'
import { useBulkTagging } from './hooks/useBulkTagging'
import { PEOPLE, PHOTO_TAGS } from '@/data/tagConfig'
import type { Person, PhotoTag } from '@/data/tagConfig'
import { trashPhotos } from '@/api/photos'
import { cn } from '@/lib/utils'

export function PhotosPage() {
  const { items: gallery, loading: galleryLoading, loadingMore, error: galleryErr, reload: loadGallery } = useGallery()
  const [showOnlyWithLocation, setShowOnlyWithLocation] = useState(false);


  const [viewerIndex, setViewerIndex] = useState<number | null>(null)
  const [bulkOpen, setBulkOpen] = useState(false)
  const [sharePreparing, setSharePreparing] = useState(false)
  const [shareStatus, setShareStatus] = useState<string | null>(null)

  const { selectionMode, selectedPaths, toggleSelected, clearSelected, selectAllFiltered } = useBulkSelection()

  const { busy: bulkBusy, error: bulkErr, bulkStateOf, toggleBulk } = useBulkTagging({
    gallery,
    selectedPaths,
    reload: loadGallery
  })

  const [filtersOpen, setFiltersOpen] = useState(false)
  const [peopleFilter, setPeopleFilter] = useState<Person[]>([])
  const [tagFilter, setTagFilter] = useState<PhotoTag[]>([])
  const [tagState, setTagState] = useState<'all' | 'untagged' | 'tagged'>('all')
  const [sortMode, setSortMode] = useState<'date' | 'added'>('date')

  const filtered = useMemo(() => {
    const matching = gallery.filter((it) => {
      // 📍 NEU: Standort-Check (zuerst, da er am schnellsten filtert)
      if (showOnlyWithLocation && (!it.location?.lat || !it.location?.lon)) {
        return false
      }

      const people = it.people ?? []
      const tags = it.tags ?? []

      if (tagState === 'untagged' && (people.length > 0 || tags.length > 0)) return false
      if (tagState === 'tagged' && people.length === 0 && tags.length === 0) return false

      // AND semantics: all selected people/tags must be present
      for (const p of peopleFilter) if (!people.includes(p)) return false
      for (const t of tagFilter) if (!tags.includes(t)) return false

      return true
    })

    if (sortMode === 'added') {
      matching.sort((a, b) => {
        const addedA = Date.parse(a.addedAt ?? '')
        const addedB = Date.parse(b.addedAt ?? '')
        if (Number.isNaN(addedA)) return Number.isNaN(addedB) ? 0 : 1
        if (Number.isNaN(addedB)) return -1
        return addedB - addedA
      })
    }
    return matching
  }, [gallery, peopleFilter, tagFilter, tagState, showOnlyWithLocation, sortMode])

  const selectedItems = useMemo(() => {
    const itemsByPath = new Map(filtered.map((it) => [it.path, it] as const))
    return Array.from(selectedPaths).map((path) => itemsByPath.get(path)).filter(Boolean) as GalleryItem[]
  }, [filtered, selectedPaths])

  return (
    <div className="space-y-4">
      <PhotoUploadCard onUploaded={loadGallery} />
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">Galerie</CardTitle>
              <div className="text-xs text-muted-foreground">
                {filtered.length} Fotos und Videos 
                {loadingMore ? ' …' : ''}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <ArrowDownWideNarrow className="mr-2 h-4 w-4" /> Sortieren
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>Sortieren nach</DropdownMenuLabel>
                  <DropdownMenuRadioGroup
                    value={sortMode}
                    onValueChange={(value) => {
                      if (value === 'date' || value === 'added') setSortMode(value)
                    }}
                  >
                    <DropdownMenuRadioItem value="date">Aufnahmedatum</DropdownMenuRadioItem>
                    <DropdownMenuRadioItem value="added">Zuletzt hinzugefügt</DropdownMenuRadioItem>
                  </DropdownMenuRadioGroup>
                </DropdownMenuContent>
              </DropdownMenu>
              <Button variant="outline" size="sm" onClick={() => setFiltersOpen((v) => !v)}>
                <Filter className="mr-2 h-4 w-4" /> Filter
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {filtersOpen ? (
            <div className="space-y-4 rounded-lg border bg-muted/20 p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="text-xs text-muted-foreground">Filter</div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setPeopleFilter([])
                    setTagFilter([])
                    setTagState('all')
                    setShowOnlyWithLocation(false) // 📍 Hinzugefügt
                  }}
                >
                  Zurücksetzen
                </Button>
              </div>

              <div className="space-y-2">
                <div className="text-xs text-muted-foreground">People</div>
                <TagChips options={PEOPLE} value={peopleFilter} onChange={setPeopleFilter} />
              </div>

              <div className="space-y-2">
                <div className="text-xs text-muted-foreground">Tags</div>
                <TagChips options={PHOTO_TAGS} value={tagFilter} onChange={setTagFilter} />
              </div>

              <div>
                <button
                  type="button"
                  onClick={() =>
                    setTagState((s) => (s === 'all' ? 'untagged' : s === 'untagged' ? 'tagged' : 'all'))
                  }
                  className="text-sm text-muted-foreground underline"
                >
                  {tagState === 'all'
                    ? 'Alle'
                    : tagState === 'untagged'
                      ? 'keine tags'
                      : 'mind. 1 tag'}
                </button>
              </div>
              <div className="pt-2 border-t">
                <button
                  type="button"
                  onClick={() => setShowOnlyWithLocation(!showOnlyWithLocation)}
                  className={cn(
                    "text-sm transition-colors flex items-center gap-2",
                    showOnlyWithLocation ? "text-primary font-bold" : "text-muted-foreground underline"
                  )}
                >
                  <span>📍</span>
                  {showOnlyWithLocation ? 'Nur mit Standort' : 'Standort egal'}
                </button>
              </div>
            </div>
          ) : null}
          {galleryErr ? <div className="text-sm text-destructive">{galleryErr}</div> : null}

          {galleryLoading && gallery.length === 0 ? (
            <div className="text-sm text-muted-foreground">Fotos werden geladen…</div>
          ) : filtered.length === 0 ? (
            <div className="text-sm text-muted-foreground">Keine Fotos gefunden (Filter?).</div>
          ) : (
            <GalleryGrid
              items={filtered}
              onSelect={(it) => setViewerIndex(filtered.findIndex((x) => x.path === it.path))}
              selectionMode={selectionMode}
              selected={selectedPaths}
              onToggleSelect={toggleSelected}
              sortMode={sortMode}
            />
          )}
        </CardContent>
      </Card>

      <PhotoViewerDialog
        items={filtered}
        index={viewerIndex}
        onChangeIndex={setViewerIndex}
        onClose={() => setViewerIndex(null)}
      />

      {selectionMode ? (
        <>
          <SelectionBar
            count={selectedPaths.size}
            shareBusy={sharePreparing}
            shareStatus={shareStatus}
            onSelectAll={() => selectAllFiltered(filtered)}
            onClear={clearSelected}
            onShare={async () => {
              if (selectedItems.length === 0) return
              const nav: any = navigator
              if (!window.isSecureContext || !nav?.share) {
                setShareStatus('Dieser Browser unterstützt kein direktes Dateiteilen. Öffne Diary in Chrome/Edge oder auf dem Smartphone über HTTPS; dort zeigt das System verfügbare Apps wie E-Mail, WhatsApp oder Telegram an.')
                return
              }

              setSharePreparing(true)
              setShareStatus('Dateien werden vorbereitet…')
              try {
                const files: File[] = []
                if (selectedItems.length <= 20) {
                  for (const it of selectedItems) {
                    const res = await fetch(it.url)
                    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
                    const blob = await res.blob()
                    const name = it.path.split('/').pop() || 'photo'
                    files.push(new File([blob], name, { type: blob.type || 'image/jpeg' }))
                  }
                } else {
                  const { zipSync } = await import('fflate')
                  const entries: Record<string, Uint8Array> = {}
                  for (const it of selectedItems) {
                    const res = await fetch(it.url)
                    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
                    entries[it.path.split('/').pop() || 'photo'] = new Uint8Array(await res.arrayBuffer())
                  }
                  const zipped = zipSync(entries, { level: 0 })
                  const date = new Date().toISOString().slice(0, 10)
                  files.push(new File([zipped.slice().buffer], `fotos_${date}.zip`, { type: 'application/zip' }))
                }
                if (nav.canShare && !nav.canShare({ files })) {
                  setShareStatus('Dieser Browser kann diese Datei(en) nicht direkt teilen.')
                  return
                }
                await nav.share({ files, title: `Fotos (${files.length})` })
                setShareStatus(null)
              } catch (e: any) {
                setShareStatus(e?.name === 'AbortError' ? 'Teilen abgebrochen.' : e?.message ?? 'Teilen fehlgeschlagen.')
              } finally {
                setSharePreparing(false)
              }
            }}
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
