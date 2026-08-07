'use client'

import React, { useState } from 'react'

export default function NewProjectPage() {
  const [target, setTarget] = useState<'LOCAL' | 'CLOUD'>('LOCAL')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [localPath, setLocalPath] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await fetch('http://localhost:8000/api/v1/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          description,
          execution_target: target,
          local_path: localPath,
        }),
      })
      window.location.href = '/'
    } catch {
      window.location.href = '/'
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Create New Project</h1>
        <p className="text-sm text-gray-400 mt-1">
          Register a project targeting a local workstation workspace or cloud environment.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-5">
        <div>
          <label className="block text-xs font-semibold uppercase text-gray-400 mb-2">
            Execution Target
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setTarget('LOCAL')}
              className={`p-4 border rounded-xl text-left transition-colors ${
                target === 'LOCAL'
                  ? 'border-blue-500 bg-blue-950/30 text-white'
                  : 'border-gray-800 bg-[#0d121f] text-gray-400'
              }`}
            >
              <div className="font-bold text-sm">Local Machine</div>
              <div className="text-xs text-gray-400 mt-1">Runs on connected developer PC via WSS</div>
            </button>
            <button
              type="button"
              onClick={() => setTarget('CLOUD')}
              className={`p-4 border rounded-xl text-left transition-colors ${
                target === 'CLOUD'
                  ? 'border-blue-500 bg-blue-950/30 text-white'
                  : 'border-gray-800 bg-[#0d121f] text-gray-400'
              }`}
            >
              <div className="font-bold text-sm">Cloud Workspace</div>
              <div className="text-xs text-gray-400 mt-1">Runs in isolated cloud container</div>
            </button>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">
            Project Name
          </label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Commerce Platform"
            className="w-full bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">
            Description
          </label>
          <textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief project summary..."
            className="w-full bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>

        {target === 'LOCAL' && (
          <div>
            <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">
              Local Workspace Path
            </label>
            <input
              type="text"
              required
              value={localPath}
              onChange={(e) => setLocalPath(e.target.value)}
              placeholder="e.g. D:\Projects\cmdx-framework"
              className="w-full bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 font-mono text-xs"
            />
          </div>
        )}

        <div className="pt-2 flex justify-end gap-3">
          <a href="/" className="px-4 py-2 text-xs font-medium text-gray-400 hover:text-white">
            Cancel
          </a>
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs px-5 py-2.5 rounded-lg transition-colors"
          >
            Register Project
          </button>
        </div>
      </form>
    </div>
  )
}
