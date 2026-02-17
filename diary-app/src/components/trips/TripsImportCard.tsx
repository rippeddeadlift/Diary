import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const KOMOOT_ACTIVITIES_URL =
  'https://www.komoot.com/de-de/user/834679236496/activities?type=recorded'

type ImportResult = {
  ok: boolean
  imported?: number | null
  output?: string
  error?: string
}

export function TripsImportCard({ onImported }: { onImported: () => Promise<void> }) {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)

  async function runImport() {
    setBusy(true)
    setResult(null)
    try {
      const res = await fetch('/api/trips/import-gpx', { method: 'POST' })
      const text = await res.text()
      let json: ImportResult
      try {
        json = JSON.parse(text)
      } catch {
        json = { ok: false, error: text }
      }
      setResult(json)
      if (json.ok) await onImported()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Komoot Import</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Workflow: Komoot öffnen → GPX herunterladen (landet in Downloads) → Import klicken.
        </p>

        <a className="text-sm underline" href={KOMOOT_ACTIVITIES_URL} target="_blank" rel="noreferrer">
          Komoot: Abgeschlossene Touren öffnen
        </a>

        <div>
          <Button onClick={runImport} disabled={busy}>
            {busy ? 'Import…' : 'GPX aus Downloads importieren'}
          </Button>
        </div>

        {result ? (
          <pre className="whitespace-pre-wrap rounded-lg border bg-muted p-3 text-xs">{result.output || result.error}</pre>
        ) : null}
      </CardContent>
    </Card>
  )
}
