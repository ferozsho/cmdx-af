'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'

export type ThemeMode = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

interface ThemeContextType {
  theme: ThemeMode
  resolvedTheme: ResolvedTheme
  setTheme: (theme: ThemeMode) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>('system')
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>('light')
  const [mounted, setMounted] = useState(false)

  const applyTheme = (mode: ThemeMode) => {
    const isDarkSystem = window.matchMedia('(prefers-color-scheme: dark)').matches
    const activeResolved: ResolvedTheme =
      mode === 'dark' || (mode === 'system' && isDarkSystem) ? 'dark' : 'light'

    setResolvedTheme(activeResolved)

    const root = document.documentElement
    if (activeResolved === 'dark') {
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
    const saved = localStorage.getItem('agentforge-theme') as ThemeMode | null
    const initial = saved || 'system'
    setThemeState(initial)
    applyTheme(initial)

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      const currentStored = (localStorage.getItem('agentforge-theme') as ThemeMode) || 'system'
      if (currentStored === 'system') {
        applyTheme('system')
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
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
