import type { GalleryItem } from '@/types/photos'
import { formatDateTimeEU } from '@/lib/format'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { PhotoPointMap } from '@/components/maps/PhotoPointMap'

export function PhotoViewerDialog({
  item,
  onClose
}: {
  item: GalleryItem | null
  onClose: () => void
}) {
  return (
    <Dialog open={!!item} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="p-0">
        {item ? (
          <div className="grid max-h-[90vh] grid-cols-1 overflow-auto sm:grid-cols-2">
            <div className="p-4">
              <div className="overflow-hidden rounded-md border bg-muted">
                <img src={item.url} alt={item.path} className="block h-auto w-full object-contain" />
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                <div className="font-mono break-all">{item.path}</div>
                {item.createdAt ? <div>{formatDateTimeEU(item.createdAt)}</div> : null}
              </div>
            </div>

            <div className="border-t p-4 sm:border-l sm:border-t-0">
              <DialogHeader>
                <DialogTitle className="text-base">Ort</DialogTitle>
              </DialogHeader>
              {item.location ? (
                <div className="mt-3 space-y-2">
                  <div className="overflow-hidden rounded-md border">
                    <PhotoPointMap lat={item.location.lat} lon={item.location.lon} />
                  </div>
                  <div className="font-mono text-xs text-muted-foreground">
                    {item.location.lat.toFixed(6)}, {item.location.lon.toFixed(6)}
                  </div>
                </div>
              ) : (
                <div className="mt-3 text-sm text-muted-foreground">Kein GPS im Foto.</div>
              )}
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
