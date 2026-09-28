import { useState } from 'react'
import { HomePage } from '@/features/home-page'
import { FEATURES, FEATURE_ITEMS, SETTINGS_PAGE, type Page } from '@/features/registry'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { Toaster } from 'sonner'
import { Layout } from './components/layout'

export default function App() {
  const [page, setPage] = useState<Page>('home')
  const ActiveFeature = page === 'home'
    ? null
    : page === 'settings'
      ? SETTINGS_PAGE.component
      : FEATURES[page].component

  return (
    <ErrorBoundary>
      <Layout page={page} setPage={setPage}>
        {ActiveFeature ? (
          <ActiveFeature />
        ) : (
          <HomePage features={FEATURE_ITEMS} onSelect={setPage} />
        )}
      </Layout>
      <Toaster />
    </ErrorBoundary>
  )
}