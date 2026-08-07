/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Prototype design tokens (source: docs/index.html)
        bg: '#f6f8fc',
        panel: '#ffffff',
        text: '#121827',
        muted: '#687386',
        line: '#e3e8f1',
        nav: '#111a33',
        'nav-dark': '#0e1529',
        'nav-hover': '#202d4f',
        purple: {
          DEFAULT: '#6f35c8',
          light: '#8a5ade',
          bg: '#f3edff',
        },
        blue: {
          DEFAULT: '#1976d2',
        },
        teal: {
          DEFAULT: '#0e8b92',
        },
        green: {
          DEFAULT: '#238636',
          bg: '#e9f8ed',
        },
        orange: {
          DEFAULT: '#dd7a00',
        },
        red: {
          DEFAULT: '#d6263b',
          bg: '#fff0f0',
        },
        gold: {
          DEFAULT: '#a56a00',
        },
        // Additional app-specific
        'af-purple': {
          DEFAULT: '#6e37c9',
          hover: '#5c2eb2',
        },
      },
      borderRadius: {
        'af': '16px',
        'af-sm': '10px',
        'af-xs': '8px',
      },
      boxShadow: {
        'af': '0 10px 30px rgba(20,32,62,.08)',
        'af-hover': '0 14px 35px rgba(20,32,62,.12)',
      },
    },
  },
  plugins: [],
}
