import { Badge } from '@/components/ui/badge'

interface ChipOption<T extends string> {
  key: T
  label: string
}

interface FilterBarProps<TChip extends string, TSort extends string> {
  chips: readonly ChipOption<TChip>[]
  activeChip: TChip
  onChipChange: (chip: TChip) => void
  sorts: readonly ChipOption<TSort>[]
  activeSort: TSort
  onSortChange: (sort: TSort) => void
  onReset: () => void
  className?: string
}

export function FilterBar<TChip extends string, TSort extends string>({
  chips,
  activeChip,
  onChipChange,
  sorts,
  activeSort,
  onSortChange,
  onReset,
  className
}: FilterBarProps<TChip, TSort>) {
  return (
    <div className={className}>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        {chips.map((it) => (
          <button
            key={it.key}
            type="button"
            onClick={() => onChipChange(it.key)}
            className="rounded-md"
          >
            <Badge variant={activeChip === it.key ? 'default' : 'secondary'}>
              {it.label}
            </Badge>
          </button>
        ))}
        <div className="w-4" />
        {sorts.map((it) => (
          <button
            key={it.key}
            type="button"
            onClick={() => onSortChange(it.key)}
            className="rounded-md"
          >
            <Badge variant={activeSort === it.key ? 'default' : 'secondary'}>
              {it.label}
            </Badge>
          </button>
        ))}
        <div className="ml-auto flex gap-2">
          <button
            type="button"
            onClick={onReset}
            className="text-sm text-muted-foreground underline hover:text-foreground"
          >
            Reset
          </button>
        </div>
      </div>
    </div>
  )
}
