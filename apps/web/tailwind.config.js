/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--background)',
        surface: 'var(--surface)',
        'surface-secondary': 'var(--surface-secondary)',
        'surface-elevated': 'var(--surface-elevated)',

        foreground: 'var(--foreground)',
        'foreground-secondary': 'var(--foreground-secondary)',
        muted: 'var(--muted-foreground)',

        border: 'var(--border)',
        'border-strong': 'var(--border-strong)',

        input: 'var(--input-background)',
        hover: 'var(--hover)',

        primary: 'var(--primary)',
        'primary-hover': 'var(--primary-hover)',

        // Legacy compatibility design tokens
        bg: 'var(--background)',
        panel: 'var(--surface)',
        text: 'var(--foreground)',
        line: 'var(--border)',
        nav: '#111a33',
        'nav-dark': '#0e1529',
        'nav-hover': '#202d4f',
        purple: {
          DEFAULT: 'var(--primary)',
          light: '#8a5ade',
          bg: 'var(--surface-secondary)',
        },
        blue: {
          DEFAULT: '#1976d2',
        },
        teal: {
          DEFAULT: '#0e8b92',
        },
        green: {
          DEFAULT: '#238636',
          bg: 'rgba(35, 134, 54, 0.15)',
        },
        orange: {
          DEFAULT: '#dd7a00',
        },
        red: {
          DEFAULT: '#d6263b',
          bg: 'rgba(214, 38, 59, 0.15)',
        },
        gold: {
          DEFAULT: '#a56a00',
        },
        'af-purple': {
          DEFAULT: 'var(--primary)',
          hover: 'var(--primary-hover)',
        },
      },
      borderRadius: {
        'af': '16px',
        'af-sm': '10px',
        'af-xs': '8px',
      },
      boxShadow: {
        'af': '0 10px 30px var(--shadow-color)',
        'af-hover': '0 14px 35px var(--shadow-color)',
      },
    },
  },
  plugins: [],
}
