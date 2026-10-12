import { num } from '../lib/format'
import type { Keyword } from '../lib/types'
import { Empty } from './ui'

export function RankChange({ change }: { change: number | null }) {
  if (change === null) return <span className="subtle">new</span>
  if (change === 0) return <span className="delta flat">–</span>
  return (
    <span className={`delta ${change > 0 ? 'up' : 'down'}`} title={change > 0 ? 'Moved up' : 'Moved down'}>
      {change > 0 ? '▲' : '▼'} {Math.abs(change)}
    </span>
  )
}

export function KeywordMovers({ keywords }: { keywords: Keyword[] }) {
  if (!keywords.length) return <Empty compact title="No rank changes yet" />
  return (
    <ul className="list">
      {keywords.map((keyword) => (
        <li key={keyword.id}>
          <div className="grow">
            <strong>{keyword.keyword}</strong>
            <div className="subtle">{num(keyword.search_volume)} searches/mo</div>
          </div>
          <span className="mono muted">
            #{keyword.previous_rank} → <strong>#{keyword.current_rank}</strong>
          </span>
          <RankChange change={keyword.rank_change} />
        </li>
      ))}
    </ul>
  )
}
