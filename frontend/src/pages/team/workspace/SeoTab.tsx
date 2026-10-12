import { useState } from 'react'
import { BarList } from '../../../components/charts'
import { RankChange } from '../../../components/KeywordMovers'
import {
  Async,
  Badge,
  Button,
  Card,
  Empty,
  Field,
  SimulatedBadge,
  SourceBadge,
} from '../../../components/ui'
import { api } from '../../../lib/api'
import { ENGINES, ENGINE_LABELS, humanize, num, pct, relative } from '../../../lib/format'
import { useToast } from '../../../lib/toast'
import type { Client, Engine, GeoCheck, KeywordIdea } from '../../../lib/types'
import { useApi } from '../../../lib/useApi'

export function SeoTab({ client }: { client: Client }) {
  return (
    <div className="stack">
      <KeywordsCard client={client} />
      <GeoCard client={client} />
    </div>
  )
}

function KeywordsCard({ client }: { client: Client }) {
  const toast = useToast()
  const state = useApi(() => api.keywords.list(client.id), [client.id])
  const [refreshing, setRefreshing] = useState(false)
  const [seed, setSeed] = useState('')
  const [ideas, setIdeas] = useState<{ items: KeywordIdea[]; source: string } | null>(null)
  const [picked, setPicked] = useState<Set<string>>(new Set())
  const [suggesting, setSuggesting] = useState(false)
  const [adding, setAdding] = useState(false)

  async function refresh() {
    setRefreshing(true)
    try {
      const result = await api.keywords.refresh(client.id)
      state.setData(result.items)
      toast.info(result.note)
    } catch (error) {
      toast.error(error)
    } finally {
      setRefreshing(false)
    }
  }

  async function suggest() {
    setSuggesting(true)
    try {
      const result = await api.ai.keywords(client.id, seed, 8)
      setIdeas({ items: result.keywords, source: result.source })
      setPicked(new Set(result.keywords.map((k) => k.keyword)))
    } catch (error) {
      toast.error(error)
    } finally {
      setSuggesting(false)
    }
  }

  async function addPicked() {
    if (!ideas) return
    setAdding(true)
    try {
      const chosen = ideas.items
        .filter((idea) => picked.has(idea.keyword))
        .map(({ keyword, intent, search_volume, difficulty }) => ({ keyword, intent, search_volume, difficulty }))
      const result = await api.keywords.bulk(client.id, chosen)
      toast.success(
        `Tracking ${result.added.length} new keyword${result.added.length === 1 ? '' : 's'}` +
          (result.skipped.length ? ` (${result.skipped.length} already tracked)` : ''),
      )
      setIdeas(null)
      state.reload()
    } catch (error) {
      toast.error(error)
    } finally {
      setAdding(false)
    }
  }

  async function remove(id: number) {
    try {
      await api.keywords.remove(id)
      state.setData((current) => (current ?? []).filter((k) => k.id !== id))
    } catch (error) {
      toast.error(error)
    }
  }

  return (
    <Card
      title="Keyword tracking"
      subtitle="Search rankings for the queries this client should own"
      actions={
        <>
          <SimulatedBadge />
          <Button busy={refreshing} onClick={refresh}>
            Refresh ranks
          </Button>
        </>
      }
      bodyless
    >
      <div className="card-body stack tight" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="row wrap">
          <input
            className="input"
            style={{ maxWidth: 320 }}
            placeholder="Seed topic (optional), e.g. AP automation"
            value={seed}
            onChange={(e) => setSeed(e.target.value)}
            aria-label="Keyword seed"
          />
          <Button variant="primary" busy={suggesting} onClick={suggest}>
            Suggest keywords
          </Button>
          {ideas ? <SourceBadge source={ideas.source} /> : null}
        </div>
        {ideas ? (
          <div className="stack tight">
            <div className="table-wrap card">
              <table className="table">
                <thead>
                  <tr>
                    <th style={{ width: 32 }} />
                    <th>Keyword</th>
                    <th>Intent</th>
                    <th className="num">Est. volume</th>
                    <th className="num">Difficulty</th>
                    <th>Why</th>
                  </tr>
                </thead>
                <tbody>
                  {ideas.items.map((idea) => (
                    <tr key={idea.keyword}>
                      <td>
                        <input
                          type="checkbox"
                          aria-label={`Select ${idea.keyword}`}
                          checked={picked.has(idea.keyword)}
                          onChange={(e) => {
                            const next = new Set(picked)
                            if (e.target.checked) next.add(idea.keyword)
                            else next.delete(idea.keyword)
                            setPicked(next)
                          }}
                        />
                      </td>
                      <td>
                        <strong>{idea.keyword}</strong>
                      </td>
                      <td>{humanize(idea.intent)}</td>
                      <td className="num">{num(idea.search_volume)}</td>
                      <td className="num">{idea.difficulty}</td>
                      <td className="subtle">{idea.rationale}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="row">
              <Button variant="primary" busy={adding} disabled={!picked.size} onClick={addPicked}>
                Track {picked.size} selected
              </Button>
              <Button variant="ghost" onClick={() => setIdeas(null)}>
                Dismiss
              </Button>
            </div>
          </div>
        ) : null}
      </div>
      <Async state={state} label="Loading keywords…">
        {(keywords) =>
          keywords.length === 0 ? (
            <Empty title="No keywords tracked yet">Use “Suggest keywords” to start a list.</Empty>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Keyword</th>
                    <th>Intent</th>
                    <th className="num">Volume</th>
                    <th className="num">Difficulty</th>
                    <th className="num">Rank</th>
                    <th className="num">Previous</th>
                    <th>Change</th>
                    <th>Updated</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {keywords.map((keyword) => (
                    <tr key={keyword.id}>
                      <td>
                        <strong>{keyword.keyword}</strong>
                      </td>
                      <td>{humanize(keyword.intent)}</td>
                      <td className="num">{num(keyword.search_volume)}</td>
                      <td className="num">{keyword.difficulty}</td>
                      <td className="num">
                        <strong>{keyword.current_rank ? `#${keyword.current_rank}` : '—'}</strong>
                      </td>
                      <td className="num subtle">{keyword.previous_rank ? `#${keyword.previous_rank}` : '—'}</td>
                      <td>
                        <RankChange change={keyword.rank_change} />
                      </td>
                      <td className="subtle">{relative(keyword.updated_at)}</td>
                      <td>
                        <Button size="sm" variant="ghost" onClick={() => void remove(keyword.id)} aria-label={`Stop tracking ${keyword.keyword}`}>
                          ×
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        }
      </Async>
    </Card>
  )
}

function GeoCard({ client }: { client: Client }) {
  const toast = useToast()
  const state = useApi(() => api.geo.overview(client.id), [client.id])
  const [prompt, setPrompt] = useState('')
  const [engines, setEngines] = useState<Engine[]>([...ENGINES])
  const [running, setRunning] = useState(false)
  const [latest, setLatest] = useState<{ checks: GeoCheck[]; note: string } | null>(null)

  async function run() {
    setRunning(true)
    try {
      const result = await api.geo.run(client.id, prompt, engines)
      setLatest({ checks: result.checks, note: result.note })
      const mentioned = result.checks.filter((c) => c.mentioned).length
      toast.success(`Named by ${mentioned} of ${result.checks.length} assistants`)
      state.reload()
    } catch (error) {
      toast.error(error)
    } finally {
      setRunning(false)
    }
  }

  return (
    <Card
      title="GEO: AI-assistant visibility"
      subtitle="Do ChatGPT, Perplexity, Gemini and Claude name this client when buyers ask?"
      bodyless
    >
      <div className="card-body stack">
        <div className="form-grid">
          <Field label="Buyer question" full>
            <input
              className="input"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={`e.g. What are the best ${client.industry.toLowerCase()} companies for ${client.target_audience.split(/[,(]/)[0].toLowerCase()}?`}
            />
          </Field>
        </div>
        <div className="row wrap">
          {ENGINES.map((engine) => (
            <label className="checkbox" key={engine}>
              <input
                type="checkbox"
                checked={engines.includes(engine)}
                onChange={(e) => setEngines(e.target.checked ? [...engines, engine] : engines.filter((x) => x !== engine))}
              />
              {ENGINE_LABELS[engine]}
            </label>
          ))}
          <span className="grow" />
          <Button variant="primary" busy={running} disabled={prompt.trim().length < 3 || !engines.length} onClick={run}>
            Run check
          </Button>
        </div>
        {latest ? (
          <div className="stack tight">
            <span className="subtle">{latest.note}</span>
            <div className="grid kpis">
              {latest.checks.map((check) => (
                <div key={check.id} className="card kpi">
                  <span className="label">{ENGINE_LABELS[check.engine]}</span>
                  <span className="value" style={{ fontSize: 20 }}>
                    {check.mentioned ? (check.position ? `Named #${check.position}` : 'Named') : 'Not named'}
                  </span>
                  <Badge tone={check.method === 'live' ? 'violet' : 'orange'} plain>
                    {check.method}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>
      <Async state={state} label="Loading GEO checks…">
        {(geo) =>
          geo.checks.length === 0 ? (
            <Empty title="No GEO checks yet">Ask a question buyers would ask an AI assistant.</Empty>
          ) : (
            <div className="grid main-side" style={{ padding: 20, borderTop: '1px solid var(--border)' }}>
              <div className="table-wrap card">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Buyer question</th>
                      {ENGINES.map((engine) => (
                        <th key={engine}>{ENGINE_LABELS[engine]}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {geo.prompts.map((question) => (
                      <tr key={question}>
                        <td style={{ maxWidth: 320 }}>{question}</td>
                        {ENGINES.map((engine) => {
                          const check = geo.checks.find((c) => c.prompt === question && c.engine === engine)
                          return (
                            <td key={engine} title={check?.excerpt}>
                              {!check ? (
                                <span className="subtle">—</span>
                              ) : check.mentioned ? (
                                <Badge tone="green">{check.position ? `#${check.position}` : 'Yes'}</Badge>
                              ) : (
                                <Badge tone="neutral">No</Badge>
                              )}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="stack tight">
                <div className="section-title">Visibility by engine</div>
                <BarList
                  items={geo.by_engine.map((engine) => ({
                    label: ENGINE_LABELS[engine.engine],
                    value: engine.visibility_pct,
                    note: `${engine.mentioned}/${engine.checks} · ${engine.method}`,
                  }))}
                  max={100}
                  format={(v) => pct(v)}
                />
                <span className="subtle">
                  Engines without a configured API key are simulated, weighted by the client's current AI visibility.
                </span>
              </div>
            </div>
          )
        }
      </Async>
    </Card>
  )
}
