import { useState } from 'react'
import { api } from '../api'
import { useT } from '../i18n'
import type { MetaFile } from '../types'

interface Props {
  files: MetaFile[]
  defaultFile: string
  /** When creating from the grid, P/U are prefilled from the cell -- otherwise the
   * new task would immediately "jump" to another cell */
  defaultP?: number | null
  defaultU?: number | null
  onClose: () => void
  onCreated: () => void
}

export function NewTaskForm({
  files,
  defaultFile,
  defaultP = null,
  defaultU = null,
  onClose,
  onCreated,
}: Props) {
  const { t } = useT()
  const [file, setFile] = useState(defaultFile)
  const [title, setTitle] = useState('')
  const [p, setP] = useState(defaultP ? String(defaultP) : '')
  const [u, setU] = useState(defaultU ? String(defaultU) : '')
  const [ddl, setDdl] = useState('')
  const [tags, setTags] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  async function submit() {
    if (!title.trim() || busy) return
    if (!file) {
      setErr(t('new.pickFile'))
      return
    }
    setBusy(true)
    setErr('')
    try {
      await api.create({
        file,
        title: title.trim(),
        p: p ? Number(p) : null,
        u: u ? Number(u) : null,
        ddl: ddl || null,
        tags: tags.split(/[,，\s]+/).filter(Boolean),
      })
      setTitle('')
      setTags('')
      setDdl('')
      onCreated()
      onClose() // collapse after creating -- leaving it open only hides the next row
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="new-form">
      <input
        className="new-title"
        autoFocus
        placeholder={t('new.placeholder')}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') void submit()
          if (e.key === 'Escape') onClose()
        }}
      />
      <div className="new-extra">
        <select value={file} onChange={(e) => setFile(e.target.value)} title={t('new.file')}>
          {files.map((f) => (
            <option key={f.file} value={f.file}>
              {f.file}
            </option>
          ))}
        </select>
        <select value={p} onChange={(e) => setP(e.target.value)} title={t('new.importance')}>
          <option value="">P-</option>
          <option value="1">P1</option>
          <option value="2">P2</option>
          <option value="3">P3</option>
        </select>
        <select value={u} onChange={(e) => setU(e.target.value)} title={t('new.urgency')}>
          <option value="">U-</option>
          <option value="1">U1</option>
          <option value="2">U2</option>
          <option value="3">U3</option>
        </select>
        <input type="date" value={ddl} onChange={(e) => setDdl(e.target.value)} title={t('new.ddl')} />
        <input
          className="new-tags"
          placeholder={t('new.tags')}
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void submit()
            if (e.key === 'Escape') onClose()
          }}
        />
        <button onClick={() => void submit()} disabled={busy}>
          {busy ? t('new.creating') : t('new.create')}
        </button>
      </div>
      {err ? <p className="error">{err}</p> : null}
    </div>
  )
}
