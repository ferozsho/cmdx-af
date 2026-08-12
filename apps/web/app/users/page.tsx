'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { listUsers, deleteUser, type UserResponse } from '@/lib/api'
import ConfirmModal from '@/components/confirm-modal'
import Pagination from '@/components/pagination'

export default function UsersPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const urlPage = Math.max(1, parseInt(searchParams.get('page') || '1', 10) || 1)
  const urlPerPage = Math.max(1, parseInt(searchParams.get('perPage') || '5', 10) || 5)
  const urlSearch = searchParams.get('q') || ''

  const [users, setUsers] = useState<UserResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [page, setPage] = useState(urlPage)
  const [perPage, setPerPage] = useState(urlPerPage)
  const [search, setSearch] = useState(urlSearch)
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; email: string } | null>(null)

  const syncUrl = (p: number, pp: number, q: string) => {
    const params = new URLSearchParams()
    if (p > 1) params.set('page', String(p))
    if (pp !== 5) params.set('perPage', String(pp))
    if (q) params.set('q', q)
    const qs = params.toString()
    router.replace(`/users${qs ? `?${qs}` : ''}`, { scroll: false })
  }

  const loadUsers = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listUsers()
      setUsers(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let ignore = false
    const run = async () => {
      try {
        const data = await listUsers()
        if (!ignore) setUsers(data)
      } catch (err: unknown) {
        if (!ignore) {
          setError(
            err instanceof Error ? err.message : 'Failed to load users',
          )
        }
      } finally {
        if (!ignore) setLoading(false)
      }
    }
    void run()
    return () => {
      ignore = true
    }
  }, [])

  const handleDelete = (userId: string, email: string) => {
    setDeleteTarget({ id: userId, email })
  }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    setMsg(null)
    try {
      await deleteUser(deleteTarget.id)
      setMsg(`User "${deleteTarget.email}" deleted.`)
      loadUsers()
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : 'Delete failed')
    } finally {
      setDeleteTarget(null)
    }
  }

  // Filter by search
  const filtered = search
    ? users.filter(
        (u) =>
          u.email.toLowerCase().includes(search.toLowerCase()) ||
          (u.full_name || '').toLowerCase().includes(search.toLowerCase()),
      )
    : users

  const totalPages = Math.max(1, Math.ceil(filtered.length / perPage))
  const safePage = Math.min(page, totalPages)
  const pageUsers = filtered.slice((safePage - 1) * perPage, safePage * perPage)

  const handlePerPageChange = (val: number) => {
    setPerPage(val)
    setPage(1)
    syncUrl(1, val, search)
  }

  const goToPage = (p: number) => {
    setPage(p)
    syncUrl(p, perPage, search)
  }

  const handleSearch = (q: string) => {
    setSearch(q)
    setPage(1)
    syncUrl(1, perPage, q)
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-surface-secondary rounded w-48" />
          <div className="h-64 bg-surface-secondary rounded-[16px]" />
        </div>
      </div>
    )
  }

  const adminCount = filtered.filter((u) => u.role === 'admin').length
  const userCount = filtered.filter((u) => u.role === 'user').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">👥 Users</h1>
          <p className="text-sm text-muted mt-1">
            Manage platform accounts and roles.
          </p>
        </div>
        <Link
          href="/users/new"
          className="btn-primary-af text-base flex items-center gap-1.5"
        >
          <span>＋</span> Add User
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card-af p-5 text-center">
          <p className="text-3xl font-bold text-foreground">{users.length}</p>
          <p className="text-xs uppercase tracking-wider text-muted mt-1.5">Total</p>
        </div>
        <div className="card-af p-5 text-center">
          <p className="text-3xl font-bold text-primary">{adminCount}</p>
          <p className="text-xs uppercase tracking-wider text-muted mt-1.5">Admins</p>
        </div>
        <div className="card-af p-5 text-center">
          <p className="text-3xl font-bold text-foreground">{userCount}</p>
          <p className="text-xs uppercase tracking-wider text-muted mt-1.5">Users</p>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="card-af p-4 text-sm text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px]">
          {error}
        </div>
      )}
      {msg && (
        <div className="card-af p-4 text-sm text-emerald-500 bg-emerald-500/10 border border-emerald-500/30 rounded-[10px] flex items-center justify-between">
          <span>{msg}</span>
          <button onClick={() => setMsg(null)} className="text-sm text-muted hover:text-foreground">✕</button>
        </div>
      )}

      {/* Users Table */}
      <div className="card-af overflow-hidden">
        {users.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-muted text-base">No users found.</p>
            <Link href="/users/new" className="text-primary text-base hover:underline mt-2 inline-block">
              Create the first user →
            </Link>
          </div>
        ) : (
          <>
            {/* Search */}
            <div className="px-5 pt-4">
              <input
                type="search"
                value={search}
                onChange={(e) => handleSearch(e.target.value)}
                placeholder="Search by email or name..."
                className="input-af w-full sm:w-80 text-sm"
              />
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface-secondary/50">
                    <th className="text-left p-5 font-semibold text-sm uppercase tracking-wider text-muted">
                      User
                    </th>
                    <th className="text-left p-5 font-semibold text-sm uppercase tracking-wider text-muted">
                      Role
                    </th>
                    <th className="text-left p-5 font-semibold text-sm uppercase tracking-wider text-muted hidden sm:table-cell">
                      Joined
                    </th>
                    <th className="text-right p-5 font-semibold text-sm uppercase tracking-wider text-muted">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {pageUsers.map((u) => {
                    const isProtected = u.email === 'admin@agentforge.ai'
                    return (
                      <tr
                        key={u.id}
                        className="border-b border-border last:border-0 hover:bg-surface-secondary/30 transition-colors"
                      >
                        <td className="p-5">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-primary/10 text-primary grid place-items-center font-bold text-sm flex-shrink-0">
                              {u.email.charAt(0).toUpperCase()}
                            </div>
                            <div className="min-w-0">
                              <p className="font-semibold text-foreground truncate text-[15px]">
                                {u.full_name || u.email.split('@')[0]}
                              </p>
                              <p className="text-sm text-muted truncate">{u.email}</p>
                            </div>
                            {isProtected && (
                              <span className="text-xs bg-amber-500/15 text-amber-500 px-2 py-0.5 rounded font-bold flex-shrink-0">
                                PROTECTED
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="p-5">
                          <span
                            className={`inline-block text-xs px-2.5 py-1 rounded-full font-bold ${
                              u.role === 'admin'
                                ? 'bg-primary/15 text-primary border border-primary/30'
                                : 'bg-surface-secondary text-muted border border-border'
                            }`}
                          >
                            {u.role}
                          </span>
                        </td>
                        <td className="p-5 text-muted text-sm hidden sm:table-cell">
                          {u.created_at
                            ? new Date(u.created_at).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric',
                              })
                            : '—'}
                        </td>
                        <td className="p-5 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Link
                              href={`/users/${encodeURIComponent(u.id)}/edit`}
                              className="btn-secondary-af !px-3 !py-1.5 text-sm"
                            >
                              Edit
                            </Link>
                            {!isProtected && (
                              <button
                                onClick={() => handleDelete(u.id, u.email)}
                                className="text-sm text-red-500 hover:text-red-400 hover:bg-red-500/10 px-3 py-1.5 rounded transition-colors"
                              >
                                Delete
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <Pagination
              storageKey="users-perpage"
              currentPage={safePage}
              totalPages={totalPages}
              totalItems={filtered.length}
              perPage={perPage}
              onPageChange={(p) => goToPage(p)}
              onPerPageChange={(pp) => handlePerPageChange(pp)}
            />
          </>
        )}
      </div>
      <ConfirmModal
        open={!!deleteTarget}
        title="Delete User"
        message={`Permanently delete user "${deleteTarget?.email}"? This cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
