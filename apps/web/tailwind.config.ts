import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx}',
    '../../packages/ui/src/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Neura neo-brutalist colors
        'neo-bg': '#FFFAE5',
        'neo-main': '#FF4D00',
        'neo-accent': '#A3FF00',
        'neo-purple': '#9D00FF',
        'neo-black': '#0f0f0f',
        'neo-white': '#ffffff',
        'neo-blue': '#0047FF',
        // Semantic color mapping to neo palette (for non-landing pages)
        background: '#FFFAE5',           // neo-bg
        foreground: '#0f0f0f',           // neo-black
        card: '#ffffff',                 // neo-white
        'card-foreground': '#0f0f0f',    // neo-black
        popover: '#ffffff',              // neo-white
        'popover-foreground': '#0f0f0f', // neo-black
        primary: '#FF4D00',              // neo-main
        'primary-foreground': '#ffffff', // neo-white
        secondary: '#A3FF00',            // neo-accent
        'secondary-foreground': '#0f0f0f', // neo-black
        muted: '#E7E1CC',                // muted version of neo-bg
        'muted-foreground': '#4a4330',   // darker muted
        accent: '#9D00FF',               // neo-purple
        'accent-foreground': '#ffffff',  // neo-white
        destructive: '#FF4D00',          // neo-main for destructive
        'destructive-foreground': '#ffffff', // neo-white
        border: '#0f0f0f',               // neo-black
        input: '#0f0f0f',                // neo-black
        ring: '#0f0f0f',                 // neo-black
      },
      fontSize: {
        hero: 'clamp(2.5rem, 8vw + 1rem, 6rem)',
        h2: '2.25rem',
        h3: '1.25rem',
        caption: '0.875rem',
      },
      lineHeight: {
        hero: '1.02',
        relaxed: '1.6',
      },
      spacing: {
        4: '1rem',
        6: '1.5rem',
        8: '2rem',
        12: '3rem',
        16: '4rem',
        128: '32rem',
      },
      cursor: {
        none: 'none',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      transitionTimingFunction: {
        smooth: 'var(--ease)',
      },
      transitionDuration: {
        fast: 'var(--duration-fast)',
        normal: 'var(--duration-normal)',
        slow: 'var(--duration-slow)',
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        nav: 'var(--shadow-nav)',
        hover: 'var(--shadow-hover)',
        // Neo-brutalist shadows
        'neo': '8px 8px 0px 0px #0f0f0f',
        'neo-sm': '4px 4px 0px 0px #0f0f0f',
        'neo-lg': '12px 12px 0px 0px #0f0f0f',
        'neo-hover': '12px 12px 0px 0px #0f0f0f',
        'neo-active': '2px 2px 0px 0px #0f0f0f',
      },
      fontFamily: {
        // Prefer Inter variable font globally when available
        sans: ['var(--font-inter)', 'system-ui', '-apple-system', 'sans-serif'],
        // Neo-brutalist fonts
        'display': ['"Syne"', 'sans-serif'],
        'body': ['"Space Grotesk"', 'sans-serif'],
        'heavy': ['"Archivo Black"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

export default config
