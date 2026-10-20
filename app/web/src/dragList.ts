import { useState, type DragEvent } from 'react'

export type DropPosition = 'before' | 'after'
/** Which axis the drop landed on: a row list only uses y; a card grid may use x or y */
export type DropAxis = 'x' | 'y'

interface Options {
  /**
   * `row` (default): vertically stacked rows; only the top/bottom half matters.
   * `grid`: a card grid (possibly several columns); both axes are considered --
   * whichever of |dx| and |dy| is larger picks the axis, then that axis' half:
   * left/top = insert before, right/bottom = insert after.
   */
  axis?: 'row' | 'grid'
}

/**
 * Drag-to-reorder inside a panel; drop detection matches the board:
 * release on the **top half** of the target row = insert before it, **bottom half**
 * = insert after it. In a card grid the dominant axis is chosen first (relative
 * to the card centre), then the half on that axis.
 *
 * After the drop the full new order is handed back via `onReorder`; the server
 * only stores the list -- these panels each have their own default ordering, so
 * no score arithmetic is done here.
 */
export function useListDrag(
  keys: string[],
  onReorder: (next: string[]) => void,
  options: Options = {},
) {
  const axis = options.axis ?? 'row'
  const [dragKey, setDragKey] = useState<string | null>(null)
  const [target, setTarget] = useState<{
    key: string
    position: DropPosition
    axis: DropAxis
  } | null>(null)

  function clear() {
    setDragKey(null)
    setTarget(null)
  }

  function dropOf(e: DragEvent<HTMLElement>): { position: DropPosition; axis: DropAxis } {
    const rect = e.currentTarget.getBoundingClientRect()
    if (axis === 'grid') {
      // Offset from the card centre: the dominant component picks the axis, which
      // makes horizontal edges feel responsive before vertical ones
      const dx = e.clientX - (rect.left + rect.width / 2)
      const dy = e.clientY - (rect.top + rect.height / 2)
      if (Math.abs(dx) > Math.abs(dy)) {
        return { position: dx < 0 ? 'before' : 'after', axis: 'x' }
      }
      return { position: dy < 0 ? 'before' : 'after', axis: 'y' }
    }
    return { position: e.clientY < rect.top + rect.height / 2 ? 'before' : 'after', axis: 'y' }
  }

  const handlers = (key: string) => ({
    draggable: true,
    onDragStart: (e: DragEvent<HTMLElement>) => {
      setDragKey(key)
      e.dataTransfer.effectAllowed = 'move'
      e.dataTransfer.setData('text/plain', key)
    },
    onDragOver: (e: DragEvent<HTMLElement>) => {
      if (!dragKey || dragKey === key) return
      e.preventDefault()
      e.dataTransfer.dropEffect = 'move'
      const { position, axis: a } = dropOf(e)
      if (target?.key !== key || target.position !== position || target.axis !== a) {
        setTarget({ key, position, axis: a })
      }
    },
    onDrop: (e: DragEvent<HTMLElement>) => {
      e.preventDefault()
      if (!dragKey || dragKey === key) {
        clear()
        return
      }
      const { position } = dropOf(e)
      const next = keys.filter((k) => k !== dragKey)
      let idx = next.indexOf(key)
      if (idx < 0) {
        clear()
        return
      }
      if (position === 'after') idx += 1
      next.splice(idx, 0, dragKey)
      onReorder(next)
      clear()
    },
    onDragEnd: clear,
  })

  /** Row classes: being dragged / drop indicator (`drop-x` means a vertical line,
   * i.e. insert on the left or right) */
  const cls = (key: string) => {
    const parts: string[] = []
    if (dragKey === key) parts.push('dragging')
    if (target?.key === key && dragKey !== key) {
      parts.push(`drop-${target.position}`, target.axis === 'x' ? 'drop-x' : 'drop-y')
    }
    return parts.join(' ')
  }

  return { handlers, cls, dragging: Boolean(dragKey) }
}
