import { useEffect, useRef, useState } from 'react'

export function PhotoPointMap({ lat, lon }: { lat: number; lon: number }) {
  const [ready, setReady] = useState(false)
  const [L, setL] = useState<any>(null)
  const mapRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    import('leaflet').then((mod) => {
      setL(mod)
      setReady(true)
    })
  }, [])

  useEffect(() => {
    if (!ready || !L) return
    const el = mapRef.current
    if (!el) return

    const map = L.map(el, { zoomControl: true })

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap'
    }).addTo(map)

    const marker = L.marker([lat, lon]).addTo(map)
    map.setView([lat, lon], 14)

    requestAnimationFrame(() => {
      try {
        map.invalidateSize()
      } catch {}
    })

    return () => {
      try {
        marker.remove()
      } catch {}
      map.remove()
    }
  }, [ready, L, lat, lon])

  return <div ref={mapRef} className="h-64 w-full" />
}
