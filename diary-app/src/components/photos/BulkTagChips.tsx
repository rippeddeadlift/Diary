import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export type BulkState = 'off' | 'on' | 'mixed'

export function BulkTagChips<T extends string>({
  options,
  stateOf,
  onToggle
}: {
  options: readonly T[]
  stateOf: (opt: T) => BulkState
  onToggle: (opt: T, current: BulkState) => void
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const st = stateOf(opt)
        const variant = st === 'on' ? 'default' : 'secondary'
        return (
          <button type="button" key={opt} onClick={() => onToggle(opt, st)}>
            <Badge
              variant={variant}
              className={cn(
                'cursor-pointer select-none transition-colors',
                st === 'off' ? 'opacity-80' : '',
                st === 'mixed' ? 'ring-2 ring-ring/60' : ''
              )}
            >
              {opt}
            </Badge>
          </button>
        )
      })}
    </div>
  )
}
