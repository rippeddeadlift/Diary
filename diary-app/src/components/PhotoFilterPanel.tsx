import { Button } from '@/components/ui/button'
import { TagChips } from '@/components/photos/TagChips'
import { PEOPLE, PHOTO_TAGS } from '@/data/tagConfig'
import type { Person, PhotoTag } from '@/data/tagConfig'
import type { TagState } from '@/pages/PhotosPage'  // or define here

interface PhotoFilterPanelProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  peopleFilter: Person[]
  setPeopleFilter: (people: Person[]) => void
  tagFilter: PhotoTag[]
  setTagFilter: (tags: PhotoTag[]) => void
  tagState: 'all' | 'untagged' | 'tagged'
  setTagState: (state: 'all' | 'untagged' | 'tagged') => void
  onReset: () => void
}

export function PhotoFilterPanel({
  open,
  onOpenChange,
  peopleFilter,
  setPeopleFilter,
  tagFilter,
  setTagFilter,
  tagState,
  setTagState,
  onReset
}: PhotoFilterPanelProps) {
  if (!open) return null

  return (
    <div className="space-y-4 rounded-lg border bg-muted/20 p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs text-muted-foreground">Filter</div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onReset}
        >
          Zurücksetzen
        </Button>
      </div>

      <div className="space-y-2">
        <div className="text-xs text-muted-foreground">People</div>
        <TagChips options={PEOPLE} value={peopleFilter} onChange={setPeopleFilter} />
      </div>

      <div className="space-y-2">
        <div className="text-xs text-muted-foreground">Tags</div>
        <TagChips options={PHOTO_TAGS} value={tagFilter} onChange={setTagFilter} />
      </div>

      <div>
        <button
          type="button"
          onClick={() => setTagState((s) => (s === 'all' ? 'untagged' : s === 'untagged' ? 'tagged' : 'all'))}
          className="text-sm text-muted-foreground underline hover:text-foreground"
        >
          {tagState === 'all'
            ? 'Alle'
            : tagState === 'untagged'
              ? 'Nur ungetaggte'
              : 'Nur getaggte'}
        </button>
      </div>
    </div>
  )
}
