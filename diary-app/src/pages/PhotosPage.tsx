import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { GalleryItem } from '@/types/photos'
import { useGallery } from '@/hooks/useGallery'
import { GalleryGrid } from '@/components/photos/GalleryGrid'
import { PhotoViewerDialog } from '@/components/photos/PhotoViewerDialog'
import { PhotoUploadCard } from '@/components/photos/PhotoUploadCard'

export function PhotosPage() {
  const { items: gallery, error: galleryErr, reload: loadGallery } = useGallery()

  const [selected, setSelected] = useState<GalleryItem | null>(null)

  return (
    <div className="space-y-4">
      <PhotoUploadCard onUploaded={loadGallery} />

      <div className="flex justify-end">
        <Button variant="outline" onClick={loadGallery}>
          Reload Galerie
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Galerie</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {galleryErr ? <div className="text-sm text-destructive">{galleryErr}</div> : null}

          {gallery.length === 0 ? (
            <div className="text-sm text-muted-foreground">Noch keine Fotos gefunden. (Oder Backend läuft nicht.)</div>
          ) : (
            <GalleryGrid items={gallery} onSelect={setSelected} />
          )}
        </CardContent>
      </Card>

      <PhotoViewerDialog item={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
