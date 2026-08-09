'use client'

import { useEffect, useState } from 'react'
import { getFullHealth } from '@/lib/api'

export function SidebarHealth() {
  const [status, setStatus] = useState<string>('healthy')
  const [message, setMessage] = useState('All services healthy')
  const [services, setServices] = useState('FastAPI · PostgreSQL · Redis · Qdrant')

  useEffect(() => {
    getFullHealth()
      .then((data) => {
        const comps = data.components || {}
        const statuses: string[] = Object.values(comps).map((c: any) => c.status)
        const hasProblem = statuses.some(
          (s: string) => s === 'unhealthy' || s === 'degraded',
        )
        const healthyOrUnconfigured = statuses.every(
          (s: string) => s === 'healthy' || s === 'not_configured',
        )

        if (healthyOrUnconfigured) {
          setStatus('healthy')
          setMessage('All services healthy')
        } else if (hasProblem) {
          setStatus('degraded')
          setMessage('Some services degraded')
        } else {
          setStatus('degraded')
          setMessage('Some services unavailable')
        }
        setServices(
          Object.keys(comps)
            .map((k) => k.charAt(0).toUpperCase() + k.slice(1).replace('_', ' '))
            .join(' · '),
        )
      })
      .catch(() => {
        setStatus('unknown')
        setMessage('Unable to reach API')
      })
  }, [])

  const dotColor =
    status === 'healthy'
      ? 'bg-[#3ed46e] shadow-[0_0_0_4px_rgba(62,212,110,.12)]'
      : status === 'degraded'
        ? 'bg-amber-500 shadow-[0_0_0_4px_rgba(245,158,11,.12)]'
        : 'bg-red-500 shadow-[0_0_0_4px_rgba(239,68,68,.12)]'

  return (
    <div className="mt-auto mb-0 mx-0 p-3.5 border border-[#263555] rounded-[12px] bg-[#151f39]">
      <div className="flex items-center gap-[7px] text-xs font-semibold text-white">
        <span className={`inline-block w-2 h-2 rounded-full ${dotColor}`} />
        {message}
      </div>
      <div className="text-[11px] text-[#8490ac] mt-2">{services}</div>
    </div>
  )
}
