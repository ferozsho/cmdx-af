'use client'

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useSyncExternalStore,
} from 'react'

export type ThemeMode = 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'

interface ThemeContextType {
  theme: ThemeMode
  resolvedTheme: ResolvedTheme
  setTheme: (theme: ThemeMode) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

const THEME_STORAGE_KEY = 'agentforge-theme'
const SERVER_THEME: ThemeMode = 'light'

function getSystemPreference(): ThemeMode {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

// Module-scoped external store: persisting the theme re-renders the provider
// without calling setState inside an effect (avoids set-state-in-effect).
let currentTheme: ThemeMode = SERVER_THEME
const themeListeners = new Set<() => void>()

function readStoredTheme(): ThemeMode {
  if (typeof window === 'undefined') return SERVER_THEME
  const saved = localStorage.getItem(THEME_STORAGE_KEY)
  currentTheme =
    saved === 'light' || saved === 'dark' ? saved : getSystemPreference()
  return currentTheme
}

function subscribeTheme(callback: () => void): () => void {
  themeListeners.add(callback)
  window.addEventListener('storage', callback)
  return () => {
    themeListeners.delete(callback)
    window.removeEventListener('storage', callback)
  }
}

function persistTheme(mode: ThemeMode): void {
  currentTheme = mode
  localStorage.setItem(THEME_STORAGE_KEY, mode)
  themeListeners.forEach((listener) => listener())
}

function applyThemeToDom(mode: ThemeMode): void {
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

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useSyncExternalStore(
    subscribeTheme,
    readStoredTheme,
    () => SERVER_THEME,
  )

  // Apply the resolved theme to <html> and clean up any legacy 'system'
  // value. This mutates the DOM / storage only — no React setState.
  useEffect(() => {
    applyThemeToDom(theme)
    const saved = localStorage.getItem(THEME_STORAGE_KEY)
    if (saved && saved !== 'light' && saved !== 'dark') {
      localStorage.setItem(THEME_STORAGE_KEY, theme)
    }
  }, [theme])

  const setTheme = useCallback((newTheme: ThemeMode) => {
    persistTheme(newTheme)
    applyThemeToDom(newTheme)
  }, [])

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme: theme, setTheme }}>
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
