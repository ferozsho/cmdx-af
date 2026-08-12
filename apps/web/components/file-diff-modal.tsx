'use client'

export interface FileDiff {
  path: string
  operation: 'created' | 'modified' | 'deleted'
  added: number
  removed: number
  diff: string
}

const OP_META: Record<
  FileDiff['operation'],
  { label: string; color: string; icon: string }
> = {
  created: { label: 'Created', color: '#16a34a', icon: '➕' },
  modified: { label: 'Modified', color: '#2563eb', icon: '📝' },
  deleted: { label: 'Deleted', color: '#dc2626', icon: '🗑' },
}

/**
 * Large modal viewer for an agent file change, rendering the git-style
 * unified diff (+/- colored lines) exactly like a git diff view.
 */
export default function FileDiffModal({
  fileChange,
  onClose,
}: {
  fileChange: FileDiff
  onClose: () => void
}) {
  const meta = OP_META[fileChange.operation] || OP_META.modified
  const lines = fileChange.diff ? fileChange.diff.split('\n') : []

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="bg-surface border border-border rounded-xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 px-5 py-4 border-b border-border">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-lg leading-none">{meta.icon}</span>
              <h3 className="text-sm font-semibold text-foreground font-mono break-all">
                {fileChange.path}
              </h3>
              <span
                className="text-[10px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap"
                style={{
                  backgroundColor: `${meta.color}18`,
                  color: meta.color,
                  border: `1px solid ${meta.color}40`,
                }}
              >
                {meta.label}
              </span>
            </div>
            <div className="text-xs text-muted mt-1.5">
              <span className="text-[#16a34a] font-medium">+{fileChange.added}</span>{' '}
              added ·{' '}
              <span className="text-[#dc2626] font-medium">
                −{fileChange.removed}
              </span>{' '}
              removed · {lines.length} diff line{lines.length === 1 ? '' : 's'}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-muted hover:text-foreground text-lg leading-none px-1 shrink-0"
            aria-label="Close diff view"
          >
            ✕
          </button>
        </div>

        {/* Diff body */}
        <div className="flex-1 overflow-auto bg-[#0f141e] font-mono text-xs leading-5 rounded-b-xl">
          {lines.length === 0 ? (
            <div className="p-4 text-[#7f899c]">
              No line-level diff available for this change.
            </div>
          ) : (
            lines.map((line, i) => {
              let cls = 'text-[#c8d0df]'
              if (line.startsWith('+++') || line.startsWith('---')) {
                cls = 'text-[#7f899c] font-semibold'
              } else if (line.startsWith('@@')) {
                cls = 'text-[#4fc1ff]'
              } else if (line.startsWith('+')) {
                cls = 'bg-[#16a34a]/15 text-[#4ade80]'
              } else if (line.startsWith('-')) {
                cls = 'bg-[#dc2626]/15 text-[#f87171]'
              }
              return (
                <div key={i} className={`px-4 whitespace-pre-wrap break-words ${cls}`}>
                  {line}
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
