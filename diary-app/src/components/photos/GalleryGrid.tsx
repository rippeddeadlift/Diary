import { useEffect, useMemo, useRef, useState } from 'react'
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

  const estimateRowPx = useMemo(() => {
    // Rough estimate: tile size is approx viewportWidth/cols, plus caption.
    const w = Math.max(320, document.documentElement.clientWidth || window.innerWidth || 1024)
    const tile = w / cols
    return Math.round(tile + 48)
  }, [cols])

  const rowVirtualizer = useWindowVirtualizer({
    count: rowCount,
    estimateSize: () => estimateRowPx,
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
                  return (
                    <button
                      type="button"
                      key={it.path}
                      onClick={() => (selectionMode ? onToggleSelect(it) : onSelect(it))}
                      className="group transition-transform duration-200 ease-out transform-gpu hover:scale-105 text-left"
                    >
                      <div className="relative">
                        <LazyThumb url={it.url} alt={it.path} />

                        {/* selection toggle (visible on hover, always visible in selection mode) */}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                            onToggleSelect(it)
                          }}
                          className={
                            "absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-full border text-xs transition-opacity " +
                            (selectionMode ? "opacity-100" : "opacity-0 group-hover:opacity-100") +
                            " " +
                            (isSelected ? "bg-primary text-primary-foreground" : "bg-background/70")
                          }
                          aria-label={isSelected ? 'Auswahl entfernen' : 'Auswählen'}
                          title={isSelected ? 'Auswahl entfernen' : 'Auswählen'}
                        >
                          {isSelected ? '✓' : ''}
                        </button>
                      </div>

                      <div className="flex items-center justify-between gap-2 p-2 text-xs text-muted-foreground">
                        {it.tags?.length || it.people?.length ? null : <span>ungetaggt</span>}
                        {it.createdAt ? <span className="font-mono">{formatDateTimeEU(it.createdAt)}</span> : null}
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          )
      })}
    </div>
  )
}
