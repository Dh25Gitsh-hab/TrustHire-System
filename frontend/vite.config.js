// vite.config.js — settings for Vite, the tool that runs and builds the React app.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  // react(): understands .jsx files. tailwindcss(): Tailwind CSS v4 (no config file needed).
  plugins: [react(), tailwindcss()],
  server: {
    // The backend only accepts browser requests from http://localhost:5173
    // (ALLOWED_ORIGINS in backend/.env). strictPort stops Vite from quietly
    // moving to port 5174, where every API request would be blocked (CORS).
    port: 5173,
    strictPort: true,
  },
})
