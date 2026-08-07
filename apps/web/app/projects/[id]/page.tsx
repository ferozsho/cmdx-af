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

  let tab = 'AGENTS'
  let file = ''
  let q = ''

  const allParamsStr = Object.entries(rawSearchParams)
    .map(([k, v]) => (v ? `${k}=${v}` : k))
    .join('&')

  const decodedParamsStr = cleanPath(allParamsStr)

  const tabMatch = decodedParamsStr.match(/tab=([^&]*)/i)
  if (tabMatch) tab = cleanPath(tabMatch[1]).toUpperCase()

  const fileMatch = decodedParamsStr.match(/file=([^&]*)/i)
  if (fileMatch) file = cleanPath(fileMatch[1])

  const qMatch = decodedParamsStr.match(/q=([^&]*)/i)
  if (qMatch) q = cleanPath(qMatch[1])

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
