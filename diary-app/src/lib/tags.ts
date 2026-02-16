export function parseCsvList(s: string): string[] {
  return s
    .split(',')
    .map((x) => x.trim())
    .filter((x) => x.length > 0)
}

export function toCsvList(items: string[] | undefined | null): string {
  return (items ?? []).join(', ')
}
