export type TrashTripsResponse = { ok: boolean; trashed: number; batch: string }

export async function trashTrips(ids: string[]): Promise<TrashTripsResponse> {
  const res = await fetch('/api/trips/trash', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ ids })
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return (await res.json()) as TrashTripsResponse
}
