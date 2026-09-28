import { memo, useEffect, useState } from 'react'
import { useWindowVirtualizer } from '@tanstack/react-virtual'

import type { GalleryItem } from '@/types/photos'
import { isVideoItem } from '@/lib/media'
import { formatDateTimeEU } from '@/lib/format'
import { useGalleryColumns } from '../hooks/useGalleryColumns'
import { cn } from '@/lib/utils'


const PhotoCard = memo(({
  it, isSelected, imgUrl, selectionMode, onToggleSelect, onSelect
}: {
  it: GalleryItem; isSelected: boolean; imgUrl: string;
  selectionMode: boolean; onToggleSelect: (it: GalleryItem) => void; onSelect: (it: GalleryItem) => void
}) => {
  const [src, setSrc] = useState<string | undefined>(undefined)
  useEffect(() => {
    setSrc(imgUrl)
  }, [imgUrl])
  return (
    <div className="group relative transition-all">
      {/* Tile clickable */}
      <div
        role="button"
        tabIndex={0}
        className={cn(
          "block cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring rounded overflow-hidden",
          selectionMode ? "hover:bg-muted/50" : ""
        )}
        onClick={() => selectionMode ? onToggleSelect(it) : onSelect(it)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            selectionMode ? onToggleSelect(it) : onSelect(it)
          }
        }}
      >
        {src ? (
          <img
            src={src}
            alt={it.path}
            decoding="async"
            className="block aspect-square w-full object-cover bg-muted opacity-100 transition-opacity duration-300"
          />
        ) : (
          <div className="flex aspect-square w-full items-center justify-center bg-muted text-xs text-muted-foreground">
            {isVideoItem(it) ? 'Video' : ''}
          </div>
        )}
        {isVideoItem(it) ? (
          <span className="pointer-events-none absolute bottom-10 left-2 rounded bg-black/70 px-1.5 py-0.5 text-[10px] font-medium text-white">
            ▶ Video
          </span>
        ) : null}
      </div>

      {/* Hover/selection circle */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation()
          onToggleSelect(it)
        }}
        className={cn(
          "absolute right-2 top-2 z-20 flex h-8 w-8 items-center justify-center rounded-full border-2 shadow-md backdrop-blur transition-all duration-200",
          selectionMode
            ? [
              "scale-110 border-black/90 bg-black/80 opacity-100 shadow-xl group-hover:bg-white/80",
              isSelected ? "group-hover:text-black" : ""
            ]
            : "opacity-0 group-hover:opacity-100 bg-black/50 border-black text-black"
        )}
        aria-label={isSelected ? 'Auswahl entfernen' : 'Auswählen'}
        title={isSelected ? 'Auswahl entfernen' : 'Auswählen'}
      >
        {isSelected ? '✓' : ''}
      </button>

      <div className="flex items-center justify-between gap-2 p-2 text-xs text-muted-foreground">
        {it.tags?.length || it.people?.length ? null : <span>0 tags</span>}
        {it.createdAt ? <span className="font-mono">{formatDateTimeEU(it.createdAt)}</span> : null}
      </div>
    </div>
  )
})
export function GalleryGrid({
  items,
  onSelect,
  selectionMode,
  selected,
  onToggleSelect
}: {
  items: GalleryItem[]
  onSelect: (it: GalleryItem) => void
  selectionMode: boolean
  selected: Set<string>
  onToggleSelect: (it: GalleryItem) => void
}) {
  const cols = useGalleryColumns()

  const rowCount = Math.ceil(items.length / cols)

  const rowVirtualizer = useWindowVirtualizer({
    count: rowCount,
    estimateSize: () => 280,
    overscan: 2  
  })

  const virtualRows = rowVirtualizer.getVirtualItems()

  return (
    <div
      className="relative w-full"
      style={{ height: `${rowVirtualizer.getTotalSize()}px` }}
    >
      {virtualRows.map((vr) => {
        const rowIndex = vr.index
        const start = rowIndex * cols
        const rowItems = items.slice(start, start + cols)

        return (
          <div
            key={vr.key}
            className="absolute left-0 w-full"
            style={{ transform: `translateY(${vr.start}px)` }}
          >
            <div
              className="grid gap-2 w-full"
              style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
            >
              {rowItems.map((it) => {
                const isSelected = selected.has(it.path)
                const imgUrl = it.thumbExists && it.thumbUrl ? it.thumbUrl : isVideoItem(it) ? '' : it.url

                return (
                  <PhotoCard
                    key={it.path}
                    it={it}
                    isSelected={isSelected}
                    imgUrl={imgUrl}
                    selectionMode={selectionMode}
                    onToggleSelect={onToggleSelect}
                    onSelect={onSelect}
                  />
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
