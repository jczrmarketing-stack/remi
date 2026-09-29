import { defineConfig } from "vitest/config";

// Las pruebas viven al lado del módulo que prueban, con el sufijo
// .prueba.ts: se leen juntas y no hay una carpeta paralela que se
// desincronice.
export default defineConfig({
  test: {
    include: ["src/**/*.prueba.ts"],
  },
});
