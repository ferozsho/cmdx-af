'use client'

import { useEffect, useState } from 'react'
import { getSettings, getModels } from '@/lib/api'

type ProviderInfo = {
  name: string
  label: string
  model: string
  color: string
  icon: string
}

const PROVIDER_META: Record<string, { label: string; color: string; icon: string }> = {
  deepseek: { label: 'DeepSeek', color: '#7e42d1', icon: '🔮' },
  openai: { label: 'OpenAI', color: '#10a37f', icon: '🧠' },
  gemini: { label: 'Gemini', color: '#4285f4', icon: '✨' },
  claude: { label: 'Claude', color: '#d97706', icon: '🧬' },
}

export default function ProviderBadge() {
  const [provider, setProvider] = useState<ProviderInfo | null>(null)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [allConfigured, setAllConfigured] = useState<ProviderInfo[]>([])

  useEffect(() => {
    Promise.all([getSettings(), getModels()]).then(([settings, models]) => {
      const configured: ProviderInfo[] = []

      const providers = ['deepseek', 'openai', 'gemini', 'claude'] as const
      for (const p of providers) {
        const hasKey = settings[`has_${p}_key` as keyof typeof settings] as boolean
        const modelName = settings[`${p}_chat_model` as keyof typeof settings] as string
        if (hasKey && modelName) {
          const meta = PROVIDER_META[p]
          const modelInfo = models.find((m) => m.name === modelName)
          configured.push({
            name: p,
            label: meta.label,
            model: modelInfo?.label || modelName,
            color: meta.color,
            icon: meta.icon,
          })
        }
      }

      setAllConfigured(configured)
      if (configured.length > 0) {
        setProvider(configured[0])
      }
    }).catch(() => {})
  }, [])

  if (!provider) {
    return (
      <div className="text-[11px] text-muted bg-muted/40 px-2.5 py-1 rounded-full border border-border/50">
        No provider configured
      </div>
    )
  }

  if (allConfigured.length === 1) {
    return (
      <div
        className="inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full border shadow-sm"
        style={{
          backgroundColor: `${provider.color}15`,
          borderColor: `${provider.color}40`,
          color: provider.color,
        }}
        title={`${provider.label} · ${provider.model}`}
      >
        <span className="text-xs">{provider.icon}</span>
        <span>{provider.model}</span>
      </div>
    )
  }

  // Multiple providers configured — show clickable badge with dropdown
  return (
    <div className="relative">
      <button
        onClick={() => setDropdownOpen(!dropdownOpen)}
        className="inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full border shadow-sm cursor-pointer hover:brightness-110 transition"
        style={{
          backgroundColor: `${provider.color}15`,
          borderColor: `${provider.color}40`,
          color: provider.color,
        }}
        title={`Active: ${provider.label} · ${provider.model}`}
      >
        <span className="text-xs">{provider.icon}</span>
        <span>{provider.model}</span>
        <svg className="w-3 h-3 opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {dropdownOpen && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setDropdownOpen(false)} />
          <div className="absolute right-0 top-full mt-1.5 z-40 bg-surface border border-border rounded-lg shadow-xl py-1 min-w-[200px]">
            <div className="px-3 py-1.5 text-[10px] uppercase tracking-wider text-muted font-semibold">
              Configured Providers
            </div>
            {allConfigured.map((p) => (
              <button
                key={p.name}
                onClick={() => { setProvider(p); setDropdownOpen(false) }}
                className="w-full flex items-center gap-2 px-3 py-2 text-[12px] hover:bg-muted/30 transition text-left"
              >
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: p.color }}
                />
                <span className="font-medium">{p.label}</span>
                <span className="text-muted ml-auto text-[11px]">{p.model}</span>
                {provider.name === p.name && (
                  <svg className="w-3.5 h-3.5 ml-0.5" style={{ color: p.color }} fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
