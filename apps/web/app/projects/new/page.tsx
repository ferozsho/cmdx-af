import React from 'react'
import type { Metadata } from 'next'
import NewProjectClient from './new-project-client'

export const metadata: Metadata = {
  title: 'Create New Project',
  description:
    'Register a new software development project targeting a local workstation workspace or cloud environment.',
}

export default function NewProjectPage() {
  return <NewProjectClient />
}
