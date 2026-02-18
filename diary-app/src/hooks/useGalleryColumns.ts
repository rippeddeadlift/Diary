import { useEffect, useState } from 'react'

// Keep in sync with GalleryGrid Tailwind breakpoints:
// base: 2 cols, sm(640): 3 cols, lg(1024): 5 cols
export function useGalleryColumns() {
  const [cols, setCols] = useState(2)

  useEffect(() => {
    function compute() {
      const w = window.innerWidth
      if (w >= 1024) return 5
      if (w >= 640) return 3
      return 2
    }

    function onResize() {
      setCols(compute())
    }

    onResize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  return cols
}
