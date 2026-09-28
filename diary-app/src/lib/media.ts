const VIDEO_EXTS = ['.mp4', '.mov', '.m4v', '.webm']

export function isVideoPath(path: string | null | undefined): boolean {
  const name = (path ?? '').toLowerCase()
  return VIDEO_EXTS.some((ext) => name.endsWith(ext))
}

export function isVideoItem(item: { kind?: string; path: string } | null | undefined): boolean {
  return item?.kind === 'video' || isVideoPath(item?.path)
}
