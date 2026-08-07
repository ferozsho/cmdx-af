import React from 'react'
import Link from 'next/link'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Project Dashboard',
  description:
    'Manage software development projects, view connected developer workstation status, and monitor live AI agent pipelines.',
}

export default function DashboardPage() {
  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Project Dashboard</h1>
          <p className="text-sm text-gray-400 mt-1">
            Manage development projects, view workstation status, and monitor live agent pipelines.
          </p>
        </div>
        <Link
          href="/projects/new"
          className="bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm px-4 py-2 rounded-lg transition-colors shadow-lg shadow-blue-900/20"
        >
          + Create New Project
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Total Projects</div>
          <div className="text-3xl font-bold text-white mt-2">4</div>
          <div className="text-xs text-emerald-400 mt-1">● 3 Local, 1 Cloud</div>
        </div>
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Connected Devices</div>
          <div className="text-3xl font-bold text-white mt-2">1</div>
          <div className="text-xs text-emerald-400 mt-1">● FEROZ-PC (Online)</div>
        </div>
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Agent Runs Today</div>
          <div className="text-3xl font-bold text-white mt-2">12</div>
          <div className="text-xs text-blue-400 mt-1">100% Success Rate</div>
        </div>
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Tests Passed</div>
          <div className="text-3xl font-bold text-white mt-2">128/128</div>
          <div className="text-xs text-emerald-400 mt-1">87.5% Avg Coverage</div>
        </div>
      </div>

      {/* Registered Projects */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Active Projects</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 hover:border-gray-700 transition-colors">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Commerce Platform</h3>
              <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800">
                LOCAL · FEROZ-PC
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Full-stack E-commerce analytics & payment platform running on local workspace.
            </p>
            <div className="mt-4 pt-4 border-t border-gray-800 flex items-center justify-between text-xs text-gray-400">
              <span>Path: <code className="text-gray-300">D:\Projects\cmdx-framework</code></span>
              <Link href="/projects/prj_demo_001?tab=agents" className="text-blue-400 font-medium hover:underline">
                Open Workspace →
              </Link>
            </div>
          </div>

          <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 hover:border-gray-700 transition-colors">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">XPLMS Core Service</h3>
              <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800">
                LOCAL · FEROZ-PC
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Learning management system backend microservices & AI auto-grader module.
            </p>
            <div className="mt-4 pt-4 border-t border-gray-800 flex items-center justify-between text-xs text-gray-400">
              <span>Path: <code className="text-gray-300">D:\Projects\xplms</code></span>
              <Link href="/projects/prj_demo_001?tab=agents" className="text-blue-400 font-medium hover:underline">
                Open Workspace →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
