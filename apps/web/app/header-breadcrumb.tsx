'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import React from 'react'

const SEGMENT_LABELS: Record<string, string> = {
  projects: 'Projects',
  new: 'New',
  agents: 'Agents',
  files: 'Files',
  rag: 'RAG',
  git: 'Git',
  artifacts: 'Artifacts',
  tests: 'Tests',
  validation: 'Validation',
  settings: 'Settings',
  users: 'Users',
  edit: 'Edit',
  devices: 'Devices',
  observability: 'Observability',
  architecture: 'Architecture',
  login: 'Sign In',
  register: 'Register',
  'forgot-password': 'Reset Password',
}

const STATIC_LABELS: Record<string, string> = {
  '/': 'Dashboard',
  '/projects/new': 'Create Project',
  '/projects': 'Live Workspace',
  '/devices': 'Devices',
  '/rag': 'RAG Manager',
  '/git': 'Git History',
  '/observability': 'Observability',
  '/architecture': 'Architecture',
  '/settings': 'Settings',
  '/agents': 'Agent Templates',
  '/users': 'Users',
  '/users/new': 'Create User',
  '/login': 'Sign In',
  '/forgot-password': 'Reset Password',
}

export function HeaderBreadcrumb() {
  const pathname = usePathname()

  // Static label takes priority for non-parameterized routes
  if (STATIC_LABELS[pathname]) {
    return (
      <div className="font-bold text-sm text-main">{STATIC_LABELS[pathname]}</div>
    )
  }

  // Build breadcrumb segments from path
  const segments = pathname.split('/').filter(Boolean)

  // For /projects/[id]/... or /users/[id]/...
  if (segments.length >= 2 && segments[0] === 'projects' && segments[1] !== 'new') {
    const items: { label: string; href?: string }[] = [
      { label: 'Live Workspace', href: '/projects' },
    ]
    // segments[1] is the project ID
    if (segments.length >= 3) {
      const tab = SEGMENT_LABELS[segments[2]] || segments[2]
      items.push({ label: tab })
    }
    return (
      <div className="flex items-center gap-1.5 text-sm text-main">
        {items.map((item, i) => (
          <React.Fragment key={i}>
            {i > 0 && <span className="text-muted font-normal">/</span>}
            {item.href ? (
              <Link href={item.href} className="font-semibold text-muted hover:text-foreground transition-colors">
                {item.label}
              </Link>
            ) : (
              <span className="font-bold text-foreground">{item.label}</span>
            )}
          </React.Fragment>
        ))}
      </div>
    )
  }

  // For /users/[id]/edit
  if (segments.length >= 3 && segments[0] === 'users' && segments[2] === 'edit') {
    return (
      <div className="flex items-center gap-1.5 text-sm text-main">
        <Link href="/users" className="font-semibold text-muted hover:text-foreground transition-colors">
          Users
        </Link>
        <span className="text-muted font-normal">/</span>
        <span className="font-bold text-foreground">Edit User</span>
      </div>
    )
  }

  // For /users/new
  if (segments.length >= 2 && segments[0] === 'users' && segments[1] === 'new') {
    return (
      <div className="flex items-center gap-1.5 text-sm text-main">
        <Link href="/users" className="font-semibold text-muted hover:text-foreground transition-colors">
          Users
        </Link>
        <span className="text-muted font-normal">/</span>
        <span className="font-bold text-foreground">Create User</span>
      </div>
    )
  }

  // For /projects/new
  if (pathname === '/projects/new') {
    return <div className="font-bold text-sm text-main">Create Project</div>
  }

  // Default: capitalize segments
  const label = segments
    .map((s) => SEGMENT_LABELS[s] || s.charAt(0).toUpperCase() + s.slice(1))
    .join(' / ')

  return <div className="font-bold text-sm text-main">{label || 'AgentForge'}</div>
}
