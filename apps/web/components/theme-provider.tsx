'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'

export type ThemeMode = 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'

interface ThemeContextType {
  theme: ThemeMode
  resolvedTheme: ResolvedTheme
  setTheme: (theme: ThemeMode) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

function getSystemPreference(): ThemeMode {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>('light')
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>('light')
  const [mounted, setMounted] = useState(false)

  const applyTheme = (mode: ThemeMode) => {
    setResolvedTheme(mode)
    const root = document.documentElement
    if (mode === 'dark') {
      root.classList.add('dark')
      root.classList.remove('light')
      root.setAttribute('data-theme', 'dark')
    } else {
      root.classList.add('light')
      root.classList.remove('dark')
      root.setAttribute('data-theme', 'light')
    }
  }

  useEffect(() => {
    setMounted(true)
    const saved = localStorage.getItem('agentforge-theme')
    const validSaved =
      saved === 'light' || saved === 'dark' ? saved : null
    const initial = validSaved || getSystemPreference()
    // Clean up legacy 'system' value from localStorage
    if (saved && !validSaved) {
      localStorage.setItem('agentforge-theme', initial)
    }
    setThemeState(initial)
    applyTheme(initial)
  }, [])

  const setTheme = (newTheme: ThemeMode) => {
    setThemeState(newTheme)
    localStorage.setItem('agentforge-theme', newTheme)
    applyTheme(newTheme)
  }

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
