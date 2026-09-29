import { memo, useEffect, useMemo, useRef, useState } from 'react'
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
  const tagCount = (it.people?.length ?? 0) + (it.tags?.length ?? 0)
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
        <span>{tagCount} {tagCount === 1 ? 'tag' : 'tags'}</span>
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
  onToggleSelect,
  sortMode = 'date'
}: {
  items: GalleryItem[]
  onSelect: (it: GalleryItem) => void
  selectionMode: boolean
  selected: Set<string>
  onToggleSelect: (it: GalleryItem) => void
  sortMode?: 'date' | 'added'
}) {
  const cols = useGalleryColumns()
  const gridRef = useRef<HTMLDivElement>(null)
  const timelineRef = useRef<HTMLDivElement>(null)
  const [activeIndex, setActiveIndex] = useState(0)
  const [timelineFocused, setTimelineFocused] = useState(false)
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  const rowCount = Math.ceil(items.length / cols)
  const timelineDateOf = (item: GalleryItem) => sortMode === 'added' ? item.addedAt : item.createdAt

  const rowVirtualizer = useWindowVirtualizer({
    count: rowCount,
    estimateSize: () => 280,
    overscan: 2
  })

  const virtualRows = rowVirtualizer.getVirtualItems()

  const dateMarks = useMemo(() => {
    const marks: { index: number; key: string; label: string; year: string }[] = []
    let previousMonth = ''
    let hasUndated = false

    items.forEach((it, index) => {
      const timelineDate = timelineDateOf(it)
      if (!timelineDate) {
        if (!hasUndated) {
          marks.push({ index, key: 'undated', label: 'Ohne Datum', year: '' })
          hasUndated = true
        }
        return
      }

      const date = new Date(timelineDate)
      if (Number.isNaN(date.getTime())) return

      const key = `${date.getFullYear()}-${date.getMonth()}`
      if (key !== previousMonth) {
        marks.push({
          index,
          key,
          label: date.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' }),
          year: String(date.getFullYear())
        })
        previousMonth = key
      }
    })

    return marks
  }, [items, sortMode])

  const currentItem = items[Math.min(activeIndex, Math.max(items.length - 1, 0))]
  const currentTimelineDate = currentItem ? timelineDateOf(currentItem) : null
  const currentDate = currentTimelineDate ? new Date(currentTimelineDate) : null
  const currentLabel = currentDate && !Number.isNaN(currentDate.getTime())
    ? currentDate.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' })
    : 'Ohne Datum'
  const previewIndex = hoveredIndex ?? Math.min(activeIndex, Math.max(items.length - 1, 0))
  const previewPercentage = items.length > 1 ? (previewIndex / (items.length - 1)) * 100 : 0
  const previewTimelineDate = items[previewIndex] ? timelineDateOf(items[previewIndex]) : null
  const previewDate = previewTimelineDate ? new Date(previewTimelineDate) : null
  const previewLabel = previewDate && !Number.isNaN(previewDate.getTime())
    ? previewDate.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' })
    : 'Ohne Datum'

  function scrollToItem(index: number) {
    const nextIndex = Math.max(0, Math.min(index, items.length - 1))
    setActiveIndex(nextIndex)
    rowVirtualizer.scrollToIndex(Math.floor(nextIndex / cols), { align: 'start' })
  }

  function scrollToTimelinePosition(clientY: number) {
    const track = timelineRef.current
    if (!track || items.length === 0) return
    const bounds = track.getBoundingClientRect()
    const ratio = Math.max(0, Math.min(1, (clientY - bounds.top) / bounds.height))
    scrollToItem(Math.round(ratio * (items.length - 1)))
  }
  const getIndexFromClientY = (clientY: number) => {
    if (!timelineRef.current || items.length === 0) return 0
    const rect = timelineRef.current.getBoundingClientRect()
    const relativeY = Math.max(0, Math.min(clientY - rect.top, rect.height))
    const percentage = relativeY / rect.height
    return Math.round(percentage * (items.length - 1))
  }

  useEffect(() => {
    const updateActiveIndex = () => {
      const rows = gridRef.current?.querySelectorAll<HTMLElement>('[data-gallery-row]')
      if (!rows?.length) return

      const anchor = window.innerHeight * 0.4
      const visibleRow = Array.from(rows).find((row) => row.getBoundingClientRect().bottom > anchor)
      const rowIndex = Number((visibleRow ?? rows[rows.length - 1]).dataset.galleryRowIndex)
      const nextIndex = Math.min(rowIndex * cols, items.length - 1)
      setActiveIndex((current) => current === nextIndex ? current : nextIndex)
    }

    let frame = 0
    const onScroll = () => {
      window.cancelAnimationFrame(frame)
      frame = window.requestAnimationFrame(updateActiveIndex)
    }

    updateActiveIndex()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.cancelAnimationFrame(frame)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [cols, items])

  return (
    <div className="relative w-full">
      <div
        ref={gridRef}
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
              data-gallery-row
              data-gallery-row-index={rowIndex}
              className="absolute left-0 w-full"
              style={{ transform: `translateY(${vr.start}px)` }}
            >
              <div
                className="grid w-full gap-2"
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

      {items.length > 0 && sortMode === 'date' ? (
        <aside className="fixed right-3 top-[20vh] z-40 h-[60vh] w-9 select-none sm:right-4 sm:w-11">
          <div
            ref={timelineRef}
            role="slider"
            tabIndex={0}
            aria-valuemin={0}
            aria-valuemax={items.length - 1}
            aria-valuenow={Math.min(activeIndex, items.length - 1)}
            aria-valuetext={currentLabel}
            className="absolute inset-0 cursor-pointer touch-none rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onPointerDown={(event) => {
              event.currentTarget.setPointerCapture(event.pointerId)
              setTimelineFocused(true)
              setHoveredIndex(getIndexFromClientY(event.clientY))
              scrollToTimelinePosition(event.clientY)
            }}
            onPointerMove={(event) => {
              setHoveredIndex(getIndexFromClientY(event.clientY))
              if (event.currentTarget.hasPointerCapture(event.pointerId)) {
                scrollToTimelinePosition(event.clientY)
              }
            }}
            onPointerUp={(event) => {
              event.currentTarget.releasePointerCapture(event.pointerId)
            }}
            onPointerCancel={() => setTimelineFocused(false)}
            onPointerEnter={() => setTimelineFocused(true)}
            onPointerLeave={(event) => {
              if (!event.currentTarget.hasPointerCapture(event.pointerId)) {
                setTimelineFocused(false)
                setHoveredIndex(null)
              }
            }}
            onFocus={() => setTimelineFocused(true)}
            onBlur={() => setTimelineFocused(false)}
          >
            <div className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-border" />
            {dateMarks.map((mark) => (
              <div
                key={mark.key}
                aria-hidden="true"
                className="absolute left-1/2 flex -translate-x-1/2 items-center"
                style={{ top: `${items.length > 1 ? (mark.index / (items.length - 1)) * 100 : 0}%` }}
              >
                <span className={mark.year ? 'h-px w-2 bg-muted-foreground' : 'h-px w-1 bg-border'} />
                {mark.year && mark.index === dateMarks.find((entry) => entry.year === mark.year)?.index ? (
                  <span className="absolute right-3 text-[9px] leading-none text-muted-foreground sm:right-4 sm:text-[10px]">
                    {mark.year}
                  </span>
                ) : null}
              </div>
            ))}
            <div
              aria-hidden="true"
              className="absolute left-1/2 h-0.5 w-10 -translate-x-1/2 -translate-y-1/2 bg-primary shadow"
              style={{ top: `${previewPercentage}%` }}
            />
            {timelineFocused && previewLabel ? (
              <span
                aria-hidden="true"
                className="pointer-events-none absolute right-full mr-2 -translate-y-1/2 whitespace-nowrap rounded border bg-background px-2 py-1 text-xs text-foreground shadow"
                style={{ top: `${previewPercentage}%` }}
              >
                {previewLabel}
              </span>
            ) : null}
          </div>
        </aside>
      ) : null}
    </div>
  )
}
