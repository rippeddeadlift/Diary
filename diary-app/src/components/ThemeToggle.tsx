import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Moon, Sun } from 'lucide-react'

type Theme = 'light' | 'dark'
const STORAGE_KEY = 'diary.theme'

function applyTheme(theme: Theme) {
  const root = document.documentElement
  root.classList.toggle('dark', theme === 'dark')
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>('dark')

  // Initial Load: Storage oder System-Preference prüfen
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY) as Theme | null
    if (saved) {
      setTheme(saved)
      applyTheme(saved)
    } else {
      const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      const initial = systemDark ? 'dark' : 'light'
      setTheme(initial)
      applyTheme(initial)
    }
  }, [])

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark'
    setTheme(nextTheme)
    localStorage.setItem(STORAGE_KEY, nextTheme)
    applyTheme(nextTheme)
  }

  return (
    <Button variant="ghost" size="icon" onClick={toggleTheme} title="Theme wechseln">
      {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  )
}