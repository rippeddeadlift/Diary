import { useEffect, useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getTodayISO, loadCounterCsv, type CounterRow } from '@/data/counterCsv'

export function CounterTracker({ title, csvPath }: { title: string; csvPath: string }) {
  const [rows, setRows] = useState<CounterRow[]>([])
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const refresh = async () => {
      try {
        setErr(null)
        const next = await loadCounterCsv(csvPath)
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
  const todayCount = useMemo(() => rows.find((r) => r.date === today)?.count ?? 0, [rows, today])

  return (
    <div className="space-y-4">
      {err ? <div className="text-sm text-destructive">{err}</div> : null}

      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="text-sm text-muted-foreground">Heute ({today})</div>
          <div className="text-4xl font-semibold">{todayCount}</div>
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
                <div key={r.date} className="flex items-center justify-between p-3">
                  <div className="font-mono text-sm">{r.date}</div>
                  <div className="text-sm font-semibold">{r.count}</div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
