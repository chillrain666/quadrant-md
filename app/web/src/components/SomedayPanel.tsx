import { useListDrag } from '../dragList'
import { renderInline } from '../inline'
import { useT } from '../i18n'
import type { Task, TasksResponse } from '../types'

interface Props {
  data: TasksResponse | null
  onSelect: (task: Task) => void
  /** Full order after dragging cards (scope=someday) */
  onReorder: (keys: string[]) => void
}

/** Strip the leading timestamp from an idea entry (`2026-10-20 — xxx` -> `xxx`) */
function stripStamp(title: string): string {
  return title.replace(/^\d{4}-\d{2}-\d{2}\s*[—\-–]\s*/, '')
}

/**
 * Someday panel: **summary only**.
 *
 * Each card shows the title (up to two lines) plus one detail line; the full
 * text opens on click, because ideas tend to be long and would drown the list.
 * Cards can be dragged to reorder.
 */
export function SomedayPanel({ data, onSelect, onReorder }: Props) {
  const { t } = useT()
  const items = data?.groups[0]?.tasks ?? []
  // Cards are laid out in a grid (possibly several columns), so both axes matter
  const drag = useListDrag(
    items.map((t) => t.id ?? t.raw),
    onReorder,
    { axis: 'grid' },
  )

  if (!data) return <p className="empty">{t('board.loading')}</p>

  if (!items.length) {
    return (
      <p className="empty">
        {t('someday.empty')}
      </p>
    )
  }

  return (
    <div className="someday-wrap">
      {items.map((task) => {
        const key = task.id ?? task.raw
        const first = task.detail.find((d) => d.trim())
        return (
          <div
            className={`someday-item ${drag.cls(key)}`}
            key={key}
            onClick={() => onSelect(task)}
            title={t('someday.open')}
            {...drag.handlers(key)}
          >
            <span className="someday-title">{renderInline(stripStamp(task.title))}</span>
            {first ? <span className="someday-sum">{first.trim()}</span> : null}
            <span className="someday-foot">
              {task.id ? <span className="badge id">{task.id}</span> : null}
              <span className="muted">
                {task.detail.length ? t('someday.detailLines', { n: task.detail.length }) : t('someday.noDetails')}
              </span>
            </span>
          </div>
        )
      })}
    </div>
  )
}
