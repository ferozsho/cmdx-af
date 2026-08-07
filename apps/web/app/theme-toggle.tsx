'use client'

import { useState, useEffect } from 'react'
import { useTheme } from '@/components/theme-provider'

export function ThemeToggle() {
  const { theme, resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const cycleTheme = () => {
    if (theme === 'light') setTheme('dark')
    else if (theme === 'dark') setTheme('system')
    else setTheme('light')
  }

  if (!mounted) {
    return (
      <button
        type="button"
        className="btn-secondary-af !px-[11px] !py-[9px] text-sm flex items-center gap-1.5 opacity-80"
        aria-label="Toggle theme"
      >
        <span>☀️</span>
      </button>
    )
  }

  const getIcon = () => {
    if (theme === 'system') return '💻'
    return resolvedTheme === 'dark' ? '🌙' : '☀️'
  }

  const getLabel = () => {
    if (theme === 'system') return 'Theme: System'
    return theme === 'dark' ? 'Theme: Dark' : 'Theme: Light'
  }

  return (
    <button
      onClick={cycleTheme}
      type="button"
      className="btn-secondary-af !px-[11px] !py-[9px] text-sm flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-primary/40"
      title={`${getLabel()} (Click to change)`}
      aria-label={getLabel()}
    >
      <span>{getIcon()}</span>
      <span className="text-xs font-medium capitalize hidden sm:inline">{theme}</span>
    </button>
  )
}
