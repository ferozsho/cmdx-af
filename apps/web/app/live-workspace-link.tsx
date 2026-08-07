'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { listProjects, type ProjectResponse } from '@/lib/api'

export function LiveWorkspaceLink() {
  const [projectId, setProjectId] = useState<string | null>(null)

  useEffect(() => {
    listProjects()
      .then((data: ProjectResponse[]) => {
        if (data.length > 0) setProjectId(data[0].id)
      })
      .catch(() => {})
  }, [])

  return (
    <Link
      href={projectId ? `/projects/${projectId}?tab=agents` : '/projects/new'}
      className="flex items-center gap-[10px] py-[11px] px-3 rounded-[10px] my-1 transition-colors text-[#b8c1d9] hover:bg-[#202d4f] hover:text-white"
    >
      <span className="w-[22px] text-center">◉</span>
      <span className="text-[13px]">Live Workspace</span>
      {projectId && (
        <span className="ml-auto bg-[#3b4a6b] text-[#dfe6fa] rounded-[10px] px-[7px] py-[2px] text-[11px]">
          1
        </span>
      )}
    </Link>
  )
}
