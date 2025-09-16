/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'deep-blue': '#1C2833',
        'slate-gray': '#2E4053',
        'silver': '#AAB7B8',
      },
    },
  },
  plugins: [],
};
