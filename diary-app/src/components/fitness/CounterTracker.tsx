import { useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDateEU, getTodayISO, type SetsRow } from '@/data/setsCsv'

// NEU: Statt csvPath erwarten wir nun direkt die fertig berechneten "rows"
export function CounterTracker({ title, rows }: { title: string; rows: SetsRow[] }) {
  const today = getTodayISO()
  const todayRow = useMemo(() => rows.find((r) => r.date === today), [rows, today])
  const todayTotal = todayRow?.total ?? 0

  return (
    <div className="space-y-4">
      {/* Das UI bleibt exakt gleich, aber der ganze Fehler- und Polling-Code (useEffect) ist weg! */}
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="text-sm text-muted-foreground">Heute ({formatDateEU(today)})</div>
          <div className="text-4xl font-semibold">{todayTotal}</div>
          {todayRow?.sets?.length ? (
            <div className="text-sm text-muted-foreground">Sets: {todayRow.sets.join(' / ')}</div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Verlauf</CardTitle>
        </CardHeader>
        <CardContent>
          {rows.length === 0 ? (
            <div className="text-sm text-muted-foreground">Noch keine Einträge.</div>
          ) : (
            <div className="divide-y rounded-lg border">
              {rows.map((r) => (
                <div key={r.date} className="flex items-start justify-between gap-3 p-3">
                  <div className="font-mono text-sm">{formatDateEU(r.date)}</div>
                  <div className="text-right">
                    <div className="text-sm font-semibold">{r.total}</div>
                    {r.sets.length ? <div className="text-xs text-muted-foreground">{r.sets.join(' / ')}</div> : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}