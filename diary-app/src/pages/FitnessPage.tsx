import { useCallback, useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CounterTracker } from '@/components/fitness/CounterTracker'
import { LogCard } from '@/components/fitness/LogCard'
import { MiniWeekBars } from '@/components/fitness/MiniWeekBars'
import { formatDateEU, getTodayISO,  type SetsRow } from '@/data/setsCsv'
import {  syncFromCSV } from '@/lib/dexie_do/fitness'
import { useLiveQuery } from 'dexie-react-hooks';
import { db } from '@/lib/dexie_do/schema'
type FitnessView = 'dashboard' | 'dips' | 'pullups'



export function FitnessPage() {
  useEffect(() => {
    syncFromCSV();
  }, []);
  const dipsLogs = useLiveQuery(
    () => db.fitnessLogs.where({ exercise: 'dips' }).reverse().sortBy('date')
  ) || [];
  const pullupsLogs = useLiveQuery(
    () => db.fitnessLogs.where({ exercise: 'pullups' }).reverse().sortBy('date')
  ) || [];

  const [view, setView] = useState<FitnessView>('dashboard')

  // Convert Dexie string sets into the array format expected by UI components
  const mappedDipsRows = useMemo(() => dipsLogs.map(log => {
    const sets = log.sets ? log.sets.split(',').map(Number) : []
    return {
      date: log.date,
      sets,
      total: sets.reduce((sum, n) => sum + (isNaN(n) ? 0 : n), 0)
    }
  }), [dipsLogs])

  const mappedPullupsRows = useMemo(() => pullupsLogs.map(log => {
    const sets = log.sets ? log.sets.split(',').map(Number) : []
    return {
      date: log.date,
      sets,
      total: sets.reduce((sum, n) => sum + (isNaN(n) ? 0 : n), 0)
    }
  }), [pullupsLogs])

  const today = getTodayISO()

  // Periodically sync Dexie cache from CSV in background
  const refresh = useCallback(async () => {
    await syncFromCSV();
  }, []);

  useEffect(() => {
    const id = window.setInterval(refresh, 5000);
    const onVis = () => document.visibilityState === 'visible' && refresh();
    document.addEventListener('visibilitychange', onVis);
    return () => {
      window.clearInterval(id);
      document.removeEventListener('visibilitychange', onVis);
    };
  }, [refresh]);

  const dipsToday = useMemo(() => mappedDipsRows.find((r) => r.date === today)?.total ?? 0, [mappedDipsRows, today])
  const pullupsToday = useMemo(() => mappedPullupsRows.find((r) => r.date === today)?.total ?? 0, [mappedPullupsRows, today])


  if (view === 'dips') {
    return (
      <div className="space-y-4">
        <Button variant="outline" size="sm" onClick={() => setView('dashboard')}>
          ← zurück
        </Button>
        <CounterTracker title="Dips" rows={mappedDipsRows} />
      </div>
    )
  }

  if (view === 'pullups') {
    return (
      <div className="space-y-4">
        <Button variant="outline" size="sm" onClick={() => setView('dashboard')}>
          ← zurück
        </Button>
        <CounterTracker title="Pull-ups" rows={mappedPullupsRows} />
      </div>
    )
  }


  return (
    <div className="space-y-6">
      <LogCard onLogged={refresh} />
      {/* {err ? <div className="text-sm text-destructive">{err}</div> : null} */}
      <div className="grid gap-4 sm:grid-cols-2">
        <FitnessTileCard title="Dips" today={dipsToday} rows={mappedDipsRows} todayISO={today} onClick={() => setView('dips')} />
        <FitnessTileCard title="Pull-ups" today={pullupsToday} rows={mappedPullupsRows} todayISO={today} onClick={() => setView('pullups')} />
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
