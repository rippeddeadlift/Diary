import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from "sonner"
import { saveSet } from '@/lib/dexie_do/fitness'

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
      // NEU: Wir schreiben direkt in die lokale DB. 
      // Der String aus dem Input ("15") wird in eine Zahl umgewandelt.
      await saveSet(exercise, Number(sets.trim()))
      
      // Löst das refresh() / syncFromCSV() in der Parent-Komponente aus
      await onLogged() 
      
      setSets('')
      toast.success('Sets geloggt!')
    } catch (e: any) {
      console.error("error logging fitness", e)
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
