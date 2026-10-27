import type { DragEvent } from 'react'
import { fileLabel } from '../fileLabel'
import { useHoverTip } from '../hoverDetails'
import { useT } from '../i18n'
import { renderInline } from '../inline'
import type { Status, Task } from '../types'

export type DropPosition = 'before' | 'after'

interface Props {
  task: Task
  groupKey: string
  today: string
  dragging: boolean
  dropPosition: DropPosition | null
  onSelect: (task: Task) => void
  onStatus: (task: Task, next: Status) => void
  onDragStart: (e: DragEvent<HTMLDivElement>, task: Task, groupKey: string) => void
  onDragOver: (e: DragEvent<HTMLDivElement>, task: Task, groupKey: string) => void
  onDrop: (e: DragEvent<HTMLDivElement>, task: Task, groupKey: string) => void
  onDragEnd: () => void
  compact?: boolean
}

export function TaskRow({
  task,
  groupKey,
  today,
  dragging,
  dropPosition,
  onSelect,
  onStatus,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
  compact = false,
}: Props) {
  const { t } = useT()
  const hover = useHoverTip()
  return (
    <div
      className={[
        'row',
        compact ? 'compact' : '',
        task.status === 'done' ? 'done' : '',
        task.status === 'blocked' ? 'blocked' : '',
        dragging ? 'dragging' : '',
        dropPosition ? `drop-${dropPosition}` : '',
      ]
        .filter(Boolean)
        .join(' ')}
      draggable={Boolean(task.id)}
      onDragStart={(e) => onDragStart(e, task, groupKey)}
      onDragOver={(e) => onDragOver(e, task, groupKey)}
      onDrop={(e) => onDrop(e, task, groupKey)}
      onDragEnd={onDragEnd}
      onClick={() => onSelect(task)}
      {...hover.bind(task.detail, t('row.edit'))}
    >
      {hover.node}

      <span className="grip" title={t('row.drag')}>
        ⠿
      </span>

      <button
        className={`check ${task.status}`}
        title={task.status === 'done' ? t('row.markTodo') : t('row.markDone')}
        onClick={(e) => {
          e.stopPropagation() // do not open the edit drawer as well
          onStatus(task, task.status === 'done' ? 'todo' : 'done')
        }}
      >
        {task.status === 'done' ? '✓' : task.status === 'blocked' ? '!' : ''}
      </button>

      <div className="body">
        <div className="title">{task.title ? renderInline(task.title) : t('row.noTitle')}</div>

        <div className="meta">
          {/* Which file this task lives in, leftmost so it reads as a column */}
          <span className="badge tag file-chip" title={task.file}>
            {fileLabel(task.file)}
          </span>

          {/* In the grid the cell header already says P/U, repeating it is noise */}
          {compact ? null : task.p ? <span className={`badge p${task.p}`}>P{task.p}</span> : null}
          {compact ? null : task.u ? <span className={`badge u${task.u}`}>U{task.u}</span> : null}
          {task.ddl ? (
            <span
              className={
                task.status !== 'done' && task.ddl < today ? 'badge ddl overdue' : 'badge ddl'
              }
            >
              {task.ddl}
              {task.ddlTime ? ` ${task.ddlTime}` : ''}
            </span>
          ) : null}
          {task.tags.map((t) => (
            <span className="badge tag" key={t}>
              #{t}
            </span>
          ))}
          {compact ? null : task.id ? <span className="badge id">{task.id}</span> : null}
        </div>
      </div>
    </div>
  )
}
