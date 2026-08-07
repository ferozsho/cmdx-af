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
    <div>
      {/* Page Header — matches prototype .page-title */}
      <div className="flex items-start justify-between mb-[22px]">
        <div>
          <h2 className="text-[26px] font-bold text-main m-0 mb-[5px]">
            Workstation Devices
          </h2>
          <p className="text-sub text-sm m-0">
            Connect your local developer PC via AgentForge Local Execution Daemon.
          </p>
        </div>
      </div>

      <div className="space-y-[18px]">
        {/* Pairing Banner */}
        <div className="card-af p-6 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-main m-0">
              Connect New Workstation
            </h3>
            <p className="text-xs text-sub mt-1 m-0">
              Install <code className="text-[#6f35c8] font-mono font-bold">agentforge</code> on your PC
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
          <div className="card-af p-6 text-center space-y-2 border-[#7846cb]">
            <div className="text-xs text-[#6f35c8] uppercase tracking-widest font-bold">
              Your Pairing Code
            </div>
            <div className="text-4xl font-mono font-bold text-main tracking-widest">
              {pairingCode}
            </div>
            <p className="text-xs text-sub m-0">
              Run <code className="text-main font-bold font-mono">agentforge connect {pairingCode}</code> on your local workstation terminal. Code expires in 10 minutes.
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
          <div className="px-6 py-4 border-b border-[var(--line)] font-bold text-sm text-main">
            Registered Workstations
          </div>

          {loading && (
            <div className="p-6 text-center">
              <div className="animate-pulse space-y-3">
                <div className="h-4 bg-[var(--line)] rounded w-3/4 mx-auto" />
                <div className="h-4 bg-[var(--line)] rounded w-1/2 mx-auto" />
              </div>
              <p className="text-xs text-sub mt-3">Loading devices...</p>
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
              <p className="text-sm text-sub m-0">
                No devices registered yet.
              </p>
              <p className="text-xs text-sub mt-1 opacity-70 m-0">
                Generate a pairing code above to connect your first workstation.
              </p>
            </div>
          )}

          {!loading && !error && devices.length > 0 && (
            <table className="w-full text-left text-xs text-main">
              <thead className="bg-[var(--tag-bg)] text-sub uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="px-6 py-3">Device Name</th>
                  <th className="px-6 py-3">Platform</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Agent Version</th>
                  <th className="px-6 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)]">
                {devices.map((device) => (
                  <tr key={device.id}>
                    <td className="px-6 py-4 font-bold text-main">
                      {device.name}
                    </td>
                    <td className="px-6 py-4 text-sub">
                      {device.platform}
                      {device.os_version ? ` (${device.os_version})` : ''}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold ${
                          device.status === 'online'
                            ? 'bg-[#e9f8ed] text-[#1b7e33]'
                            : 'bg-[var(--tag-bg)] text-sub'
                        }`}
                      >
                        ● {device.status === 'online' ? 'Online (WSS Connected)' : 'Offline'}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-sub">{device.agent_version}</td>
                    <td className="px-6 py-4">
                      <button className="text-[#d6263b] hover:underline text-[10px] font-bold">
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
    </div>
  )
}
