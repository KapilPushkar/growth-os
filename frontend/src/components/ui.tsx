import { useEffect, type ButtonHTMLAttributes, type ReactNode } from 'react'
import {
  CLIENT_STATUS_TONE,
  STAGE_META,
  STATUS_META,
  healthTone,
  humanize,
  initials,
  num,
  signedPct,
  sourceLabel,
  type Tone,
} from '../lib/format'
import { useLocation } from '../lib/router'
import type { ContentStatus, LeadStage } from '../lib/types'

export function Link({
  to,
  children,
  className,
  activeClassName = 'active',
  exact = false,
}: {
  to: string
  children: ReactNode
  className?: string
  activeClassName?: string
  exact?: boolean
}) {
  const { path } = useLocation()
  const target = to.split('?')[0]
  const active = exact ? path === target : path === target || path.startsWith(`${target}/`)
  const classes = [className, active ? activeClassName : ''].filter(Boolean).join(' ')
  return (
    <a href={`#${to}`} className={classes || undefined}>
      {children}
    </a>
  )
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'danger' | 'ghost' | 'default'
  size?: 'sm' | 'md' | 'lg'
  busy?: boolean
}

export function Button({ variant = 'default', size = 'md', busy, className, children, disabled, ...rest }: ButtonProps) {
  const classes = ['btn', variant !== 'default' && `btn-${variant}`, size !== 'md' && `btn-${size}`, className]
    .filter(Boolean)
    .join(' ')
  return (
    <button type="button" className={classes} disabled={disabled || busy} {...rest}>
      {busy ? <span className="spinner" style={{ width: 14, height: 14 }} aria-hidden /> : null}
      {children}
    </button>
  )
}

export function Badge({ tone = 'neutral', plain, children }: { tone?: Tone; plain?: boolean; children: ReactNode }) {
  return <span className={`badge tone-${tone}${plain ? ' plain' : ''}`}>{children}</span>
}

export function StatusBadge({ status }: { status: ContentStatus }) {
  const meta = STATUS_META[status]
  return <Badge tone={meta.tone}>{meta.label}</Badge>
}

export function StageBadge({ stage }: { stage: LeadStage }) {
  const meta = STAGE_META[stage]
  return <Badge tone={meta.tone}>{meta.label}</Badge>
}

export function ClientStatusBadge({ status }: { status: string }) {
  return <Badge tone={CLIENT_STATUS_TONE[status] ?? 'neutral'}>{humanize(status)}</Badge>
}

/** Shows whether text came from a live model or the template fallback. */
export function SourceBadge({ source }: { source: string | null | undefined }) {
  if (!source) return null
  const live = source.startsWith('llm:')
  return (
    <Badge tone={live ? 'violet' : 'neutral'} plain>
      {live ? '✦ ' : ''}
      {sourceLabel(source)}
    </Badge>
  )
}

export function SimulatedBadge() {
  return (
    <Badge tone="orange" plain>
      Simulated
    </Badge>
  )
}

export function Health({ score }: { score: number | null }) {
  if (score === null) return <span className="subtle">Onboarding</span>
  return (
    <span className={`health tone-${healthTone(score)}`} title="Account health (0-100)">
      {score}
    </span>
  )
}

export function Avatar({ name, size }: { name: string; size?: 'lg' }) {
  return (
    <span className={`avatar${size ? ` ${size}` : ''}`} aria-hidden>
      {initials(name)}
    </span>
  )
}

export function Card({
  title,
  subtitle,
  actions,
  children,
  bodyless,
  className,
}: {
  title?: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  children: ReactNode
  bodyless?: boolean
  className?: string
}) {
  return (
    <section className={`card${className ? ` ${className}` : ''}`}>
      {title || actions ? (
        <header className="card-header">
          <div>
            {title ? <h2>{title}</h2> : null}
            {subtitle ? <p>{subtitle}</p> : null}
          </div>
          {actions ? <div className="row wrap">{actions}</div> : null}
        </header>
      ) : null}
      {bodyless ? children : <div className="card-body">{children}</div>}
    </section>
  )
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: ReactNode
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
}) {
  return (
    <header className="page-header">
      <div>
        {eyebrow ? <div className="eyebrow">{eyebrow}</div> : null}
        <h1>{title}</h1>
        {description ? <p>{description}</p> : null}
      </div>
      {actions ? <div className="row wrap no-print">{actions}</div> : null}
    </header>
  )
}

export function Loading({ label = 'Loading…', compact }: { label?: string; compact?: boolean }) {
  return (
    <div className={`state${compact ? ' compact' : ''}`} role="status">
      <span className="spinner" aria-hidden />
      <span>{label}</span>
    </div>
  )
}

export function Empty({
  title,
  children,
  action,
  compact,
}: {
  title: string
  children?: ReactNode
  action?: ReactNode
  compact?: boolean
}) {
  return (
    <div className={`state${compact ? ' compact' : ''}`}>
      <strong>{title}</strong>
      {children ? <span>{children}</span> : null}
      {action}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state error" role="alert">
      <strong>Couldn't load this</strong>
      <span>{message}</span>
      {onRetry ? (
        <Button size="sm" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  )
}

/** Render loading / error / content for a useApi() result. */
export function Async<T>({
  state,
  children,
  label,
}: {
  state: { data: T | null; error: string | null; loading: boolean; reload: () => void }
  children: (data: T) => ReactNode
  label?: string
}) {
  if (state.error && !state.data) return <ErrorState message={state.error} onRetry={state.reload} />
  if (!state.data) return <Loading label={label} />
  return <>{children(state.data)}</>
}

export function Kpi({
  label,
  value,
  change,
  hint,
}: {
  label: string
  value: ReactNode
  change?: number | null
  hint?: ReactNode
}) {
  const direction = change === undefined || change === null ? 'flat' : change > 0 ? 'up' : change < 0 ? 'down' : 'flat'
  return (
    <div className="card kpi">
      <span className="label">{label}</span>
      <span className="value">{typeof value === 'number' ? num(value) : value}</span>
      {change !== undefined ? (
        <span className={`delta ${direction}`}>
          {direction === 'up' ? '▲ ' : direction === 'down' ? '▼ ' : ''}
          {signedPct(change)}
          {change !== null ? <span className="subtle"> vs prior</span> : null}
        </span>
      ) : null}
      {hint ? <span className="subtle">{hint}</span> : null}
    </div>
  )
}

export function Progress({ value, label }: { value: number; label?: string }) {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div
      className={`progress${clamped >= 100 ? ' done' : ''}`}
      role="progressbar"
      aria-valuenow={Math.round(clamped)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
    >
      <span style={{ width: `${clamped}%` }} />
    </div>
  )
}

export function Field({ label, hint, children, full }: { label: string; hint?: ReactNode; children: ReactNode; full?: boolean }) {
  return (
    <label className={`field${full ? ' full' : ''}`}>
      <span>{label}</span>
      {children}
      {hint ? <small>{hint}</small> : null}
    </label>
  )
}

function useEscape(onClose: () => void) {
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])
}

export function Drawer({
  title,
  subtitle,
  onClose,
  children,
  footer,
}: {
  title: ReactNode
  subtitle?: ReactNode
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}) {
  useEscape(onClose)
  return (
    <>
      <div className="overlay" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true">
        <header className="drawer-header">
          <div className="stack tight grow">
            <h2>{title}</h2>
            {subtitle}
          </div>
          <button type="button" className="close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>
        <div className="drawer-body">{children}</div>
        {footer ? <footer className="drawer-footer">{footer}</footer> : null}
      </aside>
    </>
  )
}

export function Modal({
  title,
  onClose,
  children,
  footer,
}: {
  title: ReactNode
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}) {
  useEscape(onClose)
  return (
    <>
      <div className="overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-modal="true">
        <header className="drawer-header">
          <h2>{title}</h2>
          <button type="button" className="close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>
        <div className="drawer-body">{children}</div>
        {footer ? <footer className="drawer-footer">{footer}</footer> : null}
      </div>
    </>
  )
}
