import React, { Suspense } from 'react'
import type { Metadata } from 'next'
import WorkspaceClient from './workspace-client'

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
  params: Promise<{ id: string }>
  searchParams: Promise<Record<string, string | undefined>>
}): Promise<Metadata> {
  const resolvedParams = await params
  const rawSearchParams = await searchParams

  const tabRaw = cleanPath(rawSearchParams.tab)
  const tab = tabRaw ? tabRaw.toUpperCase() : 'AGENTS'
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

export default async function WorkspacePage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = await params
  return (
    <Suspense
      fallback={
        <div className="max-w-7xl mx-auto p-12 text-center text-muted font-mono animate-pulse">
          Loading AgentForge Workspace Control Plane...
        </div>
      }
    >
      <WorkspaceClient projectId={resolvedParams.id} />
    </Suspense>
  )
}
