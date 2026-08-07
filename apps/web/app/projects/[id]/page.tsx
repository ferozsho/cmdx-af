import React, { Suspense } from 'react'
import type { Metadata } from 'next'
import WorkspaceClient from './workspace-client'

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>
  searchParams: Promise<Record<string, string | undefined>>
}): Promise<Metadata> {
  const resolvedParams = await params
  const rawSearchParams = await searchParams

  let tab = (rawSearchParams.tab || 'AGENTS').toUpperCase()
  let file = rawSearchParams.file
  let q = rawSearchParams.q

  // Handle case where query params were encoded into a single key by remote proxy
  if (!rawSearchParams.tab) {
    const rawKeys = Object.keys(rawSearchParams).join('&')
    const decoded = decodeURIComponent(rawKeys)
    const tabMatch = decoded.match(/tab=([^&]+)/i)
    if (tabMatch) tab = tabMatch[1].toUpperCase()
    const fileMatch = decoded.match(/file=([^&]+)/i)
    if (fileMatch) file = fileMatch[1]
    const qMatch = decoded.match(/q=([^&]+)/i)
    if (qMatch) q = qMatch[1]
  }

  const titleMap: Record<string, string> = {
    AGENTS: 'Live Agent Pipeline',
    FILES: file ? `File: ${file}` : 'Local Workspace Files',
    RAG: q ? `RAG Search: "${q}"` : 'Semantic RAG Search',
    GIT: 'Local Git Isolation Status',
  }

  const tabTitle = titleMap[tab] || 'Workspace'

  return {
    title: `Commerce Platform (${tabTitle})`,
    description: `Manage project ${resolvedParams.id} workspace, view multi-agent pipeline execution, explore live local files, run RAG semantic search, and monitor Git branch isolation.`,
  }
}

export default async function WorkspacePage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = await params
  return (
    <Suspense
      fallback={
        <div className="max-w-7xl mx-auto p-12 text-center text-gray-400 font-mono animate-pulse">
          Loading AgentForge Workspace Control Plane...
        </div>
      }
    >
      <WorkspaceClient projectId={resolvedParams.id} />
    </Suspense>
  )
}
