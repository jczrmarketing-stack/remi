#!/usr/bin/env node
// Imprime puerto_panel de config/nucleo.json, para que package.json arranque
// `next dev`/`next start` en ese puerto sin hardcodearlo dos veces.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const RUTA_CONFIG = resolve(__dirname, "../../../config/nucleo.json");
const { puerto_panel } = JSON.parse(readFileSync(RUTA_CONFIG, "utf-8"));
process.stdout.write(String(puerto_panel));
