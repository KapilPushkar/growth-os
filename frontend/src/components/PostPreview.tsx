import { CHANNEL_LABELS } from '../lib/format'
import type { Channel } from '../lib/types'
import { Avatar } from './ui'

/** Renders a post roughly the way it will look on the destination channel. */
export function PostPreview({
  channel,
  body,
  hashtags,
  author,
}: {
  channel: Channel
  body: string
  hashtags: string[]
  author: { name: string; title: string; company: string }
}) {
  const social = channel === 'linkedin' || channel === 'x' || channel === 'instagram'
  const handle = `@${author.name.replace(/^Dr\.?\s+/i, '').split(' ')[0].toLowerCase()}`
  return (
    <article className={`post-preview ${channel}`}>
      <header>
        <Avatar name={author.name} />
        <div className="who grow">
          <strong>{author.name}</strong>
          <span className="subtle">
            {channel === 'x' ? handle : `${author.title}${author.company ? ` at ${author.company}` : ''}`}
            {social ? ' · now' : ` · ${CHANNEL_LABELS[channel]}`}
          </span>
        </div>
      </header>
      <div className="body">
        {!body ? <span className="subtle">No copy yet.</span> : social ? body : <LongForm text={body} />}
        {hashtags.length ? <div className="tags">{hashtags.join(' ')}</div> : null}
      </div>
      {social ? (
        <footer aria-hidden>
          {channel === 'x' ? (
            <>
              <span>Reply</span>
              <span>Repost</span>
              <span>Like</span>
              <span>Views</span>
            </>
          ) : (
            <>
              <span>Like</span>
              <span>Comment</span>
              <span>Repost</span>
              <span>Send</span>
            </>
          )}
        </footer>
      ) : null}
    </article>
  )
}

/** Light rendering for articles and newsletters: headings and subject lines. */
function LongForm({ text }: { text: string }) {
  return (
    <>
      {text.split('\n').map((line, i) => {
        if (line.startsWith('# ')) return <h3 key={i}>{line.slice(2)}</h3>
        if (line.startsWith('## ')) return <h4 key={i}>{line.slice(3)}</h4>
        if (line.startsWith('Subject: ')) {
          return (
            <h3 key={i} style={{ fontSize: 16 }}>
              {line.slice(9)}
            </h3>
          )
        }
        return line ? <div key={i}>{line}</div> : <div key={i} style={{ height: 10 }} />
      })}
    </>
  )
}
