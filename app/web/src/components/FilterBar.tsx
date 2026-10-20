import { useState } from 'react'
import { useT } from '../i18n'
import {
  DUE_OPTIONS,
  GROUP_OPTIONS,
  SCOPE_OPTIONS,
  type Filters,
  toggleValue,
} from '../filters'
import type { Meta } from '../types'
import { DirFilter } from './DirFilter'

interface Props {
  meta: Meta | null
  filters: Filters
  onChange: (patch: Partial<Filters>) => void
  onReset: () => void
  onSynonyms: () => void
}

const P_VALUES = [1, 2, 3]
const U_VALUES = [1, 2, 3]

export function FilterBar({ meta, filters, onChange, onReset, onSynonyms }: Props) {
  const { t } = useT()
  const [tagOpen, setTagOpen] = useState(false)
  const activeTags = filters.tags
  const activeDirs = filters.dirs

  return (
    <section className="filters">
      <div className="filter-row">
        <span className="label">{t('filter.importance')}</span>
        <div className="chips">
          {P_VALUES.map((v) => (
            <button
              key={v}
              className={filters.p.includes(v) ? 'chip p on' : 'chip p'}
              onClick={() => onChange({ p: toggleValue(filters.p, v) })}
            >
              P{v}
              <em>{meta?.p[`P${v}`] ?? 0}</em>
            </button>
          ))}
        </div>

        <span className="label">{t('filter.urgency')}</span>
        <div className="chips">
          {U_VALUES.map((v) => (
            <button
              key={v}
              className={filters.u.includes(v) ? 'chip u on' : 'chip u'}
              onClick={() => onChange({ u: toggleValue(filters.u, v) })}
            >
              U{v}
              <em>{meta?.u[`U${v}`] ?? 0}</em>
            </button>
          ))}
        </div>
      </div>

      <div className="filter-row">
        <select
          value={filters.due}
          onChange={(e) => onChange({ due: e.target.value })}
          title={t('filter.due.title')}
        >
          {DUE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {t(o.labelKey)}
            </option>
          ))}
        </select>

        <DirFilter
          dirs={meta?.dirs ?? []}
          files={meta?.files ?? []}
          selected={activeDirs}
          onChange={(dirs) => onChange({ dirs })}
        />

        <select
          value={filters.scope}
          onChange={(e) => onChange({ scope: e.target.value as Filters['scope'] })}
          title={t('filter.scope.title')}
        >
          {SCOPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {t(o.labelKey)}
            </option>
          ))}
        </select>

        <select
          value={filters.groupBy}
          onChange={(e) => onChange({ groupBy: e.target.value })}
          title={t('filter.group.title')}
        >
          {GROUP_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {t(o.labelKey)}
            </option>
          ))}
        </select>

        <div className="tag-filter">
          <button
            className={activeTags.length ? 'chip tag on' : 'chip tag'}
            onClick={() => setTagOpen((v) => !v)}
          >
            {t('filter.tags')}{activeTags.length ? ` · ${activeTags.length}` : ''}
          </button>
          {tagOpen ? (
            <div className="tag-pop" onMouseLeave={() => setTagOpen(false)}>
              {(meta?.tags ?? []).map((tag) => (
                <button
                  key={tag.key}
                  className={activeTags.includes(tag.key) ? 'tag-item on' : 'tag-item'}
                  onClick={() => onChange({ tags: toggleValue(activeTags, tag.key) })}
                >
                  {tag.label}
                  <em>{tag.count}</em>
                </button>
              ))}
              {(meta?.tags ?? []).length === 0 ? <p className="muted">{t('filter.noTags')}</p> : null}
            </div>
          ) : null}
        </div>

        <button className="reset" onClick={onReset}>
          {t('filter.clear')}
        </button>
      </div>

      <div className="filter-row syn-row-line">
        <button className="chip tag" onClick={onSynonyms} title={t('filter.synonyms.title')}>
          {t('filter.synonyms')}
          {meta?.synonyms.length ? ` · ${meta.synonyms.length}` : ''}
        </button>
        <span className="muted">
          {t('filter.synonyms.hint')}
        </span>
      </div>

      {activeTags.length ? (
        <div className="filter-row active-tags">
          {activeTags.map((tag) => (
            <button
              key={tag}
              className="chip tag on"
              onClick={() => onChange({ tags: activeTags.filter((x) => x !== tag) })}
            >
              #{tag} <span className="x">×</span>
            </button>
          ))}
        </div>
      ) : null}
    </section>
  )
}
