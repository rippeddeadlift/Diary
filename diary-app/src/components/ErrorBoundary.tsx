import React from 'react'

type Props = {
  children: React.ReactNode
}

type State = {
  error?: unknown
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = {}

  static getDerivedStateFromError(error: unknown): State {
    return { error }
  }

  componentDidCatch(error: unknown, info: unknown) {
    // Log for debugging; can be removed later.
    console.error('UI crashed', error, info)
  }

  render() {
    if (this.state.error) {
      const msg =
        this.state.error instanceof Error
          ? `${this.state.error.name}: ${this.state.error.message}`
          : String(this.state.error)

      return (
        <div className="min-h-screen bg-background p-6 text-foreground">
          <div className="mx-auto max-w-3xl space-y-3">
            <h1 className="text-xl font-semibold">Tagebuch</h1>
            <p className="text-sm text-muted-foreground">UI Fehler (ErrorBoundary)</p>
            <pre className="whitespace-pre-wrap rounded-lg border bg-muted p-3 text-sm">{msg}</pre>
            <button
              className="text-sm underline"
              onClick={() => {
                this.setState({ error: undefined })
                window.location.reload()
              }}
            >
              Neu laden
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
