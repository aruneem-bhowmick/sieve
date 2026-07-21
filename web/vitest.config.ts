import { defineConfig } from "vitest/config";

export default defineConfig({
  root: ".",
  test: { include: ["web/src/**/*.test.ts", "api/**/*.test.ts"] },
});
