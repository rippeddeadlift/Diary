import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from "sonner"

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
      if (!res.ok) {
        const text = await res.text()
        throw new Error(text)
      }
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
          <div className="flex gap-1">
            {EXERCISES.map((ex) => (
              <Button
                key={ex}
                variant={exercise === ex ? 'default' : 'outline'}
                size="sm"
                onClick={() => setExercise(ex)}
                className="flex-1"
              >
                {ex.charAt(0).toUpperCase() + ex.slice(1)}
              </Button>
            ))}
          </div>
        </div>
        <div className="space-y-2">
          <label className="text-xs font-medium">Sets</label>
          <Input
            placeholder="Set Zahl"
            value={sets}
            onChange={(e) => setSets(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && log()}
          />
        </div>
        <Button onClick={log} disabled={busy || !sets.trim()} className="w-full">
          {busy ? 'Logge...' : 'Logge für GAINS'}
        </Button>
      </CardContent>
    </Card>
  )
}
