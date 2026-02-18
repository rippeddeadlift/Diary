export type UploadResult = {
  ok: boolean
  batch?: string
  count?: number
  duplicatesSkipped?: number
  saved?: Array<{ file: string; sidecar: string; originalName?: string }>
}
