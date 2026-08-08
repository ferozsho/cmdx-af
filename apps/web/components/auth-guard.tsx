'use client'

import { useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { clearToken, getMe, getToken } from '@/lib/api'

/**
 * Client-side auth guard. Redirects unauthenticated visitors to /login and
 * validates a stored JWT on load. Renders children only after the session
 * is confirmed.
 */
export default function AuthGuard({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const router = useRouter()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let cancelled = false
    const finish = (ok: boolean) => {
      if (!cancelled) setReady(ok)
    }

    const token = getToken()
    const isLogin = pathname?.startsWith('/login')

    if (!token) {
      if (!isLogin) router.replace('/login')
      finish(true)
      return
    }
    if (isLogin) {
      router.replace('/')
      finish(true)
      return
    }

    getMe()
      .then(() => finish(true))
      .catch(() => {
        clearToken()
        if (!cancelled) router.replace('/login')
        finish(true)
      })

    return () => {
      cancelled = true
    }
  }, [pathname, router])

  if (!ready) {
    return (
      <main className="flex-1 min-w-0 grid place-items-center p-7">
        <div className="text-muted text-xs font-mono animate-pulse">
          Checking session…
        </div>
      </main>
    )
  }

  return <>{children}</>
}
