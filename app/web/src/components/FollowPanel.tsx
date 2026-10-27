import { useState } from 'react'
import { api } from '../api'
import { useListDrag } from '../dragList'
import { useHoverTip } from '../hoverDetails'
import { renderInline } from '../inline'
import { useT } from '../i18n'
import type { Status, Task, TaskGroup, TasksResponse } from '../types'

/**
 * Follow panel: lists such as shows, serials or books in progress.
 *
 * Deliberately small: one card per file, no P/U, no DDL.
 * Ticking means finished (unticking means still in progress); clicking opens the drawer.
 * Rows can be dragged to reorder (scope = `follow:<card name>`).
 */
interface Props {
  data: TasksResponse | null
  onSelect: (task: Task) => void
  onStatus: (task: Task, next: Status) => void
  onCreated: () => void
  onReorder: (scope: string, keys: string[]) => void
}

export function FollowPanel({ data, onSelect, onStatus, onCreated, onReorder }: Props) {
  const { t } = useT()
  if (!data) return <p className="empty">{t('board.loading')}</p>
  if (!data.groups.length) {
    return <p className="empty">{t('follow.empty')}</p>
  }

  return (
    <div className="follow-wrap">
      {data.groups.map((group) => (
        <FollowGroup
          key={group.key}
          group={group}
          onSelect={onSelect}
          onStatus={onStatus}
          onCreated={onCreated}
          onReorder={(keys) => onReorder(`follow:${group.key}`, keys)}
        />
      ))}
    </div>
  )
}

interface GroupProps {
  group: TaskGroup
  onSelect: (task: Task) => void
  onStatus: (task: Task, next: Status) => void
  onCreated: () => void
  onReorder: (keys: string[]) => void
}

function FollowGroup({ group, onSelect, onStatus, onCreated, onReorder }: GroupProps) {
  const { t } = useT()
  const hover = useHoverTip()
  const [adding, setAdding] = useState(false)
  const [title, setTitle] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const drag = useListDrag(
    group.tasks.map((t) => t.id ?? t.raw),
    onReorder,
  )

  async function submit() {
    const t = title.trim()
    if (!t || busy) return
    setBusy(true)
    setErr('')
    try {
      await api.create({ file: group.tasks[0]?.file ?? '', title: t })
      setTitle('')
      setAdding(false)
      onCreated()
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="follow-card">
      {hover.node}
      <header className="follow-head">
        <h2>{group.label}</h2>
        <span className="count">{group.count}</span>
        <button
          className="add"
          title={t('follow.addTo', { what: group.label })}
          onClick={() => {
            setAdding((v) => !v)
            setTitle('')
            setErr('')
          }}
        >
          ＋
        </button>
      </header>

      {adding ? (
        <div className="follow-add">
          <input
            autoFocus
            value={title}
            placeholder={t('follow.placeholder')}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void submit()
              if (e.key === 'Escape') setAdding(false)
            }}
          />
          <button onClick={() => void submit()} disabled={busy}>
            {busy ? '…' : t('follow.add')}
          </button>
        </div>
      ) : null}

      {err ? <p className="error">{err}</p> : null}

      <div className="follow-rows">
        {group.tasks.map((task) => {
          const key = task.id ?? task.raw
          return (
            <div
              className={`follow-row ${task.status} ${drag.cls(key)}`}
              key={key}
              onClick={() => onSelect(task)}
              {...hover.bind(task.detail, t('row.editHint'))}
              {...drag.handlers(key)}
            >
              <button
                className={`check ${task.status}`}
                title={task.status === 'done' ? t('follow.markInProgress') : t('follow.markFinished')}
                onClick={(e) => {
                  e.stopPropagation()
                  onStatus(task, task.status === 'done' ? 'todo' : 'done')
                }}
              >
                {task.status === 'done' ? '✓' : task.status === 'blocked' ? '!' : ''}
              </button>
              <span className="follow-title">
                {task.title ? renderInline(task.title) : t('row.noTitle')}
              </span>
            </div>
          )
        })}
      </div>
    </section>
  )
}
