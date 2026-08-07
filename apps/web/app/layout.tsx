import './globals.css'
import React from 'react'

export const metadata = {
  title: 'AgentForge Control Plane',
  description: 'AI-Powered Multi-Agent Software Development Platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#090d16] text-gray-100 flex flex-col">
        <header className="border-b border-gray-800 bg-[#0d121f] px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 text-white font-bold rounded px-2.5 py-1 text-sm tracking-wider">
              AGENTFORGE
            </div>
            <span className="text-xs px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800">
              Cloud Control Plane
            </span>
          </div>
          <nav className="flex items-center gap-6 text-sm text-gray-300">
            <a href="/" className="hover:text-white transition-colors">Dashboard</a>
            <a href="/devices" className="hover:text-white transition-colors">Devices</a>
            <a href="/projects/new" className="hover:text-white transition-colors">New Project</a>
          </nav>
        </header>
        <main className="flex-1 p-6">{children}</main>
      </body>
    </html>
  )
}
