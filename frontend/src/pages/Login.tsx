import { useState, type FormEvent } from 'react'
import { Button, Field } from '../components/ui'
import { useAuth } from '../lib/auth'
import { navigate } from '../lib/router'
import { errorMessage } from '../lib/toast'

const DEMO_LOGINS = [
  { label: 'Agency admin', email: 'admin@growthos.dev', password: 'admin123' },
  { label: 'Strategist', email: 'priya@growthos.dev', password: 'team123' },
  { label: 'Client (LedgerLoop)', email: 'client1@growthos.dev', password: 'client123' },
]

export function Login() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login">
      <section className="login-art">
        <div className="brand" style={{ padding: 0 }}>
          <span className="brand-mark">G</span>
          Growth OS
        </div>
        <div>
          <h1>Your growth engine runs. You approve and see results.</h1>
          <p>
            Content, personal branding, lead generation and search visibility, done for you by the agency team. Your only
            job: approve what goes out in your name.
          </p>
        </div>
        <span style={{ color: '#8fa89e', fontSize: 13 }}>Done-for-you growth for founders and executives</span>
      </section>
      <section className="login-form">
        <form onSubmit={submit} noValidate>
          <div>
            <h1 style={{ fontSize: 24 }}>Sign in</h1>
            <p className="muted">Team console and client portal in one place.</p>
          </div>
          <Field label="Email">
            <input
              className="input"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </Field>
          <Field label="Password">
            <input
              className="input"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </Field>
          {error ? (
            <div className="note" role="alert" style={{ borderColor: 'var(--danger)', background: 'var(--danger-soft)' }}>
              {error}
            </div>
          ) : null}
          <Button type="submit" variant="primary" size="lg" busy={busy} disabled={!email || !password}>
            Sign in
          </Button>
          <div className="stack tight demo-logins">
            <span className="subtle">Demo accounts (after running the seed):</span>
            <div className="row wrap">
              {DEMO_LOGINS.map((demo) => (
                <button
                  key={demo.email}
                  type="button"
                  onClick={() => {
                    setEmail(demo.email)
                    setPassword(demo.password)
                  }}
                >
                  {demo.label}
                </button>
              ))}
            </div>
          </div>
        </form>
      </section>
    </div>
  )
}
