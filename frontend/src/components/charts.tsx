// Hand-built SVG charts: no chart library. Line charts measure their
// container so text stays the same size at any width.
import { useEffect, useRef, useState } from 'react'
import { num } from '../lib/format'

const CHART_COLORS = ['#0f6b55', '#c08a2b', '#5b3fb5', '#1f4f9a']

export function Sparkline({
  values,
  width = 120,
  height = 32,
  color = CHART_COLORS[0],
}: {
  values: number[]
  width?: number
  height?: number
  color?: string
}) {
  if (values.length < 2) return <span className="subtle">No data yet</span>
  const max = Math.max(...values)
  const min = Math.min(...values)
  const span = max - min || 1
  const points = values.map((value, i) => {
    const x = (i / (values.length - 1)) * width
    const y = height - 3 - ((value - min) / span) * (height - 6)
    return [x, y] as const
  })
  const line = points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const [lastX, lastY] = points[points.length - 1]
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Weekly trend">
      <polygon points={`0,${height} ${line} ${width},${height}`} fill={color} opacity={0.08} />
      <polyline points={line} fill="none" stroke={color} strokeWidth={1.75} strokeLinejoin="round" />
      <circle cx={lastX} cy={lastY} r={2.5} fill={color} />
    </svg>
  )
}

/** Round an axis maximum up to 1, 2, 2.5 or 5 times a power of ten. */
function niceMax(value: number): number {
  if (value <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(value))
  const step = [1, 2, 2.5, 5, 10].find((s) => s * magnitude >= value) ?? 10
  return step * magnitude
}

function useWidth(fallback: number) {
  const ref = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(fallback)
  useEffect(() => {
    const node = ref.current
    if (!node) return
    const observer = new ResizeObserver(([entry]) => {
      if (entry.contentRect.width > 0) setWidth(Math.round(entry.contentRect.width))
    })
    observer.observe(node)
    return () => observer.disconnect()
  }, [])
  return { ref, width }
}

const axisLabel = (value: number) => num(Math.round(value))

export interface Series {
  name: string
  values: number[]
  color?: string
}

export function LineChart({
  labels,
  series,
  height = 220,
  format = axisLabel,
}: {
  labels: string[]
  series: Series[]
  height?: number
  format?: (value: number) => string
}) {
  const { ref, width } = useWidth(640)
  const pad = { top: 12, right: 12, bottom: 26, left: 48 }
  const innerW = width - pad.left - pad.right
  const innerH = height - pad.top - pad.bottom
  const all = series.flatMap((s) => s.values)
  if (labels.length < 2 || all.length === 0) return <p className="subtle">Not enough history to chart yet.</p>
  const max = niceMax(Math.max(...all))
  const x = (i: number) => pad.left + (i / (labels.length - 1)) * innerW
  const y = (value: number) => pad.top + innerH - (value / max) * innerH
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => t * max)
  const labelEvery = Math.ceil(labels.length / Math.max(2, Math.floor(innerW / 90)))

  return (
    <div className="stack tight" ref={ref}>
      <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={series.map((s) => s.name).join(', ')}>
        {ticks.map((tick) => (
          <g key={tick}>
            <line className="grid-line" x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} />
            <text x={pad.left - 8} y={y(tick) + 4} textAnchor="end">
              {format(tick)}
            </text>
          </g>
        ))}
        {labels.map((label, i) =>
          i % labelEvery === 0 || i === labels.length - 1 ? (
            <text key={label + i} x={x(i)} y={height - 6} textAnchor="middle">
              {label}
            </text>
          ) : null,
        )}
        {series.map((s, index) => {
          const color = s.color ?? CHART_COLORS[index % CHART_COLORS.length]
          const line = s.values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
          return (
            <g key={s.name}>
              {index === 0 ? (
                <polygon
                  points={`${x(0)},${y(0)} ${line} ${x(s.values.length - 1)},${y(0)}`}
                  fill={color}
                  opacity={0.07}
                />
              ) : null}
              <polyline points={line} fill="none" stroke={color} strokeWidth={2.25} strokeLinejoin="round" />
              {s.values.map((v, i) => (
                <circle key={i} cx={x(i)} cy={y(v)} r={3} fill="#fff" stroke={color} strokeWidth={1.75}>
                  <title>{`${s.name} · ${labels[i]}: ${format(v)}`}</title>
                </circle>
              ))}
            </g>
          )
        })}
      </svg>
      {series.length > 1 ? (
        <div className="legend">
          {series.map((s, index) => (
            <span key={s.name}>
              <i style={{ background: s.color ?? CHART_COLORS[index % CHART_COLORS.length] }} />
              {s.name}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export function BarList({
  items,
  max,
  format = num,
}: {
  items: { label: string; value: number; note?: string }[]
  max?: number
  format?: (value: number) => string
}) {
  const top = max ?? Math.max(1, ...items.map((item) => item.value))
  return (
    <div className="stack tight">
      {items.map((item) => (
        <div className="bar-row" key={item.label}>
          <span className="muted">{item.label}</span>
          <div className="bar-track">
            <span style={{ width: `${Math.max(2, (item.value / top) * 100)}%` }} />
          </div>
          <span className="mono" style={{ textAlign: 'right' }} title={item.note}>
            {format(item.value)}
          </span>
        </div>
      ))}
    </div>
  )
}

export function Funnel({ steps }: { steps: { label: string; value: number }[] }) {
  const top = Math.max(1, steps[0]?.value ?? 1)
  return (
    <div className="stack tight">
      {steps.map((step, i) => {
        const previous = i > 0 ? steps[i - 1].value : null
        const rate = previous ? (step.value / previous) * 100 : null
        // Log scale keeps small stages visible next to impressions.
        const width = step.value > 0 ? 25 + 75 * (Math.log10(step.value + 1) / Math.log10(top + 1)) : 0
        return (
          <div className="funnel-step" key={step.label}>
            <span className="muted">{step.label}</span>
            <div className="row">
              <div className="funnel-bar" style={{ width: `${width}%`, opacity: 1 - i * 0.12 }}>
                <span>{num(step.value)}</span>
              </div>
              {rate !== null ? (
                <span className="subtle" title="Conversion from the previous stage">
                  {rate < 1 ? rate.toFixed(1) : Math.round(rate)}%
                </span>
              ) : null}
            </div>
          </div>
        )
      })}
    </div>
  )
}
