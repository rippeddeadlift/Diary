import { useEffect, useRef, useState } from 'react'

export function LeafletMap({ gpxText }: { gpxText: string }) {
  // lazy import leaflet only in browser
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

    const parser = new DOMParser()
    const xml = parser.parseFromString(gpxText, 'application/xml')
    const pts = Array.from(xml.getElementsByTagName('trkpt')).map((p) => {
      const lat = Number(p.getAttribute('lat'))
      const lon = Number(p.getAttribute('lon'))
      return [lat, lon] as [number, number]
    })

    const line = L.polyline(pts, { color: '#7c3aed', weight: 5, opacity: 0.9 }).addTo(map)
    map.fitBounds(line.getBounds().pad(0.2))

    // Force size recalculation after layout settles (helps with blank strips)
    requestAnimationFrame(() => {
      try {
        map.invalidateSize()
      } catch {}
      requestAnimationFrame(() => {
        try {
          map.invalidateSize()
        } catch {}
      })
    })

    return () => {
      map.remove()
    }
  }, [ready, L, gpxText])

  return (
    <div style={{ border: '1px solid rgba(0,0,0,0.12)', borderRadius: 12, overflow: 'hidden', background: 'white' }}>
      <div style={{ padding: 10, fontWeight: 700 }}>Route (GPX)</div>
      <div ref={mapRef} style={{ height: 420, width: '100%' }} />
    </div>
  )
}
