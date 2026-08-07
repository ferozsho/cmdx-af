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
    <div>
      {/* Page Header — matches prototype .page-title */}
      <div className="flex items-start justify-between mb-[22px]">
        <div>
          <h2 className="text-[26px] font-bold text-main m-0 mb-[5px]">
            Observability
          </h2>
          <p className="text-sub text-sm m-0">
            Operational metrics for pipelines, agents, RAG, and LLM usage.
          </p>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-[18px]">
        {/* Agent Duration */}
        <div className="card-af p-[18px]">
          <h3 className="text-sm font-bold text-main m-0 mb-4">
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
            <div key={name} className="grid grid-cols-[120px_1fr_48px] gap-[10px] items-center my-3 text-xs">
              <span className="text-main truncate">{name}</span>
              <div className="h-2 bg-[#edf0f5] dark:bg-[#1f2937] rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#1b78d2] to-[#6e38c7] rounded-full"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-main font-mono text-right font-bold">
                {pct}s
              </span>
            </div>
          ))}
        </div>

        {/* Pipeline Health */}
        <div className="card-af p-[18px]">
          <h3 className="text-sm font-bold text-main m-0 mb-4">
            Pipeline Health
          </h3>
          <div className="space-y-1 text-xs">
            {[
              ['Success rate', '—'],
              ['Avg pipeline duration', '—'],
              ['RAG search P95', '—'],
              ['LLM error rate', '—'],
              ['Queue depth', '—'],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex justify-between py-[11px] border-b border-[#e3e8f1] dark:border-[#1f2937] last:border-0"
              >
                <span className="text-sub">{label}</span>
                <span className="text-main font-bold">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* LLM Usage */}
        <div className="card-af p-[18px]">
          <h3 className="text-sm font-bold text-main m-0 mb-4">
            DeepSeek Usage
          </h3>
          <div className="space-y-1 text-xs">
            {[
              ['Prompt tokens (today)', '—'],
              ['Completion tokens', '—'],
              ['Estimated spend', '—'],
              ['Top model', health?.mode === 'mock' ? 'mock' : 'deepseek-coder'],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex justify-between py-[11px] border-b border-[#e3e8f1] dark:border-[#1f2937] last:border-0"
              >
                <span className="text-sub">{label}</span>
                <span className="text-main font-bold">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Infrastructure Health */}
        <div className="card-af p-[18px]">
          <h3 className="text-sm font-bold text-main m-0 mb-4">
            Infrastructure
          </h3>
          <div className="space-y-1 text-xs">
            {[
              ['FastAPI', health ? 'Healthy' : '—'],
              ['PostgreSQL', '—'],
              ['Redis', '—'],
              ['Qdrant', '—'],
              ['Celery workers', '—'],
            ].map(([name, status]) => (
              <div
                key={name}
                className="flex justify-between py-[11px] border-b border-[#e3e8f1] dark:border-[#1f2937] last:border-0"
              >
                <span className="text-sub">{name}</span>
                <span
                  className={`font-bold ${
                    status === 'Healthy'
                      ? 'text-[#238636]'
                      : status === '—'
                        ? 'text-sub'
                        : 'text-[#d6263b]'
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
