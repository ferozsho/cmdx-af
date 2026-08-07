'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { createProject, validateProjectPath, type ValidatePathResponse } from '@/lib/api'

const ALL_TECHS = [
  'Python', 'FastAPI', 'Django', 'Next.js', 'React', 'Node.js',
  'TypeScript', 'PHP', 'Moodle', 'PostgreSQL', 'MySQL', 'MongoDB',
  'Redis', 'Docker',
]

export default function NewProjectClient() {
  const [target, setTarget] = useState<'LOCAL' | 'CLOUD'>('LOCAL')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [localPath, setLocalPath] = useState('')
  const [techStack, setTechStack] = useState<string[]>([])
  const [initialInstruction, setInitialInstruction] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // Path validation state
  const [checking, setChecking] = useState(false)
  const [pathResult, setPathResult] = useState<ValidatePathResponse | null>(null)
  const [pathError, setPathError] = useState<string | null>(null)

  const handleCheckFolder = async () => {
    if (!localPath.trim()) return
    setChecking(true)
    setPathResult(null)
    setPathError(null)
    try {
      const result = await validateProjectPath(localPath.trim())
      setPathResult(result)
      // Auto-populate tech stack from detection
      if (result.detected_stack.length > 0) {
        setTechStack((prev) => {
          const merged = new Set([...prev, ...result.detected_stack])
          return Array.from(merged)
        })
      }
      // Auto-populate project name from folder
      if (result.project_name && !name) {
        setName(result.project_name)
      }
    } catch (err) {
      setPathError(
        err instanceof Error ? err.message : 'Failed to validate path',
      )
    } finally {
      setChecking(false)
    }
  }

  const toggleTech = (tech: string) => {
    setTechStack((prev) =>
      prev.includes(tech) ? prev.filter((t) => t !== tech) : [...prev, tech],
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setSubmitError(null)
    try {
      await createProject({
        name,
        description,
        execution_target: target,
        local_path: localPath,
        tech_stack: techStack,
      })
      window.location.href = '/'
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : 'Failed to create project.',
      )
      setSubmitting(false)
    }
  }

  return (
    <div>
      {/* Page Header — matches prototype .page-title */}
      <div className="flex items-start justify-between mb-[22px]">
        <div>
          <h2 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">
            Create New Project
          </h2>
          <p className="text-muted text-sm m-0">
            Connect a project directory and let the agent pipeline understand it.
          </p>
        </div>
      </div>

      <form
        onSubmit={handleSubmit}
        className="card-af max-w-[920px] p-6 space-y-5"
      >
        {/* Execution Target */}
        <div>
          <label className="block text-[13px] font-bold text-foreground mb-2">
            Execution Target
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setTarget('LOCAL')}
              className={`p-4 border rounded-xl text-left transition-colors ${
                target === 'LOCAL'
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'btn-secondary-af !font-normal'
              }`}
            >
              <div className="font-bold text-sm">Local Machine</div>
              <div className="text-xs opacity-80 mt-1">
                Runs on connected developer PC via WSS
              </div>
            </button>
            <button
              type="button"
              onClick={() => setTarget('CLOUD')}
              className={`p-4 border rounded-xl text-left transition-colors ${
                target === 'CLOUD'
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'btn-secondary-af !font-normal'
              }`}
            >
              <div className="font-bold text-sm">Cloud Workspace</div>
              <div className="text-xs opacity-80 mt-1">
                Runs in isolated cloud container
              </div>
            </button>
          </div>
        </div>

        {/* Project Name */}
        <div>
          <label className="block text-[13px] font-bold text-foreground mb-1">
            Project Name
          </label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Commerce Platform"
            className="input-af"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-[13px] font-bold text-foreground mb-1">
            Description
          </label>
          <textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief project summary..."
            className="input-af"
          />
        </div>

        {/* Local Path + Check Folder */}
        {target === 'LOCAL' && (
          <div>
            <label className="block text-[13px] font-bold text-foreground mb-1">
              Local Workspace Path
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                required
                value={localPath}
                onChange={(e) => {
                  setLocalPath(e.target.value)
                  setPathResult(null)
                  setPathError(null)
                }}
                placeholder="e.g. D:\Projects\cmdx-framework"
                className="input-af font-mono !text-xs flex-1"
              />
              <button
                type="button"
                onClick={handleCheckFolder}
                disabled={checking || !localPath.trim()}
                className="btn-secondary-af !py-2.5 text-xs whitespace-nowrap disabled:opacity-50"
              >
                {checking ? 'Checking...' : 'Check Folder'}
              </button>
            </div>

            {/* Path validation result */}
            {checking && (
              <div className="mt-2 text-xs text-muted animate-pulse">
                Validating project folder...
              </div>
            )}

            {pathResult && (
              <div
                className={`mt-3 rounded-[10px] p-4 text-xs space-y-1.5 ${
                  pathResult.valid
                    ? 'bg-emerald-500/10 border border-emerald-500/30'
                    : 'bg-red-500/10 border border-red-500/30'
                }`}
              >
                <div className="font-semibold text-sm mb-2 text-foreground">
                  {pathResult.valid ? '✓ Folder Valid' : '✕ Folder Issues'}
                </div>
                {pathResult.exists && (
                  <div className="text-emerald-600 dark:text-emerald-400 font-medium">✓ Directory exists</div>
                )}
                {!pathResult.exists && (
                  <div className="text-red-600 dark:text-red-400 font-medium">✕ Directory does not exist</div>
                )}
                {pathResult.readable && (
                  <div className="text-emerald-600 dark:text-emerald-400 font-medium">✓ Read permission</div>
                )}
                {!pathResult.readable && pathResult.exists && (
                  <div className="text-red-600 dark:text-red-400 font-medium">✕ Not readable</div>
                )}
                {pathResult.writable && (
                  <div className="text-emerald-600 dark:text-emerald-400 font-medium">✓ Write permission</div>
                )}
                {!pathResult.writable && pathResult.exists && (
                  <div className="text-amber-600 dark:text-amber-400 font-medium">⚠ Not writable</div>
                )}
                {pathResult.git_repository && (
                  <div className="text-emerald-600 dark:text-emerald-400 font-medium">✓ Git repository detected</div>
                )}
                {!pathResult.git_repository && pathResult.exists && (
                  <div className="text-amber-600 dark:text-amber-400 font-medium">
                    ⚠ No Git repository found
                  </div>
                )}
                {pathResult.files_count > 0 && (
                  <div className="text-foreground">
                    {pathResult.files_count} files, {pathResult.directories_count}{' '}
                    directories
                  </div>
                )}
                {pathResult.detected_stack.length > 0 && (
                  <div className="text-primary font-semibold">
                    Detected: {pathResult.detected_stack.join(', ')}
                  </div>
                )}
                {pathResult.warnings.map((w, i) => (
                  <div key={i} className="text-amber-600 dark:text-amber-400 font-medium">
                    ⚠ {w}
                  </div>
                ))}
              </div>
            )}

            {pathError && (
              <div className="mt-2 text-xs text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px] p-3">
                {pathError}
              </div>
            )}
          </div>
        )}

        {/* Technology Stack */}
        <div>
          <label className="block text-[13px] font-bold text-foreground mb-2">
            Technology Stack
          </label>
          <div className="flex flex-wrap gap-2">
            {ALL_TECHS.map((tech) => (
              <button
                key={tech}
                type="button"
                onClick={() => toggleTech(tech)}
                className={`text-xs px-2.5 py-2 rounded-[9px] border transition-colors ${
                  techStack.includes(tech)
                    ? 'border-primary bg-primary/10 text-primary font-bold'
                    : 'border-border bg-surface-secondary text-foreground-secondary hover:bg-hover'
                }`}
              >
                {tech}
              </button>
            ))}
          </div>
        </div>

        {/* Initial Instruction */}
        <div>
          <label className="block text-[13px] font-bold text-foreground mb-1">
            Initial Instruction (optional)
          </label>
          <textarea
            rows={3}
            value={initialInstruction}
            onChange={(e) => setInitialInstruction(e.target.value)}
            placeholder="e.g. Create a payments module with SQLAlchemy models, FastAPI endpoints, tests, and documentation."
            className="input-af resize-y"
          />
        </div>

        {/* Error */}
        {submitError && (
          <div className="text-xs text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px] p-3">
            {submitError}
          </div>
        )}

        {/* Actions */}
        <div className="pt-4 flex justify-end gap-2.5 border-t border-border">
          <Link
            href="/"
            className="btn-secondary-af text-xs flex items-center justify-center"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={submitting}
            className="btn-primary-af text-xs disabled:opacity-50"
          >
            {submitting ? 'Creating...' : 'Create & Index Project'}
          </button>
        </div>
      </form>
    </div>
  )
}
