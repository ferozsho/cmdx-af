'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { login, register, setTokens } from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password) return
    setBusy(true)
    setError(null)
    try {
      const res =
        mode === 'login'
          ? await login(email.trim(), password)
          : await register(email.trim(), password, fullName.trim() || undefined)
      setTokens(res.access_token, res.refresh_token)
      router.replace('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="flex-1 min-w-0 grid place-items-center p-7">
      <div className="card-af w-full max-w-[420px] p-7 space-y-5">
        <div className="text-center space-y-1">
          <div className="text-3xl">⚡</div>
          <h1 className="text-lg font-bold text-foreground">AgentForge</h1>
          <p className="text-xs text-muted">
            {mode === 'login'
              ? 'Sign in to your workspace'
              : 'Create an account to get started'}
          </p>
        </div>

        {/* Mode toggle */}
        <div className="grid grid-cols-2 gap-1 rounded-[10px] bg-surface-secondary border border-border p-1 text-xs font-semibold">
          {(['login', 'register'] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => {
                setMode(m)
                setError(null)
              }}
              className={`py-1.5 rounded-[8px] transition-colors ${
                mode === m
                  ? 'btn-primary-af !py-1.5 !text-xs'
                  : 'text-muted hover:text-foreground'
              }`}
            >
              {m === 'login' ? 'Sign In' : 'Register'}
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="space-y-3">
          {mode === 'register' && (
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Full name (optional)"
              className="input-af w-full"
            />
          )}
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
            className="input-af w-full"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password (min 6 characters)"
            required
            minLength={6}
            className="input-af w-full"
          />

          {error && (
            <div className="rounded-[10px] border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-xs text-red-500">
              ⚠ {error}
            </div>
          )}

          <button
            type="submit"
            disabled={busy}
            className="btn-primary-af w-full disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {busy
              ? 'Please wait…'
              : mode === 'login'
                ? 'Sign In'
                : 'Create Account'}
          </button>
        </form>

        {mode === 'login' && (
          <div className="text-center text-xs text-muted">
            <Link
              href="/forgot-password"
              className="text-primary hover:underline"
            >
              Forgot password?
            </Link>
          </div>
        )}
      </div>
    </main>
  )
}
