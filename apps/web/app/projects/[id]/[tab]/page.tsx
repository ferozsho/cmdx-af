import React, { Suspense } from 'react'
import type { Metadata } from 'next'
import WorkspaceClient from '../workspace-client'

const TABS = [
  'agents',
  'files',
  'rag',
  'git',
  'artifacts',
  'tests',
  'validation',
  'settings',
]

function cleanPath(str: string | null | undefined): string {
  if (!str) return ''
  let s = str
  try {
    if (s.includes('%')) s = decodeURIComponent(s)
    if (s.includes('%')) s = decodeURIComponent(s)
  } catch {
    // ignore
  }
  return s.replace(/[=%\s]+$/g, '').trim()
}

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: Promise<{ id: string; tab: string }>
  searchParams: Promise<Record<string, string | undefined>>
}): Promise<Metadata> {
  const resolvedParams = await params
  const rawSearchParams = await searchParams

  const tabRaw = cleanPath(resolvedParams.tab).toLowerCase()
  const tab = TABS.includes(tabRaw) ? tabRaw.toUpperCase() : 'AGENTS'
  const file = cleanPath(rawSearchParams.file)
  const q = cleanPath(rawSearchParams.q)

  const titleMap: Record<string, string> = {
    AGENTS: 'Live Agent Pipeline',
    FILES: file ? `File: ${file}` : 'Local Workspace Files',
    RAG: q ? `RAG Search: "${q}"` : 'Semantic RAG Search',
    GIT: 'Local Git Isolation Status',
  }

  const tabTitle = titleMap[tab] || 'Workspace'

  return {
    title: `Project (${tabTitle})`,
    description: `Manage project workspace, view multi-agent pipeline execution, explore live local files, run RAG semantic search, and monitor Git branch isolation.`,
  }
}

export default async function ProjectTabPage({
  params,
}: {
  params: Promise<{ id: string; tab: string }>
}) {
  const resolvedParams = await params
  const tabRaw = cleanPath(resolvedParams.tab).toLowerCase()
  const tab = TABS.includes(tabRaw) ? tabRaw : 'agents'
  return (
    <Suspense
      fallback={
        <div className="max-w-7xl mx-auto p-12 text-center text-muted font-mono animate-pulse">
          Loading AgentForge Workspace Control Plane...
        </div>
      }
    >
      <WorkspaceClient projectId={resolvedParams.id} initialTab={tab} />
    </Suspense>
  )
}
