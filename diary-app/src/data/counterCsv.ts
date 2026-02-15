export type CounterRow = { date: string; count: number }

export async function loadCounterCsv(csvPath: string): Promise<CounterRow[]> {
  // cache-bust so browser doesn't keep an old response
  const res = await fetch(`${csvPath}?ts=${Date.now()}`)
  if (!res.ok) throw new Error(`Cannot load ${csvPath}`)
  const text = await res.text()

  const lines = text.trim().split(/\r?\n/)
  if (lines.length <= 1) return []

  const out: CounterRow[] = []
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

/** Format an ISO date (YYYY-MM-DD) as EU date (DD.MM.YYYY). */
export function formatDateEU(isoDate: string): string {
  const m = isoDate.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!m) return isoDate
  const [, yyyy, mm, dd] = m
  return `${dd}.${mm}.${yyyy}`
}
