import { useEffect, useState } from 'react'
import type { Trip } from '../../data/trips'
import { loadTripNotes } from '../../data/trips'

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

  if (err) return <div style={{ color: 'crimson' }}>{err}</div>
  if (!text) return null

  return (
  <div style={{ border: '1px solid rgba(0,0,0,0.12)', borderRadius: 12, padding: 14, background: 'black', color: 'white' }}>
    <div style={{ fontWeight: 700, marginBottom: 8 }}>Notizen</div>
    <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{text}</pre>
  </div>
)

}
