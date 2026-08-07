import React from 'react'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'System Architecture',
  description: 'AgentForge platform architecture and component stack.',
}

export default function ArchitecturePage() {
  const layers = [
    {
      title: 'DEEPSEEK API — Paid Component',
      color: 'red',
      items: ['deepseek-chat', 'deepseek-coder'],
    },
    {
      title: 'CREWAI — Multi-Agent Orchestration',
      color: 'purple',
      items: [
        '📋 Planning Agent',
        '🏗 Architecture Agent',
        '🎨 UI/UX Agent',
        '📘 Documentation Agent',
        '⌨ Code Agents (Frontend/Backend/DB)',
        '🧪 Test Agent',
        '🛡 Validation Agent',
        '⑂ Git Agent',
      ],
    },
    {
      title: 'RAG + TOOLS',
      color: 'blue',
      items: [
        '📁 Filesystem — Pathlib + Watchdog',
        '◫ Qdrant RAG — Embeddings + Search',
        '▣ Execution — pytest + Ruff + Bandit',
      ],
    },
    {
      title: 'FASTAPI BACKEND',
      color: 'teal',
      items: [
        'Crew orchestration',
        'SSE event streaming',
        'WSS Tool Gateway',
      ],
    },
    {
      title: 'DATA LAYER',
      color: 'gold',
      items: [
        'PostgreSQL — Projects · Runs · Artifacts',
        'Qdrant — Code + Doc embeddings',
        'Redis — Queue · Cache · Pub/Sub',
      ],
    },
    {
      title: 'NEXT.JS FRONTEND',
      color: 'green',
      items: [
        'Dashboard',
        'Live Agent View',
        'Files · RAG · Git',
        'Observability',
      ],
    },
  ]

  const colorMap: Record<string, string> = {
    red: 'border-red-800 bg-red-950/20',
    purple: 'border-purple-800 bg-purple-950/20',
    blue: 'border-blue-800 bg-blue-950/20',
    teal: 'border-teal-800 bg-teal-950/20',
    gold: 'border-amber-800 bg-amber-950/20',
    green: 'border-emerald-800 bg-emerald-950/20',
  }

  const textColorMap: Record<string, string> = {
    red: 'text-red-400',
    purple: 'text-purple-400',
    blue: 'text-blue-400',
    teal: 'text-teal-400',
    gold: 'text-amber-400',
    green: 'text-emerald-400',
  }

  return (
    <div>
      {/* Page Header — matches prototype .page-title */}
      <div className="flex items-start justify-between mb-[22px]">
        <div>
          <h2 className="text-[26px] font-bold text-main m-0 mb-[5px]">
            System Architecture
          </h2>
          <p className="text-sub text-sm m-0">
            End-to-end platform stack for the AgentForge AI Agent Framework.
          </p>
        </div>
      </div>

      <div className="card-af p-[18px]">
        {layers.map((layer, i) => (
          <React.Fragment key={layer.title}>
            <div
              className={`border border-[1.5px] rounded-[13px] p-[14px] my-[10px] text-center ${colorMap[layer.color] || 'border-[#e3e8f1] bg-white'}`}
            >
              <div
                className={`font-black mb-2 text-xs uppercase tracking-wider ${textColorMap[layer.color] || 'text-main'}`}
              >
                {layer.title}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-[8px]">
                {layer.items.map((item) => (
                  <div
                    key={item}
                    className="bg-white dark:bg-[#1f2937] border border-[#dfe4ee] dark:border-[#374151] rounded-[9px] p-[9px] text-xs text-main font-medium"
                  >
                    {item}
                  </div>
                ))}
              </div>
            </div>
            {i < layers.length - 1 && (
              <div className="text-center text-[#778198] text-[22px] h-[18px] leading-none my-1">
                ↓
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  )
}
