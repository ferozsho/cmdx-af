'use client'

import React, { useState } from 'react'

export default function SettingsPage() {
  const [saved, setSaved] = useState(false)

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  return (
    <div>
      {/* Page Header — matches prototype .page-title */}
      <div className="flex items-start justify-between mb-[22px]">
        <div>
          <h2 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">
            Settings
          </h2>
          <p className="text-muted text-sm m-0">
            Configure AgentForge platform settings and API connections.
          </p>
        </div>
        <button
          onClick={handleSave}
          className="btn-primary-af text-sm"
        >
          Save Changes
        </button>
      </div>

      {saved && (
        <div className="max-w-[920px] rounded-[10px] p-3 text-xs font-medium mb-4 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
          Settings saved successfully.
        </div>
      )}

      {/* Form Card — matches prototype .card.form-card */}
      <form
        onSubmit={handleSave}
        className="card-af max-w-[920px] p-6 space-y-5"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-[18px]">
          <SettingsField label="DeepSeek Base URL" defaultValue="https://api.deepseek.com" />
          <SettingsField label="Chat Model" defaultValue="deepseek-chat" />
          <SettingsField label="Coder Model" defaultValue="deepseek-coder" />
          <SettingsField label="Max Agent Steps" defaultValue="10" type="number" />
          <SettingsField label="Agent Timeout (seconds)" defaultValue="600" type="number" />
          <SettingsField label="RAG Top K" defaultValue="5" type="number" />
          <SettingsField label="RAG Similarity Threshold" defaultValue="0.65" type="number" step="0.01" />
          <SettingsField label="Context Window Budget" defaultValue="30%" />
        </div>

        <div className="field">
          <label className="block font-bold text-[13px] text-foreground mb-[7px]">
            DeepSeek API Key
          </label>
          <input
            type="password"
            placeholder="••••••••••••••••"
            className="input-af"
          />
          <p className="text-[10px] text-muted mt-1">
            Your API key is never exposed to the browser and is stored encrypted.
          </p>
        </div>

        <div className="field">
          <label className="block font-bold text-[13px] text-foreground mb-[7px]">
            Allowed Commands
          </label>
          <textarea
            rows={3}
            defaultValue="pip install, npm install, npm run build, python -m, npx, pytest, jest, ruff, eslint, mypy, bandit"
            className="input-af font-mono text-xs resize-y"
          />
        </div>

        <div className="pt-[18px] border-t border-border flex gap-2.5">
          <button
            type="button"
            className="btn-secondary-af text-xs !px-[15px] !py-[10px]"
          >
            Test DeepSeek Connection
          </button>
          <button
            type="button"
            className="btn-secondary-af text-xs !px-[15px] !py-[10px]"
          >
            Test Database Connection
          </button>
        </div>
      </form>
    </div>
  )
}

function SettingsField({
  label,
  defaultValue,
  type = 'text',
  step,
}: {
  label: string
  defaultValue: string
  type?: string
  step?: string
}) {
  return (
    <div>
      <label className="block font-bold text-[13px] text-foreground mb-[7px]">
        {label}
      </label>
      <input
        type={type}
        defaultValue={defaultValue}
        step={step}
        className="input-af"
      />
    </div>
  )
}
