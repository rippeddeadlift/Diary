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
  const dx = Math.max(1e-9, maxLon - minLon)
  const dy = Math.max(1e-9, maxLat - minLat)

  // map lon->x, lat->y (invert y)
  const toXY = ([lat, lon]: [number, number]) => {
    const x = (lon - minLon) / dx
    const y = 1 - (lat - minLat) / dy
    return [x, y] as const
  }

  const coords = points.map(toXY)

  // fit into viewBox with padding
  const pad = 6
  const W = 100
  const H = 56

  const path = coords
    .map(([x, y], i) => {
      const px = pad + x * (W - pad * 2)
      const py = pad + y * (H - pad * 2)
      return `${i === 0 ? 'M' : 'L'} ${px.toFixed(2)} ${py.toFixed(2)}`
    })
    .join(' ')

  return (
    <div className={cn('overflow-hidden rounded-md border bg-muted/40', className)}>
      <svg viewBox={`0 0 ${W} ${H}`} className="block h-20 w-full">
        <path d={path} fill="none" stroke="currentColor" strokeWidth={2.2} className="text-primary" />
      </svg>
    </div>
  )
}
