'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { listDevices, getProjectStats, listProjects, type DeviceResponse } from '@/lib/api'

interface NotificationItem {
  id: string
  icon: string
  message: string
  time: string
  link?: string
  seen?: boolean
}

const POLL_MS = 15000
const STORAGE_KEY = 'agentforge_seen_notifications'

function loadSeenIds(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return new Set(JSON.parse(raw))
  } catch { /* ignore */ }
  return new Set()
}

function saveSeenIds(ids: Set<string>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(ids)))
  } catch { /* ignore */ }
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [seenIds, setSeenIds] = useState<Set<string>>(loadSeenIds)
  const [devices, setDevices] = useState<DeviceResponse[]>([])
  const prevRunsRef = useRef(0)
  const prevTestsRef = useRef(0)
  const initializedRef = useRef(false)
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
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open])

  const hasUnseen = notifications.some((n) => !n.seen)

  // Poll device status + agent runs
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
        const now = new Date().toLocaleTimeString()

        // Device status (always show current state)
        if (onlineDevs.length === 0) {
          items.push({
            id: 'device-offline',
            icon: '🔴',
            message: 'No workstation connected. Start agentforge to run pipelines.',
            time: now,
            link: '/devices',
          })
        } else {
          items.push({
            id: 'device-online',
            icon: '🟢',
            message: `${onlineDevs.length} device${onlineDevs.length > 1 ? 's' : ''} connected`,
            time: now,
            link: '/devices',
          })
        }

        // Background pipeline activity — detect new runs since last poll
        if (initializedRef.current) {
          const newRuns = stats.agent_runs - prevRunsRef.current
          if (newRuns > 0) {
            items.push({
              id: `pipeline-completed-${Date.now()}`,
              icon: '🏁',
              message: `${newRuns} pipeline run${newRuns > 1 ? 's' : ''} completed`,
              time: now,
              link: '/observability',
            })
          }
          const newTests = stats.tests_passed - prevTestsRef.current
          if (newTests > 0) {
            items.push({
              id: `tests-${Date.now()}`,
              icon: '✅',
              message: `${newTests} test${newTests > 1 ? 's' : ''} passed across projects`,
              time: now,
            })
          }
        }

        prevRunsRef.current = stats.agent_runs
        prevTestsRef.current = stats.tests_passed
        initializedRef.current = true

        // Mark seen status based on previously seen IDs
        const marked = items.map((n) => ({
          ...n,
          seen: seenIds.has(n.id),
        }))
        setNotifications(marked)
        // Prune stale IDs from localStorage (keep only current notification IDs)
        const currentIds = new Set(items.map((n) => n.id))
        const pruned = new Set(Array.from(seenIds).filter((id) => currentIds.has(id)))
        if (pruned.size !== seenIds.size) {
          setSeenIds(pruned)
          saveSeenIds(pruned)
        }
      } catch {
        setNotifications([
          { id: 'api-offline', icon: '🔴', message: 'API is unreachable.', time: new Date().toLocaleTimeString() },
        ])
      }
    }
    tick()
    const timer = window.setInterval(tick, POLL_MS)
    return () => window.clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seenIds])

  const onlineCount = devices.filter((d) => d.status === 'online').length

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => {
          if (!open) {
            const ids = new Set(notifications.map((n) => n.id))
            setSeenIds(ids)
            saveSeenIds(ids)
            setNotifications((prev) => prev.map((n) => ({ ...n, seen: true })))
          }
          setOpen(!open)
        }}
        className={`btn-secondary-af !px-[11px] !py-[9px] text-sm relative ${
          hasUnseen ? '!border-amber-500/50 !bg-amber-500/10' : ''
        }`}
        aria-label={`Notifications${hasUnseen ? ' — new alerts' : ''}`}
      >
        🔔
        {hasUnseen && (
          <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-amber-500 rounded-full border-2 border-surface animate-pulse" />
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-surface border border-border rounded-[14px] shadow-2xl z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface-secondary/50">
            <h3 className="text-sm font-semibold text-foreground">Notifications</h3>
            <span className="text-[10px] text-muted">
              {onlineCount > 0 ? `🟢 ${onlineCount} online` : '🔴 offline'}
            </span>
          </div>

          <div className="max-h-[320px] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-muted">No notifications yet.</div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className={`flex items-start gap-3 px-4 py-3 border-b border-border last:border-0 hover:bg-surface-secondary/40 transition-colors ${
                    !n.seen ? 'bg-amber-500/5' : ''
                  }`}
                >
                  <span className="text-base flex-shrink-0 mt-0.5">{n.icon}</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] text-foreground leading-snug">{n.message}</p>
                    <p className="text-[10px] text-muted mt-0.5">{n.time}</p>
                  </div>
                  {!n.seen && (
                    <span className="w-2 h-2 rounded-full bg-amber-500 flex-shrink-0 mt-1.5" />
                  )}
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
