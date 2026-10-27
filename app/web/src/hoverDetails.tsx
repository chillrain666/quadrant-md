import { useCallback, useEffect, useRef, useState, type MouseEvent, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { renderInline } from './inline'

/** Lines shown before the tooltip stops listing them. */
const MAX_LINES = 12
/** Hover intent delay: long enough not to flash while the mouse crosses rows. */
const DELAY_MS = 220

interface TipState {
  detail: string[]
  pos: { top: number; left: number; maxWidth: number; above: boolean }
}

/**
 * Hover tooltip that renders a task's detail lines with the same lightweight
 * markdown as the rest of the UI (`**bold**`, `` `code` ``).
 *
 * Native `title` attributes cannot render markup, so this draws a portal instead.
 * It is `pointer-events: none`, which keeps clicking, dragging and scrolling on the
 * row working exactly as before.
 *
 * One hook per list, not per row: `bind()` gives each row its handlers and the list
 * renders `node` once.
 */
export function useHoverTip() {
  const [tip, setTip] = useState<TipState | null>(null)
  const timer = useRef<number | null>(null)

  const clear = useCallback(() => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current)
      timer.current = null
    }
    setTip(null)
  }, [])

  useEffect(() => clear, [clear])

  const bind = useCallback(
    (detail: string[], fallback: string) => ({
      title: detail.length ? undefined : fallback,
      onMouseEnter: (e: MouseEvent<HTMLElement>) => {
        if (!detail.length) return
        const el = e.currentTarget
        if (timer.current !== null) window.clearTimeout(timer.current)
        timer.current = window.setTimeout(() => {
          const r = el.getBoundingClientRect()
          const above = r.bottom + 240 > window.innerHeight
          setTip({
            detail,
            pos: {
              top: above ? r.top - 8 : r.bottom + 6,
              left: Math.min(r.left, Math.max(8, window.innerWidth - 480)),
              maxWidth: Math.min(520, Math.max(280, r.width)),
              above,
            },
          })
        }, DELAY_MS)
      },
      onMouseLeave: clear,
    }),
    [clear],
  )

  const lines = (tip?.detail ?? []).map((line) => line.replace(/^\s+/, '')).filter(Boolean)
  const shown = lines.slice(0, MAX_LINES)
  const extra = lines.length - shown.length

  const node: ReactNode =
    tip && shown.length ? (
      createPortal(
        <div
          className={`hover-tip${tip.pos.above ? ' above' : ''}`}
          role="tooltip"
          style={{ top: tip.pos.top, left: tip.pos.left, maxWidth: tip.pos.maxWidth }}
        >
          {shown.map((line, i) => (
            <div className="hover-line" key={i}>
              {renderInline(line)}
            </div>
          ))}
          {extra > 0 ? <div className="hover-more">+{extra}</div> : null}
        </div>,
        document.body,
      )
    ) : null

  return { bind, node }
}
