'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createUser } from '@/lib/api'

export default function NewUserPage() {
  const router = useRouter()
  const [form, setForm] = useState({
    email: '', password: '', full_name: '', role: 'user',
    org_name: '', job_title: '', agent_quota: 10,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.email || !form.password) {
      setError('Email and password are required.')
      return
    }
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await createUser(form)
      router.push('/users')
    } catch (err: any) {
      setError(err?.message || 'Failed to create user')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <Link href="/users" className="text-sm text-primary hover:underline">
          ← Back to Users
        </Link>
        <h1 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">➕ Create User</h1>
        <p className="text-sm text-muted mt-1">
          Add a new user account to the platform.
        </p>
      </div>

      {error && (
        <div className="card-af p-4 text-sm text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px]">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="card-af p-6 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Email *</label>
            <input type="email" value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="input-af w-full" placeholder="user@example.com" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Password *</label>
            <input type="password" value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="input-af w-full" placeholder="Min 6 characters" required minLength={6} />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Full Name</label>
            <input type="text" value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              className="input-af w-full" placeholder="Jane Smith" />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Role</label>
            <select value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="input-af w-full">
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Organization</label>
            <input type="text" value={form.org_name}
              onChange={(e) => setForm({ ...form, org_name: e.target.value })}
              className="input-af w-full" placeholder="Acme Corp" />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Job Title</label>
            <input type="text" value={form.job_title}
              onChange={(e) => setForm({ ...form, job_title: e.target.value })}
              className="input-af w-full" placeholder="Senior Developer" />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Agent Quota</label>
            <input type="number" value={form.agent_quota}
              onChange={(e) => setForm({ ...form, agent_quota: Number(e.target.value) })}
              className="input-af w-full" min={0} max={1000} />
            <p className="text-[11px] text-muted mt-1">Max concurrent agent runs.</p>
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={saving} className="btn-primary-af text-sm disabled:opacity-50">
            {saving ? 'Creating...' : 'Create User'}
          </button>
          <Link href="/users" className="btn-secondary-af text-sm">Cancel</Link>
        </div>
      </form>
    </div>
  )
}
