import type { GalleryItem } from '@/types/photos'
import { formatDateTimeEU } from '@/lib/format'

export function GalleryGrid({ items, onSelect }: { items: GalleryItem[]; onSelect: (it: GalleryItem) => void }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
      {items.map((it) => (
        <button
          type="button"
          key={it.path}
          onClick={() => onSelect(it)}
          className="transition-transform duration-200 ease-out transform-gpu hover:scale-105 "
        >
          <img src={it.url} alt={it.path} loading="lazy" className="block aspect-square w-full object-cover" />
          <div className="flex items-center justify-between gap-2 p-2 text-xs text-muted-foreground">
            {it.tags?.length || it.people?.length ? null : <span>ungetaggt</span>}
            {it.createdAt ? <span className="font-mono">{formatDateTimeEU(it.createdAt)}</span> : null}
          </div>
        </button>
      ))}
    </div>
  )
}
