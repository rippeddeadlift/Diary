import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export function TagChips({
  options,
  value,
  onChange
}: {
  options: readonly string[]
  value: string[]
  onChange: (next: string[]) => void
}) {
  function toggle(tag: string) {
    const has = value.includes(tag)
    if (has) onChange(value.filter((t) => t !== tag))
    else onChange([...value, tag])
  }

  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const active = value.includes(opt)
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
