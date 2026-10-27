import { useEffect, useId, useRef, useState } from 'react'

const POPOVER_WIDTH = 320
const VIEWPORT_MARGIN = 16

/**
 * A `[F3]` chip after a claim. Hover previews the source; click (or Enter)
 * pins it open until Escape, a second click, or a click elsewhere.
 */
export default function CitationChip({ id, source }) {
  // null = closed, 'hover' = transient preview, 'pinned' = opened by click
  const [mode, setMode] = useState(null)
  const [offset, setOffset] = useState(0)
  const wrapRef = useRef(null)
  const chipRef = useRef(null)
  const popoverId = useId()

  // Keep the popover inside the viewport on narrow screens.
  const place = () => {
    const rect = wrapRef.current?.getBoundingClientRect()
    if (!rect) return
    const viewport = window.innerWidth || document.documentElement.clientWidth
    const width = Math.min(POPOVER_WIDTH, viewport - VIEWPORT_MARGIN * 2)
    const overflow = rect.left + width - (viewport - VIEWPORT_MARGIN)
    setOffset(overflow > 0 ? -Math.min(overflow, rect.left - VIEWPORT_MARGIN) : 0)
  }

  const close = () => setMode(null)

  const onMouseEnter = () => {
    place()
    setMode((m) => m ?? 'hover')
  }
  const onMouseLeave = () => setMode((m) => (m === 'hover' ? null : m))
  const onClick = () => {
    if (mode === 'pinned') return close()
    place()
    setMode('pinned')
  }
  const onKeyDown = (event) => {
    if (event.key === 'Escape' && mode) {
      event.stopPropagation()
      close()
      chipRef.current?.focus()
    }
  }

  useEffect(() => {
    if (mode !== 'pinned') return undefined
    const onPointerDown = (event) => {
      if (!wrapRef.current?.contains(event.target)) setMode(null)
    }
    const onEscape = (event) => event.key === 'Escape' && setMode(null)
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onEscape)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onEscape)
    }
  }, [mode])

  const missing = !source
  return (
    <span ref={wrapRef} style={styles.wrap} onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave} onKeyDown={onKeyDown}>
      <button
        ref={chipRef}
        type="button"
        style={{ ...styles.chip, ...(missing ? styles.chipMissing : null), ...(mode ? styles.chipActive : null) }}
        aria-label={`Source ${id}${source?.label ? `: ${source.label}` : ''}`}
        aria-expanded={Boolean(mode)}
        aria-controls={mode ? popoverId : undefined}
        onClick={onClick}
      >
        [{id}]
      </button>
      {mode && (
        <span
          id={popoverId}
          role="dialog"
          aria-label={`Source ${id}`}
          style={{ ...styles.popover, left: offset, width: `min(${POPOVER_WIDTH}px, calc(100vw - ${VIEWPORT_MARGIN * 2}px))` }}
        >
          <span style={styles.card}>
            <span style={styles.head}>
              <span style={styles.idBadge}>{id}</span>
              {source?.kind && <span style={styles.kind}>{String(source.kind).toUpperCase()}</span>}
              {source?.date && <span style={styles.date}>{source.date}</span>}
            </span>
            {missing ? (
              <span style={styles.excerpt}>This source is not available in the report.</span>
            ) : (
              <>
                <span style={styles.label}>{source.label}</span>
                {source.excerpt && <span style={styles.excerpt}>“{source.excerpt.trim()}”</span>}
                {source.url && (
                  <a href={source.url} target="_blank" rel="noopener noreferrer" style={styles.link}>
                    Open source ↗
                  </a>
                )}
              </>
            )}
          </span>
        </span>
      )}
    </span>
  )
}

/** Renders the chips for a list of source ids, skipping duplicates. */
export function Citations({ ids, sources }) {
  const unique = [...new Set((ids || []).filter(Boolean))]
  if (!unique.length) return null
  return (
    <span style={styles.group}>
      {unique.map((id) => (
        <CitationChip key={id} id={id} source={sources?.[id]} />
      ))}
    </span>
  )
}

const styles = {
  group: { whiteSpace: 'normal' },
  wrap: { position: 'relative', display: 'inline-block', marginLeft: '4px' },
  chip: {
    fontFamily: 'var(--font-mono)',
    fontSize: '9px',
    lineHeight: 1,
    letterSpacing: '0.5px',
    color: 'var(--accent-blue)',
    background: 'rgba(68, 136, 255, 0.1)',
    borderWidth: '1px',
    borderStyle: 'solid',
    borderColor: 'rgba(68, 136, 255, 0.3)',
    padding: '2px 4px',
    cursor: 'pointer',
    verticalAlign: '1px',
    transition: 'background 0.15s, border-color 0.15s',
  },
  chipActive: { background: 'rgba(68, 136, 255, 0.25)', borderColor: 'var(--accent-blue)', color: 'var(--text-primary)' },
  chipMissing: { color: 'var(--text-muted)', borderStyle: 'dashed', borderColor: 'var(--border-bright)', background: 'transparent' },
  // padding-top bridges the gap so the pointer can travel from chip to popover
  popover: { position: 'absolute', top: '100%', zIndex: 30, paddingTop: '6px', display: 'block' },
  card: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    padding: '12px 14px',
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-bright)',
    borderTop: '2px solid var(--accent-blue)',
    boxShadow: '0 12px 32px rgba(0, 0, 0, 0.6)',
    textAlign: 'left',
  },
  head: { display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' },
  idBadge: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    fontWeight: 700,
    color: 'var(--bg-primary)',
    background: 'var(--accent-blue)',
    padding: '1px 5px',
  },
  kind: { fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '2px', color: 'var(--text-secondary)' },
  date: { fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', marginLeft: 'auto' },
  label: { fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.4, overflowWrap: 'anywhere' },
  excerpt: {
    fontSize: '11px',
    lineHeight: 1.55,
    color: 'var(--text-secondary)',
    fontStyle: 'italic',
    display: '-webkit-box',
    WebkitLineClamp: 6,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
    overflowWrap: 'anywhere',
  },
  link: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    letterSpacing: '1px',
    color: 'var(--accent-green)',
    alignSelf: 'flex-start',
  },
}
