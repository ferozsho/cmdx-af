'use client'

import React, { useState, useEffect } from 'react'
import DiffViewer from '@/components/diff-viewer'

export default function ProjectWorkspacePage({ params }: { params: { id: string } }) {
  const [activeTab, setActiveTab] = useState<'AGENTS' | 'FILES' | 'RAG' | 'GIT'>('AGENTS')
  const [prompt, setPrompt] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [events, setEvents] = useState<any[]>([])
  const [ragQuery, setRagQuery] = useState('')
  const [ragResults, setRagResults] = useState<any[]>([])

  const [agentsState, setAgentsState] = useState<any[]>([
    { name: 'Planning Agent', status: 'PENDING', duration: '-' },
    { name: 'Architecture Agent', status: 'PENDING', duration: '-' },
    { name: 'Visual Analysis Agent', status: 'PENDING', duration: '-' },
    { name: 'UI/UX Agent', status: 'PENDING', duration: '-' },
    { name: 'Documentation Agent', status: 'PENDING', duration: '-' },
    { name: 'Frontend Agent', status: 'PENDING', duration: '-' },
    { name: 'Backend Agent', status: 'PENDING', duration: '-' },
    { name: 'Database Agent', status: 'PENDING', duration: '-' },
    { name: 'Test Agent', status: 'PENDING', duration: '-' },
    { name: 'Validation Agent', status: 'PENDING', duration: '-' },
    { name: 'Git Agent', status: 'PENDING', duration: '-' },
  ])

  useEffect(() => {
    const eventSource = new EventSource(`http://localhost:8000/api/v1/projects/${params.id}/stream`)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        const time = new Date().toLocaleTimeString()

        setEvents((prev) => [
          ...prev,
          { time, text: `[${data.agent_name || 'System'}] ${data.message}` },
        ])

        if (data.agent_name) {
          setAgentsState((prev) =>
            prev.map((ag) => {
              if (ag.name === data.agent_name) {
                return {
                  ...ag,
                  status: data.status,
                  duration: data.status === 'COMPLETED' ? '1.0s' : ag.duration,
                }
              }
              return ag
            })
          )
        }

        if (data.agent_name === 'Git Agent' && data.status === 'COMPLETED') {
          setIsRunning(false)
        }
      } catch (err) {
        console.error('SSE Error:', err)
      }
    }

    return () => {
      eventSource.close()
    }
  }, [params.id])

  const handleStartPipeline = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim()) return
    setIsRunning(true)
    setEvents((prev) => [
      ...prev,
      { time: new Date().toLocaleTimeString(), text: `[Instruction Submitted] ${prompt}` },
    ])

    // Reset agent statuses to PENDING
    setAgentsState((prev) => prev.map((ag) => ({ ...ag, status: 'PENDING', duration: '-' })))

    try {
      await fetch(`http://localhost:8000/api/v1/projects/${params.id}/instructions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      })
    } catch (err) {
      console.error('Failed to trigger instruction pipeline:', err)
      setIsRunning(false)
    }
  }

  const handleRagSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setRagResults([
      {
        file_path: 'src/modules/payment/service.py',
        start_line: 12,
        end_line: 45,
        score: 0.94,
        content: 'class PaymentService:\n    def process_transaction(self, amount, currency):\n        pass',
      },
      {
        file_path: 'src/models/payment.py',
        start_line: 1,
        end_line: 25,
        score: 0.88,
        content: 'class PaymentModel(Base):\n    id = Column(String, primary_key=True)',
      },
    ])
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white">Commerce Platform</h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800">
              ● FEROZ-PC (Connected)
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Local Workspace: <code className="text-gray-200">D:\Projects\cmdx-framework</code>
          </p>
        </div>
        <div className="flex gap-2">
          {['AGENTS', 'FILES', 'RAG', 'GIT'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                activeTab === tab
                  ? 'bg-blue-600 text-white'
                  : 'bg-[#111827] text-gray-400 hover:text-white border border-gray-800'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Instruction Form */}
      <form onSubmit={handleStartPipeline} className="bg-[#111827] border border-gray-800 rounded-xl p-4 flex gap-3">
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. Create payment management module with FastAPI endpoints, React admin table, unit tests, and git commit..."
          className="flex-1 bg-[#0d121f] border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500"
        />
        <button
          type="submit"
          disabled={isRunning}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-bold px-5 py-2.5 rounded-lg transition-colors"
        >
          {isRunning ? 'Running Pipeline...' : 'Run Instruction'}
        </button>
      </form>

      {/* Main Tab Content */}
      {activeTab === 'AGENTS' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Agent Sequence List */}
          <div className="md:col-span-1 space-y-3">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Agent Sequence</h2>
            <div className="space-y-2">
              {agentsState.map((ag) => (
                <div
                  key={ag.name}
                  className="bg-[#111827] border border-gray-800 rounded-lg p-3 flex items-center justify-between text-xs"
                >
                  <span className="font-medium text-white">{ag.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-500">{ag.duration}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        ag.status === 'COMPLETED'
                          ? 'bg-emerald-950 text-emerald-400'
                          : ag.status === 'RUNNING'
                          ? 'bg-blue-950 text-blue-400 animate-pulse'
                          : 'bg-gray-800 text-gray-400'
                      }`}
                    >
                      {ag.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Live Event Console */}
          <div className="md:col-span-2 bg-[#111827] border border-gray-800 rounded-xl p-4 flex flex-col h-[500px]">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Live Event Console</h2>
            <div className="flex-1 bg-[#090d16] border border-gray-900 rounded-lg p-3 font-mono text-xs overflow-y-auto space-y-2">
              <div className="text-gray-500">[System] Connected to WSS stream for project prj_demo_001</div>
              {events.map((ev, i) => (
                <div key={i} className="text-emerald-400">
                  <span className="text-gray-500">[{ev.time}]</span> {ev.text}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'FILES' && (
        <div className="space-y-6">
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 text-xs text-gray-300 font-mono space-y-2">
            <div className="text-sm font-semibold text-white font-sans mb-3">Generated Workspace File Tree</div>
            <div>📁 app/</div>
            <div className="pl-4 text-emerald-400">📄 analytics/page.tsx (+ new)</div>
            <div>📁 src/</div>
            <div className="pl-4">📁 modules/</div>
            <div className="pl-8 text-emerald-400">📄 payment/service.py (+ new)</div>
            <div className="pl-8 text-emerald-400">📄 payment/schema.py (+ new)</div>
            <div className="pl-4">📄 main.py (modified)</div>
          </div>

          <DiffViewer
            filePath="src/modules/payment/service.py"
            originalCode="# Existing payment module placeholder"
            modifiedCode={`class PaymentService:
    def __init__(self, db_session):
        self.db = db_session

    async def process_payment(self, amount: float, currency: str) -> dict:
        # Agent generated payment processing implementation
        return {"status": "SUCCESS", "amount": amount, "currency": currency}`}
          />
        </div>
      )}

      {activeTab === 'RAG' && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-4">
          <h2 className="text-sm font-semibold text-white">Local RAG Semantic Search</h2>
          <form onSubmit={handleRagSearch} className="flex gap-2">
            <input
              type="text"
              value={ragQuery}
              onChange={(e) => setRagQuery(e.target.value)}
              placeholder="Search codebase semantically (e.g. payment processing logic)..."
              className="flex-1 bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-xs text-white"
            />
            <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-lg text-xs font-semibold">
              Search RAG
            </button>
          </form>

          {ragResults.length > 0 && (
            <div className="space-y-3 pt-2">
              {ragResults.map((res, i) => (
                <div key={i} className="bg-[#0d121f] border border-gray-800 rounded-lg p-3 text-xs space-y-1 font-mono">
                  <div className="flex justify-between text-blue-400 font-sans font-semibold">
                    <span>{res.file_path} (Lines {res.start_line}-{res.end_line})</span>
                    <span>Relevance: {(res.score * 100).toFixed(0)}%</span>
                  </div>
                  <pre className="text-gray-300 bg-[#090d16] p-2 rounded overflow-x-auto">{res.content}</pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'GIT' && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 text-xs space-y-3">
          <h2 className="text-sm font-semibold text-white">Local Git Isolation History</h2>
          <div className="border border-gray-800 rounded-lg divide-y divide-gray-800 bg-[#0d121f]">
            <div className="p-3 flex justify-between items-center">
              <div>
                <div className="font-bold text-white">[Release] Payment management module implementation</div>
                <div className="text-[10px] text-gray-500">Branch: agent/ins_a72841 · Hash: a1b2c3d4</div>
              </div>
              <button className="bg-red-950 text-red-400 border border-red-800 px-3 py-1 rounded text-[10px]">
                Rollback
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
