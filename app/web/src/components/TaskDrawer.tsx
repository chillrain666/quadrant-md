import { useEffect, useState } from 'react'
import { api } from '../api'
import { useT } from '../i18n'
import type { Status, Task } from '../types'

interface Props {
  task: Task | null
  onClose: () => void
  onSaved: () => void
  onDeleted: () => void
}

const STATUSES: Status[] = ['todo', 'done', 'blocked']
const STATUS_KEYS: Record<Status, string> = { todo: 'status.todo', done: 'status.done', blocked: 'status.blocked' }

/**
 * Task edit drawer (slides in from the right).
 *
 * Why a drawer instead of inline expansion or a centred modal:
 * - inline expansion pushes every task below it down (and stretches grid cells),
 *   which is exactly what we want to avoid;
 * - a centred modal covers the whole board, so comparing the next task means
 *   opening and closing it repeatedly;
 * - a right-hand drawer keeps the layout stable, leaves two thirds of the board
 *   visible on wide screens, and still has room for the form.
 */
export function TaskDrawer({ task, onClose, onSaved, onDeleted }: Props) {
  const { t } = useT()
  const [title, setTitle] = useState('')
  const [p, setP] = useState('')
  const [u, setU] = useState('')
  const [status, setStatus] = useState<Status>('todo')
  const [ddl, setDdl] = useState('')
  const [tags, setTags] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  // Deleting needs confirmation: a wrong delete costs more than a wrong edit
  const [confirming, setConfirming] = useState(false)

  // Reset only when the task changes -- do not depend on the whole task object,
  // otherwise a refresh (new object identity) wipes what is being typed.
  useEffect(() => {
    const t = task
    if (!t) return
    setTitle(t.title)
    setP(t.p ? String(t.p) : '')
    setU(t.u ? String(t.u) : '')
    setStatus(t.status)
    setDdl(t.ddl ?? '')
    setTags(t.tags.join(' '))
    setErr('')
    setBusy(false)
    setConfirming(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task?.id])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  if (!task) return null

  async function save() {
    if (!task?.id || busy) return
    if (!title.trim()) {
      setErr(t('drawer.titleRequired'))
      return
    }
    setBusy(true)
    setErr('')
    try {
      await api.updateTask(task.id, {
        title: title.trim(),
        p: p ? Number(p) : null,
        u: u ? Number(u) : null,
        status,
        ddl: ddl || null,
        tags: tags.split(/[,，\s]+/).filter(Boolean),
      })
      onSaved()
      onClose()
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    if (!task?.id || busy) return
    setBusy(true)
    setErr('')
    try {
      await api.deleteTask(task.id)
      onDeleted()
      onClose()
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      // Must reset: the drawer is never unmounted, a stale true locks the next save
      setBusy(false)
    }
  }

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label={t('drawer.title')}>
        <header className="drawer-head">
          <h2>{t('drawer.title')}</h2>
          <button className="icon" onClick={onClose} title={t('drawer.close')}>
            ×
          </button>
        </header>

        <div className="drawer-body">
          <label className="field">
            <span>{t('drawer.field.title')}</span>
            <input
              value={title}
              autoFocus
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void save()
              }}
            />
          </label>

          <div className="field-row">
            <label className="field">
              <span>{t('drawer.field.importance')}</span>
              <select value={p} onChange={(e) => setP(e.target.value)}>
                <option value="">{t('drawer.none')}</option>
                <option value="1">{t('drawer.p1')}</option>
                <option value="2">{t('drawer.p2')}</option>
                <option value="3">{t('drawer.p3')}</option>
              </select>
            </label>
            <label className="field">
              <span>{t('drawer.field.urgency')}</span>
              <select value={u} onChange={(e) => setU(e.target.value)}>
                <option value="">{t('drawer.none')}</option>
                <option value="1">{t('drawer.u1')}</option>
                <option value="2">{t('drawer.u2')}</option>
                <option value="3">{t('drawer.u3')}</option>
              </select>
            </label>
          </div>

          <div className="field">
            <span>{t('drawer.field.status')}</span>
            <div className="segmented">
              {STATUSES.map((s) => (
                <button
                  key={s}
                  className={status === s ? 'on' : ''}
                  onClick={() => setStatus(s)}
                >
                  {t(STATUS_KEYS[s])}
                </button>
              ))}
            </div>
          </div>

          <label className="field">
            <span>{t('drawer.field.ddl')}</span>
            <div className="ddl-row">
              <input type="date" value={ddl} onChange={(e) => setDdl(e.target.value)} />
              {ddl ? (
                <button className="link" onClick={() => setDdl('')}>
                  {t('drawer.clear')}
                </button>
              ) : null}
            </div>
          </label>

          <label className="field">
            <span>{t('drawer.field.tags')}</span>
            <input
              value={tags}
              placeholder="e.g. study React"
              onChange={(e) => setTags(e.target.value)}
            />
          </label>

          <div className="field">
            <span>{t('drawer.field.details')}</span>
            {task.detail.length ? (
              <pre className="detail-text">{task.detail.join('\n').trim()}</pre>
            ) : (
              <p className="muted">{t('drawer.noDetails')}</p>
            )}
          </div>

          <div className="field">
            <span>{t('drawer.field.raw')}</span>
            <pre className="raw">{task.raw}</pre>
          </div>

          <p className="muted drawer-meta">
            {task.file}:{task.line}
            {task.id ? ` · ${task.id}` : ''}
          </p>

          {err ? <p className="error">{err}</p> : null}
        </div>

        <footer className="drawer-foot">
          {task.id ? (
            confirming ? (
              <span className="confirm-del">
                {t('drawer.deleteConfirm')}
                <button className="danger" onClick={() => void remove()} disabled={busy}>
                  {t('drawer.delete')}
                </button>
                <button onClick={() => setConfirming(false)}>Cancel</button>
              </span>
            ) : (
              <button className="danger-ghost" onClick={() => setConfirming(true)}>
                {t('drawer.delete')}
              </button>
            )
          ) : null}
          <span className="spacer" />
          <button className="primary" onClick={() => void save()} disabled={busy}>
            {busy ? t('drawer.saving') : t('drawer.save')}
          </button>
          <button onClick={onClose}>{t('drawer.cancel')}</button>
        </footer>
      </aside>
    </>
  )
}
