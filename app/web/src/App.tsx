import { useCallback, useEffect, useMemo, useState } from 'react'
import { LangContext, translate, type Lang } from './i18n'
import { api } from './api'
import { FilterBar } from './components/FilterBar'
import { FocusView } from './components/FocusView'
import { Header } from './components/Header'
import { TaskList } from './components/TaskList'
import { TaskDrawer } from './components/TaskDrawer'
import { SynonymsDialog } from './components/SynonymsDialog'
import { FollowPanel } from './components/FollowPanel'
import { SomedayPanel } from './components/SomedayPanel'
import { NoteDialog } from './components/NoteDialog'
import { DEFAULT_FILTERS, hasFilters, toQuery, type Filters } from './filters'
import type { FocusResponse, Meta, Status, Task, TasksResponse } from './types'

function errText(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

export default function App() {
  const [view, setView] = useState<'board' | 'focus' | 'follow' | 'someday'>('board')
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)
  const [queryInput, setQueryInput] = useState('')
  const [data, setData] = useState<TasksResponse | null>(null)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [focus, setFocus] = useState<FocusResponse | null>(null)
  const [follow, setFollow] = useState<TasksResponse | null>(null)
  const [someday, setSomeday] = useState<TasksResponse | null>(null)
  const [note, setNote] = useState<Task | null>(null)
  const [focusLimit, setFocusLimit] = useState(7)
  const [editing, setEditing] = useState<Task | null>(null)
  const [synOpen, setSynOpen] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [lang, setLang] = useState<Lang>(() => {
    const saved = globalThis.localStorage?.getItem('quadrant.lang')
    return saved === 'zh' || saved === 'en' ? saved : 'en'
  })
  const i18n = useMemo(
    () => ({ lang, t: (key: string, vars?: Record<string, string | number>) => translate(lang, key, vars) }),
    [lang],
  )
  const t = i18n.t

  const changeLang = useCallback((next: Lang) => {
    setLang(next)
    try {
      globalThis.localStorage?.setItem('quadrant.lang', next)
    } catch {
      /* private mode: just do not persist */
    }
  }, [])

  // Search debounce: fire the request 220ms after typing stops
  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters((f) => (f.q === queryInput ? f : { ...f, q: queryInput }))
    }, 220)
    return () => clearTimeout(timer)
  }, [queryInput])

  const query = useMemo(() => toQuery(filters), [filters])

  const refresh = useCallback(async () => {
    setBusy(true)
    setError('')
    try {
      const [nextMeta, nextData] = await Promise.all([api.meta(), api.tasks(query)])
      setMeta(nextMeta)
      setData(nextData)
      if (view === 'focus') setFocus(await api.focus(focusLimit, filters.q || undefined))
      if (view === 'follow') setFollow(await api.follow(filters.q || undefined))
      if (view === 'someday') setSomeday(await api.someday(filters.q || undefined))
    } catch (e) {
      setError(errText(e))
    } finally {
      setBusy(false)
    }
  }, [query, view, focusLimit, filters.q])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const patchFilters = useCallback((patch: Partial<Filters>) => {
    setFilters((f) => ({ ...f, ...patch }))
  }, [])

  const resetFilters = useCallback(() => {
    setQueryInput('')
    setFilters(DEFAULT_FILTERS)
  }, [])

  /** Open the drawer; a hand-written task without an ID gets one on the way in. */
  const openEditor = useCallback(
    async (task: Task) => {
      if (task.id) {
        setEditing(task)
        return
      }
      try {
        const withId = await api.assignId(task.file, task.line, task.raw)
        setEditing(withId)
        await refresh()
      } catch (e) {
        setError(errText(e))
      }
    },
    [refresh],
  )

  /** Re-number duplicate IDs so those tasks become editable again. */
  const repairIds = useCallback(async () => {
    setBusy(true)
    setError('')
    try {
      const res = await api.repairIds()
      await refresh()
      setError(res.changed ? translate(lang, 'banner.repaired', { n: res.changed }) : '')
    } catch (e) {
      setError(errText(e))
    } finally {
      setBusy(false)
    }
  }, [refresh])

  const handleStatus = useCallback(
    async (task: Task, next: Status) => {
      if (!task.id) {
        setError(translate(lang, 'banner.noId'))
        return
      }
      try {
        await api.setStatus(task.id, next)
        await refresh()
      } catch (e) {
        setError(errText(e))
      }
    },
    [refresh],
  )

  const handleMove = useCallback(
    async (mover: string, anchor: string, position: 'before' | 'after') => {
      try {
        await api.move({ id: mover, anchor, position })
        await refresh()
      } catch (e) {
        setError(errText(e))
      }
    },
    [refresh],
  )

  /** Cross-cell drag: change P/U first, then (optionally) insert next to the drop row */
  /** Panel drag: persist the full order under the matching scope (focus / follow:x / someday) */
  const handleReorder = useCallback(
    async (scope: string, keys: string[]) => {
      try {
        await api.saveList(scope, keys)
        await refresh()
      } catch (e) {
        setError(errText(e))
      }
    },
    [refresh],
  )

  const handleCellDrop = useCallback(
    async (
      id: string,
      p: number,
      u: number,
      anchorId?: string,
      position?: 'before' | 'after',
    ) => {
      try {
        await api.setPU(id, p, u)
        if (anchorId && position) await api.move({ id, anchor: anchorId, position })
        await refresh()
      } catch (e) {
        setError(errText(e))
      }
    },
    [refresh],
  )

  /** Dropping a dragged task on a tab: Focus adds the tag, someday moves the file. */
  const handleDropTask = useCallback(
    async (target: 'focus' | 'someday', taskId: string) => {
      try {
        if (target === 'focus') await api.addFocus(taskId)
        else await api.moveToSomeday(taskId)
        await refresh()
      } catch (e) {
        setError(errText(e))
      }
    },
    [refresh],
  )

  const isGrid = view === 'board' && filters.groupBy === 'p9'

  return (
    <LangContext.Provider value={i18n}>
      <div className="app">
      <Header
        view={view}
        onView={setView}
        query={queryInput}
        onQuery={setQueryInput}
        meta={meta}
        data={data}
        onDropTask={(target, taskId) => void handleDropTask(target, taskId)}
        lang={lang}
        onLang={changeLang}
      />

      {error ? (
        <div className="banner error">
          <span>{error}</span>
          <button onClick={() => setError('')}>×</button>
        </div>
      ) : null}

      {meta && meta.duplicateIds.length > 0 ? (
        <div className="banner warn">
          <span>
            {t('banner.duplicates', { n: meta.duplicateIds.length })} (
            {meta.duplicateIds.slice(0, 3).map((d) => d.id).join(', ')}
            {meta.duplicateIds.length > 3 ? ', …' : ''})
          </span>
          <button className="chip" onClick={() => void repairIds()} disabled={busy}>
            {t('banner.repair')}
          </button>
        </div>
      ) : null}

      {meta && meta.suspicious.length > 0 ? (
        <details className="banner warn">
          <summary>
            {t('banner.suspicious', { n: meta.suspicious.length })}{' '}
            <code>- [ ]</code>
          </summary>
          <ul>
            {meta.suspicious.map((s) => (
              <li key={`${s.file}:${s.line}`}>
                <code>
                  {s.file}:{s.line}
                </code>{' '}
                {s.raw}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      {view === 'board' ? (
        <>
          <FilterBar
            meta={meta}
            filters={filters}
            onChange={patchFilters}
            onReset={resetFilters}
            onSynonyms={() => setSynOpen(true)}
          />
          <main className={isGrid ? 'content grid-mode' : 'content'}>
            {data ? (
              <TaskList
                data={data}
                meta={meta}
                onSelect={openEditor}
                onStatus={handleStatus}
                onMove={handleMove}
                onCellDrop={handleCellDrop}
                onCreated={refresh}
              />
            ) : (
              <p className="empty">{t('board.loading')}</p>
            )}
          </main>
        </>
      ) : view === 'follow' ? (
        <main className="content">
          <FollowPanel
            data={follow}
            onSelect={openEditor}
            onStatus={handleStatus}
            onCreated={refresh}
            onReorder={handleReorder}
          />
        </main>
      ) : view === 'someday' ? (
        <main className="content">
          <SomedayPanel
            data={someday}
            onSelect={(t) => (t.id ? setEditing(t) : setNote(t))}
            onReorder={(keys) => handleReorder('someday', keys)}
          />
        </main>
      ) : (
        <main className="content">
          <FocusView
            focus={focus}
            limit={focusLimit}
            onLimit={setFocusLimit}
            onStatus={handleStatus}
            onSelect={openEditor}
            onReorder={(keys) => handleReorder('focus', keys)}
          />
        </main>
      )}

      <p className="footer">
        {view === 'board' && data
          ? `${t('board.matched', { matched: data.matched, total: data.total, today: data.today })}${
              hasFilters(filters) ? '' : t('board.noFilters')
            }`
          : null}
        {busy ? t('board.syncing') : ''}
      </p>

      <TaskDrawer
        key={editing?.id ?? 'none'}
        task={editing}
        onClose={() => setEditing(null)}
        onSaved={refresh}
        onDeleted={refresh}
      />

      {note ? <NoteDialog task={note} onClose={() => setNote(null)} /> : null}

      {synOpen && meta ? (
        <SynonymsDialog
          groups={meta.synonyms}
          onClose={() => setSynOpen(false)}
          onSaved={refresh}
        />
      ) : null}
      </div>
    </LangContext.Provider>
  )
}
