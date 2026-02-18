export type UploadResult = {
  ok: boolean
  batch?: string
  count?: number
  duplicatesSkipped?: number
  skippedNonImages?: number
  errors?: string[]
  saved?: Array<{ file: string; sidecar: string; originalName?: string }>
}
