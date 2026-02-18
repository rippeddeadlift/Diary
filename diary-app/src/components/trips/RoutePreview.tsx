import { cn } from '@/lib/utils'

export function RoutePreview({
  points,
  bbox,
  className
}: {
  points: [number, number][]
  bbox: [number, number, number, number]
  className?: string
}) {
  if (!points || points.length < 2) return null

  const [minLat, minLon, maxLat, maxLon] = bbox

  // Rough projection: lon scaled by cos(mid-lat) to reduce horizontal distortion.
  const midLat = (minLat + maxLat) / 2
  const cos = Math.cos((midLat * Math.PI) / 180)

  const proj = ([lat, lon]: [number, number]) => {
    const x = lon * cos
    const y = lat
    return [x, y] as const
  }

  const projPts = points.map(proj)
  const xs = projPts.map((p) => p[0])
  const ys = projPts.map((p) => p[1])
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)

  const dx = Math.max(1e-9, maxX - minX)
  const dy = Math.max(1e-9, maxY - minY)

  // fit into viewBox with uniform scale (no stretch)
  const pad = 6
  const W = 100
  const H = 56
  const innerW = W - pad * 2
  const innerH = H - pad * 2

  const scale = Math.min(innerW / dx, innerH / dy)
  const offX = pad + (innerW - dx * scale) / 2
  const offY = pad + (innerH - dy * scale) / 2

  const path = projPts
    .map(([x, y], i) => {
      const px = offX + (x - minX) * scale
      const py = offY + (maxY - y) * scale // invert Y
      return `${i === 0 ? 'M' : 'L'} ${px.toFixed(2)} ${py.toFixed(2)}`
    })
    .join(' ')

  return (
    <div className={cn('overflow-hidden', className)}>
      <svg viewBox={`0 0 ${W} ${H}`} className="block h-full w-full" preserveAspectRatio="xMidYMid meet">
        <path
          d={path}
          fill="none"
          stroke="currentColor"
          strokeWidth={2.2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-white/90"
        />
      </svg>
    </div>
  )
}
