import './globals.css'
import React from 'react'
import type { Metadata } from 'next'
import { HeaderBreadcrumb } from './header-breadcrumb'
import { ThemeToggle } from './theme-toggle'
import { LiveWorkspaceLink } from './live-workspace-link'
import { NavItem } from './nav-item'
import { ThemeProvider } from '@/components/theme-provider'

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
      <NavItem href="/rag" label="RAG Manager" icon="◫" />
      <NavItem href="/git" label="Git History" icon="⑂" />
      <NavItem href="/observability" label="Observability" icon="⌁" />
      <NavItem href="/architecture" label="Architecture" icon="⬡" />

      {/* System Section */}
      <div className="text-[10px] uppercase tracking-[.16em] text-[#677493] my-[18px] mx-3 font-semibold">
        System
      </div>
      <NavItem href="/settings" label="Settings" icon="⚙" />

      {/* Sidebar Footer */}
      <div className="mt-auto mb-0 mx-0 p-3.5 border border-[#263555] rounded-[12px] bg-[#151f39]">
        <div className="flex items-center gap-[7px] text-xs font-semibold text-white">
          <span className="inline-block w-2 h-2 rounded-full bg-[#3ed46e] shadow-[0_0_0_4px_rgba(62,212,110,.12)]" />
          All services healthy
        </div>
        <div className="text-[11px] text-[#8490ac] mt-2">
          FastAPI · PostgreSQL · Redis · Qdrant
        </div>
      </div>
    </aside>
  )
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var saved = localStorage.getItem('agentforge-theme');
                  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                  if (saved === 'dark' || (!saved || saved === 'system') && prefersDark) {
                    document.documentElement.classList.add('dark');
                    document.documentElement.classList.remove('light');
                    document.documentElement.setAttribute('data-theme', 'dark');
                  } else {
                    document.documentElement.classList.add('light');
                    document.documentElement.classList.remove('dark');
                    document.documentElement.setAttribute('data-theme', 'light');
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="min-h-screen bg-background text-foreground flex font-sans antialiased">
        <ThemeProvider>
          <Sidebar />

          <main className="flex-1 flex flex-col min-w-0">
            {/* Top Header Bar */}
            <header className="h-[74px] bg-surface border-b border-border text-foreground flex items-center justify-between px-7 sticky top-0 z-20 transition-colors">
              <HeaderBreadcrumb />
              <div className="flex items-center gap-[10px]">
                <ThemeToggle />
                <button
                  type="button"
                  className="btn-secondary-af !px-[11px] !py-[9px] text-sm"
                  aria-label="Notifications"
                >
                  🔔
                </button>
                <div className="w-9 h-9 rounded-full bg-[#6e37c9] text-white grid place-items-center font-bold text-xs shadow-sm">
                  AF
                </div>
              </div>
            </header>

            {/* Page Content */}
            <div className="p-7">{children}</div>
          </main>
        </ThemeProvider>
      </body>
    </html>
  )
}
