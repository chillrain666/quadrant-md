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
 * Task editor: a small centred dialog.
 *
 * It used to be a right-hand drawer. Why a compact modal now:
 * - the drawer was full height, so a form with six fields looked enormous;
 * - editing one task rarely means comparing it with the task below, so covering
 *   the board is acceptable;
 * - a narrow (<= 640px) dialog keeps the type tight and the eye on one column.
 *
 * The detail block is edited as plain Markdown lines and written back into the
 * file as the indented lines under the task (see writer.set_details).
 */
export function TaskDrawer({ task, onClose, onSaved, onDeleted }: Props) {
  const { t } = useT()
  const [title, setTitle] = useState('')
  const [p, setP] = useState('')
  const [u, setU] = useState('')
  const [status, setStatus] = useState<Status>('todo')
  const [ddl, setDdl] = useState('')
  const [tags, setTags] = useState('')
  const [details, setDetails] = useState('')
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
    setDetails(t.detail.map((line) => line.replace(/^\s+/, '')).join('\n'))
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
      // Only touch the file again when the detail block really changed
      const before = task.detail.map((line) => line.trim()).join('\n')
      const after = details
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .join('\n')
      if (before !== after) {
        await api.setDetails(task.id, details.split('\n'))
      }
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

          <label className="field">
            <span>{t('drawer.field.details')}</span>
            <textarea
              className="details-input"
              rows={4}
              value={details}
              placeholder={t('drawer.detailsPlaceholder')}
              onChange={(e) => setDetails(e.target.value)}
            />
            <small className="muted">{t('drawer.detailsHint')}</small>
          </label>

          <details className="field raw-block">
            <summary>{t('drawer.field.raw')}</summary>
            <pre className="raw">{task.raw}</pre>
          </details>

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
