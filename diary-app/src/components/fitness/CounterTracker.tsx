import { useEffect, useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDateEU, getTodayISO, loadSetsCsv, type SetsRow } from '@/data/setsCsv'

export function CounterTracker({ title, csvPath }: { title: string; csvPath: string }) {
  const [rows, setRows] = useState<SetsRow[]>([])
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const refresh = async () => {
      try {
        setErr(null)
        const next = await loadSetsCsv(csvPath)
        if (!cancelled) setRows(next)
      } catch (e: any) {
        if (!cancelled) setErr(e?.message ?? String(e))
      }
    }

    refresh()

    const id = window.setInterval(refresh, 5000)

    const onVis = () => {
      if (document.visibilityState === 'visible') refresh()
    }
    document.addEventListener('visibilitychange', onVis)

    return () => {
      cancelled = true
      window.clearInterval(id)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [csvPath])

  const today = getTodayISO()
  const todayRow = useMemo(() => rows.find((r) => r.date === today), [rows, today])
  const todayTotal = todayRow?.total ?? 0

  return (
    <div className="space-y-4">
      {err ? <div className="text-sm text-destructive">{err}</div> : null}

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
