import { Fragment, useMemo, useState, type DragEvent } from 'react'
import { groupLabel, useT } from '../i18n'
import type { Meta, Status, Task, TaskGroup, TasksResponse } from '../types'
import { NewTaskForm } from './NewTaskForm'
import { TaskRow, type DropPosition } from './TaskRow'

interface Props {
  data: TasksResponse
  meta: Meta | null
  onSelect: (task: Task) => void
  onStatus: (task: Task, next: Status) => void
  onMove: (mover: string, anchor: string, position: DropPosition) => void
  /** Cross-cell drag: change P/U (optionally with a drop target, for exact insertion) */
  onCellDrop: (
    id: string,
    p: number,
    u: number,
    anchorId?: string,
    position?: DropPosition,
  ) => void
  onCreated: () => void
}

const P_ROWS = [1, 2, 3]
const U_COLS = [1, 2, 3]
const P_HINT: Record<number, string> = { 1: 'axis.p1', 2: 'axis.p2', 3: 'axis.p3' }
const U_HINT: Record<number, string> = { 1: 'axis.u1', 2: 'axis.u2', 3: 'axis.u3' }

function cellPU(key: string): [number, number] | null {
  const m = /^P([1-3])U([1-3])$/.exec(key)
  return m ? [Number(m[1]), Number(m[2])] : null
}

export function TaskList({
  data,
  meta,
  onSelect,
  onStatus,
  onMove,
  onCellDrop,
  onCreated,
}: Props) {
  const { t, lang } = useT()
  const [drag, setDrag] = useState<{ id: string; group: string } | null>(null)
  const [target, setTarget] = useState<{ id: string; position: DropPosition } | null>(null)
  const [overCell, setOverCell] = useState<string | null>(null)
  const [newFor, setNewFor] = useState<string | null>(null)

  const files = meta?.files ?? []
  const byKey = useMemo(() => new Map(data.groups.map((g) => [g.key, g])), [data.groups])
  const canCrossCell = data.groupBy === 'p9'

  function handleDragStart(e: DragEvent<HTMLDivElement>, task: Task, group: string) {
    if (!task.id) return
    setDrag({ id: task.id, group })
    e.dataTransfer.effectAllowed = 'move'
    // Firefox will not start a drag unless setData is called
    e.dataTransfer.setData('text/plain', task.id)
  }

  function handleDragOver(e: DragEvent<HTMLDivElement>, task: Task, group: string) {
    if (!drag || !task.id) return
    if (drag.group === group) {
      // Same cell: reorder
      if (drag.id === task.id) return
      e.preventDefault()
      e.dataTransfer.dropEffect = 'move'
      const rect = e.currentTarget.getBoundingClientRect()
      const position: DropPosition = e.clientY < rect.top + rect.height / 2 ? 'before' : 'after'
      if (target?.id !== task.id || target.position !== position) {
        setTarget({ id: task.id, position })
      }
      return
    }
    // Different cell: change P/U
    if (canCrossCell && cellPU(group)) {
      e.preventDefault()
      e.dataTransfer.dropEffect = 'move'
      if (overCell !== group) setOverCell(group)
    }
  }

  function handleDrop(e: DragEvent<HTMLDivElement>, task: Task, group: string) {
    if (!drag || !task.id || drag.id === task.id) {
      clearDrag()
      return
    }
    e.preventDefault()
    e.stopPropagation() // do not let the cell's drop handler run as well

    const rect = e.currentTarget.getBoundingClientRect()
    const position: DropPosition = e.clientY < rect.top + rect.height / 2 ? 'before' : 'after'

    if (drag.group === group) {
      // No-op check: it is already there, so do not write.
      // Otherwise you get "nothing looks different, yet the global position moved
      // by a dozen entries" behaviour.
      const ids = byKey.get(group)?.tasks.map((t) => t.id) ?? []
      const moverIdx = ids.indexOf(drag.id)
      const anchorIdx = ids.indexOf(task.id)
      const alreadyThere =
        position === 'before' ? anchorIdx === moverIdx + 1 : anchorIdx === moverIdx - 1
      if (!alreadyThere) onMove(drag.id, task.id, position)
    } else if (canCrossCell) {
      const pu = cellPU(group)
      if (pu) onCellDrop(drag.id, pu[0], pu[1], task.id, position)
    }
    clearDrag()
  }

  function handleCellDragOver(e: DragEvent<HTMLElement>, key: string) {
    if (!drag || !canCrossCell || drag.group === key) return
    if (!cellPU(key)) return
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    if (overCell !== key) setOverCell(key)
  }

  function handleCellDrop(e: DragEvent<HTMLElement>, key: string) {
    if (!drag || !canCrossCell || drag.group === key) return
    const pu = cellPU(key)
    if (!pu) return
    e.preventDefault()
    e.stopPropagation()
    onCellDrop(drag.id, pu[0], pu[1])
    clearDrag()
  }

  function clearDrag() {
    setDrag(null)
    setTarget(null)
    setOverCell(null)
  }

  function rowsOf(group: TaskGroup, compact: boolean) {
    return group.tasks.map((task) => {
      const key = task.id ?? `${task.file}:${task.line}`
      return (
        <TaskRow
          key={key}
          task={task}
          groupKey={group.key}
          today={data.today}
          dragging={drag?.id === task.id}
          dropPosition={target?.id === task.id && drag?.id !== task.id ? target.position : null}
          onSelect={onSelect}
          onStatus={onStatus}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onDragEnd={clearDrag}
          compact={compact}
        />
      )
    })
  }

  function newFormFor(fallbackFile: string, p?: number, u?: number) {
    return (
      <NewTaskForm
        files={files}
        defaultFile={fallbackFile || files[0]?.file || ''}
        defaultP={p ?? null}
        defaultU={u ?? null}
        onClose={() => setNewFor(null)}
        onCreated={onCreated}
      />
    )
  }

  if (!data.groups.length) {
    return <p className="empty">{t('board.empty')}</p>
  }

  // ------------------------------------------------ 3x3 grid (default view)
  if (data.groupBy === 'p9') {
    const unclassified = byKey.get('PU-')
    return (
      <div className="groups">
        <div className="grid9">
          <div className="corner" />
          {U_COLS.map((u) => (
            <div className="collabel" key={`c${u}`}>
              <b>U{u}</b>
              <span>{t(U_HINT[u])}</span>
            </div>
          ))}

          {P_ROWS.map((p) => (
            <Fragment key={`r${p}`}>
              <div className="rowlabel">
                <b>P{p}</b>
                <span>{t(P_HINT[p])}</span>
              </div>
              {U_COLS.map((u) => {
                const key = `P${p}U${u}`
                const group = byKey.get(key)
                const empty = !group || group.count === 0
                const isDropTarget = overCell === key && drag?.group !== key
                return (
                  <section
                    className={[
                      'cell',
                      empty ? 'is-empty' : '',
                      isDropTarget ? 'drop-target' : '',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                    key={key}
                    data-p={p}
                    data-u={u}
                    onDragOver={(e) => handleCellDragOver(e, key)}
                    onDragLeave={(e) => {
                      const el = e.currentTarget as HTMLElement
                      if (!el.contains(e.relatedTarget as Node)) {
                        setOverCell((c) => (c === key ? null : c))
                      }
                    }}
                    onDrop={(e) => handleCellDrop(e, key)}
                  >
                    <header className="cell-head">
                      <span className="cell-name">P{p}·U{u}</span>
                      <span className="count">{group?.count ?? 0}</span>
                      <button
                        className="add"
                        title={t('board.newIn', { where: `P${p}·U${u}` })}
                        onClick={() => setNewFor(newFor === key ? null : key)}
                      >
                        ＋
                      </button>
                    </header>

                    {newFor === key ? newFormFor(group?.tasks[0]?.file ?? '', p, u) : null}

                    <div className="cell-body">
                      {empty ? (
                        <span className="cell-empty">—</span>
                      ) : (
                        rowsOf(group as TaskGroup, true)
                      )}
                    </div>
                  </section>
                )
              })}
            </Fragment>
          ))}
        </div>

        {unclassified && unclassified.count > 0 ? (
          <section className="group uncat">
            <header className="group-head">
              <h2>{t('board.unclassified')}</h2>
              <span className="count">{unclassified.count}</span>
              <button className="add" onClick={() => setNewFor(newFor === 'PU-' ? null : 'PU-')}>
                {t('board.new')}
              </button>
            </header>
            {newFor === 'PU-' ? newFormFor(unclassified.tasks[0]?.file ?? '') : null}
            <div className="rows">{rowsOf(unclassified, false)}</div>
          </section>
        ) : null}
      </div>
    )
  }

  // ------------------------------------------------ plain grouped list
  return (
    <div className="groups">
      {data.groups.map((group) => (
        <section className="group" key={group.key}>
          <header className="group-head">
            <h2>{groupLabel(lang, group.key, group.label)}</h2>
            <span className="count">{group.count}</span>
            <button
              className="add"
              onClick={() => setNewFor(newFor === group.key ? null : group.key)}
            >
              {t('board.new')}
            </button>
          </header>

          {newFor === group.key ? newFormFor(group.tasks[0]?.file ?? '') : null}

          <div className="rows">{rowsOf(group, false)}</div>
        </section>
      ))}
    </div>
  )
}
