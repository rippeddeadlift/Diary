import { Button } from '@/components/ui/button'

export function SelectionBar({
  count,
  onSelectAll,
  onClear,
  onTrash,
  onOpenTags,
  onDone
}: {
  count: number
  onSelectAll: () => void
  onClear: () => void
  onTrash: () => void
  onOpenTags: () => void
  onDone: () => void
}) {
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
          <Button variant="destructive" size="sm" onClick={onTrash} disabled={count === 0}>
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
    </div>
  )
}
