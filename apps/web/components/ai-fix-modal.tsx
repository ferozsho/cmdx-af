'use client'

import { useEffect, useRef, useState } from 'react'

interface FixInfo {
  prompt: string
  errors: string[]
  recommendations: string[]
  agentNames: string[]
}

interface AiFixModalProps {
  open: boolean
  fixInfo: FixInfo | null
  onConfirm: () => void
  onCancel: () => void
  submitting: boolean
}

export default function AiFixModal({
  open,
  fixInfo,
  onConfirm,
  onCancel,
  submitting,
}: AiFixModalProps) {
  const confirmRef = useRef<HTMLButtonElement>(null)
  const [step, setStep] = useState<'review' | 'submitting'>('review')
  const [prevOpen, setPrevOpen] = useState(open)

  // Reset to the review step whenever the modal opens. Adjusting state during
  // render is the React-recommended pattern for resetting state on a prop
  // change (avoids react-hooks/set-state-in-effect).
  if (open !== prevOpen) {
    setPrevOpen(open)
    if (open) setStep('review')
  }

  // The submitting prop drives the submitting step directly.
  const effectiveStep = submitting ? 'submitting' : step

  useEffect(() => {
    if (open) {
      setTimeout(() => confirmRef.current?.focus(), 100)
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) onCancel()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onCancel, submitting])

  if (!open || !fixInfo) return null

  const { prompt, errors, recommendations, agentNames } = fixInfo

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-[2px]"
        onClick={() => !submitting && onCancel()}
      />

      {/* Modal */}
      <div
        role="dialog"
        aria-modal="true"
        className="relative z-10 w-full max-w-lg bg-white dark:bg-[#111827] rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700/50 overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-100 dark:border-gray-700/50 bg-gray-50/50 dark:bg-[#0a0f1a]">
          <div className="w-10 h-10 rounded-xl bg-primary/10 dark:bg-primary/20 grid place-items-center flex-shrink-0">
            <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <h2 className="text-sm font-bold text-gray-900 dark:text-white">
              AI Auto-Fix
            </h2>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">
              {effectiveStep === 'review'
                ? 'Review the issues and confirm to fix'
                : 'Fix submitted — agents are working…'}
            </p>
          </div>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4 max-h-[380px] overflow-y-auto bg-white dark:bg-[#111827]">
          {/* Step indicator */}
          <div className="flex items-center gap-2">
            <div className={`w-6 h-6 rounded-full grid place-items-center text-[10px] font-bold text-white transition-all duration-300 ${
              effectiveStep === 'review' ? 'bg-primary scale-110 shadow-lg shadow-primary/30' : 'bg-emerald-500'
            }`}>
              {effectiveStep === 'review' ? '1' : '✓'}
            </div>
            <div className="flex-1 h-1 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
              <div
                className={`h-full rounded-full bg-primary transition-all duration-700 ease-out ${
                  effectiveStep === 'submitting' ? 'w-full' : 'w-0'
                }`}
              />
            </div>
            <div className={`w-6 h-6 rounded-full grid place-items-center text-[10px] font-bold transition-all duration-300 ${
              effectiveStep === 'submitting'
                ? 'bg-primary text-white animate-pulse shadow-lg shadow-primary/30'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500'
            }`}>
              2
            </div>
          </div>

          {/* Original instruction */}
          <div>
            <div className="text-[10px] uppercase tracking-wider text-gray-400 dark:text-gray-500 font-semibold mb-1.5">
              Original Instruction
            </div>
            <div className="bg-gray-50 dark:bg-[#0a0f1a] border border-gray-200 dark:border-gray-700/50 rounded-lg px-3 py-2.5 text-xs text-gray-800 dark:text-gray-200 font-mono leading-relaxed">
              {prompt}
            </div>
          </div>

          {/* Errors */}
          {errors.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-red-500 dark:text-red-400 font-semibold mb-1.5 flex items-center gap-1.5">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                Errors Detected ({errors.length})
              </div>
              <div className="space-y-1">
                {errors.map((err, i) => (
                  <div key={i} className="bg-red-50 dark:bg-red-500/8 border border-red-200 dark:border-red-500/20 rounded-lg px-3 py-2 text-xs text-red-600 dark:text-red-400 font-mono">
                    {err}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wider text-amber-600 dark:text-amber-400 font-semibold mb-1.5">
                Recommendations
              </div>
              <ul className="space-y-1">
                {recommendations.map((rec, i) => (
                  <li key={i} className="flex gap-2 text-xs text-gray-600 dark:text-gray-400">
                    <span className="text-amber-500 dark:text-amber-400 flex-shrink-0">→</span>
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Agents that will run */}
          <div>
            <div className="text-[10px] uppercase tracking-wider text-gray-400 dark:text-gray-500 font-semibold mb-1.5">
              Agents That Will Fix
            </div>
            <div className="flex flex-wrap gap-1.5">
              {agentNames.length > 0 ? (
                agentNames.map((name) => (
                  <span
                    key={name}
                    className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-primary/10 text-primary border border-primary/20"
                  >
                    {name}
                  </span>
                ))
              ) : (
                <span className="text-xs text-gray-400 dark:text-gray-500">All enabled agents</span>
              )}
            </div>
          </div>

          {/* Submitting progress */}
          {step === 'submitting' && (
            <div className="bg-primary/5 dark:bg-primary/10 border border-primary/20 rounded-xl px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                <div>
                  <div className="text-xs font-semibold text-primary">
                    Agents are working…
                  </div>
                  <div className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">
                    Analyzing errors and applying fixes. Watch the Live Event Console for progress.
                  </div>
                </div>
              </div>
              <div className="mt-3 h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                <div className="h-full w-1/2 rounded-full bg-gradient-to-r from-primary to-primary/60 animate-progress-bar" />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2.5 px-5 py-3.5 border-t border-gray-100 dark:border-gray-700/50 bg-gray-50/50 dark:bg-[#0a0f1a]">
          {step === 'review' ? (
            <>
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 rounded-lg text-xs font-semibold text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                ref={confirmRef}
                type="button"
                onClick={onConfirm}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-lg text-xs font-bold text-white bg-primary hover:bg-primary/90 shadow-lg shadow-primary/25 hover:shadow-primary/40 transition-all active:scale-95"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Start AI Fix
              </button>
            </>
          ) : (
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              Closing modal…
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
