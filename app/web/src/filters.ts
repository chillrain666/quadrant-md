import type { TaskQuery } from './api'

/** Filter state as the UI holds it. Not the same as API params: `scope` maps to status / includeDone. */
export interface Filters {
  q: string
  p: number[]
  u: number[]
  tags: string[]
  dirs: string[]
  due: string
  scope: 'open' | 'all' | 'done' | 'blocked'
  groupBy: string
}

export const DEFAULT_FILTERS: Filters = {
  q: '',
  p: [],
  u: [],
  tags: [],
  dirs: [],
  due: '',
  scope: 'open',
  groupBy: 'p9',
}

export const GROUP_OPTIONS: { value: string; labelKey: string }[] = [
  { value: 'p9', labelKey: 'group.p9' },
  { value: 'none', labelKey: 'group.none' },
  { value: 'project', labelKey: 'group.project' },
  { value: 'due', labelKey: 'group.due' },
  { value: 'status', labelKey: 'group.status' },
]

export const DUE_OPTIONS: { value: string; labelKey: string }[] = [
  { value: '', labelKey: 'due.any' },
  { value: 'overdue', labelKey: 'due.overdue' },
  { value: 'today', labelKey: 'due.today' },
  { value: 'week', labelKey: 'due.week' },
  { value: 'month', labelKey: 'due.month' },
  { value: 'none', labelKey: 'due.none' },
]

export const SCOPE_OPTIONS: { value: Filters['scope']; labelKey: string }[] = [
  { value: 'open', labelKey: 'scope.open' },
  { value: 'all', labelKey: 'scope.all' },
  { value: 'done', labelKey: 'scope.done' },
  { value: 'blocked', labelKey: 'scope.blocked' },
]

export function toQuery(f: Filters): TaskQuery {
  const status =
    f.scope === 'done' ? ['done'] : f.scope === 'blocked' ? ['blocked'] : undefined
  return {
    q: f.q.trim() || undefined,
    p: f.p.length ? f.p : undefined,
    u: f.u.length ? f.u : undefined,
    tag: f.tags.length ? f.tags : undefined,
    status,
    dir: f.dirs.length ? f.dirs : undefined,
    due: f.due || undefined,
    // scope=all also brings in done items; otherwise status decides
    includeDone: f.scope === 'all',
    groupBy: f.groupBy,
  }
}

/** Any filter besides grouping and scope? (drives the "clear" button) */
export function hasFilters(f: Filters): boolean {
  return Boolean(
    f.q.trim() || f.p.length || f.u.length || f.tags.length || f.dirs.length || f.due ||
      f.scope !== 'open' || f.groupBy !== 'p9',
  )
}

export function toggleValue<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value]
}
