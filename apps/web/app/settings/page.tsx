'use client'

import React, { useCallback, useEffect, useRef, useState } from 'react'
import {
  changePassword,
  getFullHealth,
  getModels,
  getSettings,
  setTokens,
  testProviderConnection,
  updateSettings,
  type ComponentHealth,
} from '@/lib/api'

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
  // OpenAI
  const oaiKeyRef = useRef<HTMLInputElement>(null)
  const oaiBaseUrlRef = useRef<HTMLInputElement>(null)
  // Gemini
  const gemKeyRef = useRef<HTMLInputElement>(null)
  // Claude
  const claudeKeyRef = useRef<HTMLInputElement>(null)
  // General
  const maxStepsRef = useRef<HTMLInputElement>(null)
  const timeoutRef = useRef<HTMLInputElement>(null)
  const ragTopKRef = useRef<HTMLInputElement>(null)
  const ragThresholdRef = useRef<HTMLInputElement>(null)
  const ragChunkSizeRef = useRef<HTMLInputElement>(null)
  const ragChunkOverlapRef = useRef<HTMLInputElement>(null)
  const contextBudgetRef = useRef<HTMLInputElement>(null)
  const allowedCommandsRef = useRef<HTMLTextAreaElement>(null)

  const [activeProvider, setActiveProvider] = useState('deepseek')

  // Model selection state (replaces refs for selects)
  const [dsModel, setDsModel] = useState('deepseek-chat')
  const [oaiModel, setOaiModel] = useState('gpt-4o')
  const [gemModel, setGemModel] = useState('gemini-2.5-pro')
  const [claudeModel, setClaudeModel] = useState('claude-3-5-sonnet-20241022')
  const [allModels, setAllModels] = useState<any[]>([])

  // Masked key display values
  const [maskedKeys, setMaskedKeys] = useState<Record<string, string>>({})
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({})

  const [deepseekResult, setDeepseekResult] = useState<TestResult>({
    status: 'idle',
    message: '',
  })
  const [dbResult, setDbResult] = useState<TestResult>({
    status: 'idle',
    message: '',
  })

  // Change-password card state
  const [pwBusy, setPwBusy] = useState(false)
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwMessage, setPwMessage] = useState<string | null>(null)
  const pwCurrentRef = useRef<HTMLInputElement>(null)
  const pwNewRef = useRef<HTMLInputElement>(null)
  const pwConfirmRef = useRef<HTMLInputElement>(null)

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    const current = pwCurrentRef.current?.value || ''
    const next = pwNewRef.current?.value || ''
    const confirm = pwConfirmRef.current?.value || ''
    if (!current || !next) return
    if (next.length < 6) {
      setPwError('New password must be at least 6 characters.')
      return
    }
    if (next !== confirm) {
      setPwError('New passwords do not match.')
      return
    }
    setPwBusy(true)
    setPwError(null)
    setPwMessage(null)
    try {
      const res = await changePassword(current, next)
      setTokens(res.access_token, res.refresh_token)
      setPwMessage('Password updated — you have been re-authenticated.')
      if (pwCurrentRef.current) pwCurrentRef.current.value = ''
      if (pwNewRef.current) pwNewRef.current.value = ''
      if (pwConfirmRef.current) pwConfirmRef.current.value = ''
    } catch (err) {
      setPwError(
        err instanceof Error ? err.message : 'Failed to change password',
      )
    } finally {
      setPwBusy(false)
    }
  }

  // Load current settings from API on mount
  useEffect(() => {
    getModels().then(setAllModels).catch(() => {})
    getSettings().then((s) => {
      if (baseUrlRef.current) baseUrlRef.current.value = s.deepseek_base_url || ''
      setDsModel(s.deepseek_chat_model || 'deepseek-chat')
      if (oaiBaseUrlRef.current) oaiBaseUrlRef.current.value = s.openai_base_url || ''
      setOaiModel(s.openai_chat_model || 'gpt-4o')
      setGemModel(s.gemini_chat_model || 'gemini-2.5-pro')
      setClaudeModel(s.claude_chat_model || 'claude-3-5-sonnet-20241022')
      // Store masked keys for display
      setMaskedKeys({
        deepseek: s.deepseek_api_key_masked || '',
        openai: s.openai_api_key_masked || '',
        gemini: s.gemini_api_key_masked || '',
        claude: s.claude_api_key_masked || '',
      })
      // Pre-fill password fields with masked values so user sees a key exists
      if (apiKeyRef.current && s.has_deepseek_key) apiKeyRef.current.value = s.deepseek_api_key_masked
      if (oaiKeyRef.current && s.has_openai_key) oaiKeyRef.current.value = s.openai_api_key_masked
      if (gemKeyRef.current && s.has_gemini_key) gemKeyRef.current.value = s.gemini_api_key_masked
      if (claudeKeyRef.current && s.has_claude_key) claudeKeyRef.current.value = s.claude_api_key_masked
      // General fields
      if (maxStepsRef.current) maxStepsRef.current.value = String(s.max_agent_steps ?? 10)
      if (timeoutRef.current) timeoutRef.current.value = String(s.agent_timeout ?? 600)
      if (ragTopKRef.current) ragTopKRef.current.value = String(s.rag_top_k ?? 5)
      if (ragChunkSizeRef.current) ragChunkSizeRef.current.value = String(s.rag_chunk_size ?? 500)
      if (ragChunkOverlapRef.current) ragChunkOverlapRef.current.value = String(s.rag_chunk_overlap ?? 50)
      if (ragThresholdRef.current) ragThresholdRef.current.value = String(s.rag_similarity_threshold ?? 0.65)
      if (contextBudgetRef.current) contextBudgetRef.current.value = s.context_window_budget || ''
      if (allowedCommandsRef.current) allowedCommandsRef.current.value = s.allowed_commands || ''
    }).catch(() => {})
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setSaveError(null)
    try {
      await updateSettings({
        deepseek_api_key: apiKeyRef.current?.value || '',
        deepseek_base_url: baseUrlRef.current?.value || '',
        deepseek_chat_model: dsModel,
        openai_api_key: oaiKeyRef.current?.value || '',
        openai_base_url: oaiBaseUrlRef.current?.value || '',
        openai_chat_model: oaiModel,
        gemini_api_key: gemKeyRef.current?.value || '',
        gemini_chat_model: gemModel,
        claude_api_key: claudeKeyRef.current?.value || '',
        claude_chat_model: claudeModel,
        max_agent_steps: parseInt(maxStepsRef.current?.value || '10', 10),
        agent_timeout: parseInt(timeoutRef.current?.value || '600', 10),
        rag_top_k: parseInt(ragTopKRef.current?.value || '5', 10),
        rag_chunk_size: parseInt(ragChunkSizeRef.current?.value || '500', 10),
        rag_chunk_overlap: parseInt(ragChunkOverlapRef.current?.value || '50', 10),
        rag_similarity_threshold: parseFloat(ragThresholdRef.current?.value || '0.65'),
        context_window_budget: contextBudgetRef.current?.value || '30%',
        allowed_commands: allowedCommandsRef.current?.value || '',
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

  const testProviderConn = useCallback(
    async (provider: string) => {
      setTestResults((prev) => ({
        ...prev,
        [provider]: { status: 'testing', message: 'Testing...' },
      }))
      try {
        const result = await testProviderConnection(provider)
        if (result.ok) {
          setTestResults((prev) => ({
            ...prev,
            [provider]: {
              status: 'success',
              message: result.detail || 'Connected successfully.',
            },
          }))
        } else {
          setTestResults((prev) => ({
            ...prev,
            [provider]: {
              status: 'error',
              message: result.error || 'Connection failed.',
            },
          }))
        }
      } catch (err: unknown) {
        setTestResults((prev) => ({
          ...prev,
          [provider]: {
            status: 'error',
            message: err instanceof Error ? err.message : 'Unknown error',
          },
        }))
      }
    },
    [],
  )

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
      <form onSubmit={handleSave} className="card-af max-w-[920px] p-6 space-y-5">
        {/* Provider Tabs */}
        <div className="flex gap-1 border-b border-border pb-0">
          {(['deepseek', 'openai', 'gemini', 'claude', 'general'] as const).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setActiveProvider(p)}
              className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors -mb-[1px] border-b-2 ${
                activeProvider === p
                  ? 'border-primary text-primary bg-primary/5'
                  : 'border-transparent text-muted hover:text-foreground'
              }`}
            >
              {p === 'deepseek' ? 'DeepSeek' : p === 'openai' ? 'OpenAI' : p === 'gemini' ? 'Gemini' : p === 'claude' ? 'Claude' : 'General'}
            </button>
          ))}
        </div>

        {/* DeepSeek Tab */}
        {activeProvider === 'deepseek' && (
          <div className="space-y-4">
            <div>
              <label className="block font-bold text-[13px] text-foreground mb-[7px]">
                DeepSeek API Key
              </label>
              <input ref={apiKeyRef} type="password" defaultValue="" placeholder={maskedKeys.deepseek || 'sk-...'} className="input-af" />
              {maskedKeys.deepseek && (
                <p className="text-[10px] text-emerald-500 mt-1">✓ Key configured</p>
              )}
            </div>
            <Field label="Base URL" inputRef={baseUrlRef} defaultValue="https://api.deepseek.com/v1" />
            <div>
              <label className="block font-bold text-[13px] text-foreground mb-[7px]">Chat Model</label>
              <select value={dsModel} onChange={(e) => setDsModel(e.target.value)} className="input-af">
                {allModels.filter(m => m.provider === 'deepseek').map(m => (
                  <option key={m.name} value={m.name}>{m.label} ({(m.context_limit/1000).toFixed(0)}K){m.vision ? ' 👁' : ''}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-wrap gap-2">
              <button type="button" className="btn-secondary-af text-xs" onClick={() => testProviderConn('deepseek')} disabled={testResults['deepseek']?.status === 'testing'}>
                {testResults['deepseek']?.status === 'testing' ? 'Testing...' : 'Test Connection'}
              </button>
              <button type="button" className="btn-secondary-af text-xs" onClick={() => testConnection('postgresql', setDbResult)} disabled={dbResult.status === 'testing'}>
                {dbResult.status === 'testing' ? 'Testing...' : 'Test Database'}
              </button>
            </div>
            {testResults['deepseek']?.status !== 'idle' && testResults['deepseek'] && <TestFeedback result={testResults['deepseek']} />}
            {dbResult.status !== 'idle' && <TestFeedback result={dbResult} />}
          </div>
        )}

        {/* OpenAI Tab */}
        {activeProvider === 'openai' && (
          <div className="space-y-4">
            <div>
              <label className="block font-bold text-[13px] text-foreground mb-[7px]">
                OpenAI API Key
              </label>
              <input ref={oaiKeyRef} type="password" defaultValue="" placeholder={maskedKeys.openai || 'sk-...'} className="input-af" />
              {maskedKeys.openai && (
                <p className="text-[10px] text-emerald-500 mt-1">✓ Key configured</p>
              )}
            </div>
            <Field label="Base URL" inputRef={oaiBaseUrlRef} defaultValue="https://api.openai.com/v1" />
            <div>
              <label className="block font-bold text-[13px] text-foreground mb-[7px]">Chat Model</label>
              <select value={oaiModel} onChange={(e) => setOaiModel(e.target.value)} className="input-af">
                {allModels.filter(m => m.provider === 'openai').map(m => (
                  <option key={m.name} value={m.name}>{m.label} ({(m.context_limit/1000).toFixed(0)}K){m.vision ? ' 👁' : ''}</option>
                ))}
              </select>
            </div>
            <p className="text-[10px] text-muted">Supports: gpt-4o, gpt-4-turbo, gpt-3.5-turbo</p>
            <button type="button" className="btn-secondary-af text-xs" onClick={() => testProviderConn('openai')} disabled={testResults['openai']?.status === 'testing'}>
              {testResults['openai']?.status === 'testing' ? 'Testing...' : 'Test Connection'}
            </button>
            {testResults['openai']?.status !== 'idle' && testResults['openai'] && <TestFeedback result={testResults['openai']} />}
          </div>
        )}

        {/* Gemini Tab */}
        {activeProvider === 'gemini' && (
          <div className="space-y-4">
            <div>
              <label className="block font-bold text-[13px] text-foreground mb-[7px]">
                Gemini API Key
              </label>
              <input ref={gemKeyRef} type="password" defaultValue="" placeholder={maskedKeys.gemini || 'AIza...'} className="input-af" />
              {maskedKeys.gemini && (
                <p className="text-[10px] text-emerald-500 mt-1">✓ Key configured</p>
              )}
            </div>
            <div>
              <label className="block font-bold text-[13px] text-foreground mb-[7px]">Chat Model</label>
              <select value={gemModel} onChange={(e) => setGemModel(e.target.value)} className="input-af">
                {allModels.filter(m => m.provider === 'gemini').map(m => (
                  <option key={m.name} value={m.name}>{m.label} ({(m.context_limit/1000).toFixed(0)}K){m.vision ? ' 👁' : ''}</option>
                ))}
              </select>
            </div>
            <p className="text-[10px] text-muted">Supports: gemini-2.5-pro, gemini-2.5-flash, gemini-1.5-pro</p>
            <button type="button" className="btn-secondary-af text-xs" onClick={() => testProviderConn('gemini')} disabled={testResults['gemini']?.status === 'testing'}>
              {testResults['gemini']?.status === 'testing' ? 'Testing...' : 'Test Connection'}
            </button>
            {testResults['gemini']?.status !== 'idle' && testResults['gemini'] && <TestFeedback result={testResults['gemini']} />}
          </div>
        )}

        {/* Claude Tab */}
        {activeProvider === 'claude' && (
          <div className="space-y-4">
            <div>
              <label className="block font-bold text-[13px] text-foreground mb-[7px]">
                Claude API Key
              </label>
              <input ref={claudeKeyRef} type="password" defaultValue="" placeholder={maskedKeys.claude || 'sk-ant-...'} className="input-af" />
              {maskedKeys.claude && (
                <p className="text-[10px] text-emerald-500 mt-1">✓ Key configured</p>
              )}
            </div>
            <div>
              <label className="block font-bold text-[13px] text-foreground mb-[7px]">Chat Model</label>
              <select value={claudeModel} onChange={(e) => setClaudeModel(e.target.value)} className="input-af">
                {allModels.filter(m => m.provider === 'claude').map(m => (
                  <option key={m.name} value={m.name}>{m.label} ({(m.context_limit/1000).toFixed(0)}K){m.vision ? ' 👁' : ''}</option>
                ))}
              </select>
            </div>
            <p className="text-[10px] text-muted">Supports: claude-3-5-sonnet, claude-3-opus, claude-3-haiku</p>
            <button type="button" className="btn-secondary-af text-xs" onClick={() => testProviderConn('claude')} disabled={testResults['claude']?.status === 'testing'}>
              {testResults['claude']?.status === 'testing' ? 'Testing...' : 'Test Connection'}
            </button>
            {testResults['claude']?.status !== 'idle' && testResults['claude'] && <TestFeedback result={testResults['claude']} />}
          </div>
        )}

        {/* General Tab */}
        {activeProvider === 'general' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-[18px]">
              <Field label="Max Agent Steps" inputRef={maxStepsRef} defaultValue="10" type="number" />
              <Field label="Agent Timeout (seconds)" inputRef={timeoutRef} defaultValue="600" type="number" />
              <Field label="RAG Top K" inputRef={ragTopKRef} defaultValue="5" type="number" />
              <Field label="RAG Chunk Size" inputRef={ragChunkSizeRef} defaultValue="500" type="number" />
              <Field label="RAG Chunk Overlap" inputRef={ragChunkOverlapRef} defaultValue="50" type="number" />
              <Field label="RAG Similarity Threshold" inputRef={ragThresholdRef} defaultValue="0.65" type="number" step="0.01" />
              <Field label="Context Window Budget" inputRef={contextBudgetRef} defaultValue="30%" />
            </div>
            <div>
              <label className="block font-bold text-[13px] text-foreground mb-[7px]">Allowed Commands</label>
              <textarea ref={allowedCommandsRef} rows={3} defaultValue="pip install, npm install, npm run build, python -m, npx, pytest, jest, ruff, eslint, mypy, bandit" className="input-af font-mono text-xs resize-y" />
            </div>
            <button
              type="button"
              className="btn-secondary-af text-xs"
              onClick={() => testConnection('postgresql', setDbResult)}
              disabled={dbResult.status === 'testing'}
            >
              {dbResult.status === 'testing' ? 'Testing...' : 'Test Database Connection'}
            </button>
            {dbResult.status !== 'idle' && <TestFeedback result={dbResult} />}
          </div>
        )}
      </form>

      {/* Change Password — admin account security */}
      <form
        onSubmit={handleChangePassword}
        className="card-af max-w-[920px] p-6 space-y-4 mt-[18px]"
      >
        <div>
          <h3 className="text-sm font-bold text-foreground m-0">
            Change Password
          </h3>
          <p className="text-xs text-muted mt-1 m-0">
            Changing your password revokes all existing sessions immediately.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-[18px]">
          <div>
            <label className="block font-bold text-[13px] text-foreground mb-[7px]">
              Current Password
            </label>
            <input
              ref={pwCurrentRef}
              type="password"
              required
              className="input-af"
            />
          </div>
          <div>
            <label className="block font-bold text-[13px] text-foreground mb-[7px]">
              New Password
            </label>
            <input
              ref={pwNewRef}
              type="password"
              required
              minLength={6}
              className="input-af"
            />
          </div>
          <div>
            <label className="block font-bold text-[13px] text-foreground mb-[7px]">
              Confirm New Password
            </label>
            <input
              ref={pwConfirmRef}
              type="password"
              required
              className="input-af"
            />
          </div>
        </div>
        {pwError && (
          <div className="rounded-[10px] p-3 text-xs font-medium bg-red-500/10 text-red-500 border border-red-500/30">
            ⚠ {pwError}
          </div>
        )}
        {pwMessage && (
          <div className="rounded-[10px] p-3 text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
            ✓ {pwMessage}
          </div>
        )}
        <button
          type="submit"
          disabled={pwBusy}
          className="btn-secondary-af text-xs !px-[15px] !py-[10px] disabled:opacity-50"
        >
          {pwBusy ? 'Updating...' : 'Update Password'}
        </button>
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
