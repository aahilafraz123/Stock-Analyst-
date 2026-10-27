import { Fragment, useId, useState } from 'react'
import { useRequest } from '../hooks/useRequest'
import { askFilings, getErrorDetail, getRagDocuments } from '../services/api'
import { formatInteger, formatMs } from '../utils/format'
import ErrorNotice from './ErrorNotice'

const SUGGESTED_QUESTIONS = [
  'How did revenue and margins change in the most recent quarter?',
  'What are the most significant risks management highlights?',
  'What guidance did management give on the latest earnings call?',
]

/** Question answering over the ticker's 10-K, 10-Q and earnings-call text, with citations. */
export default function AskFilings({ ticker }) {
  const [draft, setDraft] = useState('')
  const [query, setQuery] = useState(null) // { question, n } — n makes repeated questions re-run
  const idPrefix = useId()

  const docs = useRequest(ticker, (signal) => getRagDocuments(ticker, { signal }))
  const answer = useRequest(query && `${ticker}:${query.n}`, (signal) =>
    askFilings(ticker, query.question, { signal }),
  )

  const indexed = answer.data?.documents ?? docs.data?.documents?.length ?? null
  const firstRun = !indexed

  const submit = (text) => {
    const question = text.trim()
    if (question.length < 3 || answer.loading) return
    setDraft(question)
    setQuery((prev) => ({ question, n: (prev?.n ?? 0) + 1 }))
  }

  return (
    <section className="panel" aria-labelledby="ask-title">
      <div className="panel-title">
        <span id="ask-title">ASK THE FILINGS</span>
        <span style={styles.docCount} data-testid="indexed-count">
          {docs.loading && indexed == null
            ? 'CHECKING INDEX…'
            : indexed
              ? `${indexed} DOCUMENT${indexed === 1 ? '' : 'S'} INDEXED${docs.data?.retrieval ? ` · ${docs.data.retrieval.toUpperCase()}` : ''}`
              : 'NOT INDEXED YET'}
        </span>
      </div>

      <form
        style={styles.form}
        onSubmit={(e) => {
          e.preventDefault()
          submit(draft)
        }}
      >
        <label htmlFor={`${idPrefix}-q`} className="sr-only">
          Ask a question about {ticker}'s filings
        </label>
        <span style={styles.prompt} aria-hidden="true">?</span>
        <input
          id={`${idPrefix}-q`}
          style={styles.input}
          value={draft}
          maxLength={500}
          placeholder={`Ask about ${ticker}'s 10-K, 10-Q or earnings call…`}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button type="submit" className="btn btn--primary" style={styles.askBtn} disabled={answer.loading || draft.trim().length < 3}>
          ASK →
        </button>
      </form>

      <div style={styles.suggestions}>
        {SUGGESTED_QUESTIONS.map((q) => (
          <button key={q} type="button" className="btn btn--small" style={styles.suggestion} disabled={answer.loading} onClick={() => submit(q)}>
            {q}
          </button>
        ))}
      </div>

      {answer.loading && (
        <div style={styles.loading} role="status" aria-live="polite">
          <span className="spinner spinner--sm" aria-hidden="true" />
          {firstRun
            ? `Indexing ${ticker}'s filings and earnings calls for the first time. This can take up to a minute…`
            : 'Retrieving relevant passages and drafting a cited answer…'}
        </div>
      )}

      {answer.error && (
        <div style={{ marginTop: '16px' }}>
          <ErrorNotice title="COULD NOT ANSWER" detail={getErrorDetail(answer.error)} onRetry={answer.reload} compact />
        </div>
      )}

      {answer.data && <Answer data={answer.data} idPrefix={idPrefix} />}
    </section>
  )
}

function Answer({ data, idPrefix }) {
  const sources = data.sources || []
  const anchor = (i) => `${idPrefix}-src-${i}`

  return (
    <div style={styles.answer} aria-live="polite">
      <div style={styles.question}>Q · {data.question}</div>
      <p style={styles.answerText} data-testid="answer-text">
        {(data.answer || []).map((segment, i) => {
          const cited = [...new Set((segment.citations || []).map((c) => c.source))].filter((n) => sources[n])
          return (
            <Fragment key={i}>
              {segment.text}
              {cited.map((n) => {
                const quote = segment.citations.find((c) => c.source === n)?.citedText
                return (
                  <sup key={n} style={styles.sup}>
                    <a href={`#${anchor(n)}`} style={styles.marker} title={quote || sources[n].label} aria-label={`Source ${n + 1}`}>
                      {n + 1}
                    </a>
                  </sup>
                )
              })}
            </Fragment>
          )
        })}
      </p>

      {sources.length > 0 && (
        <ol style={styles.sourceList} aria-label="Answer sources">
          {sources.map((s, i) => (
            <li key={s.chunkId || i} id={anchor(i)} className="ask-source" style={styles.source}>
              <span style={styles.sourceNum}>{i + 1}</span>
              <div style={styles.sourceBody}>
                <div style={styles.sourceHead}>
                  <span style={styles.sourceLabel}>{s.label}</span>
                  {s.date && <span style={styles.sourceDate}>{s.date}</span>}
                </div>
                {s.excerpt && <p style={styles.excerpt}>“{s.excerpt.trim()}”</p>}
                {s.url && (
                  <a href={s.url} target="_blank" rel="noopener noreferrer" style={styles.link}>
                    Open filing ↗
                  </a>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}

      {data.meta && (
        <div style={styles.meta}>
          {[data.meta.model, data.meta.latencyMs != null && formatMs(data.meta.latencyMs), data.meta.inputTokens != null && `${formatInteger(data.meta.inputTokens)} in / ${formatInteger(data.meta.outputTokens)} out tokens`]
            .filter(Boolean)
            .join(' · ')}
        </div>
      )}
    </div>
  )
}

const mono = { fontFamily: 'var(--font-mono)' }

const styles = {
  docCount: { ...mono, letterSpacing: '1.5px', fontSize: '9px', color: 'var(--text-secondary)' },
  form: { display: 'flex', alignItems: 'stretch', border: '1px solid var(--border-bright)', background: 'var(--bg-secondary)' },
  prompt: { ...mono, display: 'flex', alignItems: 'center', padding: '0 12px', color: 'var(--accent-green)', fontSize: '15px' },
  input: {
    flex: 1,
    minWidth: 0,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-sans)',
    fontSize: '14px',
    padding: '12px 0',
  },
  askBtn: { padding: '0 18px' },
  suggestions: { display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '10px' },
  suggestion: { whiteSpace: 'normal', textAlign: 'left', letterSpacing: '0.5px', fontFamily: 'var(--font-sans)', fontSize: '11px' },
  loading: {
    ...mono,
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginTop: '16px',
    fontSize: '11px',
    lineHeight: 1.5,
    color: 'var(--accent-blue)',
  },
  answer: { marginTop: '20px', paddingTop: '18px', borderTop: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '14px' },
  question: { ...mono, fontSize: '10px', letterSpacing: '1px', color: 'var(--text-muted)' },
  answerText: { fontSize: '14px', lineHeight: 1.75, color: 'var(--text-primary)' },
  sup: { lineHeight: 0, marginLeft: '2px' },
  marker: {
    ...mono,
    fontSize: '10px',
    color: 'var(--accent-blue)',
    padding: '0 2px',
    borderBottom: '1px solid rgba(68, 136, 255, 0.4)',
  },
  sourceList: { listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '1px', background: 'var(--border)', border: '1px solid var(--border)' },
  source: { display: 'flex', gap: '12px', padding: '12px 14px', background: 'var(--bg-secondary)', scrollMarginTop: '80px' },
  sourceNum: { ...mono, fontSize: '11px', fontWeight: 700, color: 'var(--accent-blue)', minWidth: '14px' },
  sourceBody: { display: 'flex', flexDirection: 'column', gap: '6px', minWidth: 0 },
  sourceHead: { display: 'flex', flexWrap: 'wrap', gap: '4px 12px', alignItems: 'baseline' },
  sourceLabel: { fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', overflowWrap: 'anywhere' },
  sourceDate: { ...mono, fontSize: '9px', color: 'var(--text-muted)' },
  excerpt: {
    fontSize: '11px',
    lineHeight: 1.6,
    color: 'var(--text-secondary)',
    fontStyle: 'italic',
    display: '-webkit-box',
    WebkitLineClamp: 4,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  link: { ...mono, fontSize: '10px', color: 'var(--accent-green)', alignSelf: 'flex-start' },
  meta: { ...mono, fontSize: '9px', letterSpacing: '1px', color: 'var(--text-muted)' },
}
