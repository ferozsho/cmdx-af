'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createAgent } from '@/lib/api'

const CAPABILITIES = ['reasoning', 'coding', 'analysis', 'testing', 'validation', 'git']

export default function NewAgentPage() {
  const router = useRouter()
  const [form, setForm] = useState({
    name: '', description: '', capability: 'reasoning', system_prompt: '', tools: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) { setError('Name is required.'); return }
    setSaving(true)
    setError(null)
    try {
      await createAgent({
        name: form.name.trim(),
        description: form.description.trim(),
        capability: form.capability,
        system_prompt: form.system_prompt.trim(),
        tools: form.tools.split(',').map((t) => t.trim()).filter(Boolean),
      })
      router.push('/agents')
    } catch (err: any) {
      setError(err?.message || 'Failed to create agent')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <Link href="/agents" className="text-sm text-primary hover:underline">← Back to Agents</Link>
        <h1 className="text-2xl font-bold text-foreground mt-2">➕ New Agent</h1>
        <p className="text-sm text-muted mt-1">Create a new agent template for the pipeline.</p>
      </div>
      {error && (
        <div className="card-af p-4 text-sm text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px]">{error}</div>
      )}
      <form onSubmit={handleSubmit} className="card-af p-6 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Name *</label>
            <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="input-af w-full" placeholder="Planning Agent" required />
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
            className="input-af w-full" placeholder="Analyzes instructions and produces structured plans..." />
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">System Prompt</label>
          <textarea value={form.system_prompt} onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
            rows={5} className="input-af w-full text-sm font-mono"
            placeholder="You are a Senior Software Architect..." />
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Tools (comma-separated)</label>
          <input type="text" value={form.tools} onChange={(e) => setForm({ ...form, tools: e.target.value })}
            className="input-af w-full" placeholder="read_file, write_file, run_command" />
        </div>
        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={saving} className="btn-primary-af text-sm disabled:opacity-50">
            {saving ? 'Creating...' : 'Create Agent'}
          </button>
          <Link href="/agents" className="btn-secondary-af text-sm">Cancel</Link>
        </div>
      </form>
    </div>
  )
}
