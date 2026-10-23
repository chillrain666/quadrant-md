/**
 * Short label for the file a task lives in.
 *
 * The board shows the whole relative path in the drawer, but a chip on the row
 * only needs the last path segment, without the `.md` suffix:
 * `1-active/notes/notes.md` -> `notes`
 */
export function fileLabel(file: string): string {
  if (!file) return ''
  const segment = file.split(/[\\/]/).filter(Boolean).pop() ?? file
  return segment.replace(/\.md$/i, '')
}
