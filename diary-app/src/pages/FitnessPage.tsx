import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CounterTracker } from '@/components/fitness/CounterTracker'
import { formatDateEU, getTodayISO, loadSetsCsv, type SetsRow } from '@/data/setsCsv'

type FitnessView = 'dashboard' | 'dips' | 'pullups'

const DIPS_PATH = '/fitness/dips.csv'
const PULLUPS_PATH = '/fitness/pullups.csv'

export function FitnessPage() {
  const [view, setView] = useState<FitnessView>('dashboard')

  if (view === 'dips') {
    return (
      <div className="space-y-4">
        <Button variant="outline" size="sm" onClick={() => setView('dashboard')}>
          ← zurück
        </Button>
        <CounterTracker title="Dips" csvPath={DIPS_PATH} />
      </div>
    )
  }

  if (view === 'pullups') {
    return (
      <div className="space-y-4">
        <Button variant="outline" size="sm" onClick={() => setView('dashboard')}>
          ← zurück
        </Button>
        <CounterTracker title="Pull-ups" csvPath={PULLUPS_PATH} />
      </div>
    )
  }

  return <FitnessDashboard onOpenDips={() => setView('dips')} onOpenPullups={() => setView('pullups')} />
}

function FitnessDashboard({ onOpenDips, onOpenPullups }: { onOpenDips: () => void; onOpenPullups: () => void }) {
  const today = getTodayISO()

  const [dipsRows, setDipsRows] = useState<SetsRow[] | null>(null)
  const [pullupsRows, setPullupsRows] = useState<SetsRow[] | null>(null)
  const [err, setErr] = useState<string | null>(null)

  // lightweight polling on the dashboard too
  useMemo(() => {
    let cancelled = false

    const refresh = async () => {
      try {
        setErr(null)
        const [dips, pullups] = await Promise.all([loadSetsCsv(DIPS_PATH), loadSetsCsv(PULLUPS_PATH)])
        if (!cancelled) {
          setDipsRows(dips)
          setPullupsRows(pullups)
        }
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
  }, [])

  const dipsToday = useMemo(() => dipsRows?.find((r) => r.date === today)?.total ?? 0, [dipsRows, today])
  const pullupsToday = useMemo(() => pullupsRows?.find((r) => r.date === today)?.total ?? 0, [pullupsRows, today])

  return (
    <div className="space-y-4">
      
      {err ? <div className="text-sm text-destructive">{err}</div> : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <FitnessTile title="Dips" today={dipsToday} onClick={onOpenDips} />
        <FitnessTile title="Pull-ups" today={pullupsToday} onClick={onOpenPullups} />
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

function FitnessTile({ title, today, onClick }: { title: string; today: number; onClick: () => void }) {
  return (
    <button onClick={onClick} className="text-left">
      <Card className="shadow-sm transition hover:shadow-md">
        <CardHeader>
          <CardTitle className="text-lg">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">Heute</div>
          <div className="text-4xl font-semibold">{today}</div>
        </CardContent>
      </Card>
    </button>
  )
}
