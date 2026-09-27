import type { SetsRow } from '@/data/setsCsv'

function lastNDaysISO(n: number): string[] {
  const out: string[] = []
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  for (let i = n - 1; i >= 0; i--) {
    const x = new Date(d)
    x.setDate(d.getDate() - i)
    const yyyy = x.getFullYear()
    const mm = String(x.getMonth() + 1).padStart(2, '0')
    const dd = String(x.getDate()).padStart(2, '0')
    out.push(`${yyyy}-${mm}-${dd}`)
  }
  return out
}

export function MiniWeekBars({ rows, todayISO }: { rows: SetsRow[] | null; todayISO: string }) {
  const days = lastNDaysISO(7)
  const totals = days.map((day) => rows?.find((r) => r.date === day)?.total ?? 0)
  const max = Math.max(1, ...totals)

  return (
    <div className="mt-3 flex items-end gap-1">
      {days.map((day, idx) => {
        const v = totals[idx]
        const h = Math.round((v / max) * 24) // px
        const isToday = day === todayISO
        return (
          <div
            key={day}
            className={
              'w-2 rounded-sm ' +
              (isToday ? 'bg-primary' : 'bg-muted-foreground/30')
            }
            style={{ height: Math.max(2, h) }}
            title={`${day}: ${v}`}
          />
        )
      })}
    </div>
  )
}
