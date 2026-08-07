import './globals.css'
import React from 'react'
import Link from 'next/link'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: {
    default: 'AgentForge Control Plane | AI Multi-Agent Development Platform',
    template: '%s | AgentForge',
  },
  description:
    'Enterprise AI Agent Framework with Cloud Control Plane and Local Execution Daemon for autonomous software development.',
  keywords: [
    'AI Coding Agent',
    'AgentForge',
    'Multi-Agent Framework',
    'DeepSeek',
    'FastAPI',
    'Next.js',
    'Software Automation',
    'Autonomous Development',
  ],
  authors: [{ name: 'AgentForge AI' }],
  creator: 'AgentForge Team',
  openGraph: {
    title: 'AgentForge Control Plane',
    description:
      'AI-Powered Multi-Agent Software Development Platform with local machine execution daemon.',
    type: 'website',
    siteName: 'AgentForge',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'AgentForge Control Plane',
    description: 'AI-Powered Multi-Agent Software Development Platform.',
  },
  robots: {
    index: true,
    follow: true,
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#090d16] text-gray-100 flex flex-col font-sans antialiased">
        <header className="border-b border-gray-800 bg-[#0d121f] px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="bg-blue-600 group-hover:bg-blue-500 text-white font-bold rounded px-2.5 py-1 text-sm tracking-wider transition-colors">
                AGENTFORGE
              </div>
            </Link>
            <span className="text-xs px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800">
              Cloud Control Plane
            </span>
          </div>
          <nav className="flex items-center gap-6 text-sm text-gray-300">
            <Link href="/" className="hover:text-white transition-colors">
              Dashboard
            </Link>
            <Link href="/devices" className="hover:text-white transition-colors">
              Devices
            </Link>
            <Link href="/projects/new" className="hover:text-white transition-colors">
              New Project
            </Link>
          </nav>
        </header>
        <main className="flex-1 p-6">{children}</main>
      </body>
    </html>
  )
}
