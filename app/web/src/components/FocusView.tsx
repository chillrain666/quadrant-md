import { useListDrag } from '../dragList'
import { renderInline } from '../inline'
import type { FocusResponse, Status, Task } from '../types'
import { useT } from '../i18n'

interface Props {
  focus: FocusResponse | null
  limit: number
  onLimit: (n: number) => void
  onStatus: (task: Task, next: Status) => void
  onSelect: (task: Task) => void
  /** Full order after a drag (persisted under scope=focus) */
  onReorder: (keys: string[]) => void
}

export function FocusView({ focus, limit, onLimit, onStatus, onSelect, onReorder }: Props) {
  const { t } = useT()
  const tasks = focus?.tasks ?? []
  const drag = useListDrag(
    tasks.map((t) => t.id ?? t.raw),
    onReorder,
  )

  return (
    <div className="focus">
      <div className="focus-head">
        <h2>{t('focus.heading')}</h2>
        <label className="limit">
          {t('focus.show')}
          <select value={limit} onChange={(e) => onLimit(Number(e.target.value))}>
            {[3, 5, 7, 10, 15].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
          {t('focus.items')}
        </label>
      </div>

      <p className="hint">
        {t('focus.rule')} {t('focus.order')}
      </p>

      {!focus ? (
        <p className="empty">{t('board.loading')}</p>
      ) : focus.total === 0 ? (
        <p className="empty">
          {t('focus.empty')}
        </p>
      ) : (
        <ol className="focus-list">
          {tasks.map((task) => {
            const key = task.id ?? task.raw
            return (
              <li
                key={key}
                className={`focus-item ${drag.cls(key)}`}
                onClick={() => onSelect(task)}
                title={t('row.editHint')}
                {...drag.handlers(key)}
              >
                <span className="rank" />
                <button
                  className={`check ${task.status}`}
                  onClick={(e) => {
                    e.stopPropagation()
                    onStatus(task, task.status === 'done' ? 'todo' : 'done')
                  }}
                  title={task.status === 'done' ? t('row.markTodo') : t('row.markDone')}
                >
                  {task.status === 'done' ? '✓' : task.status === 'blocked' ? '!' : ''}
                </button>
                <div className="body">
                  <div className="title">{task.title ? renderInline(task.title) : t('row.noTitle')}</div>
                  <div className="meta">
                    {task.p ? <span className={`badge p${task.p}`}>P{task.p}</span> : null}
                    {task.u ? <span className={`badge u${task.u}`}>U{task.u}</span> : null}
                    {task.ddl ? (
                      <span
                        className={
                          task.status !== 'done' && task.ddl < focus.today
                            ? 'badge ddl overdue'
                            : 'badge ddl'
                        }
                      >
                        {task.ddl}
                      </span>
                    ) : null}
                    {task.tags.map((t) => (
                      <span className="badge tag" key={t}>
                        #{t}
                      </span>
                    ))}
                    <span className="badge file">{task.project}</span>
                  </div>
                </div>
              </li>
            )
          })}
        </ol>
      )}

      {focus && focus.total > focus.tasks.length ? (
        <p className="muted">
          {t('focus.hidden', { n: focus.total - focus.tasks.length })}
        </p>
      ) : null}
    </div>
  )
}
