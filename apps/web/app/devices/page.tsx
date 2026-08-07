'use client'

import React, { useState } from 'react'

export default function DevicesPage() {
  const [pairingCode, setPairingCode] = useState<string | null>(null)

  const handleGenerateCode = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/devices/pairing-code', {
        method: 'POST',
      })
      const data = await res.json()
      setPairingCode(data.pairing_code)
    } catch {
      setPairingCode('AGF-84K2')
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Workstation Devices</h1>
        <p className="text-sm text-gray-400 mt-1">
          Connect your local developer PC via AgentForge Local Execution Daemon.
        </p>
      </div>

      {/* Pairing Banner */}
      <div className="bg-[#111827] border border-blue-900/50 rounded-xl p-6 flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-white">Connect New Workstation</h3>
          <p className="text-xs text-gray-400 mt-1">
            Install <code className="text-blue-300">agentforge</code> on your PC and pair using temporary code.
          </p>
        </div>
        <button
          onClick={handleGenerateCode}
          className="bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs px-4 py-2 rounded-lg transition-colors"
        >
          Generate Pairing Code
        </button>
      </div>

      {pairingCode && (
        <div className="bg-blue-950/40 border border-blue-800 rounded-xl p-6 text-center space-y-2">
          <div className="text-xs text-blue-300 uppercase tracking-widest font-semibold">Your Pairing Code</div>
          <div className="text-4xl font-mono font-bold text-white tracking-widest">{pairingCode}</div>
          <p className="text-xs text-gray-400">
            Run <code className="text-gray-200">agentforge connect {pairingCode}</code> on your local workstation terminal. Code expires in 10 minutes.
          </p>
        </div>
      )}

      {/* Connected Devices Table */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800 font-semibold text-sm text-white">
          Registered Workstations
        </div>
        <table className="w-full text-left text-xs text-gray-300">
          <thead className="bg-[#0d121f] text-gray-400 uppercase tracking-wider text-[10px]">
            <tr>
              <th className="px-6 py-3">Device Name</th>
              <th className="px-6 py-3">Platform</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3">Agent Version</th>
              <th className="px-6 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            <tr>
              <td className="px-6 py-4 font-medium text-white">FEROZ-PC</td>
              <td className="px-6 py-4">Windows 11 Pro (x64)</td>
              <td className="px-6 py-4">
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
                  ● Online (WSS Connected)
                </span>
              </td>
              <td className="px-6 py-4">v0.1.0</td>
              <td className="px-6 py-4">
                <button className="text-red-400 hover:underline">Revoke</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
