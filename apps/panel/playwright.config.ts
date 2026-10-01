import { defineConfig } from "@playwright/test";

const PUERTO_NUCLEO_FALSO = 4498;
const PUERTO_PANEL_PRUEBAS = 4403;

export default defineConfig({
  testDir: "./tests",
  timeout: 20_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  use: {
    baseURL: `http://localhost:${PUERTO_PANEL_PRUEBAS}`,
  },
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
  ],
});
