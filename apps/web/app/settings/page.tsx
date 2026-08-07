'use client'

import React, { useCallback, useRef, useState } from 'react'
import { getFullHealth, updateSettings, type ComponentHealth } from '@/lib/api'

type TestStatus = 'idle' | 'testing' | 'success' | 'error'

interface TestResult {
  status: TestStatus
  message: string
}

export default function SettingsPage() {
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const apiKeyRef = useRef<HTMLInputElement>(null)
  const baseUrlRef = useRef<HTMLInputElement>(null)
  const chatModelRef = useRef<HTMLInputElement>(null)
  const coderModelRef = useRef<HTMLInputElement>(null)
  const maxStepsRef = useRef<HTMLInputElement>(null)
  const timeoutRef = useRef<HTMLInputElement>(null)
  const ragTopKRef = useRef<HTMLInputElement>(null)
  const ragThresholdRef = useRef<HTMLInputElement>(null)
  const contextBudgetRef = useRef<HTMLInputElement>(null)
  const allowedCommandsRef = useRef<HTMLTextAreaElement>(null)

  const [deepseekResult, setDeepseekResult] = useState<TestResult>({
    status: 'idle',
    message: '',
  })
  const [dbResult, setDbResult] = useState<TestResult>({
    status: 'idle',
    message: '',
  })

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setSaveError(null)
    try {
      await updateSettings({
        deepseek_api_key: apiKeyRef.current?.value || '',
        deepseek_base_url: baseUrlRef.current?.value || '',
        chat_model: chatModelRef.current?.value || '',
        coder_model: coderModelRef.current?.value || '',
        max_agent_steps: parseInt(maxStepsRef.current?.value || '10', 10),
        agent_timeout: parseInt(timeoutRef.current?.value || '600', 10),
        rag_top_k: parseInt(ragTopKRef.current?.value || '5', 10),
        rag_similarity_threshold: parseFloat(
          ragThresholdRef.current?.value || '0.65',
        ),
        context_window_budget:
          contextBudgetRef.current?.value || '30%',
        allowed_commands:
          allowedCommandsRef.current?.value || '',
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      setSaveError(
        err instanceof Error ? err.message : 'Failed to save settings',
      )
    } finally {
      setSaving(false)
    }
  }

  const testConnection = useCallback(
    async (
      componentKey: string,
      setResult: (r: TestResult) => void,
    ) => {
      setResult({ status: 'testing', message: 'Testing...' })
      try {
        const health = await getFullHealth()
        const component: ComponentHealth | undefined =
          health.components[componentKey]
        if (!component) {
          setResult({
            status: 'error',
            message: `Component "${componentKey}" not found in health response.`,
          })
          return
        }
        if (component.status === 'healthy') {
          setResult({
            status: 'success',
            message: component.message || 'Connected successfully.',
          })
        } else if (component.status === 'degraded') {
          setResult({
            status: 'error',
            message: `Degraded: ${component.message}`,
          })
        } else if (component.status === 'not_configured') {
          setResult({
            status: 'error',
            message: component.message || 'Not configured.',
          })
        } else {
          setResult({
            status: 'error',
            message: `Unhealthy: ${component.message}`,
          })
        }
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : 'Unknown error'
        setResult({ status: 'error', message: `Connection failed: ${msg}` })
      }
    },
    [],
  )

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
          disabled={saving}
          className="btn-primary-af text-sm disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {saveError && (
        <div className="max-w-[920px] rounded-[10px] p-3 text-xs font-medium mb-4 bg-red-500/10 text-red-500 border border-red-500/30">
          {saveError}
        </div>
      )}

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
          <div>
            <label className="block font-bold text-[13px] text-foreground mb-[7px]">
              DeepSeek Base URL
            </label>
            <input
              ref={baseUrlRef}
              type="text"
              defaultValue="https://api.deepseek.com"
              className="input-af"
            />
          </div>
          <Field label="Chat Model" inputRef={chatModelRef} defaultValue="deepseek-chat" />
          <Field label="Coder Model" inputRef={coderModelRef} defaultValue="deepseek-coder" />
          <Field label="Max Agent Steps" inputRef={maxStepsRef} defaultValue="10" type="number" />
          <Field label="Agent Timeout (seconds)" inputRef={timeoutRef} defaultValue="600" type="number" />
          <Field label="RAG Top K" inputRef={ragTopKRef} defaultValue="5" type="number" />
          <Field label="RAG Similarity Threshold" inputRef={ragThresholdRef} defaultValue="0.65" type="number" step="0.01" />
          <Field label="Context Window Budget" inputRef={contextBudgetRef} defaultValue="30%" />
        </div>

        <div className="field">
          <label className="block font-bold text-[13px] text-foreground mb-[7px]">
            DeepSeek API Key
          </label>
          <input
            ref={apiKeyRef}
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
            ref={allowedCommandsRef}
            rows={3}
            defaultValue="pip install, npm install, npm run build, python -m, npx, pytest, jest, ruff, eslint, mypy, bandit"
            className="input-af font-mono text-xs resize-y"
          />
        </div>

        <div className="pt-[18px] border-t border-border flex flex-wrap gap-2.5 items-start">
          <div className="flex flex-col gap-1.5">
            <button
              type="button"
              className="btn-secondary-af text-xs !px-[15px] !py-[10px]"
              onClick={() =>
                testConnection('deepseek_api', (r) => setDeepseekResult(r))
              }
              disabled={deepseekResult.status === 'testing'}
            >
              {deepseekResult.status === 'testing'
                ? 'Testing...'
                : 'Test DeepSeek Connection'}
            </button>
            {deepseekResult.status !== 'idle' && (
              <TestFeedback result={deepseekResult} />
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <button
              type="button"
              className="btn-secondary-af text-xs !px-[15px] !py-[10px]"
              onClick={() =>
                testConnection('postgresql', (r) => setDbResult(r))
              }
              disabled={dbResult.status === 'testing'}
            >
              {dbResult.status === 'testing'
                ? 'Testing...'
                : 'Test Database Connection'}
            </button>
            {dbResult.status !== 'idle' && (
              <TestFeedback result={dbResult} />
            )}
          </div>
        </div>
      </form>
    </div>
  )
}

function Field({
  label,
  defaultValue,
  type = 'text',
  step,
  inputRef,
}: {
  label: string
  defaultValue: string
  type?: string
  step?: string
  inputRef: React.RefObject<HTMLInputElement | null>
}) {
  return (
    <div>
      <label className="block font-bold text-[13px] text-foreground mb-[7px]">
        {label}
      </label>
      <input
        ref={inputRef}
        type={type}
        defaultValue={defaultValue}
        step={step}
        className="input-af"
      />
    </div>
  )
}

function TestFeedback({ result }: { result: TestResult }) {
  if (result.status === 'testing') {
    return (
      <span className="text-[11px] text-muted animate-pulse">
        {result.message}
      </span>
    )
  }
  if (result.status === 'success') {
    return (
      <span className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
        ✓ {result.message}
      </span>
    )
  }
  if (result.status === 'error') {
    return (
      <span className="text-[11px] font-medium text-red-500">
        ✗ {result.message}
      </span>
    )
  }
  return null
}
