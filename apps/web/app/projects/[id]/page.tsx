import React, { Suspense } from 'react'
import type { Metadata } from 'next'
import WorkspaceClient from './workspace-client'

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: { id: string }
  searchParams: { tab?: string; file?: string; q?: string }
}): Promise<Metadata> {
  const tab = (searchParams.tab || 'AGENTS').toUpperCase()
  const titleMap: Record<string, string> = {
    AGENTS: 'Live Agent Pipeline',
    FILES: searchParams.file ? `File: ${searchParams.file}` : 'Local Workspace Files',
    RAG: searchParams.q ? `RAG Search: "${searchParams.q}"` : 'Semantic RAG Search',
    GIT: 'Local Git Isolation Status',
  }

  const tabTitle = titleMap[tab] || 'Workspace'

  return {
    title: `Commerce Platform (${tabTitle})`,
    description: `Manage project ${params.id} workspace, view multi-agent pipeline execution, explore live local files, run RAG semantic search, and monitor Git branch isolation.`,
  }
}

export default function WorkspacePage({ params }: { params: { id: string } }) {
  return (
    <Suspense
      fallback={
        <div className="max-w-7xl mx-auto p-12 text-center text-gray-400 font-mono animate-pulse">
          Loading AgentForge Workspace Control Plane...
        </div>
      }
    >
      <WorkspaceClient projectId={params.id} />
    </Suspense>
  )
}
