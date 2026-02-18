import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '@/components/ui/alert-dialog'

export function SelectionBar({
  count,
  onSelectAll,
  onClear,
  onShare,
  onTrash,
  onOpenTags,
  onDone
}: {
  count: number
  onSelectAll: () => void
  onClear: () => void
  onShare: () => Promise<void> | void
  onTrash: () => Promise<void> | void
  onOpenTags: () => void
  onDone: () => void
}) {
  const [trashOpen, setTrashOpen] = useState(false)
  return (
    <div className="fixed inset-x-0 bottom-0 z-40 border-t bg-background/95 p-3 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-2">
        <div className="text-sm">
          <span className="font-semibold">{count}</span> ausgewählt
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onSelectAll}>
            Alle
          </Button>
          <Button variant="outline" size="sm" onClick={onClear}>
            Leeren
          </Button>
          <Button variant="outline" size="sm" onClick={onShare} disabled={count === 0}>
            Teilen
          </Button>
          <Button variant="destructive" size="sm" onClick={() => setTrashOpen(true)} disabled={count === 0}>
            Löschen
          </Button>
          <Button variant="default" size="sm" onClick={onOpenTags} disabled={count === 0}>
            Tags
          </Button>
          <Button variant="outline" size="sm" onClick={onDone}>
            Fertig
          </Button>
        </div>
      </div>

      <AlertDialog open={trashOpen} onOpenChange={setTrashOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>In den Papierkorb verschieben?</AlertDialogTitle>
            <AlertDialogDescription>
              {count} Foto(s) werden nach <span className="font-mono">data/photos/_trash/…</span> verschoben und aus der Galerie entfernt.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Abbrechen</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                setTrashOpen(false)
                await onTrash()
              }}
            >
              In Papierkorb
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
