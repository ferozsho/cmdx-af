'use client'

import React, { useEffect, useState } from 'react'
import { getHealth } from '@/lib/api'

export default function ObservabilityPage() {
  const [health, setHealth] = useState<any>(null)

  useEffect(() => {
    getHealth()
      .then((data) => setHealth(data))
      .catch(console.error)
  }, [])

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Observability</h1>
        <p className="text-sm text-gray-400 mt-1">
          Operational metrics for pipelines, agents, RAG, and LLM usage.
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Agent Duration */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4">
            Agent Duration (avg)
          </h3>
          {[
            ['Planning', 34],
            ['Architecture', 46],
            ['Code Generation', 78],
            ['Testing', 62],
            ['Validation', 48],
            ['Git', 22],
          ].map(([name, pct]) => (
            <div key={name} className="flex items-center gap-3 mb-3 text-xs">
              <span className="w-28 text-gray-400">{name}</span>
              <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-600 to-purple-600 rounded-full"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-gray-300 font-mono w-8 text-right">
                {pct}s
              </span>
            </div>
          ))}
        </div>

        {/* Pipeline Health */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4">
            Pipeline Health
          </h3>
          <div className="space-y-3 text-xs">
            {[
              ['Success rate', '—'],
              ['Avg pipeline duration', '—'],
              ['RAG search P95', '—'],
              ['LLM error rate', '—'],
              ['Queue depth', '—'],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex justify-between py-2 border-b border-gray-800 last:border-0"
              >
                <span className="text-gray-400">{label}</span>
                <span className="text-gray-200 font-mono">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* LLM Usage */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4">
            DeepSeek Usage
          </h3>
          <div className="space-y-3 text-xs">
            {[
              ['Prompt tokens (today)', '—'],
              ['Completion tokens', '—'],
              ['Estimated spend', '—'],
              ['Top model', health?.mode === 'mock' ? 'mock' : 'deepseek-coder'],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex justify-between py-2 border-b border-gray-800 last:border-0"
              >
                <span className="text-gray-400">{label}</span>
                <span className="text-gray-200 font-mono">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Infrastructure Health */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-4">
            Infrastructure
          </h3>
          <div className="space-y-3 text-xs">
            {[
              ['FastAPI', health ? 'Healthy' : '—'],
              ['PostgreSQL', '—'],
              ['Redis', '—'],
              ['Qdrant', '—'],
              ['Celery workers', '—'],
            ].map(([name, status]) => (
              <div
                key={name}
                className="flex justify-between py-2 border-b border-gray-800 last:border-0"
              >
                <span className="text-gray-400">{name}</span>
                <span
                  className={`font-mono ${
                    status === 'Healthy'
                      ? 'text-emerald-400'
                      : status === '—'
                        ? 'text-gray-600'
                        : 'text-red-400'
                  }`}
                >
                  {status === 'Healthy' && '● '}
                  {status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
