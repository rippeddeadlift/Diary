import { useEffect, useState } from 'react'
import type { Trip } from '../../data/trips'
import { loadTripNotes } from '../../data/trips'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function Notes({ trip }: { trip: Trip }) {
  const [text, setText] = useState<string>('')
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    ;(async () => {
      try {
        setErr(null)
        setText(await loadTripNotes(trip))
      } catch (e: any) {
        setErr(e?.message ?? String(e))
      }
    })()
  }, [trip])

  if (err) return <div className="text-sm text-destructive">{err}</div>
  if (!text) return null

  return (
    <Card>
      <CardHeader className="py-2">
        <CardTitle className="text-base">Notizen</CardTitle>
      </CardHeader>
      <CardContent>
        <pre className="m-0 whitespace-pre-wrap">{text}</pre>
      </CardContent>
    </Card>
  )
}
