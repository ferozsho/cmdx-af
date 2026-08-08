'use client'

import React, { useMemo, useState } from 'react'

interface DiffViewerProps {
  filePath: string
  originalCode: string
  modifiedCode: string
}

type DiffType = 'context' | 'added' | 'removed'

interface DiffLine {
  type: DiffType
  text: string
}

/** Compute a unified diff using longest-common-subsequence (LCS) DP. */
function computeDiff(original: string[], modified: string[]): DiffLine[] {
  const n = original.length
  const m = modified.length

  // LCS length table
  const dp: number[][] = Array.from({ length: n + 1 }, () =>
    new Array<number>(m + 1).fill(0),
  )
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] =
        original[i] === modified[j]
          ? dp[i + 1][j + 1] + 1
          : Math.max(dp[i + 1][j], dp[i][j + 1])
    }
  }

  const lines: DiffLine[] = []
  let i = 0
  let j = 0
  while (i < n && j < m) {
    if (original[i] === modified[j]) {
      lines.push({ type: 'context', text: original[i] })
      i++
      j++
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      lines.push({ type: 'removed', text: original[i] })
      i++
    } else {
      lines.push({ type: 'added', text: modified[j] })
      j++
    }
  }
  while (i < n) {
    lines.push({ type: 'removed', text: original[i] })
    i++
  }
  while (j < m) {
    lines.push({ type: 'added', text: modified[j] })
    j++
  }
  return lines
}

const LINE_STYLES: Record<DiffType, string> = {
  context: 'text-slate-300',
  added: 'text-emerald-400 bg-emerald-500/10',
  removed: 'text-red-400 bg-red-500/10',
}

const PREFIX: Record<DiffType, string> = {
  context: ' ',
  added: '+',
  removed: '-',
}

export default function DiffViewer({
  filePath,
  originalCode,
  modifiedCode,
}: DiffViewerProps) {
  const [viewMode, setViewMode] = useState<'DIFF' | 'MODIFIED'>('DIFF')

  const originalLines = useMemo(() => originalCode.split('\n'), [originalCode])
  const modifiedLines = useMemo(() => modifiedCode.split('\n'), [modifiedCode])
  const diffLines = useMemo(
    () => computeDiff(originalLines, modifiedLines),
    [originalLines, modifiedLines],
  )

  const hasBaseline = originalCode.trim().length > 0

  return (
    <div className="bg-[#0d121f] border border-border rounded-xl overflow-hidden text-xs font-mono max-h-[550px] flex flex-col shadow-xl">
      {/* Header bar */}
      <div className="bg-[#111827] px-4 py-2.5 border-b border-border flex items-center justify-between text-gray-200 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-primary font-semibold font-sans">📄 {filePath}</span>
          <span className="text-[10px] bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded font-sans">
            Modified by Agent
          </span>
        </div>
        <div className="flex gap-1.5 text-[11px] font-sans">
          <button
            onClick={() => setViewMode('DIFF')}
            className={`px-2.5 py-1 rounded transition-colors ${
              viewMode === 'DIFF'
                ? 'btn-primary-af !px-2.5 !py-1 !text-xs'
                : 'btn-secondary-af !px-2.5 !py-1 !text-xs'
            }`}
          >
            Diff View
          </button>
          <button
            onClick={() => setViewMode('MODIFIED')}
            className={`px-2.5 py-1 rounded transition-colors ${
              viewMode === 'MODIFIED'
                ? 'btn-primary-af !px-2.5 !py-1 !text-xs'
                : 'btn-secondary-af !px-2.5 !py-1 !text-xs'
            }`}
          >
            Full Source
          </button>
        </div>
      </div>

      {/* Code Area */}
      {viewMode === 'DIFF' ? (
        <div className="p-4 overflow-y-auto overflow-x-auto flex-1">
          {!hasBaseline && (
            <div className="text-[11px] text-muted pb-2 border-b border-border/60 mb-2">
              No committed baseline found for this file — treating all lines as
              additions (new file).
            </div>
          )}
          {diffLines.map((line, idx) => (
            <div
              key={idx}
              className={`flex gap-3 px-2 py-0.5 rounded items-start ${LINE_STYLES[line.type]}`}
            >
              <span className="w-8 text-slate-500 text-right select-none flex-shrink-0">
                {idx + 1}
              </span>
              <span className="select-none flex-shrink-0">{PREFIX[line.type]}</span>
              <pre className="flex-1 whitespace-pre-wrap break-all font-mono text-xs">
                {line.text}
              </pre>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-4 overflow-y-auto overflow-x-auto flex-1">
          {modifiedLines.map((line, idx) => (
            <div
              key={`line-${idx}`}
              className="flex gap-3 text-slate-300 px-2 py-0.5 rounded hover:bg-slate-800/40 items-start"
            >
              <span className="w-8 text-slate-500 text-right select-none flex-shrink-0">
                {idx + 1}
              </span>
              <pre className="flex-1 whitespace-pre-wrap break-all font-mono text-xs">
                {line}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
