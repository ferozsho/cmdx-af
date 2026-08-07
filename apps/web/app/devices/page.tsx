import React from 'react'
import type { Metadata } from 'next'
import DevicesClient from './devices-client'

export const metadata: Metadata = {
  title: 'Workstation Devices',
  description:
    'Manage connected developer workstations and generate temporary pairing codes for the AgentForge Local Daemon.',
}

export default function DevicesPage() {
  return <DevicesClient />
}
