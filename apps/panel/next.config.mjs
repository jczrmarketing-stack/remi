import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// El panel sirve desde el teléfono: el browser pega a /nucleo (mismo
// origen), y acá Next lo reenvía al núcleo real, cabeceras incluidas (las
// Cf-* del túnel también llegan así). El host/puerto salen de
// config/nucleo.json, nunca a mano — mismo archivo que lee
// scripts/generar-config.mjs. URL_NUCLEO_REWRITE lo pisa para Playwright,
// que necesita apuntar al núcleo falso en vez del real.
const { host, puerto } = JSON.parse(
  readFileSync(resolve(__dirname, "../../config/nucleo.json"), "utf-8")
);
const DESTINO_NUCLEO = process.env.URL_NUCLEO_REWRITE || `http://${host}:${puerto}`;

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: __dirname,
  // Solo para Playwright: un build aparte (sin NEXT_PUBLIC_URL_NUCLEO, para
  // probar el camino de /nucleo de verdad) no puede compartir .next con el
  // build normal — chocarían si Playwright los arranca a la vez.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  async rewrites() {
    return [{ source: "/nucleo/:path*", destination: `${DESTINO_NUCLEO}/:path*` }];
  },
};

export default nextConfig;
