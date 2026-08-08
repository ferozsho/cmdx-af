'use client'

import { useState } from 'react'
import Link from 'next/link'
import { forgotPassword, resetPassword } from '@/lib/api'

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<1 | 2>(1)
  const [email, setEmail] = useState('')
  const [token, setToken] = useState('')
  const [devToken, setDevToken] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const requestToken = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const res = await forgotPassword(email.trim())
      if (res.reset_token) {
        setDevToken(res.reset_token)
        setToken(res.reset_token)
      }
      setMessage(res.detail)
      setStep(2)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setBusy(false)
    }
  }

  const doReset = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token.trim() || !password) return
    if (password.length < 6) {
      setError('New password must be at least 6 characters.')
      return
    }
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const res = await resetPassword(token.trim(), password)
      setMessage(res.detail)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Reset failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="flex-1 min-w-0 grid place-items-center p-7">
      <div className="card-af w-full max-w-[420px] p-7 space-y-5">
        <div className="text-center space-y-1">
          <div className="text-3xl">🔑</div>
          <h1 className="text-lg font-bold text-foreground">
            {step === 1 ? 'Reset Password' : 'Set New Password'}
          </h1>
          <p className="text-xs text-muted">
            {step === 1
              ? 'Enter your account email to receive a reset token.'
              : 'Enter the reset token and your new password.'}
          </p>
        </div>

        {step === 1 ? (
          <form onSubmit={requestToken} className="space-y-3">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              required
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
              {busy ? 'Please wait…' : 'Send Reset Token'}
            </button>
          </form>
        ) : (
          <form onSubmit={doReset} className="space-y-3">
            {message && (
              <div className="rounded-[10px] border border-primary/30 bg-primary/10 px-4 py-2.5 text-xs text-primary">
                {message}
              </div>
            )}
            {devToken && (
              <div className="rounded-[10px] border border-border bg-surface-secondary px-4 py-3 text-xs">
                <div className="text-[10px] text-muted mb-1 font-semibold">
                  Dev-mode reset token (no email server configured):
                </div>
                <code className="font-mono text-primary break-all select-all">
                  {devToken}
                </code>
              </div>
            )}
            <input
              type="text"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Reset token"
              required
              className="input-af w-full font-mono"
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="New password (min 6 characters)"
              required
              minLength={6}
              className="input-af w-full"
            />
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Confirm new password"
              required
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
              {busy ? 'Please wait…' : 'Reset Password'}
            </button>
          </form>
        )}

        <div className="text-center text-xs text-muted">
          <Link href="/login" className="text-primary hover:underline">
            ← Back to sign in
          </Link>
        </div>
      </div>
    </main>
  )
}
