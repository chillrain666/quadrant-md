import { useT, type Lang } from '../i18n'
import type { Meta, TasksResponse } from '../types'

interface Props {
  view: 'board' | 'focus' | 'follow' | 'someday'
  onView: (v: 'board' | 'focus' | 'follow' | 'someday') => void
  query: string
  onQuery: (v: string) => void
  meta: Meta | null
  data: TasksResponse | null
  /** Dropping a dragged task on a tab: focus = add #TopN, someday = move it there */
  onDropTask: (view: 'focus' | 'someday', taskId: string) => void
  lang: Lang
  onLang: (lang: Lang) => void
}

const DROP_TABS = new Set(['focus', 'someday'])

export function Header({
  view,
  onView,
  query,
  onQuery,
  meta,
  data,
  onDropTask,
  lang,
  onLang,
}: Props) {
  const { t } = useT()
  const dropProps = (target: 'focus' | 'someday') => ({
    onDragOver: (e: React.DragEvent<HTMLButtonElement>) => {
      e.preventDefault()
      e.dataTransfer.dropEffect = 'move'
    },
    onDrop: (e: React.DragEvent<HTMLButtonElement>) => {
      e.preventDefault()
      const id = e.dataTransfer.getData('text/plain')
      if (id && !DROP_TABS.has(view)) onDropTask(target, id)
    },
  })
  return (
    <header className="header">
      <div className="header-top">
        <h1>
          {t('app.title')}
          <span className="root" title={meta?.tasksRoot ?? ''}>
            {meta?.tasksRoot ?? ''}
          </span>
        </h1>

        <nav className="tabs">
          <button
            className={view === 'board' ? 'tab active' : 'tab'}
            onClick={() => onView('board')}
          >
            {t('tab.all')}
            {data ? <em>{data.matched}</em> : null}
          </button>
          <button
            className={view === 'focus' ? 'tab active' : 'tab'}
            onClick={() => onView('focus')}
            title={t("focus.dropHint")}
            {...dropProps('focus')}
          >
            {t('tab.focus')}
            {meta ? <em>{meta.focus}</em> : null}
          </button>
          <button
            className={view === 'follow' ? 'tab active' : 'tab'}
            onClick={() => onView('follow')}
          >
            {t('tab.follow')}
            {meta ? <em>{meta.follow}</em> : null}
          </button>
          <button
            className={view === 'someday' ? 'tab active' : 'tab'}
            onClick={() => onView('someday')}
            title={t("someday.dropHint")}
            {...dropProps('someday')}
          >
            {t('tab.someday')}
            {meta ? <em>{meta.someday}</em> : null}
          </button>
        </nav>

        <select
          className="lang"
          value={lang}
          onChange={(e) => onLang(e.target.value as Lang)}
          title="Language / 语言"
        >
          <option value="en">EN</option>
          <option value="zh">中文</option>
        </select>

        <div className="search">
          <input
            value={query}
            placeholder={t('search.placeholder')}
            onChange={(e) => onQuery(e.target.value)}
            spellCheck={false}
          />
          {query ? (
            <button className="clear" onClick={() => onQuery('')} title={t('search.clear')}>
              ×
            </button>
          ) : null}
        </div>
      </div>
    </header>
  )
}
