import { createContext, useContext } from 'react'

export type Lang = 'en' | 'zh'

type Dict = Record<string, string>

const en: Dict = {
  'app.title': 'Todo board',
  'tab.all': 'All',
  'tab.focus': 'Focus',
  'tab.follow': 'Following',
  'tab.someday': 'someday',
  'search.placeholder': 'Search title / tag / project / ID…',
  'search.clear': 'Clear',
  'focus.dropHint': 'Drop a task here to put it in Focus',
  'someday.dropHint': 'Drop a task here to move it to someday',

  'filter.importance': 'Importance',
  'filter.urgency': 'Urgency',
  'filter.tags': 'Tags',
  'filter.synonyms': 'Synonyms',
  'filter.clear': 'Clear',
  'filter.due.title': 'Due window',
  'filter.scope.title': 'Scope',
  'filter.group.title': 'Grouping',
  'filter.synonyms.title': 'Edit synonym groups',
  'filter.synonyms.hint':
    'Terms in a group are equivalent (e.g. TopN = focus, reading = books); search and tag filters both treat them as one',
  'filter.noTags': 'No tags yet',

  'group.p9': 'P×U grid',
  'group.none': 'No grouping',
  'group.project': 'Project',
  'group.due': 'Due date',
  'group.status': 'Status',
  'due.any': 'Any time',
  'due.overdue': 'Overdue',
  'due.today': 'Today',
  'due.week': 'This week (7 days)',
  'due.month': 'This month',
  'due.none': 'No DDL',
  'scope.open': 'To do only',
  'scope.all': 'Everything (done + blocked)',
  'scope.done': 'Done only',
  'scope.blocked': 'Blocked only',

  'axis.p1': 'most', 'axis.p2': 'medium', 'axis.p3': 'least',
  'axis.u1': 'most', 'axis.u2': 'medium', 'axis.u3': 'least',
  'board.empty': 'No matching tasks.',
  'board.unclassified': 'Unclassified (missing P or U)',
  'board.new': '+ New',
  'board.newIn': 'New task in {where}',
  'board.matched': 'matched {matched} / {total} · today {today}',
  'board.noFilters': ' · no filters',
  'board.syncing': ' · syncing…',
  'board.loading': 'Loading…',

  'row.edit': 'Click to edit',
  'row.editHint': 'Click to edit; drag to reorder',
  'row.drag': 'Drag to reorder',
  'row.markTodo': 'Mark as to-do',
  'row.markDone': 'Mark as done',
  'row.noTitle': '(no title)',

  'drawer.title': 'Edit task',
  'drawer.close': 'Close (Esc)',
  'drawer.field.title': 'Title',
  'drawer.field.importance': 'Importance',
  'drawer.field.urgency': 'Urgency',
  'drawer.field.status': 'Status',
  'drawer.field.ddl': 'Due date (DDL)',
  'drawer.field.tags': 'Tags (space or comma separated)',
  'drawer.field.details': 'Detail lines',
  'drawer.field.raw': 'Raw line',
  'drawer.none': 'none',
  'status.todo': 'To do',
  'status.done': 'Done',
  'status.blocked': 'Blocked',
  'drawer.p1': 'P1 most important',
  'drawer.p2': 'P2 medium',
  'drawer.p3': 'P3 least important',
  'drawer.u1': 'U1 most urgent',
  'drawer.u2': 'U2 medium',
  'drawer.u3': 'U3 least urgent',
  'drawer.clear': 'Clear',
  'drawer.noDetails': 'No indented detail lines',
  'drawer.detailsPlaceholder': 'One Markdown line per row, e.g.\n- 2026-10-20 talked to A, waiting for the quote',
  'drawer.detailsHint': 'Saved as the indented lines under this task; Markdown is fine.',
  'drawer.deleteConfirm': 'Delete this task?',
  'drawer.delete': 'Delete',
  'drawer.save': 'Save',
  'drawer.saving': 'Saving…',
  'drawer.cancel': 'Cancel',
  'drawer.titleRequired': 'Title cannot be empty',

  'focus.heading': 'Focus · the few things to do next',
  'focus.show': 'Show',
  'focus.items': 'items',
  'focus.rule': 'Selection: the task carries a #TopN tag.',
  'focus.order':
    'Order: overdue → due today → P1+U1 → P1 → U1 → nearest DDL → drag order.',
  'focus.empty':
    'No task carries #TopN yet. Add the tag to any task in any project file and it shows up here.',
  'focus.hidden': '{n} more #TopN tasks are hidden by the limit.',

  'follow.empty': 'Nothing on the follow list yet — create a markdown file under tasks/follow/.',
  'follow.addTo': 'Add an entry to {what}',
  'follow.placeholder': 'Book / show title (progress in brackets, e.g. (S2E4))',
  'follow.add': 'Add',
  'follow.markInProgress': 'Mark as in progress again',
  'follow.markFinished': 'Mark as finished',

  'someday.empty': 'Nothing in someday yet — add `- one line` to tasks/4-someday.md.',
  'someday.detailLines': '{n} detail lines',
  'someday.noDetails': 'no details',
  'someday.open': 'Click for details; drag to reorder',

  'note.title': 'Idea detail',
  'note.empty': 'Nothing more to show',
  'note.close': 'Close',

  'syn.title': 'Synonyms',
  'syn.hint':
    'Terms in a group are equivalent, case-insensitive, and a group may hold more than two. Search, tag filters and Focus all treat them as one; groups with fewer than two terms are ignored.',
  'syn.defaults':
    'No personal table yet — these are the shipped defaults. Saving creates your own copy, which will not be overwritten by updates.',
  'syn.placeholder': 'e.g. TopN, focus',
  'syn.remove': 'Remove',
  'syn.addGroup': '+ Add a group',
  'syn.save': 'Save',
  'syn.saving': 'Saving…',
  'syn.cancel': 'Cancel',

  'new.placeholder': 'New task title; Enter to create / Esc to cancel',
  'new.file': 'Which file to write to',
  'new.importance': 'Importance',
  'new.urgency': 'Urgency',
  'new.ddl': 'Due date',
  'new.tags': 'Tags, space separated',
  'new.create': 'Create',
  'new.creating': 'Writing…',
  'new.pickFile': 'Pick a file first',

  'dir.all': 'All directories',
  'dir.allShort': 'All',
  'dir.level': 'Level {n}',
  'dir.level1': 'Level 1 directory',

  'banner.duplicates': '{n} duplicate ID(s): editing those tasks fails until they are re-numbered',
  'banner.repair': 'Repair IDs',
  'banner.repaired': 'Re-numbered {n} duplicate ID(s)',
  'banner.suspicious':
    '{n} lines look like tasks but are malformed and were ignored (usually a missing space after - [ ])',
  'banner.noId': 'This task has no ID, its status cannot be changed',
}

const zh: Dict = {
  'app.title': '待办看板',
  'tab.all': '全部',
  'tab.focus': 'Focus',
  'tab.follow': '跟进',
  'tab.someday': 'someday',
  'search.placeholder': '搜索标题 / 标签 / 项目 / ID…',
  'search.clear': '清空',
  'focus.dropHint': '拖到这里加入 Focus',
  'someday.dropHint': '拖到这里移到 someday',

  'filter.importance': '重要性',
  'filter.urgency': '紧迫性',
  'filter.tags': '标签',
  'filter.synonyms': '同义词',
  'filter.clear': '清空',
  'filter.due.title': '时间窗口',
  'filter.scope.title': '范围',
  'filter.group.title': '分组方式',
  'filter.synonyms.title': '设置同义词组',
  'filter.synonyms.hint':
    '一组里的词彼此等价（如 TopN = focus、reading = books），搜索和标签筛选都按组处理',
  'filter.noTags': '还没有标签',

  'group.p9': 'P×U 九宫格',
  'group.none': '不分组',
  'group.project': '项目',
  'group.due': '时间',
  'group.status': '状态',
  'due.any': '任何时间',
  'due.overdue': '已过期',
  'due.today': '今天',
  'due.week': '本周（7 天内）',
  'due.month': '本月',
  'due.none': '没有 DDL',
  'scope.open': '只看待办',
  'scope.all': '全部（含已完成、搁置）',
  'scope.done': '只看已完成',
  'scope.blocked': '只看搁置',

  'axis.p1': '最重要', 'axis.p2': '中', 'axis.p3': '最不重要',
  'axis.u1': '最急', 'axis.u2': '中', 'axis.u3': '最不急',
  'board.empty': '没有匹配的任务。',
  'board.unclassified': '未分类（缺 P 或 U）',
  'board.new': '＋ 新建',
  'board.newIn': '在 {where} 里新建',
  'board.matched': '匹配 {matched} / 共 {total} 条 · 今天 {today}',
  'board.noFilters': ' · 未筛选',
  'board.syncing': ' · 同步中…',
  'board.loading': '加载中…',

  'row.edit': '点击编辑',
  'row.editHint': '点击编辑；拖动可调顺序',
  'row.drag': '拖动排序',
  'row.markTodo': '标记为待办',
  'row.markDone': '标记为完成',
  'row.noTitle': '（无标题）',

  'drawer.title': '编辑任务',
  'drawer.close': '关闭 (Esc)',
  'drawer.field.title': '标题',
  'drawer.field.importance': '重要性',
  'drawer.field.urgency': '紧迫性',
  'drawer.field.status': '状态',
  'drawer.field.ddl': '截止日（DDL）',
  'drawer.field.tags': '标签（空格或逗号分隔）',
  'drawer.field.details': '详情行',
  'drawer.field.raw': '原始行',
  'drawer.none': '无',
  'status.todo': '待办',
  'status.done': '完成',
  'status.blocked': '搁置',
  'drawer.p1': 'P1 最重要',
  'drawer.p2': 'P2 中',
  'drawer.p3': 'P3 最不重要',
  'drawer.u1': 'U1 最急',
  'drawer.u2': 'U2 中',
  'drawer.u3': 'U3 最不急',
  'drawer.clear': '清除',
  'drawer.noDetails': '没有缩进详情行',
  'drawer.detailsPlaceholder': '一行一条，Markdown 也行，例如\n- 2026-10-20 问过 A，等报价',
  'drawer.detailsHint': '会写回任务下面的缩进行，Markdown 语法可用。',
  'drawer.deleteConfirm': '确定删除？',
  'drawer.delete': '删除',
  'drawer.save': '保存',
  'drawer.saving': '保存中…',
  'drawer.cancel': '取消',
  'drawer.titleRequired': '标题不能为空',

  'focus.heading': 'Focus · 接下来要做的几件事',
  'focus.show': '显示',
  'focus.items': '条',
  'focus.rule': '入选规则：任务行里带 #TopN 标签。',
  'focus.order': '排序：已过期 → 今天到期 → P1+U1 → P1 → U1 → DDL 由近到远 → 拖拽顺序。',
  'focus.empty': '还没有带 #TopN 的任务。在任意项目文件里给它加个 #TopN 标签，就会出现在这里。',
  'focus.hidden': '还有 {n} 条带 #TopN 的任务没显示出来（超出上限）。',

  'follow.empty': '跟进清单是空的 —— 在 tasks/follow/ 下建一个 md 就行。',
  'follow.addTo': '在 {what} 里加一条',
  'follow.placeholder': '书名 / 剧名（进度可写在括号里，如（S2E4））',
  'follow.add': '加',
  'follow.markInProgress': '改回「在看」',
  'follow.markFinished': '标记为看完',

  'someday.empty': 'someday 是空的 —— 在 tasks/4-someday.md 里写 `- 一句话` 就行。',
  'someday.detailLines': '{n} 行详情',
  'someday.noDetails': '无详情',
  'someday.open': '点击看详情；拖动可调顺序',

  'note.title': '灵感详情',
  'note.empty': '没有更多内容',
  'note.close': '关闭',

  'syn.title': '同义词',
  'syn.hint':
    '一组里的词彼此等价，不区分大小写，可以多于两个。搜索、标签筛选、Focus 判定都会按组处理；少于两个词的组会被忽略。',
  'syn.defaults':
    '当前用的是自带的默认表。保存后会在本机生成你自己的副本，以后更新不会覆盖它。',
  'syn.placeholder': '例如：TopN, focus',
  'syn.remove': '删除',
  'syn.addGroup': '＋ 添加一组',
  'syn.save': '保存',
  'syn.saving': '保存中…',
  'syn.cancel': '取消',

  'new.placeholder': '新任务标题，回车创建 / Esc 取消',
  'new.file': '写到哪个文件',
  'new.importance': '重要性',
  'new.urgency': '紧迫性',
  'new.ddl': '截止日期',
  'new.tags': '标签，空格分隔',
  'new.create': '创建',
  'new.creating': '写入中…',
  'new.pickFile': '先选一个文件',

  'dir.all': '全部目录',
  'dir.allShort': '全部',
  'dir.level': '第 {n} 级',
  'dir.level1': '第 1 级目录',

  'banner.duplicates': '有 {n} 组重复 ID：这些任务在重新编号前无法编辑',
  'banner.repair': '修复 ID',
  'banner.repaired': '已重新编号 {n} 条重复 ID',
  'banner.suspicious': '{n} 行看着像任务但格式不对，已被忽略（多半是 - [ ] 后面漏了空格）',
  'banner.noId': '这条任务没有 ID，改不了状态',
}

const DICTS: Record<Lang, Dict> = { en, zh }

export function translate(lang: Lang, key: string, vars?: Record<string, string | number>) {
  const template = DICTS[lang][key] ?? DICTS.en[key] ?? key
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (_, name: string) =>
    vars[name] === undefined ? `{${name}}` : String(vars[name]),
  )
}

/**
 * Server-side group labels are English; map the well-known keys so the Chinese UI
 * does not mix languages. Unknown keys fall back to whatever the server sent.
 */
const GROUP_LABELS: Record<Lang, Record<string, string>> = {
  en: {},
  zh: {
    all: '全部任务',
    unclassified: '未分类',
    'PU-': '未分类',
    Q1: 'Q1 重要且紧急',
    Q2: 'Q2 重要不紧急',
    Q3: 'Q3 紧急不重要',
    Q4: 'Q4 不重要也不紧急',
    overdue: '已过期',
    today: '今天到期',
    week: '明天起 7 天内',
    later: '更远',
    none: '无 DDL',
    todo: '待办',
    done: '已完成',
    blocked: '搁置',
  },
}

export function groupLabel(lang: Lang, key: string, fallback: string): string {
  return GROUP_LABELS[lang][key] ?? fallback
}

export interface I18n {
  lang: Lang
  t: (key: string, vars?: Record<string, string | number>) => string
}

export const LangContext = createContext<I18n>({
  lang: 'en',
  t: (key, vars) => translate('en', key, vars),
})

export function useT(): I18n {
  return useContext(LangContext)
}
