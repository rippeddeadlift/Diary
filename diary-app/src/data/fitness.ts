export type DipsRow = { date: string; count: number }

export async function loadDips(): Promise<DipsRow[]> {
  // cache-bust so browser doesn't keep an old response
  const res = await fetch(`/fitness/dips.csv?ts=${Date.now()}`)
  if (!res.ok) throw new Error('Cannot load fitness/dips.csv')
  const text = await res.text()

  const lines = text.trim().split(/\r?\n/)
  if (lines.length <= 1) return []

  const out: DipsRow[] = []
  for (let i = 1; i < lines.length; i++) {
    const [date, countStr] = lines[i].split(',')
    const count = Number(countStr)
    if (!date) continue
    if (!Number.isFinite(count)) continue
    out.push({ date, count })
  }

  // newest first
  out.sort((a, b) => b.date.localeCompare(a.date))
  return out
}

export function getTodayISO(): string {
  const d = new Date()
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}
