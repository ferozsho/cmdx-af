'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { getUser, updateUser, type UserResponse } from '@/lib/api'

export default function EditUserPage() {
  const router = useRouter()
  const params = useParams()
  const userId = params.id as string

  const [user, setUser] = useState<UserResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ full_name: '', role: 'user' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  const isProtected = user?.email === 'admin@agentforge.ai'

  useEffect(() => {
    async function load() {
      try {
        const u = await getUser(userId)
        setUser(u)
        setForm({ full_name: u.full_name || '', role: u.role })
      } catch (err: any) {
        setError(err?.message || 'Failed to load user')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [userId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (isProtected) {
      setError('The primary admin account cannot be modified.')
      return
    }
    setSaving(true)
    setError(null)
    setMsg(null)
    try {
      await updateUser(userId, form)
      setMsg('User updated successfully.')
      setTimeout(() => router.push('/users'), 1000)
    } catch (err: any) {
      setError(err?.message || 'Failed to update user')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-lg mx-auto p-7">
        <p className="text-sm text-muted animate-pulse">Loading user...</p>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="max-w-lg mx-auto p-7">
        <p className="text-sm text-red-500">User not found.</p>
        <Link href="/users" className="text-xs text-primary hover:underline mt-2 block">
          ← Back to Users
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto space-y-6">
      <div>
        <Link href="/users" className="text-xs text-primary hover:underline">
          ← Back to Users
        </Link>
        <h1 className="text-xl font-bold text-foreground mt-2">✏️ Edit User</h1>
        <p className="text-xs text-muted mt-1">
          {user.email}
          {isProtected && (
            <span className="ml-2 text-[10px] bg-amber-500/15 text-amber-500 px-1.5 py-0.5 rounded font-bold">
              PROTECTED
            </span>
          )}
        </p>
      </div>

      {error && (
        <div className="card-af p-4 text-sm text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px]">
          {error}
        </div>
      )}
      {msg && (
        <div className="card-af p-4 text-sm text-emerald-500 bg-emerald-500/10 border border-emerald-500/30 rounded-[10px]">
          {msg}
        </div>
      )}

      <form onSubmit={handleSubmit} className="card-af p-6 space-y-4">
        <div className="flex items-center gap-3 pb-3 border-b border-border">
          <div className="w-10 h-10 rounded-full bg-primary/15 text-primary grid place-items-center font-bold text-sm">
            {user.email.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">{user.email}</p>
            <p className="text-[10px] text-muted">ID: {user.id.slice(0, 8)}...</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Full Name</label>
          <input
            type="text"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            className="input-af w-full"
            placeholder="Jane Smith"
            disabled={isProtected}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Role</label>
          <select
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
            className="input-af w-full"
            disabled={isProtected}
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
          {isProtected && (
            <p className="text-[10px] text-amber-500 mt-1">
              The primary admin role cannot be changed.
            </p>
          )}
        </div>

        <div className="flex gap-3 pt-2">
          {!isProtected && (
            <button
              type="submit"
              disabled={saving}
              className="btn-primary-af text-sm disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          )}
          <Link href="/users" className="btn-secondary-af text-sm">
            {isProtected ? 'Back to Users' : 'Cancel'}
          </Link>
        </div>
      </form>
    </div>
  )
}
