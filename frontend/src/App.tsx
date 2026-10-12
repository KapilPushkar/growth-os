import { useEffect, useState } from 'react'
import './App.css'

type Health = { status: string; db: string }

type HealthState =
  | { kind: 'loading' }
  | { kind: 'ok'; health: Health }
  | { kind: 'error'; message: string }

function App() {
  const [state, setState] = useState<HealthState>({ kind: 'loading' })

  useEffect(() => {
    fetch('/api/health')
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        setState({ kind: 'ok', health: (await res.json()) as Health })
      })
      .catch((err: unknown) => {
        setState({ kind: 'error', message: err instanceof Error ? err.message : String(err) })
      })
  }, [])

  return (
    <main className="app">
      <h1>Growth OS</h1>
      <section className="health">
        <h2>API health</h2>
        {state.kind === 'loading' && <p>Checking…</p>}
        {state.kind === 'ok' && (
          <p className="ok">
            status: <strong>{state.health.status}</strong> · db: <strong>{state.health.db}</strong>
          </p>
        )}
        {state.kind === 'error' && (
          <p className="error">
            Backend unreachable ({state.message}). Is uvicorn running on port 8000?
          </p>
        )}
      </section>
    </main>
  )
}

export default App
