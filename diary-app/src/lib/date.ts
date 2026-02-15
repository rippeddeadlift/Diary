/** Format an ISO date (YYYY-MM-DD) as EU date (DD.MM.YYYY). */
export function formatDateEU(isoDate: string): string {
  const m = isoDate.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!m) return isoDate
  const [, yyyy, mm, dd] = m
  return `${dd}.${mm}.${yyyy}`
}
