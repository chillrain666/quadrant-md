import { useT } from '../i18n'
import type { MetaDir, MetaFile } from '../types'

interface Props {
  dirs: MetaDir[]
  files: MetaFile[]
  /** 0 entries = no filter; 1 entry = the selected directory or file path */
  selected: string[]
  onChange: (next: string[]) => void
}

interface Node {
  path: string
  name: string
  count: number
  isFile: boolean
}

/** The board only scans 1-active, so it is a constant prefix, not a dropdown level */
const ROOT = '1-active'

/** Parent path: `a/b/c` -> `a/b`; a top-level entry (including root files) -> "" */
function parentOf(path: string): string {
  const i = path.lastIndexOf('/')
  return i === -1 ? '' : path.slice(0, i)
}

/**
 * Cascading directory filter: **one dropdown per level**.
 *
 * Level 2 only appears after level 1 is chosen, and so on; the last level holds
 * files. So a path with N levels produces exactly N dropdowns.
 */
export function DirFilter({ dirs, files, selected, onChange }: Props) {
  const { t } = useT()
  const nodes: Node[] = []

  for (const d of dirs) {
    // Neither the root nor 1-active itself is an option: their children are level 1
    if (d.path === '' || d.path === ROOT) continue
    nodes.push({
      path: d.path,
      name: d.path.split('/').slice(-1)[0],
      count: d.count,
      isFile: false,
    })
  }
  for (const f of files) {
    nodes.push({ path: f.file, name: f.project, count: f.count, isFile: true })
  }

  const childrenOf = (parent: string) =>
    nodes
      .filter((n) => parentOf(n.path) === parent)
      // Directories first, files after; each group sorted by name
      .sort((a, b) =>
        a.isFile === b.isFile ? a.name.localeCompare(b.name) : a.isFile ? 1 : -1,
      )

  const chosen = selected[0] ?? ''
  // All paths carry the 1-active/ prefix, but levels start **below** it
  const rel = chosen.startsWith(ROOT + '/') ? chosen.slice(ROOT.length + 1).split('/') : []
  const abs = (depth: number) =>
    rel.length > depth ? [ROOT, ...rel.slice(0, depth + 1)].join('/') : ''

  const chain: { nodes: Node[]; value: string }[] = []
  let parent = ROOT
  for (let depth = 0; depth < 8; depth++) {
    const level = childrenOf(parent)
    if (!level.length) break
    const value = abs(depth)
    chain.push({ nodes: level, value })
    const next = value ? level.find((n) => n.path === value) : undefined
    if (!next) break
    parent = next.path
  }

  if (!chain.length) return null

  return (
    <div className="dir-cascade">
      {chain.map((lv, i) => (
        <select
          key={i}
          value={lv.value}
          title={i === 0 ? t('dir.level1') : t('dir.level', { n: i + 1 })}
          onChange={(e) => {
            const v = e.target.value
            if (v) onChange([v])
            // Picking "all" goes back one level; at level 1 it clears the filter
            else onChange(i === 0 ? [] : [chain[i - 1].value])
          }}
        >
          <option value="">{i === 0 ? t('dir.all') : t('dir.allShort')}</option>
          {lv.nodes.map((n) => (
            <option key={n.path} value={n.path}>
              {n.name}
              {n.isFile ? '' : '/'} ({n.count})
            </option>
          ))}
        </select>
      ))}
    </div>
  )
}
