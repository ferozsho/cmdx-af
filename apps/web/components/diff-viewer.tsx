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
    <div className="bg-[#0d121f] border border-gray-800 rounded-xl overflow-hidden text-xs font-mono max-h-[550px] flex flex-col shadow-xl">
      {/* Header bar */}
      <div className="bg-[#111827] px-4 py-2.5 border-b border-gray-800 flex items-center justify-between text-gray-300 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-blue-400 font-semibold font-sans">📄 {filePath}</span>
          <span className="text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded font-sans">
            Modified by Agent
          </span>
        </div>
        <div className="flex gap-1 text-[11px] font-sans">
          <button
            onClick={() => setViewMode('DIFF')}
            className={`px-2.5 py-1 rounded transition-colors ${
              viewMode === 'DIFF'
                ? 'bg-blue-600 text-white font-bold'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Diff View
          </button>
          <button
            onClick={() => setViewMode('MODIFIED')}
            className={`px-2.5 py-1 rounded transition-colors ${
              viewMode === 'MODIFIED'
                ? 'bg-blue-600 text-white font-bold'
                : 'text-gray-400 hover:text-white'
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
            <div key={`orig-${idx}`} className="flex gap-3 text-red-400 bg-red-950/20 px-2 py-0.5 rounded items-start">
              <span className="w-8 text-gray-600 text-right select-none flex-shrink-0">{idx + 1}</span>
              <span className="select-none text-red-500 flex-shrink-0">-</span>
              <pre className="flex-1 whitespace-pre-wrap break-all font-mono text-xs">{line}</pre>
            </div>
          ))}
          {modifiedLines.map((line, idx) => (
            <div key={`mod-${idx}`} className="flex gap-3 text-emerald-400 bg-emerald-950/20 px-2 py-0.5 rounded items-start">
              <span className="w-8 text-gray-600 text-right select-none flex-shrink-0">{idx + 1}</span>
              <span className="select-none text-emerald-500 flex-shrink-0">+</span>
              <pre className="flex-1 whitespace-pre-wrap break-all font-mono text-xs">{line}</pre>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-4 overflow-y-auto overflow-x-auto space-y-1 flex-1">
          {modifiedLines.map((line, idx) => (
            <div key={`line-${idx}`} className="flex gap-3 text-gray-300 px-2 py-0.5 rounded hover:bg-gray-800/40 items-start">
              <span className="w-8 text-gray-600 text-right select-none flex-shrink-0">{idx + 1}</span>
              <pre className="flex-1 whitespace-pre-wrap break-all font-mono text-xs">{line}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
