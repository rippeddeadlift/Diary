import { useEffect, useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { loadDips, type DipsRow, getTodayISO } from '@/data/fitness'

export function FitnessPage() {
  const [rows, setRows] = useState<DipsRow[]>([])
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const refresh = async () => {
      try {
        setErr(null)
        const next = await loadDips()
        if (!cancelled) setRows(next)
      } catch (e: any) {
        if (!cancelled) setErr(e?.message ?? String(e))
      }
    }

    // initial load
    refresh()

    // periodic refresh (simple polling)
    const id = window.setInterval(refresh, 5000)

    // refresh when tab becomes visible again
    const onVis = () => {
      if (document.visibilityState === 'visible') refresh()
    }
    document.addEventListener('visibilitychange', onVis)

    return () => {
      cancelled = true
      window.clearInterval(id)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [])

  const today = getTodayISO()
  const todayCount = useMemo(() => rows.find((r) => r.date === today)?.count ?? 0, [rows, today])

  return (
    <div className="space-y-4">
      {err ? <div className="text-sm text-destructive">{err}</div> : null}

      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle>Fitness</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="text-sm text-muted-foreground">Dips heute ({today})</div>
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
