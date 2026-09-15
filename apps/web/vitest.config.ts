import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

/* The tests import route handlers, which use the "@/..." alias of tsconfig.json. */
export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL(".", import.meta.url)) },
  },
  test: {
    include: ["**/*.test.ts"],
    exclude: ["node_modules/**", ".next/**"],
  },
});
