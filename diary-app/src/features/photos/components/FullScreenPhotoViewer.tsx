import { useEffect } from 'react'
import type { GalleryItem } from '@/types/photos'
import { isVideoItem } from '@/lib/media'
import { X, ChevronLeft, ChevronRight } from 'lucide-react'

export function FullScreenPhotoViewer({
  items,
  index,
  onChangeIndex,
  onExit
}: {
  items: GalleryItem[]
  index: number | null
  onChangeIndex: (next: number | null) => void
  onExit: () => void
}) {
  const item = index === null ? null : items[index] ?? null

  function go(delta: number) {
    if (index === null) return
    const next = index + delta
    if (next < 0 || next >= items.length) return
    onChangeIndex(next)
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (index === null) return
      if (e.key === 'ArrowLeft') go(-1)
      if (e.key === 'ArrowRight') go(1)
      if (e.key === 'Escape') onExit()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [index, items.length, onChangeIndex, onExit])

  if (index === null || !item) return null

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black"
      onClick={onExit}
    >
      <div
        className="relative flex h-full w-full items-center justify-center"
        onClick={(e) => e.stopPropagation()}
      >
        {isVideoItem(item) ? (
          <video
            key={item.path}
            src={item.url}
            poster={item.thumbUrl ?? undefined}
            controls
            autoPlay
            playsInline
            className="max-h-[100dvh] max-w-[100vw] bg-black"
          />
        ) : (
          <img
            src={item.url}
            alt={item.path}
            className="max-h-[100dvh] max-w-[100vw] select-none object-contain"
            draggable={false}
          />
        )}

        {/* Close button */}
        <button
          type="button"
          onClick={onExit}
          className="absolute right-4 top-4 rounded-full bg-black/60 p-2 text-white transition hover:bg-black/80 focus:outline-none focus:ring-2 focus:ring-white/50"
          aria-label="Schließen"
          title="Schließen (Esc)"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Counter */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 rounded bg-black/60 px-3 py-1 font-mono text-sm text-white">
          {index + 1} / {items.length}
        </div>

        {/* Prev */}
        <button
          type="button"
          onClick={() => go(-1)}
          disabled={index === 0}
          className="absolute left-4 top-1/2 -translate-y-1/2 rounded bg-black/60 p-3 text-white transition hover:bg-black/80 disabled:cursor-not-allowed disabled:opacity-30 focus:outline-none focus:ring-2 focus:ring-white/50"
          aria-label="Vorheriges Foto"
        >
          <ChevronLeft className="h-6 w-6" />
        </button>

        {/* Next */}
        <button
          type="button"
          onClick={() => go(1)}
          disabled={index === items.length - 1}
          className="absolute right-4 top-1/2 -translate-y-1/2 rounded bg-black/60 p-3 text-white transition hover:bg-black/80 disabled:cursor-not-allowed disabled:opacity-30 focus:outline-none focus:ring-2 focus:ring-white/50"
          aria-label="Nächstes Foto"
        >
          <ChevronRight className="h-6 w-6" />
        </button>
      </div>
    </div>
  )
}

