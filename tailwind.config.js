/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/*.html"],
  theme: {
    extend: {
      colors: {
        purple: '#6962f7',
        purple1: '#7000ff',
        blue: '#2176FF',
        celestial: '#33A1FD',
        green1: '#1FD660',
        gray1: '#2C2C2D',
        bgcol: '#121212',
        bgcol1: '#F7FFF7',
        accent: '#2176FF',
      },

      fontFamily: {
        'mont': ['Montserrat', 'sans-serif'],
        'roboto': ['Roboto', 'sans-serif']
      },
    },
  },
  plugins: [],
}

