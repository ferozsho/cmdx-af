'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { getAgent, updateAgent, type AgentTemplateResponse } from '@/lib/api'

const CAPABILITIES = ['reasoning', 'coding', 'analysis', 'testing', 'validation', 'git']

export default function EditAgentPage() {
  const router = useRouter()
  const params = useParams()
  const agentId = params.id as string
  const [agent, setAgent] = useState<AgentTemplateResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({
    name: '', description: '', capability: 'reasoning', system_prompt: '', tools: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    getAgent(agentId)
      .then((a) => {
        setAgent(a)
        setForm({
          name: a.name, description: a.description || '', capability: a.capability,
          system_prompt: a.system_prompt || '', tools: (a.tools || []).join(', '),
        })
      })
      .catch((err) => setError(err?.message || 'Failed to load agent'))
      .finally(() => setLoading(false))
  }, [agentId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) { setError('Name is required.'); return }
    setSaving(true)
    setError(null)
    try {
      await updateAgent(agentId, {
        name: form.name.trim(),
        description: form.description.trim(),
        capability: form.capability,
        system_prompt: form.system_prompt.trim(),
        tools: form.tools.split(',').map((t) => t.trim()).filter(Boolean),
      })
      setMsg('Agent updated. New version created.')
      setTimeout(() => router.push('/agents'), 1200)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update agent')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="max-w-2xl p-7 text-sm text-muted animate-pulse">Loading agent...</div>
  if (!agent) return <div className="max-w-2xl p-7"><p className="text-sm text-red-500">Agent not found.</p><Link href="/agents" className="text-xs text-primary hover:underline mt-2 block">← Back to Agents</Link></div>

  return (
    <div className="space-y-6">
      <div>
        <Link href="/agents" className="text-sm text-primary hover:underline">← Back to Agents</Link>
        <h1 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">✏️ Edit Agent</h1>
        <p className="text-sm text-muted mt-1">
          {agent.name} · v{agent.version}
          {!agent.is_active && <span className="ml-2 text-xs bg-red-500/15 text-red-500 px-1.5 py-0.5 rounded font-bold">Inactive</span>}
        </p>
      </div>
      {error && <div className="card-af p-4 text-sm text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px]">{error}</div>}
      {msg && <div className="card-af p-4 text-sm text-emerald-500 bg-emerald-500/10 border border-emerald-500/30 rounded-[10px]">{msg}</div>}
      <form onSubmit={handleSubmit} className="card-af p-6 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Name *</label>
            <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="input-af w-full" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Capability</label>
            <select value={form.capability} onChange={(e) => setForm({ ...form, capability: e.target.value })}
              className="input-af w-full">
              {CAPABILITIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Description</label>
          <input type="text" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="input-af w-full" />
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">System Prompt</label>
          <textarea value={form.system_prompt} onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
            rows={5} className="input-af w-full text-sm font-mono" />
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Tools (comma-separated)</label>
          <input type="text" value={form.tools} onChange={(e) => setForm({ ...form, tools: e.target.value })}
            className="input-af w-full" placeholder="read_file, write_file, run_command" />
        </div>
        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={saving} className="btn-primary-af text-sm disabled:opacity-50">
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
          <Link href="/agents" className="btn-secondary-af text-sm">Cancel</Link>
        </div>
      </form>
    </div>
  )
}
