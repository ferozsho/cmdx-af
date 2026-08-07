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
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">System Architecture</h1>
        <p className="text-sm text-gray-400 mt-1">
          End-to-end platform stack for the AgentForge AI Agent Framework.
        </p>
      </div>

      <div className="space-y-4">
        {layers.map((layer, i) => (
          <React.Fragment key={layer.title}>
            <div
              className={`border rounded-xl p-5 ${colorMap[layer.color] || 'border-gray-800 bg-[#111827]'}`}
            >
              <div
                className={`text-xs font-bold uppercase tracking-wider mb-3 ${textColorMap[layer.color] || 'text-gray-300'}`}
              >
                {layer.title}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                {layer.items.map((item) => (
                  <div
                    key={item}
                    className="bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-xs text-gray-300"
                  >
                    {item}
                  </div>
                ))}
              </div>
            </div>
            {i < layers.length - 1 && (
              <div className="text-center text-gray-600 text-lg">↓</div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  )
}
