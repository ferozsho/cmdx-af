'use client'

import React, { useState } from 'react'

interface DiffViewerProps {
  filePath: string
  originalCode: string
  modifiedCode: string
}

export default function DiffViewer({ filePath, originalCode, modifiedCode }: DiffViewerProps) {
  const [viewMode, setViewMode] = useState<'DIFF' | 'MODIFIED'>('DIFF')

  const originalLines = originalCode.split('\n')
  const modifiedLines = modifiedCode.split('\n')

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
        <div className="p-4 overflow-y-auto overflow-x-auto space-y-1 flex-1">
          {originalLines.map((line, idx) => (
            <div key={`orig-${idx}`} className="flex gap-3 text-red-400 bg-red-500/10 px-2 py-0.5 rounded items-start">
              <span className="w-8 text-slate-500 text-right select-none flex-shrink-0">{idx + 1}</span>
              <span className="select-none text-red-400 flex-shrink-0">-</span>
              <pre className="flex-1 whitespace-pre-wrap break-all font-mono text-xs">{line}</pre>
            </div>
          ))}
          {modifiedLines.map((line, idx) => (
            <div key={`mod-${idx}`} className="flex gap-3 text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded items-start">
              <span className="w-8 text-slate-500 text-right select-none flex-shrink-0">{idx + 1}</span>
              <span className="select-none text-emerald-400 flex-shrink-0">+</span>
              <pre className="flex-1 whitespace-pre-wrap break-all font-mono text-xs">{line}</pre>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-4 overflow-y-auto overflow-x-auto space-y-1 flex-1">
          {modifiedLines.map((line, idx) => (
            <div key={`line-${idx}`} className="flex gap-3 text-slate-300 px-2 py-0.5 rounded hover:bg-slate-800/40 items-start">
              <span className="w-8 text-slate-500 text-right select-none flex-shrink-0">{idx + 1}</span>
              <pre className="flex-1 whitespace-pre-wrap break-all font-mono text-xs">{line}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
