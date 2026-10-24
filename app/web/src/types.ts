/** Types aligned with the backend responses. Field names are camelCase (TaskOut already converts). */

export type Status = 'todo' | 'done' | 'blocked'

export interface Task {
  id: string | null
  status: Status
  statusLabel: string
  title: string
  p: number | null
  u: number | null
  quadrant: string
  quadrantLabel: string
  tags: string[]
  ddl: string | null
  ddlTime: string | null
  done: string | null
  blockRef: string | null
  links: string[]
  kind: 'task' | 'follow'
  file: string
  project: string
  groupPath: string[]
  line: number
  raw: string
  detail: string[]
}

export interface TaskGroup {
  key: string
  label: string
  count: number
  tasks: Task[]
}

export interface TasksResponse {
  today: string
  generatedAt: string
  tasksRoot: string
  total: number
  matched: number
  groupBy: string
  filters: Record<string, unknown>
  groups: TaskGroup[]
}

export interface MetaTag {
  key: string
  label: string
  count: number
}

export interface MetaFile {
  file: string
  project: string
  groupPath: string[]
  count: number
}

export interface MetaDir {
  path: string
  count: number
}

export interface Meta {
  today: string
  tasksRoot: string
  total: number
  tags: MetaTag[]
  projects: string[]
  files: MetaFile[]
  dirs: MetaDir[]
  status: Record<string, number>
  quadrant: Record<string, number>
  p: Record<string, number>
  u: Record<string, number>
  due: Record<string, number>
  focus: number
  follow: number
  someday: number
  overrides: number
  synonyms: string[][]
  suspicious: { file: string; line: number; raw: string }[]
  duplicateIds: {
    id: string
    count: number
    occurrences: { file: string; line: number; title: string }[]
  }[]
}

export interface FocusResponse {
  today: string
  total: number
  limit: number
  tasks: Task[]
}

export interface NewTaskBody {
  file: string
  title: string
  p?: number | null
  u?: number | null
  tags?: string[]
  ddl?: string | null
}

export interface MoveBody {
  id: string
  anchor: string
  position: 'before' | 'after'
}
