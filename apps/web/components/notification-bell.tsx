'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { listDevices, getProjectStats, type DeviceResponse } from '@/lib/api'

interface NotificationItem {
  id: string
  icon: string
  message: string
  time: string
  link?: string
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [devices, setDevices] = useState<DeviceResponse[]>([])
  const [unread, setUnread] = useState(0)
  const ref = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open])

  // Poll device status + recent agent runs
  useEffect(() => {
    const tick = async () => {
      try {
        const [devs, stats] = await Promise.all([
          listDevices(),
          getProjectStats().catch(() => ({ agent_runs: 0, tests_passed: 0 })),
        ])
        setDevices(devs)
        const items: NotificationItem[] = []
        const onlineDevs = devs.filter((d) => d.status === 'online')
        if (onlineDevs.length === 0) {
          items.push({
            id: 'device-offline',
            icon: '🔴',
            message: 'No workstation connected. Start agentforge to run pipelines.',
            time: 'Now',
            link: '/devices',
          })
        } else {
          items.push({
            id: 'device-online',
            icon: '🟢',
            message: `${onlineDevs.length} device${onlineDevs.length > 1 ? 's' : ''} connected`,
            time: 'Now',
            link: '/devices',
          })
        }
        if (stats.agent_runs > 0) {
          items.push({
            id: 'agent-runs',
            icon: '🚀',
            message: `${stats.agent_runs} agent runs completed`,
            time: 'Recent',
            link: '/observability',
          })
        }
        if (stats.tests_passed > 0) {
          items.push({
            id: 'tests-passed',
            icon: '✅',
            message: `${stats.tests_passed} tests passed across all projects`,
            time: 'Recent',
          })
        }
        setNotifications(items)
      } catch {
        // offline — show disconnected
        setNotifications([
          {
            id: 'api-offline',
            icon: '🔴',
            message: 'API is unreachable. Check if the server is running.',
            time: 'Now',
          },
        ])
      }
    }
    tick()
    const timer = window.setInterval(tick, 30000)
    return () => window.clearInterval(timer)
  }, [])

  const onlineCount = devices.filter((d) => d.status === 'online').length
  const hasAlert = onlineCount === 0

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => {
          setOpen(!open)
          if (!open) setUnread(0)
        }}
        className={`btn-secondary-af !px-[11px] !py-[9px] text-sm relative ${
          hasAlert ? '!border-amber-500/50 !bg-amber-500/10' : ''
        }`}
        aria-label={`Notifications${hasAlert ? ' — device offline' : ''}`}
      >
        🔔
        {hasAlert && (
          <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-amber-500 rounded-full border-2 border-surface" />
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-surface border border-border rounded-[14px] shadow-2xl z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface-secondary/50">
            <h3 className="text-sm font-semibold text-foreground">Notifications</h3>
            <span className="text-[10px] text-muted">
              {onlineCount > 0 ? `🟢 ${onlineCount} online` : '🔴 offline'}
            </span>
          </div>

          {/* List */}
          <div className="max-h-[320px] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-muted">
                No notifications yet.
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className="flex items-start gap-3 px-4 py-3 border-b border-border last:border-0 hover:bg-surface-secondary/40 transition-colors"
                >
                  <span className="text-base flex-shrink-0 mt-0.5">{n.icon}</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] text-foreground leading-snug">{n.message}</p>
                    <p className="text-[10px] text-muted mt-0.5">{n.time}</p>
                  </div>
                  {n.link && (
                    <Link
                      href={n.link}
                      onClick={() => setOpen(false)}
                      className="text-[10px] text-primary hover:underline flex-shrink-0 mt-0.5"
                    >
                      View →
                    </Link>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-border px-4 py-2.5 bg-surface-secondary/30">
            <Link
              href="/observability"
              onClick={() => setOpen(false)}
              className="text-[11px] text-primary hover:underline block text-center"
            >
              Open Observability Dashboard →
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
