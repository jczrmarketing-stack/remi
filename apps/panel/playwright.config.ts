import { defineConfig } from "@playwright/test";

const PUERTO_NUCLEO_FALSO = 4498;
const PUERTO_PANEL_PRUEBAS = 4403;
// Build aparte, servido en otro puerto, sin NEXT_PUBLIC_URL_NUCLEO: el
// cliente usa "/nucleo" (mismo origen) y next.config.mjs lo reenvía al
// núcleo falso vía URL_NUCLEO_REWRITE — así se prueba el camino real del
// teléfono (rewrite), no un atajo de test.
const PUERTO_PANEL_REWRITE = 4404;

export default defineConfig({
  testDir: "./tests",
  timeout: 20_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  projects: [
    {
      name: "directo",
      testIgnore: ["**/nucleo-rewrite.spec.ts"],
      use: { baseURL: `http://localhost:${PUERTO_PANEL_PRUEBAS}` },
    },
    {
      name: "rewrite",
      testMatch: ["**/nucleo-rewrite.spec.ts"],
      use: { baseURL: `http://localhost:${PUERTO_PANEL_REWRITE}` },
    },
  ],
  webServer: [
    {
      command: `node tests/nucleo-falso.mjs`,
      env: { PUERTO_NUCLEO_FALSO: String(PUERTO_NUCLEO_FALSO) },
      port: PUERTO_NUCLEO_FALSO,
      reuseExistingServer: false,
    },
    {
      // `next build` + `next start`, no `next dev`: con dev, los workers en
      // paralelo pegándole a rutas recién compiladas producían timeouts que
      // no eran del código sino del compilador on-demand.
      command: `npx next build && npx next start -p ${PUERTO_PANEL_PRUEBAS}`,
      env: { NEXT_PUBLIC_URL_NUCLEO: `http://localhost:${PUERTO_NUCLEO_FALSO}` },
      port: PUERTO_PANEL_PRUEBAS,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `npx next build && npx next start -p ${PUERTO_PANEL_REWRITE}`,
      env: {
        NEXT_DIST_DIR: ".next-rewrite",
        URL_NUCLEO_REWRITE: `http://localhost:${PUERTO_NUCLEO_FALSO}`,
      },
      port: PUERTO_PANEL_REWRITE,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
