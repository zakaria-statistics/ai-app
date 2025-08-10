import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        strictPort: true,
        // Optional local dev proxy if your API is on localhost:8000
        proxy: {
            // "/ask": "http://localhost:8000",
            // "/ask_sse_post": "http://localhost:8000"
        }
    }
});
