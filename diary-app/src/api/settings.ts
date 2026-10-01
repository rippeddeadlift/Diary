export type MediaDirectorySetting = {
  path: string
  activePath: string
  restartRequired: boolean
}

type PickMediaDirectoryResult = MediaDirectorySetting & {
  cancelled: boolean
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail ?? 'Der Medienordner konnte nicht geladen werden.')
  }
  return payload as T
}

export function getMediaDirectory(): Promise<MediaDirectorySetting> {
  return request('/api/settings/media-directory')
}

export function pickMediaDirectory(): Promise<PickMediaDirectoryResult> {
  return request('/api/settings/media-directory/pick', { method: 'POST' })
}