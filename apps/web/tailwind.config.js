module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}", // adjust if using pages/ or src/
    "./components/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        'neo-bg': '#FFFAE5',
        'neo-main': '#FF4D00',
        'neo-accent': '#A3FF00',
        'neo-purple': '#9D00FF',
        'neo-black': '#0f0f0f',
        'neo-white': '#ffffff',
        'neo-blue': '#0047FF'
      },
      fontFamily: {
        'display': ['Syne', 'sans-serif'],
        'body': ['Space Grotesk', 'sans-serif'],
        'heavy': ['Archivo Black', 'sans-serif'],
      },
      boxShadow: {
        'neo': '8px 8px 0px 0px #0f0f0f',
        'neo-sm': '4px 4px 0px 0px #0f0f0f',
        'neo-lg': '12px 12px 0px 0px #0f0f0f',
        'neo-hover': '12px 12px 0px 0px #0f0f0f',
        'neo-active': '2px 2px 0px 0px #0f0f0f',
      },
      spacing: { '128': '32rem' },
      cursor: { 'none': 'none' }
    }
  },
  plugins: [],
}
