'use client'

import React, { useEffect, useState } from 'react'
import {
  listAgents,
  createAgent,
  updateAgent,
  type AgentTemplateResponse,
} from '@/lib/api'

const CAPABILITIES = ['reasoning', 'coding', 'analysis', 'testing', 'validation', 'git']

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentTemplateResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Create/Edit form state
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formName, setFormName] = useState('')
  const [formDesc, setFormDesc] = useState('')
  const [formCapability, setFormCapability] = useState('reasoning')
  const [formPrompt, setFormPrompt] = useState('')
  const [formTools, setFormTools] = useState('')
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const load = async () => {
    try {
      const data = await listAgents()
      setAgents(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const resetForm = () => {
    setShowForm(false)
    setEditingId(null)
    setFormName('')
    setFormDesc('')
    setFormCapability('reasoning')
    setFormPrompt('')
    setFormTools('')
    setFormError(null)
    setSaving(false)
  }

  const startEdit = (agent: AgentTemplateResponse) => {
    setShowForm(true)
    setEditingId(agent.id)
    setFormName(agent.name)
    setFormDesc(agent.description || '')
    setFormCapability(agent.capability || 'reasoning')
    setFormPrompt(agent.system_prompt || '')
    setFormTools((agent.tools || []).join(', '))
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formName.trim()) return
    setSaving(true)
    setFormError(null)
    try {
      const toolsList = formTools
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean)
      if (editingId) {
        await updateAgent(editingId, {
          name: formName.trim(),
          description: formDesc.trim(),
          capability: formCapability,
          system_prompt: formPrompt.trim(),
          tools: toolsList,
        })
      } else {
        await createAgent({
          name: formName.trim(),
          description: formDesc.trim(),
          capability: formCapability,
          system_prompt: formPrompt.trim(),
          tools: toolsList,
        })
      }
      resetForm()
      await load()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to save agent'
      setFormError(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-[22px]">
        <div>
          <h2 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">
            Agent Templates
          </h2>
          <p className="text-muted text-sm m-0">
            Define, version, and manage reusable agent templates for your
            pipeline. Updates create new versions automatically.
          </p>
        </div>
        <button
          onClick={() => {
            resetForm()
            setShowForm(true)
          }}
          className="btn-primary-af text-sm"
        >
          ＋ New Agent
        </button>
      </div>

      {error && (
        <div className="text-xs text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px] p-3 mb-4">
          {error}
          <button onClick={load} className="ml-3 underline">
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className="card-af p-8 text-center text-muted animate-pulse">
          Loading agent templates...
        </div>
      ) : agents.length === 0 ? (
        <div className="card-af p-8 text-center">
          <p className="text-muted text-sm">
            No agent templates defined yet.
          </p>
          <p className="text-muted text-xs mt-1">
            Click &quot;New Agent&quot; to create your first agent template.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className={`card-af p-4 transition-all flex flex-col ${
                editingId === agent.id
                  ? 'border-primary ring-1 ring-primary/30'
                  : ''
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-foreground text-sm truncate">
                    {agent.name}
                  </h3>
                  <p className="text-muted text-xs mt-0.5 line-clamp-2">
                    {agent.description || 'No description'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => startEdit(agent)}
                  className="btn-secondary-af !p-1.5 !text-xs !rounded-lg flex-shrink-0"
                  title="Edit agent"
                >
                  ✏️
                </button>
              </div>

              <div className="flex items-center gap-2 mt-2">
                <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-primary/15 text-primary">
                  {agent.capability}
                </span>
                <span className="text-[10px] text-muted">
                  v{agent.version}
                </span>
                {!agent.is_active && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/15 text-red-500">
                    Inactive
                  </span>
                )}
              </div>

              {(agent.tools || []).length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-border">
                  {agent.tools.map((tool: string) => (
                    <span
                      key={tool}
                      className="text-[10px] px-2 py-0.5 rounded-md bg-surface-secondary text-foreground-secondary border border-border"
                    >
                      {tool}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal Overlay */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-[10vh] bg-black/50 backdrop-blur-sm">
          <div className="card-af max-w-[520px] w-full mx-4 p-6 space-y-4 shadow-2xl max-h-[80vh] overflow-y-auto">
            <h3 className="text-sm font-bold text-foreground">
              {editingId ? 'Edit Agent Template' : 'New Agent Template'}
            </h3>

            {formError && (
              <div className="text-xs text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px] p-2.5">
                {formError}
              </div>
            )}

            <form onSubmit={handleSave} className="space-y-3">
              <div>
                <label className="block text-[13px] font-bold text-foreground mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="e.g. Planning Agent"
                  className="input-af"
                  required
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-[13px] font-bold text-foreground mb-1">
                  Description
                </label>
                <textarea
                  rows={2}
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  placeholder="What this agent does..."
                  className="input-af resize-y"
                />
              </div>
              <div>
                <label className="block text-[13px] font-bold text-foreground mb-1">
                  Capability
                </label>
                <select
                  value={formCapability}
                  onChange={(e) => setFormCapability(e.target.value)}
                  className="input-af"
                >
                  {CAPABILITIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[13px] font-bold text-foreground mb-1">
                  System Prompt
                </label>
                <textarea
                  rows={4}
                  value={formPrompt}
                  onChange={(e) => setFormPrompt(e.target.value)}
                  placeholder="You are a specialized agent that..."
                  className="input-af font-mono text-xs resize-y"
                />
              </div>
              <div>
                <label className="block text-[13px] font-bold text-foreground mb-1">
                  Tools (comma-separated)
                </label>
                <input
                  type="text"
                  value={formTools}
                  onChange={(e) => setFormTools(e.target.value)}
                  placeholder="read_file, write_file, search_code"
                  className="input-af"
                />
              </div>
              <div className="flex justify-end gap-2.5 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={resetForm}
                  className="btn-secondary-af text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving || !formName.trim()}
                  className="btn-primary-af text-xs disabled:opacity-50"
                >
                  {saving
                    ? 'Saving...'
                    : editingId
                      ? 'Save Changes'
                      : 'Create Agent'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
