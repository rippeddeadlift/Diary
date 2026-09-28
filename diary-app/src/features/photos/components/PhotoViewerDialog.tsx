import { useEffect, useMemo, useRef, useState } from 'react'
import type { GalleryItem } from '@/types/photos'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { getSidecar, updateSidecar } from '@/api/photos'
import { Button } from '@/components/ui/button'
import { PhotoPointMap } from '@/components/maps/PhotoPointMap'
import { PEOPLE, PHOTO_TAGS } from '@/data/tagConfig'
import { TagChips } from './TagChips'
import { Switch } from '@/components/ui/switch'
import { FullScreenPhotoViewer } from './FullScreenPhotoViewer'
import { isVideoItem } from '@/lib/media'
import { Maximize2 } from 'lucide-react'



function MapBlock({ lat, lon }: { lat: number; lon: number }) {
  const [showMap, setShowMap] = useState(false)
  console.debug('MapBlock render', { lat, lon })
  console.debug('MapBlock showMap', showMap)

  useEffect(() => {
    const t = window.setTimeout(() => setShowMap(true), 200)
    return () => window.clearTimeout(t)
  }, [])

  return (
    <>
      <div className="overflow-hidden rounded-md border">
        {showMap ? (
          <PhotoPointMap lat={lat} lon={lon} />
        ) : (
          <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">Karte lädt…</div>
        )}
      </div>
      <div className="font-mono text-xs text-muted-foreground">
        {lat.toFixed(6)}, {lon.toFixed(6)}
      </div>
    </>
  )
}

export function PhotoViewerDialog({
  items,
  index,
  onChangeIndex,
  onClose
}: {
  items: GalleryItem[]
  index: number | null
  onChangeIndex: (next: number | null) => void
  onClose: () => void
}) {
  const [people, setPeople] = useState<string[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [fsIndex, setFsIndex] = useState<number | null>(null)
  const [sharePreparing, setSharePreparing] = useState(false)
  const [shareStatus, setShareStatus] = useState<string | null>(null)

  const initialRef = useRef<{ people: string[]; tags: string[] } | null>(null)
  const loadedPathRef = useRef<string | null>(null)
  const navigationRef = useRef(false)
  const [loadedPath, setLoadedPath] = useState<string | null>(null)

  const item = index === null ? null : items[index] ?? null
  const path = item?.path

  useEffect(() => {
    if (!path) return

    let active = true
    loadedPathRef.current = null
    setLoadedPath(null)
    initialRef.current = null
    setPeople([])
    setTags([])

      ; (async () => {
        try {
          setErr(null)
          const sc = await getSidecar(path)
          if (!active) {
            return
          }
          const p = sc.people ?? []
          const t = sc.tags ?? []
          setPeople(p)
          setTags(t)
          initialRef.current = { people: p, tags: t }
          loadedPathRef.current = path
          setLoadedPath(path)
          // caption intentionally omitted for now
        } catch (e: any) {
          if (active) setErr(e?.message ?? String(e))
        }
      })()

    return () => {
      active = false
    }
  }, [path])

  useEffect(() => {
    setShareStatus(null)
  }, [path])

  const dirty = useMemo(() => {
    const init = initialRef.current
    if (loadedPath !== path || !init) return false
    const a = JSON.stringify({ people: init.people, tags: init.tags })
    const b = JSON.stringify({ people, tags })
    return a !== b
  }, [people, tags, loadedPath, path])

  async function save(): Promise<boolean> {
    if (!path || loadedPathRef.current !== path) return false
    if (!dirty) return true

    const savePath = path
    const savePeople = [...people]
    const saveTags = [...tags]
    setBusy(true)
    setErr(null)
    try {
      await updateSidecar({ path: savePath, people: savePeople, tags: saveTags })
      if (loadedPathRef.current === savePath) {
        initialRef.current = { people: savePeople, tags: saveTags }
      }
      return true
    } catch (e: any) {
      if (loadedPathRef.current === savePath) setErr(e?.message ?? String(e))
      return false
    } finally {
      setBusy(false)
    }
  }

  async function go(delta: number) {
    if (navigationRef.current) return
    if (index === null) return
    const next = index + delta
    if (next < 0 || next >= items.length) return

    navigationRef.current = true
    try {
      if (await save()) onChangeIndex(next)
    } finally {
      navigationRef.current = false
    }
  }

  function openFullScreen() {
    if (index !== null) setFsIndex(index)
  }

  async function exitFullScreen() {
    if (fsIndex !== null) {
      if (await save()) onChangeIndex(fsIndex)
    }
    setFsIndex(null)
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (index === null || fsIndex !== null) return
      if (e.key === 'ArrowLeft') void go(-1)
      if (e.key === 'ArrowRight') void go(1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [index, items.length, fsIndex, go])

  async function shareCurrent() {
    if (!item) return
    const nav: any = navigator
    if (!window.isSecureContext || !nav?.share) {
      setShareStatus('Dieser Browser unterstützt kein direktes Dateiteilen. Öffne Diary in Chrome/Edge oder auf dem Smartphone über HTTPS; dort zeigt das System verfügbare Apps wie E-Mail, WhatsApp oder Telegram an.')
      return
    }

    setSharePreparing(true)
    setShareStatus('Datei wird vorbereitet…')
    try {
      const res = await fetch(item.url)
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      const blob = await res.blob()
      const fileName = item.path.split('/').pop() || 'photo'
      const file = new File([blob], fileName, { type: blob.type || 'image/jpeg' })
      if (nav.canShare && !nav.canShare({ files: [file] })) {
        setShareStatus('Dieser Browser kann diesen Dateityp nicht direkt teilen.')
        return
      }
      await nav.share({ files: [file], title: 'Foto' })
      setShareStatus(null)
    } catch (e: any) {
      setShareStatus(e?.name === 'AbortError' ? 'Teilen abgebrochen.' : e?.message ?? 'Teilen fehlgeschlagen.')
    } finally {
      setSharePreparing(false)
    }
  }

  return (
    <>
      <Dialog
        open={index !== null}
        onOpenChange={(open) => {
          if (!open) {
            // Fire-and-forget save on close (don't block UI)
            void save()
            onChangeIndex(null)
            onClose()
          }
        }}
      >
        <DialogContent className="p-0">
          {item ? (
            <div className="grid max-h-[90vh] grid-cols-1 overflow-auto sm:grid-cols-2">
              <div className="p-4">
                <div className="relative overflow-hidden rounded-md border bg-muted">
                  {isVideoItem(item) ? (
                    <video
                      key={item.path}
                      src={item.url}
                      poster={item.thumbUrl ?? undefined}
                      controls
                      playsInline
                      className="block max-h-[70vh] w-full bg-black"
                    />
                  ) : (
                    <img src={item.url} alt={item.path} className="block h-auto w-full object-contain" />
                  )}

                  <div className="absolute inset-x-0 top-2 flex items-center justify-between px-2">
                    <button
                      type="button"
                      onClick={() => void go(-1)}
                      disabled={index === 0}
                      className="rounded-md border bg-background/80 px-2 py-1 text-xs text-foreground disabled:opacity-40"
                    >
                      ←
                    </button>

                    <div className="flex items-center gap-2">
                      <div className="rounded-md border bg-background/80 px-2 py-1 text-xs text-muted-foreground">
                        {index! + 1} / {items.length}
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={sharePreparing}
                        onClick={() => void shareCurrent()}
                      >
                        {sharePreparing ? 'Teilen…' : 'Teilen'}
                      </Button>
                      <button
                        type="button"
                        onClick={openFullScreen}
                        className="rounded-md border bg-background/80 px-2 py-1 text-xs text-foreground hover:bg-background"
                        title="Vollbild"
                        aria-label="Vollbild öffnen"
                      >
                        <Maximize2 className="h-3.5 w-3.5" />
                      </button>
                    </div>

                    <button
                      type="button"
                      onClick={() => void go(1)}
                      disabled={index === items.length - 1}
                      className="rounded-md border bg-background/80 px-2 py-1 text-xs text-foreground disabled:opacity-40"
                    >
                      →
                    </button>
                  </div>
                </div>

                {shareStatus ? <div role="status" className="mt-2 text-xs text-muted-foreground">{shareStatus}</div> : null}


                <div className="mt-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <DialogHeader>
                      <DialogTitle className="text-base">Tags</DialogTitle>
                    </DialogHeader>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">Settings</span>
                      <Switch checked={settingsOpen} onCheckedChange={setSettingsOpen} />
                    </div>
                  </div>

                  {settingsOpen ? (
                    <>
                      <div className="space-y-2">
                        <div className="text-xs text-muted-foreground">People</div>
                        <TagChips options={PEOPLE} value={people} onChange={setPeople} />
                      </div>

                      <div className="space-y-2">
                        <div className="text-xs text-muted-foreground">Tags</div>
                        <TagChips options={PHOTO_TAGS} value={tags} onChange={setTags} />
                      </div>

                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        {busy ? 'Speichern…' : dirty ? 'Ungespeichert (wird beim Schließen gespeichert)' : 'Gespeichert'}
                      </div>

                      {err ? <div className="text-sm text-destructive">{err}</div> : null}
                    </>
                  ) : null}
                </div>
              </div>

              <div className="border-t p-4 sm:border-l sm:border-t-0">
                <DialogHeader>
                  <DialogTitle className="text-base">Ort</DialogTitle>
                </DialogHeader>
                {item.location ? (
                  <div className="mt-3 space-y-2">
                    <MapBlock lat={item.location.lat} lon={item.location.lon} />
                  </div>
                ) : (
                  <div className="mt-3 text-sm text-muted-foreground">Kein GPS im Foto.</div>
                )}
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      <FullScreenPhotoViewer
        items={items}
        index={fsIndex}
        onChangeIndex={setFsIndex}
        onExit={exitFullScreen}
      />
    </>
  )
}
