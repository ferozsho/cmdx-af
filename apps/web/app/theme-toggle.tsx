'use client'

import { useState, useEffect } from 'react'
import { useTheme } from '@/components/theme-provider'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light')
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

  const icon = theme === 'dark' ? '🌙' : '☀️'
  const label = theme === 'dark' ? 'Theme: Dark' : 'Theme: Light'

  return (
    <button
      onClick={toggleTheme}
      type="button"
      className="btn-secondary-af !px-[11px] !py-[9px] text-sm flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-primary/40"
      title={`${label} (Click to toggle)`}
      aria-label={label}
    >
      <span>{icon}</span>
      <span className="text-xs font-medium capitalize hidden sm:inline">
        {theme}
      </span>
    </button>
  )
}
