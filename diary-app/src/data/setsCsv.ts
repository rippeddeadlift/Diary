export type SetsRow = { date: string; sets: number[]; total: number }

function parseSetsCell(cell: string): number[] {
  const raw = cell.trim().replace(/^"|"$/g, '')
  if (!raw) return []
  return raw
    .split(',')
    .map((s) => Number(s.trim()))
    .filter((n) => Number.isFinite(n))
}

export async function loadSetsCsv(csvPath: string): Promise<SetsRow[]> {
  const res = await fetch(`${csvPath}?ts=${Date.now()}`)
  if (!res.ok) throw new Error(`Cannot load ${csvPath}`)
  const text = await res.text()

  const lines = text.trim().split(/\r?\n/)
  if (lines.length <= 1) return []

  const out: SetsRow[] = []
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i]
    if (!line) continue

    const idx = line.indexOf(',')
    if (idx === -1) continue

    const date = line.slice(0, idx).trim()
    const setsCell = line.slice(idx + 1)
    if (!date) continue

    const sets = parseSetsCell(setsCell)
    const total = sets.reduce((a, b) => a + b, 0)
    out.push({ date, sets, total })
  }

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
