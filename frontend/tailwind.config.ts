import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // MC Press Brand Colors (using CSS variables)
        'mc-blue': {
          DEFAULT: 'var(--mc-blue)',
          light: 'var(--mc-blue-light)',
          lighter: 'var(--mc-blue-lighter)',
          dark: 'var(--mc-blue-dark)',
          darker: 'var(--mc-blue-darker)',
        },
        'mc-green': {
          DEFAULT: 'var(--mc-green)',
          light: 'var(--mc-green-light)',
          lighter: 'var(--mc-green-lighter)',
          dark: 'var(--mc-green-dark)',
          darker: 'var(--mc-green-darker)',
        },
        'mc-orange': {
          DEFAULT: 'var(--mc-orange)',
          light: 'var(--mc-orange-light)',
          lighter: 'var(--mc-orange-lighter)',
          dark: 'var(--mc-orange-dark)',
          darker: 'var(--mc-orange-darker)',
        },
        'mc-red': {
          DEFAULT: 'var(--mc-red)',
          light: 'var(--mc-red-light)',
          lighter: 'var(--mc-red-lighter)',
          dark: 'var(--mc-red-dark)',
          darker: 'var(--mc-red-darker)',
        },
        'mc-gray': {
          DEFAULT: 'var(--mc-gray)',
          light: 'var(--mc-gray-light)',
          lighter: 'var(--mc-gray-lighter)',
          dark: 'var(--mc-gray-dark)',
          darker: 'var(--mc-gray-darker)',
        },

        // Semantic colors
        primary: 'var(--color-primary)',
        success: 'var(--color-success)',
        warning: 'var(--color-warning)',
        danger: 'var(--color-danger)',
        info: 'var(--color-info)',
        cta: 'var(--color-cta)',
      },
      fontFamily: {
        sans: 'var(--font-family-sans)',
        mono: 'var(--font-family-mono)',
      },
      fontSize: {
        xs: 'var(--font-size-xs)',
        sm: 'var(--font-size-sm)',
        base: 'var(--font-size-base)',
        lg: 'var(--font-size-lg)',
        xl: 'var(--font-size-xl)',
        '2xl': 'var(--font-size-2xl)',
        '3xl': 'var(--font-size-3xl)',
        '4xl': 'var(--font-size-4xl)',
        '5xl': 'var(--font-size-5xl)',
      },
      spacing: {
        '1': 'var(--space-1)',
        '2': 'var(--space-2)',
        '3': 'var(--space-3)',
        '4': 'var(--space-4)',
        '5': 'var(--space-5)',
        '6': 'var(--space-6)',
        '8': 'var(--space-8)',
        '10': 'var(--space-10)',
        '12': 'var(--space-12)',
        '16': 'var(--space-16)',
        '20': 'var(--space-20)',
        '24': 'var(--space-24)',
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        DEFAULT: 'var(--radius-md)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
        '2xl': 'var(--radius-2xl)',
        full: 'var(--radius-full)',
      },
      boxShadow: {
        xs: 'var(--shadow-xs)',
        sm: 'var(--shadow-sm)',
        DEFAULT: 'var(--shadow-md)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        xl: 'var(--shadow-xl)',
        '2xl': 'var(--shadow-2xl)',
        inner: 'var(--shadow-inner)',
        focus: 'var(--shadow-focus)',
      },
      transitionDuration: {
        fast: 'var(--transition-fast)',
        DEFAULT: 'var(--transition-base)',
        slow: 'var(--transition-slow)',
        slower: 'var(--transition-slower)',
      },
    },
  },
  plugins: [],
}
export default config