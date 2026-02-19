export type TrashTripsResponse = { ok: boolean; trashed: number; batch: string }

export type UpdateTripMetaResponse = { ok: boolean }

export async function updateTripMeta(req: { id: string; title: string; tags: string[] }): Promise<UpdateTripMetaResponse> {
  const res = await fetch('/api/trips/meta', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(req)
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return (await res.json()) as UpdateTripMetaResponse
}

export async function trashTrips(ids: string[]): Promise<TrashTripsResponse> {
  const res = await fetch('/api/trips/trash', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ ids })
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return (await res.json()) as TrashTripsResponse
}
