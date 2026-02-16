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
          className="overflow-hidden rounded-lg border bg-muted text-left"
        >
          <img src={it.url} alt={it.path} loading="lazy" className="block aspect-square w-full object-cover" />
          <div className="flex items-center justify-between gap-2 p-2 text-xs text-muted-foreground">
            <span>{it.hasSidecar ? 'taggable' : 'no json'}</span>
            {it.createdAt ? <span className="font-mono">{formatDateTimeEU(it.createdAt)}</span> : null}
          </div>
        </button>
      ))}
    </div>
  )
}
