import type { ReactNode } from 'react'

/**
 * Render the lightweight markdown found in titles: `**bold**` and `` `code` ``.
 *
 * Only React elements are used, **never dangerouslySetInnerHTML** -- titles are
 * user text and may contain `<`, so building HTML would risk injection.
 * Everything else (`[[wiki links]]`, ...) is shown as plain text.
 */
export function renderInline(text: string): ReactNode[] {
  const out: ReactNode[] = []
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g
  let last = 0
  let key = 0
  let m: RegExpExecArray | null

  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index))
    const token = m[0]
    if (token.startsWith('**')) {
      out.push(<strong key={key++}>{token.slice(2, -2)}</strong>)
    } else {
      out.push(<code key={key++}>{token.slice(1, -1)}</code>)
    }
    last = m.index + token.length
  }

  if (last < text.length) out.push(text.slice(last))
  return out
}
