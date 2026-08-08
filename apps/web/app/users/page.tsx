'use client'

import { useEffect, useState } from 'react'
import { listUsers, updateUser, deleteUser, type UserResponse } from '@/lib/api'

export default function UsersPage() {
  const [users, setUsers] = useState<UserResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState({ full_name: '', role: 'user' })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const loadUsers = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listUsers()
      setUsers(data)
    } catch (err: any) {
      setError(err?.message || 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadUsers() }, [])

  const startEdit = (u: UserResponse) => {
    setEditingId(u.id)
    setEditForm({ full_name: u.full_name || '', role: u.role })
    setMsg(null)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setMsg(null)
  }

  const handleSave = async (userId: string) => {
    setSaving(true)
    setMsg(null)
    try {
      await updateUser(userId, editForm)
      setMsg('User updated.')
      setEditingId(null)
      loadUsers()
    } catch (err: any) {
      setMsg(err?.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (userId: string, email: string) => {
    if (!confirm(`Delete user ${email}?`)) return
    setMsg(null)
    try {
      await deleteUser(userId)
      setMsg(`User ${email} deleted.`)
      loadUsers()
    } catch (err: any) {
      setMsg(err?.message || 'Delete failed')
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-7">
        <p className="text-sm text-muted animate-pulse">Loading users...</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">👥 Users</h1>
          <p className="text-xs text-muted mt-1">
            {users.length} user{users.length !== 1 ? 's' : ''} registered
          </p>
        </div>
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

      <div className="card-af overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-muted text-xs uppercase tracking-wider">
              <th className="text-left p-4 font-semibold">Email</th>
              <th className="text-left p-4 font-semibold">Name</th>
              <th className="text-left p-4 font-semibold">Role</th>
              <th className="text-right p-4 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => {
              const isProtected = u.email === 'admin@agentforge.ai'
              const isEditing = editingId === u.id
              return (
                <tr key={u.id} className="border-b border-border last:border-0">
                  <td className="p-4 font-medium text-foreground">
                    {u.email}
                    {isProtected && (
                      <span className="ml-2 text-[10px] bg-amber-500/15 text-amber-500 px-1.5 py-0.5 rounded font-bold">
                        PROTECTED
                      </span>
                    )}
                  </td>
                  {isEditing ? (
                    <>
                      <td className="p-4">
                        <input
                          type="text"
                          value={editForm.full_name}
                          onChange={(e) =>
                            setEditForm({ ...editForm, full_name: e.target.value })
                          }
                          className="input-af w-full text-xs"
                        />
                      </td>
                      <td className="p-4">
                        <select
                          value={editForm.role}
                          onChange={(e) =>
                            setEditForm({ ...editForm, role: e.target.value })
                          }
                          className="input-af w-full text-xs"
                        >
                          <option value="user">user</option>
                          <option value="admin">admin</option>
                        </select>
                      </td>
                      <td className="p-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleSave(u.id)}
                            disabled={saving}
                            className="btn-primary-af !px-3 !py-1 !text-xs"
                          >
                            {saving ? 'Saving...' : 'Save'}
                          </button>
                          <button
                            onClick={cancelEdit}
                            className="btn-secondary-af !px-3 !py-1 !text-xs"
                          >
                            Cancel
                          </button>
                        </div>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="p-4 text-muted">{u.full_name || '—'}</td>
                      <td className="p-4">
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                            u.role === 'admin'
                              ? 'bg-primary/15 text-primary'
                              : 'bg-surface-secondary text-muted'
                          }`}
                        >
                          {u.role}
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        {!isProtected && (
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => startEdit(u)}
                              className="btn-secondary-af !px-3 !py-1 !text-xs"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDelete(u.id, u.email)}
                              className="text-xs text-red-500 hover:text-red-400 px-2 py-1"
                            >
                              Delete
                            </button>
                          </div>
                        )}
                        {isProtected && (
                          <span className="text-[10px] text-muted italic">
                            Not editable
                          </span>
                        )}
                      </td>
                    </>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
