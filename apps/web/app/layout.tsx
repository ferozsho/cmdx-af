import './globals.css'
import React from 'react'
import Link from 'next/link'
import type { Metadata } from 'next'
import { HeaderBreadcrumb } from './header-breadcrumb'

export const metadata: Metadata = {
  title: {
    default: 'AgentForge | AI Multi-Agent Development Platform',
    template: '%s | AgentForge',
  },
  description:
    'Enterprise AI Agent Framework with Cloud Control Plane and Local Execution Daemon for autonomous software development.',
}

function Sidebar() {
  return (
    <aside className="w-[250px] min-w-[250px] bg-gradient-to-b from-[#111a33] to-[#0e1529] text-[#d9e0f2] flex flex-col h-screen sticky top-0 overflow-auto py-6 px-4">
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
      <div className="text-[10px] uppercase tracking-[.16em] text-[#677493] my-[18px] mx-3">
        Workspace
      </div>
      <NavItem href="/" label="Dashboard" icon="▦" active />
      <NavItem href="/projects/new" label="New Project" icon="＋" />

      {/* Operations Section */}
      <div className="text-[10px] uppercase tracking-[.16em] text-[#677493] my-[18px] mx-3">
        Operations
      </div>
      <NavItem href="/rag" label="RAG Manager" icon="◫" />
      <NavItem href="/git" label="Git History" icon="⑂" />
      <NavItem href="/observability" label="Observability" icon="⌁" />
      <NavItem href="/architecture" label="Architecture" icon="⬡" />

      {/* System Section */}
      <div className="text-[10px] uppercase tracking-[.16em] text-[#677493] my-[18px] mx-3">
        System
      </div>
      <NavItem href="/settings" label="Settings" icon="⚙" />

      {/* Sidebar Footer */}
      <div className="mt-auto mb-0 mx-0 p-3.5 border border-[#263555] rounded-[12px] bg-[#151f39]">
        <div className="flex items-center gap-[7px] text-xs">
          <span className="inline-block w-2 h-2 rounded-full bg-[#3ed46e] shadow-[0_0_0_4px_rgba(62,212,110,.12)]" />
          <b>All services healthy</b>
        </div>
        <div className="text-[11px] text-[#8490ac] mt-2">
          FastAPI · PostgreSQL · Redis · Qdrant
        </div>
      </div>
    </aside>
  )
}

function NavItem({
  href,
  label,
  icon,
  active,
  badge,
}: {
  href: string
  label: string
  icon: string
  active?: boolean
  badge?: string
}) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-[10px] py-[11px] px-3 rounded-[10px] my-1 transition-colors ${
        active
          ? 'bg-[#202d4f] text-white'
          : 'text-[#b8c1d9] hover:bg-[#202d4f] hover:text-white'
      }`}
    >
      <span className="w-[22px] text-center">{icon}</span>
      <span className="text-[13px]">{label}</span>
      {badge && (
        <span className="ml-auto bg-[#3b4a6b] text-[#dfe6fa] rounded-[10px] px-[7px] py-[2px] text-[11px]">
          {badge}
        </span>
      )}
    </Link>
  )
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#f6f8fc] text-[#121827] flex font-sans antialiased">
        <Sidebar />

        <main className="flex-1 flex flex-col min-w-0">
          {/* Top Header Bar */}
          <header className="h-[74px] bg-white border-b border-[#e3e8f1] flex items-center justify-between px-7 sticky top-0 z-20">
            <div className="font-bold text-sm text-[#121827]">
              <HeaderBreadcrumb />
            </div>
            <div className="flex items-center gap-[10px]">
              <button className="border border-[#e3e8f1] bg-white rounded-[10px] px-[11px] py-[9px] text-sm hover:bg-gray-50 transition-colors">
                🔔
              </button>
              <div className="w-9 h-9 rounded-full bg-[#111a33] text-white grid place-items-center font-bold text-xs">
                AF
              </div>
            </div>
          </header>

          {/* Page Content */}
          <div className="p-7">{children}</div>
        </main>
      </body>
    </html>
  )
}
