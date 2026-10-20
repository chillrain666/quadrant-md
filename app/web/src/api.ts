import type {
  FocusResponse,
  Meta,
  MoveBody,
  NewTaskBody,
  Status,
  Task,
  TasksResponse,
} from './types'

// During development this goes through the Vite proxy (same origin); in production
// FastAPI serves the build itself. Either way, relative paths are used.
const BASE = ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* Not JSON: fall back to the status text */
    }
    throw new Error(detail)
  }
  return (await res.json()) as T
}

export interface TaskQuery {
  q?: string
  p?: number[]
  u?: number[]
  tag?: string[]
  status?: string[]
  dir?: string[]
  due?: string
  includeDone?: boolean
  groupBy?: string
}

function toSearch(q: TaskQuery): string {
  const sp = new URLSearchParams()
  if (q.q) sp.set('q', q.q)
  for (const v of q.p ?? []) sp.append('p', String(v))
  for (const v of q.u ?? []) sp.append('u', String(v))
  for (const v of q.tag ?? []) sp.append('tag', v)
  for (const v of q.status ?? []) sp.append('status', v)
  for (const v of q.dir ?? []) sp.append('dir', v)
  if (q.due) sp.set('due', q.due)
  if (q.includeDone) sp.set('include_done', 'true')
  if (q.groupBy) sp.set('group_by', q.groupBy)
  return sp.toString()
}

export const api = {
  tasks: (q: TaskQuery) => request<TasksResponse>(`/api/tasks?${toSearch(q)}`),
  meta: () => request<Meta>('/api/meta'),
  focus: (limit: number, q?: string) =>
    request<FocusResponse>(
      `/api/focus?limit=${limit}${q ? `&q=${encodeURIComponent(q)}` : ''}`,
    ),
  /** Watch lists (shows / serials): grouped by file, no P/U */
  watch: (q?: string) =>
    request<TasksResponse>(`/api/watch${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  /** Someday (ideas / not now): a single file, no P/U */
  someday: (q?: string) =>
    request<TasksResponse>(`/api/someday${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  /** Give a hand-written task line an ID, so it can be edited like any other */
  assignId: (file: string, line: number, raw: string) =>
    request<Task>('/api/ids/assign', {
      method: 'POST',
      body: JSON.stringify({ file, line, raw }),
    }),
  /** Re-number duplicate IDs (the first occurrence keeps its own) */
  repairIds: () =>
    request<{ changed: number; renamed: unknown[] }>('/api/ids/repair', { method: 'POST' }),
  create: (body: NewTaskBody) =>
    request<Task>('/api/tasks', { method: 'POST', body: JSON.stringify(body) }),
  setStatus: (id: string, status: Status) =>
    request<Task>(`/api/tasks/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
  /** Cross-cell drag: change P/U (only the two #P/#U tokens) */
  setPU: (id: string, p: number, u: number) =>
    request<Task>(`/api/tasks/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify({ p, u }),
    }),
  /** Drawer edit: update by field (send only what changed; the backend knows) */
  updateTask: (
    id: string,
    patch: {
      title?: string
      p?: number | null
      u?: number | null
      status?: Status
      ddl?: string | null
      tags?: string[]
    },
  ) =>
    request<Task>(`/api/tasks/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    }),
  move: (body: MoveBody) =>
    request<{ changed: boolean }>('/api/order', { method: 'PUT', body: JSON.stringify(body) }),
  /** Delete one task (its line plus indented detail lines). Irreversible. */
  deleteTask: (id: string) =>
    request<{ id: string; file: string; title: string; removedLines: number }>(
      `/api/tasks/${encodeURIComponent(id)}`,
      { method: 'DELETE' },
    ),
  /** Drop on the Focus tab: add the #TopN tag */
  addFocus: (id: string) =>
    request<Task>(`/api/tasks/${encodeURIComponent(id)}/focus`, { method: 'POST' }),
  /** Drop on the someday tab: move the task into 4-someday.md */
  moveToSomeday: (id: string) =>
    request<{ id: string; from: string; to: string; movedLines: number }>(
      `/api/tasks/${encodeURIComponent(id)}/someday`,
      { method: 'POST' },
    ),
  synonyms: () => request<{ groups: string[][] }>('/api/synonyms'),
  /** Persist one panel's order; scopes look like focus / watch:shows / someday */
  saveList: (scope: string, keys: string[]) =>
    request<{ scope: string; count: number }>('/api/lists', {
      method: 'PUT',
      body: JSON.stringify({ scope, keys }),
    }),
  saveSynonyms: (groups: string[][]) =>
    request<{ groups: string[][] }>('/api/synonyms', {
      method: 'PUT',
      body: JSON.stringify({ groups }),
    }),
}
