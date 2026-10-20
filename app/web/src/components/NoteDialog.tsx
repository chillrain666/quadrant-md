import { useEffect } from 'react'
import { renderInline } from '../inline'
import { useT } from '../i18n'
import type { Task } from '../types'

interface Props {
  task: Task
  onClose: () => void
}

/** An ID-less idea entry (a plain bullet in someday): read-only detail view. */
export function NoteDialog({ task, onClose }: Props) {
  const { t } = useT()
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      className="modal-wrap"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="modal">
        <header className="modal-head">
          <h2>{t('note.title')}</h2>
          <button className="icon" onClick={onClose} title={t('drawer.close')}>
            ×
          </button>
        </header>

        <div className="modal-body">
          <p className="note-title">{renderInline(task.title)}</p>
          {task.detail.length ? (
            <pre className="detail-text">{task.detail.join('\n').trim()}</pre>
          ) : (
            <p className="muted">{t('note.empty')}</p>
          )}
          <p className="muted">
            {task.file}:{task.line}
          </p>
        </div>

        <footer className="modal-foot">
          <button className="primary" onClick={onClose}>
            {t('note.close')}
          </button>
        </footer>
      </div>
    </div>
  )
}
