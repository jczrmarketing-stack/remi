#!/usr/bin/env node
// Genera src/config.ts desde config/nucleo.json.
// No editar a mano: correr `npm run generar:config` de nuevo.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const RUTA_CONFIG = resolve(__dirname, "../../../config/nucleo.json");
const RUTA_SALIDA = resolve(__dirname, "../src/config.ts");

function generar() {
  const { host, puerto, puerto_panel } = JSON.parse(readFileSync(RUTA_CONFIG, "utf-8"));

  const lineas = [
    "/* Generado desde config/nucleo.json por scripts/generar-config.mjs. */",
    "/* No editar a mano: correr `npm run generar:config` de nuevo. */",
    "",
    `export const URL_NUCLEO = "http://${host}:${puerto}";`,
    `export const PUERTO_PANEL = ${puerto_panel};`,
    "",
  ];

  writeFileSync(RUTA_SALIDA, lineas.join("\n"));
  console.log(`Escrito ${RUTA_SALIDA}`);
}

generar();
