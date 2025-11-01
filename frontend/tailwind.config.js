/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#FDF8F0',
          100: '#F9EFE0',
          200: '#F2E5D0',
          300: '#E6C896',
          400: '#D4A574',
          500: '#C89B5F',
          600: '#B5864D',
          700: '#9A7042',
          800: '#7D5B38',
          900: '#614629',
        },
        dark: {
          bg: '#1F2428',
          'bg-soft': '#353B41',
          'bg-mute': '#242A2E',
          navbar: '#1F2428',
          chat: '#1F2428',
          'chat-user': '#272D32',
          'chat-assistant': '#2A3035',
          'text-user': 'rgba(230, 240, 242, 0.95)',
        },
        light: {
          bg: '#FCF9F5',
          'bg-soft': '#F5EFE8',
          'bg-mute': '#F0E9E1',
          navbar: '#F8F4EE',
          chat: '#FFFAF5',
          'chat-user': '#FCF9F5',
          'chat-assistant': '#F5EFE8',
          white: '#FFFAF5',
        }
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          '"Helvetica Neue"',
          'Arial',
          '"Microsoft YaHei"',
          'sans-serif'
        ],
      }
    },
  },
  plugins: [],
}
