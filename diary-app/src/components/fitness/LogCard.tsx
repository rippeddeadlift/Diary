import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from 'sonner'

const EXERCISES = ['dips', 'pullups'] as const
type Exercise = (typeof EXERCISES)[number]

interface LogCardProps {
  onLogged: () => Promise<void>
}

export function LogCard({ onLogged }: LogCardProps) {
  const [exercise, setExercise] = useState<Exercise>('pullups')
  const [sets, setSets] = useState('')
  const [busy, setBusy] = useState(false)

  const log = async () => {
    if (!sets.trim()) return
    setBusy(true)
    try {
      const res = await fetch('/api/fitness/log', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ exercise, sets: sets.trim() })
      })
      if (!res.ok) throw new Error(await res.text())
      await onLogged()
      setSets('')
      toast.success('Sets geloggt!')
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Neue Sets loggen</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <label className="text-xs font-medium">Exercise</label>
          <Select value={exercise} onValueChange={(v) => setExercise(v as Exercise)}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {EXERCISES.map((ex) => (
                <SelectItem key={ex} value={ex}>{ex}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <label className="text-xs font-medium">Sets (comma reps oder +N)</label>
          <Input
            placeholder="8,7,6 oder +7"
            value={sets}
            onChange={(e) => setSets(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && log()}
          />
          <div className="text-xs text-muted-foreground">Beispiel: "10" oder "12,11,10" oder "+5"</div>
        </div>
        <Button onClick={log} disabled={busy || !sets.trim()} className="w-full">
          {busy ? 'Logge...' : 'Loggen'}
        </Button>
      </CardContent>
    </Card>
  )
}
