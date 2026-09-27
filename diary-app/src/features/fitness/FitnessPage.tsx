import { useCallback, useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CounterTracker } from '@/features/fitness/components/CounterTracker'
import { LogCard } from '@/features/fitness/components/LogCard'
import { MiniWeekBars } from '@/features/fitness/components/MiniWeekBars'
import { formatDateEU, getTodayISO, type SetsRow } from '@/data/setsCsv'
import { loadExerciseRows } from '@/api/fitness'

type FitnessView = 'dashboard' | 'dips' | 'pullups'

export function FitnessPage() {
  const [dipsRows, setDipsRows] = useState<SetsRow[]>([])
  const [pullupsRows, setPullupsRows] = useState<SetsRow[]>([])
  const [view, setView] = useState<FitnessView>('dashboard')
  const [err, setErr] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [dips, pullups] = await Promise.all([
        loadExerciseRows('dips'),
        loadExerciseRows('pullups'),
      ])
      setDipsRows(dips)
      setPullupsRows(pullups)
      setErr(null)
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    const id = window.setInterval(() => void refresh(), 5000)
    const onVis = () => {
      if (document.visibilityState === 'visible') void refresh()
    }
    document.addEventListener('visibilitychange', onVis)
    return () => {
      window.clearInterval(id)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [refresh])

  const today = getTodayISO()
  const dipsToday = useMemo(() => dipsRows.find((r) => r.date === today)?.total ?? 0, [dipsRows, today])
  const pullupsToday = useMemo(() => pullupsRows.find((r) => r.date === today)?.total ?? 0, [pullupsRows, today])

  if (view === 'dips') {
    return (
      <div className="space-y-4">
        <Button variant="outline" size="sm" onClick={() => setView('dashboard')}>
          ← zurück
        </Button>
        <CounterTracker title="Dips" rows={dipsRows} />
      </div>
    )
  }

  if (view === 'pullups') {
    return (
      <div className="space-y-4">
        <Button variant="outline" size="sm" onClick={() => setView('dashboard')}>
          ← zurück
        </Button>
        <CounterTracker title="Pull-ups" rows={pullupsRows} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <LogCard onLogged={refresh} />
      {err ? <div className="text-sm text-destructive">{err}</div> : null}
      <div className="grid gap-4 sm:grid-cols-2">
        <FitnessTileCard title="Dips" today={dipsToday} rows={dipsRows} todayISO={today} onClick={() => setView('dips')} />
        <FitnessTileCard title="Pull-ups" today={pullupsToday} rows={pullupsRows} todayISO={today} onClick={() => setView('pullups')} />
      </div>
      <Card className="border-0 shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Datum</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">{formatDateEU(today)}</CardContent>
      </Card>
    </div>
  )
}

function FitnessTileCard({
  title,
  today,
  rows,
  todayISO,
  onClick
}: {
  title: string
  today: number
  rows: SetsRow[] | null
  todayISO: string
  onClick: () => void
}) {
  return (
    <button onClick={onClick} className="text-left">
      <Card className="shadow-sm transition hover:shadow-md">
        <CardHeader>
          <CardTitle className="text-lg">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Heute</div>
          <div className="text-4xl font-semibold">{today}</div>
          <MiniWeekBars rows={rows} todayISO={todayISO} />
        </CardContent>
      </Card>
    </button>
  )
}
