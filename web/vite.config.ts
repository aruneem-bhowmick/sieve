import { defineConfig } from "vite";
import { fileURLToPath, URL } from "node:url";

const replayBundlePath = fileURLToPath(new URL("./static/replay.json", import.meta.url));

export default defineConfig({
  root: "web",
  publicDir: "static",
  build: {
    outDir: "../public",
    emptyOutDir: true,
    rollupOptions: { output: { manualChunks: { "replay-data": [replayBundlePath] } } },
  },
});
