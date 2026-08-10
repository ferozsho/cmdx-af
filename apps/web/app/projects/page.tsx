'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function ProjectsPage() {
  const router = useRouter()

  useEffect(() => {
    router.replace('/')
  }, [router])

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <p className="text-sm text-muted animate-pulse">Redirecting to Dashboard…</p>
    </div>
  )
}
