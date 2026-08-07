'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  listProjects,
  listDevices,
  type ProjectResponse,
  type DeviceResponse,
} from '@/lib/api'

export default function DashboardPage() {
  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [devices, setDevices] = useState<DeviceResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const [projData, devData] = await Promise.all([
          listProjects(),
          listDevices(),
        ])
        setProjects(projData)
        setDevices(devData)
      } catch (err) {
        console.error('Failed to load dashboard data:', err)
        setError('Could not load dashboard data. Is the API running?')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const onlineDevices = devices.filter((d) => d.status === 'online').length

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-64" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="card-af p-5 h-28" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card-af p-6 text-center border-red-200">
        <p className="text-red-600 font-medium text-sm">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-3 text-sm text-red-500 hover:text-red-400 underline"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div>
      {/* Page Header — matches prototype .page-title */}
      <div className="flex items-start justify-between mb-[22px]">
        <div>
          <h2 className="text-[26px] font-bold text-[#121827] m-0 mb-[5px]">
            Projects
          </h2>
          <p className="text-[#687386] text-sm m-0">
            Monitor agentic coding projects and recent pipeline activity.
          </p>
        </div>
        <Link
          href="/projects/new"
          className="inline-block border-0 rounded-[10px] py-[10px] px-[15px] font-bold text-sm bg-[#6e37c9] text-white hover:bg-[#5c2eb2] transition-colors"
        >
          ＋ Create Project
        </Link>
      </div>

      {/* KPI Cards — matches prototype .stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-[18px] mb-[22px]">
        <StatCard
          label="Total Projects"
          value={projects.length}
          trend={`${projects.filter((p) => p.execution_target === 'LOCAL').length} Local${projects.filter((p) => p.execution_target === 'CLOUD').length > 0 ? `, ${projects.filter((p) => p.execution_target === 'CLOUD').length} Cloud` : ''}`}
          icon="▦"
        />
        <StatCard
          label="Connected Devices"
          value={devices.length}
          trend={`${onlineDevices} Online`}
          icon="◉"
        />
        <StatCard
          label="Agent Runs"
          value="—"
          trend="Observability coming soon"
          icon="◉"
        />
        <StatCard
          label="Tests Passed"
          value="—"
          trend="Observability coming soon"
          icon="✓"
        />
      </div>

      {/* Projects Grid — matches prototype .projects-grid (3 columns) */}
      {projects.length === 0 ? (
        <div className="card-af p-10 text-center">
          <p className="text-[#687386] text-sm">No projects yet.</p>
          <Link
            href="/projects/new"
            className="text-[#6f35c8] text-sm font-medium hover:underline mt-2 inline-block"
          >
            Create your first project →
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-[18px]">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${encodeURIComponent(project.id)}?tab=agents`}
              className="card-af p-5 transition-all duration-200 hover:-translate-y-0.5 block"
              style={{ transition: '.2s' }}
            >
              <div className="flex items-start justify-between mb-0">
                <div className="w-11 h-11 rounded-[12px] bg-[#eee7fb] text-[#6734bd] grid place-items-center text-[21px] flex-shrink-0">
                  ⚡
                </div>
                <span className="inline-flex items-center gap-[6px] rounded-full py-[5px] px-[10px] text-xs font-bold bg-[#eee8ff] text-[#6c36bf]">
                  ● {project.execution_target}
                </span>
              </div>
              <h3 className="font-bold text-[#121827] text-[15px] mt-3 mb-0">
                {project.name}
              </h3>
              <p className="text-[#687386] text-[13px] mt-0.5 min-h-[40px] line-clamp-2">
                {project.description || 'No description provided.'}
              </p>
              {project.tech_stack && Object.keys(project.tech_stack).length > 0 && (
                <div className="flex flex-wrap gap-[6px] my-[14px]">
                  {Object.keys(project.tech_stack).map((tech) => (
                    <span
                      key={tech}
                      className="text-[11px] py-[5px] px-2 border border-[#e3e8f1] rounded-[7px] bg-[#f9fafc] text-[#526077]"
                    >
                      {tech}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex justify-between pt-[14px] border-t border-[#e3e8f1] text-xs text-[#687386]">
                <span>
                  {project.created_at
                    ? new Date(project.created_at).toLocaleDateString()
                    : '—'}
                </span>
                <span className="text-[#1976d2] font-medium">
                  Open Workspace →
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

function StatCard({
  label,
  value,
  trend,
  icon,
}: {
  label: string
  value: string | number
  trend: string
  icon: string
}) {
  return (
    <div className="card-af p-5">
      <div className="flex justify-between text-[#687386] text-[13px]">
        <span>{label}</span>
        <span>{icon}</span>
      </div>
      <div className="text-[30px] font-extrabold text-[#121827] my-[7px]">
        {value}
      </div>
      <div className="text-xs text-[#238636]">{trend}</div>
    </div>
  )
}
