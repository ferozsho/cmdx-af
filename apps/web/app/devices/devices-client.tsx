'use client'

import React, { useEffect, useState } from 'react'
import {
  generatePairingCode,
  listDevices,
  type DeviceResponse,
} from '@/lib/api'

export default function DevicesClient() {
  const [pairingCode, setPairingCode] = useState<string | null>(null)
  const [devices, setDevices] = useState<DeviceResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pairingError, setPairingError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const data = await listDevices()
        setDevices(data)
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to load devices',
        )
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleGenerateCode = async () => {
    setPairingError(null)
    try {
      const data = await generatePairingCode()
      setPairingCode(data.pairing_code)
    } catch (err) {
      setPairingError(
        err instanceof Error ? err.message : 'Failed to generate pairing code',
      )
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-[26px] font-bold text-[#121827]">Workstation Devices</h1>
        <p className="text-sm text-[#687386] mt-1">
          Connect your local developer PC via AgentForge Local Execution Daemon.
        </p>
      </div>

      {/* Pairing Banner */}
      <div className="card-af p-6 flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-[#121827]">
            Connect New Workstation
          </h3>
          <p className="text-xs text-gray-400 mt-1">
            Install <code className="text-blue-300">agentforge</code> on your PC
            and pair using temporary code.
          </p>
        </div>
        <button
          onClick={handleGenerateCode}
          className="btn-primary-af text-xs"
        >
          Generate Pairing Code
        </button>
      </div>

      {pairingCode && (
        <div className="bg-blue-950/40 border border-blue-800 rounded-xl p-6 text-center space-y-2">
          <div className="text-xs text-blue-300 uppercase tracking-widest font-semibold">
            Your Pairing Code
          </div>
          <div className="text-4xl font-mono font-bold text-white tracking-widest">
            {pairingCode}
          </div>
          <p className="text-xs text-gray-400">
            Run{' '}
            <code className="text-gray-200">
              agentforge connect {pairingCode}
            </code>{' '}
            on your local workstation terminal. Code expires in 10 minutes.
          </p>
        </div>
      )}

      {pairingError && (
        <div className="text-xs text-[#d6263b] bg-[#fff0f0] border border-[#ffd0d4] rounded-[10px] p-3">
          {pairingError}
        </div>
      )}

      {/* Connected Devices Table */}
      <div className="card-af overflow-hidden">
        <div className="px-6 py-4 border-b border-[#e3e8f1] font-semibold text-sm text-[#121827]">
          Registered Workstations
        </div>

        {loading && (
          <div className="p-6 text-center">
            <div className="animate-pulse space-y-3">
              <div className="h-4 bg-[#e3e8f1] rounded w-3/4 mx-auto" />
              <div className="h-4 bg-[#e3e8f1] rounded w-1/2 mx-auto" />
            </div>
            <p className="text-xs text-[#687386] mt-3">Loading devices...</p>
          </div>
        )}

        {error && (
          <div className="p-6 text-center">
            <p className="text-xs text-[#d6263b]">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="text-xs text-[#6f35c8] hover:underline mt-2"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && devices.length === 0 && (
          <div className="p-10 text-center">
            <p className="text-sm text-[#687386]">
              No devices registered yet.
            </p>
            <p className="text-xs text-[#687386] mt-1 opacity-70">
              Generate a pairing code above to connect your first workstation.
            </p>
          </div>
        )}

        {!loading && !error && devices.length > 0 && (
          <table className="w-full text-left text-xs text-[#121827]">
          <thead className="bg-[#f9fafc] text-[#687386] uppercase tracking-wider text-[10px]">
              <tr>
                <th className="px-6 py-3">Device Name</th>
                <th className="px-6 py-3">Platform</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Agent Version</th>
                <th className="px-6 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#e3e8f1]">
              {devices.map((device) => (
                <tr key={device.id}>
                  <td className="px-6 py-4 font-medium text-white">
                    {device.name}
                  </td>
                  <td className="px-6 py-4">
                    {device.platform}
                    {device.os_version ? ` (${device.os_version})` : ''}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                        device.status === 'online'
                          ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                          : 'bg-gray-800 text-gray-400 border-gray-700'
                      }`}
                    >
                      ●{' '}
                      {device.status === 'online'
                        ? 'Online (WSS Connected)'
                        : 'Offline'}
                    </span>
                  </td>
                  <td className="px-6 py-4">{device.agent_version}</td>
                  <td className="px-6 py-4">
                    <button className="text-red-400 hover:underline text-[10px]">
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
