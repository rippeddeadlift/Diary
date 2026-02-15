import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'

type Theme = 'light' | 'dark' | 'system'
const STORAGE_KEY = 'diary.theme'

function applyTheme(theme: Theme) {
  const root = document.documentElement

  const systemDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
  const shouldDark = theme === 'dark' || (theme === 'system' && systemDark)

  root.classList.toggle('dark', shouldDark)
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>('system')

  // initial load
  useEffect(() => {
    const saved = (localStorage.getItem(STORAGE_KEY) as Theme | null) ?? 'system'
    setTheme(saved)
    applyTheme(saved)
  }, [])

  // update on change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, theme)
    applyTheme(theme)

    // if system theme changes while we're in system mode
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)')
    if (!mq) return

    const onChange = () => {
      if (theme === 'system') applyTheme('system')
    }

    mq.addEventListener?.('change', onChange)
    return () => mq.removeEventListener?.('change', onChange)
  }, [theme])

  const label = useMemo(() => {
    if (theme === 'light') return 'Hell'
    if (theme === 'dark') return 'Dunkel'
    return 'System'
  }, [theme])

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          Theme: {label}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setTheme('light')}>Hell</DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('dark')}>Dunkel</DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('system')}>System</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
