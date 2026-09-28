import { ThemeToggle } from './ThemeToggle'
import type { ReactNode } from 'react'
import { Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { FEATURE_ITEMS, type Page } from '@/features/registry'

interface LayoutProps {
  children: ReactNode
  page: Page
  setPage: (page: Page) => void
}

export function Layout({ children, page, setPage }: LayoutProps) {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <header className="border-b bg-card w-full">
        <div className="flex h-16 w-full items-center justify-between px-6">
          
          {/* Links: App-Titel + Navigationslinks */}
          <div className="flex items-center gap-6">
            <span 
              onClick={() => setPage('home')} 
              className="text-xl font-semibold tracking-tight cursor-pointer"
            >
              Tagebuch
            </span>

            <nav className="flex items-center gap-1 text-sm font-medium">
              {[
                { id: 'home' as const, label: 'Home' },
                ...FEATURE_ITEMS,
              ].map((item) => {
                const isActive = page === item.id
                return (
                  <button
                    key={item.id}
                    onClick={() => setPage(item.id)}
                    className={`px-3 py-1.5 rounded-md transition-colors ${
                      isActive
                        ? 'bg-secondary text-foreground font-semibold'
                        : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                    }`}
                  >
                    {item.label}
                  </button>
                )
              })}
            </nav>
          </div>

          <div className="flex items-center gap-1">
            <Button
              type="button"
              variant={page === 'settings' ? 'destructive' : 'ghost'}
              size="icon"
              aria-label="Einstellungen"
              title="Einstellungen"
              onClick={() => setPage('settings')}
            >
              <Settings className="h-4 w-4" />
            </Button>
            <ThemeToggle />
          </div>

        </div>
      </header>

      {/* Content Bereich */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-6">
        {children}
      </main>
    </div>
  )
}