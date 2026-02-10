/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Ethereal Design System - Zinc Scale
        primary: {
          DEFAULT: '#3B82F6', // Blue 500 - Vivid yet professional
          dark: '#1D4ED8',    // Blue 700
          light: '#60A5FA',   // Blue 400
          foreground: '#FFFFFF',
        },
        dark: {
          bg: '#09090b',      // Zinc 950 - Matte Black
          panel: '#18181b',   // Zinc 900 - Card Surface
          surface: '#27272a', // Zinc 800 - Secondary Surface
          border: '#27272a',  // Zinc 800 - Subtle Border
          text: '#FAFAFA',    // Zinc 50 - Primary Text
          muted: '#A1A1AA',   // Zinc 400 - Secondary Text
          input: '#27272a',   // Zinc 800 - Input Bg
        },
        status: {
          success: '#10B981', // Emerald 500
          warning: '#F59E0B', // Amber 500
          error: '#EF4444',   // Red 500
          info: '#3B82F6',    // Blue 500
        }
      },
      fontFamily: {
        sans: ['"Inter"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
        glass: '12px',
        heavy: '24px',
      },
      boxShadow: {
        'premium-base': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'premium-glow': '0 0 20px rgba(99, 102, 241, 0.15)',
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'clean': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
      },
      backgroundImage: {
        'gradient-premium': 'linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%)',
        'glass-gradient': 'linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%)',
      }
    },
  },
  plugins: [],
}
