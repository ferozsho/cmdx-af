'use client'

import { usePathname } from 'next/navigation'

const LABELS: Record<string, string> = {
  '/': 'Dashboard',
  '/projects/new': 'Create Project',
  '/devices': 'Workstation Devices',
  '/rag': 'RAG Manager',
  '/git': 'Git History',
  '/observability': 'Observability',
  '/architecture': 'System Architecture',
  '/settings': 'Settings',
}

export function HeaderBreadcrumb() {
  const pathname = usePathname()

  // Match exact paths first, then project paths
  const label =
    LABELS[pathname] ||
    (pathname.startsWith('/projects/') && pathname !== '/projects/new'
      ? 'Live Workspace'
      : 'AgentForge')

  return (
    <div className="font-bold text-sm text-[#121827]">{label}</div>
  )
}
