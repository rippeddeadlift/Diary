import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { PEOPLE, TAGS } from '@/data/tagConfig'
import { BulkTagChips } from '@/components/photos/BulkTagChips'
import type { BulkState } from '@/hooks/useBulkTagging'

export function BulkTagDialog({
  open,
  onOpenChange,
  count,
  busy,
  error,
  bulkStateOf,
  onToggle
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  count: number
  busy: boolean
  error: string | null
  bulkStateOf: (opt: string, kind: 'people' | 'tags') => BulkState
  onToggle: (opt: string, state: BulkState, kind: 'people' | 'tags') => Promise<void>
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="text-base">Bulk Tags</DialogTitle>
          <div className="text-xs text-muted-foreground">{count} Foto(s) ausgewählt</div>
        </DialogHeader>

        <div className="space-y-4">
          <div className="text-xs text-muted-foreground">Chip klicken: AUS/GEMISCHT → alle an, AN → alle aus.</div>

          <div className="space-y-2">
            <div className="text-xs text-muted-foreground">People</div>
            <div className={busy ? 'pointer-events-none opacity-60' : ''}>
              <BulkTagChips
                options={PEOPLE}
                stateOf={(opt) => bulkStateOf(opt, 'people')}
                onToggle={(opt, st) => void onToggle(opt, st, 'people')}
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-xs text-muted-foreground">Tags</div>
            <div className={busy ? 'pointer-events-none opacity-60' : ''}>
              <BulkTagChips
                options={TAGS}
                stateOf={(opt) => bulkStateOf(opt, 'tags')}
                onToggle={(opt, st) => void onToggle(opt, st, 'tags')}
              />
            </div>
          </div>

          <div className="text-xs text-muted-foreground">{busy ? 'Speichern…' : 'Bereit'}</div>
          {error ? <div className="text-sm text-destructive">{error}</div> : null}
        </div>
      </DialogContent>
    </Dialog>
  )
}
