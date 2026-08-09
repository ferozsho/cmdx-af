'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { getToken } from '@/lib/api'
import { HeaderBreadcrumb } from '@/app/header-breadcrumb'
import { ThemeToggle } from '@/app/theme-toggle'
import { LiveWorkspaceLink } from '@/app/live-workspace-link'
import { SidebarHealth } from '@/app/sidebar-health'
import { NavItem } from '@/app/nav-item'
import LogoutButton from '@/components/logout-button'
import NotificationBell from '@/components/notification-bell'
import ProviderBadge from '@/components/provider-badge'

const PUBLIC_PATHS = ['/login', '/forgot-password']

function Sidebar() {
  return (
    <aside className="w-[250px] min-w-[250px] bg-gradient-to-b from-[#111a33] to-[#0e1529] text-[#d9e0f2] flex flex-col h-screen sticky top-0 overflow-auto py-6 px-4 flex-shrink-0">
      {/* Brand */}
      <div className="flex items-center gap-3 px-2 pb-[22px]">
        <div className="w-[42px] h-[42px] rounded-[12px] bg-gradient-to-br from-[#7e42d1] to-[#2c83e6] grid place-items-center text-[23px] shadow-[0_8px_18px_rgba(111,53,200,.35)] flex-shrink-0">
          ⚡
        </div>
        <div>
          <h1 className="text-[17px] font-bold text-white leading-none m-0">
            AgentForge
          </h1>
          <small className="text-[#8995b4] text-[11px] block mt-[3px]">
            AI Agent Framework
          </small>
        </div>
      </div>

      {/* Workspace Section */}
      <div className="text-[10px] uppercase tracking-[.16em] text-[#677493] my-[18px] mx-3 font-semibold">
        Workspace
      </div>
      <NavItem href="/" label="Dashboard" icon="▦" />
      <NavItem href="/projects/new" label="New Project" icon="＋" />
      <LiveWorkspaceLink />

      {/* Operations Section */}
      <div className="text-[10px] uppercase tracking-[.16em] text-[#677493] my-[18px] mx-3 font-semibold">
        Operations
      </div>
      <NavItem href="/agents" label="Agent Templates" icon="⚙" />
      <NavItem href="/rag" label="RAG Manager" icon="◫" />
      <NavItem href="/git" label="Git History" icon="⑂" />
      <NavItem href="/observability" label="Observability" icon="⌁" />
      <NavItem href="/ai-logs" label="AI Logs" icon="🤖" />
      <NavItem href="/architecture" label="Architecture" icon="⬡" />

      {/* System Section */}
      <div className="text-[10px] uppercase tracking-[.16em] text-[#677493] my-[18px] mx-3 font-semibold">
        System
      </div>
      <NavItem href="/devices" label="Devices" icon="🖥" />
      <NavItem href="/users" label="Users" icon="👥" />
      <NavItem href="/settings" label="Settings" icon="⚙" />

      {/* Sidebar Footer — live health */}
      <SidebarHealth />
    </aside>
  )
}

/**
 * AppShell gates the sidebar and header behind authentication.
 * On public pages (/login, /forgot-password), only the children are rendered.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [hasToken, setHasToken] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setHasToken(!!getToken())
    setMounted(true)
  }, [pathname])

  // During SSR / before hydration, render nothing inside the shell to avoid
  // flash of the sidebar on public pages.
  if (!mounted) {
    return (
      <main className="flex-1 min-w-0 grid place-items-center p-7">
        <div className="text-muted text-xs font-mono animate-pulse">
          Loading…
        </div>
      </main>
    )
  }

  const isPublic = PUBLIC_PATHS.some(
    (p) => pathname === p || pathname?.startsWith(`${p}?`),
  )

  // Public pages: render just the children (login card, no sidebar/header)
  if (isPublic || !hasToken) {
    return <>{children}</>
  }

  // Authenticated pages: full shell with sidebar + header
  return (
    <>
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0">
        {/* Top Header Bar */}
        <header className="h-[74px] bg-surface border-b border-border text-foreground flex items-center justify-between px-7 sticky top-0 z-20 transition-colors">
          <HeaderBreadcrumb />
          <div className="flex items-center gap-3">
            <ProviderBadge />
            <ThemeToggle />
            <NotificationBell />
            <LogoutButton />
            <div className="w-9 h-9 rounded-full bg-[#6e37c9] text-white grid place-items-center font-bold text-xs shadow-sm">
              AF
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-7 flex-1 flex flex-col min-h-0">
          {children}
        </div>
      </main>
    </>
  )
}
