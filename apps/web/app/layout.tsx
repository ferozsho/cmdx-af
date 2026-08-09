import './globals.css'
import React from 'react'
import type { Metadata } from 'next'
import { ThemeProvider } from '@/components/theme-provider'
import AuthGuard from '@/components/auth-guard'
import AppShell from '@/components/app-shell'
import ErrorBoundary from '@/components/error-boundary'

export const metadata: Metadata = {
  title: {
    default: 'AgentForge | AI Multi-Agent Development Platform',
    template: '%s | AgentForge',
  },
  description:
    'Enterprise AI Agent Framework with Cloud Control Plane and Local Execution Daemon for autonomous software development.',
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
                  if (saved && saved !== 'light' && saved !== 'dark') {
                    localStorage.removeItem('agentforge-theme');
                    saved = null;
                  }
                  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                  var isDark = saved === 'dark' || (!saved && prefersDark);
                  if (isDark) {
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
          <ErrorBoundary>
            <AppShell>
              <AuthGuard>{children}</AuthGuard>
            </AppShell>
          </ErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  )
}
