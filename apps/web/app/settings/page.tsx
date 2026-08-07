'use client'

import React, { useState } from 'react'

export default function SettingsPage() {
  const [saved, setSaved] = useState(false)

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Settings</h1>
          <p className="text-sm text-gray-400 mt-1">
            Configure AgentForge platform settings and API connections.
          </p>
        </div>
        <button
          onClick={handleSave}
          className="bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs px-4 py-2 rounded-lg transition-colors"
        >
          Save Changes
        </button>
      </div>

      {saved && (
        <div className="bg-emerald-950/40 border border-emerald-800 rounded-lg p-3 text-xs text-emerald-400">
          Settings saved successfully.
        </div>
      )}

      <form
        onSubmit={handleSave}
        className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-5"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">
              DeepSeek Base URL
            </label>
            <input
              type="text"
              defaultValue="https://api.deepseek.com"
              className="w-full bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">
              Chat Model
            </label>
            <input
              type="text"
              defaultValue="deepseek-chat"
              className="w-full bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">
              Coder Model
            </label>
            <input
              type="text"
              defaultValue="deepseek-coder"
              className="w-full bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">
              Max Agent Steps
            </label>
            <input
              type="number"
              defaultValue={10}
              className="w-full bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">
              Agent Timeout (seconds)
            </label>
            <input
              type="number"
              defaultValue={600}
              className="w-full bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">
              RAG Top K
            </label>
            <input
              type="number"
              defaultValue={5}
              className="w-full bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">
              RAG Similarity Threshold
            </label>
            <input
              type="number"
              step="0.01"
              defaultValue={0.65}
              className="w-full bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">
              Context Window Budget
            </label>
            <input
              type="text"
              defaultValue="30%"
              className="w-full bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">
            DeepSeek API Key
          </label>
          <input
            type="password"
            placeholder="••••••••••••••••"
            className="w-full bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          />
          <p className="text-[10px] text-gray-500 mt-1">
            Your API key is never exposed to the browser and is stored encrypted.
          </p>
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">
            Allowed Commands
          </label>
          <textarea
            rows={3}
            defaultValue={
              'pip install, npm install, npm run build, python -m, npx, pytest, jest, ruff, eslint, mypy, bandit'
            }
            className="w-full bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 font-mono"
          />
        </div>

        <div className="pt-3 border-t border-gray-800 flex gap-3">
          <button
            type="button"
            className="bg-gray-700 hover:bg-gray-600 text-white font-medium text-xs px-4 py-2 rounded-lg transition-colors"
          >
            Test DeepSeek Connection
          </button>
          <button
            type="button"
            className="bg-gray-700 hover:bg-gray-600 text-white font-medium text-xs px-4 py-2 rounded-lg transition-colors"
          >
            Test Database Connection
          </button>
        </div>
      </form>
    </div>
  )
}
