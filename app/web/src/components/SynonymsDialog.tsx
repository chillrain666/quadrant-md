import { useEffect, useState } from 'react'
import { api } from '../api'
import { useT } from '../i18n'

interface Props {
  groups: string[][]
  onClose: () => void
  onSaved: () => void
}

/** Synonym settings: terms in a group are equivalent; search, tag filters and Focus all use them. */
export function SynonymsDialog({ groups, onClose, onSaved }: Props) {
  const { t } = useT()
  const [rows, setRows] = useState<string[]>(() =>
    groups.length ? groups.map((g) => g.join(', ')) : [''],
  )
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  function setRow(i: number, value: string) {
    setRows((prev) => prev.map((r, idx) => (idx === i ? value : r)))
  }

  async function save() {
    if (busy) return
    setBusy(true)
    setErr('')
    try {
      // Commas, CJK commas and whitespace all separate terms; groups with fewer
      // than two terms are dropped by the server
      const parsed = rows.map((r) => r.split(/[,，、\s]+/).filter(Boolean))
      await api.saveSynonyms(parsed)
      onSaved()
      onClose()
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
      setBusy(false)
    }
  }

  return (
    <div
      className="modal-wrap"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="modal">
        <header className="modal-head">
          <h2>{t('syn.title')}</h2>
          <button className="icon" onClick={onClose} title={t('drawer.close')}>
            ×
          </button>
        </header>

        <div className="modal-body">
          <p className="hint">
            {t('syn.hint')}
          </p>

          {rows.map((row, i) => (
            <div className="syn-row" key={i}>
              <input
                value={row}
                placeholder={t('syn.placeholder')}
                onChange={(e) => setRow(i, e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') void save()
                }}
              />
              <button
                className="link"
                onClick={() => setRows((prev) => prev.filter((_, idx) => idx !== i))}
              >
                {t('syn.remove')}
              </button>
            </div>
          ))}

          <button className="link add-group" onClick={() => setRows((prev) => [...prev, ''])}>
            {t('syn.addGroup')}
          </button>

          {err ? <p className="error">{err}</p> : null}
        </div>

        <footer className="modal-foot">
          <button className="primary" onClick={() => void save()} disabled={busy}>
            {busy ? t('syn.saving') : t('syn.save')}
          </button>
          <button onClick={onClose}>{t('syn.cancel')}</button>
        </footer>
      </div>
    </div>
  )
}
