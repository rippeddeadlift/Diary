import { useEffect, useRef, useState } from 'react'
import { useWindowVirtualizer } from '@tanstack/react-virtual'

import type { GalleryItem } from '@/types/photos'
import { formatDateTimeEU } from '@/lib/format'
import { useGalleryColumns } from '@/hooks/useGalleryColumns'

function LazyThumb({ url, alt }: { url: string; alt: string }) {
  const ref = useRef<HTMLDivElement | null>(null)
  const [show, setShow] = useState(false)

  useEffect(() => {
    if (show) return
    const el = ref.current
    if (!el) return

    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            setShow(true)
            obs.disconnect()
            break
          }
        }
      },
      { root: null, rootMargin: '600px' }
    )

    obs.observe(el)
    return () => obs.disconnect()
  }, [show])

  return (
    <div ref={ref} className="block aspect-square w-full bg-muted">
      {show ? (
        <img src={url} alt={alt} loading="lazy" decoding="async" className="block aspect-square w-full object-cover" />
      ) : null}
    </div>
  )
}

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
    overscan: 3
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
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
              {rowItems.map((it) => {
                const isSelected = selected.has(it.path)
                const imgUrl = it.thumbExists && it.thumbUrl ? it.thumbUrl : it.url
                return (
                  <div key={it.path} className="group relative transition-all hover:scale-[1.02]">
                    {/* Tile clickable */}
                    <div
                      role="button"
                      tabIndex={0}
                      className="block cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring rounded overflow-hidden"
                      onClick={() => selectionMode ? onToggleSelect(it) : onSelect(it)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          selectionMode ? onToggleSelect(it) : onSelect(it)
                        }
                      }}
                    >
                      <LazyThumb url={imgUrl} alt={it.path} />
                    </div>

                    {/* Hover/selection circle (precise toggle, always hover-visible) */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        onToggleSelect(it)
                      }}
                      className={
                        "absolute right-2 top-2 z-20 flex h-8 w-8 items-center justify-center rounded-full border-2 shadow-md backdrop-blur transition-all " +
                        (selectionMode 
                          ? "opacity-100 border-primary bg-primary/90 text-primary-foreground hover:scale-110" 
                          : "opacity-0 group-hover:opacity-100 border-muted bg-background/80 hover:bg-accent"
                        )
                      }
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
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
