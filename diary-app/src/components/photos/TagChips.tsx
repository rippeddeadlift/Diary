import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export function TagChips<T extends string>({
  options,
  value,
  onChange,
  hideInactive
}: {
  options: readonly T[]
  value: T[]
  onChange: (next: T[]) => void
  hideInactive?: boolean
}) {
  function toggle(tag: T) {
    const has = value.includes(tag)
    if (has) onChange(value.filter((t) => t !== tag))
    else onChange([...value, tag])
  }

  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const active = value.includes(opt)
        if (hideInactive && !active) return null
        return (
          <button type="button" key={opt} onClick={() => toggle(opt)}>
            <Badge
              variant={active ? 'default' : 'secondary'}
              className={cn('cursor-pointer select-none', active ? '' : 'opacity-80')}
            >
              {opt}
            </Badge>
          </button>
        )
      })}
    </div>
  )
}
