#!/usr/bin/env node
// Genera src/tokens.css desde design/tokens.json: tema Noche en :root y
// tema Día (el «Claro» de la ventanita, 3d · 11) en :root[data-tema="claro"].
// No editar a mano: correr `npm run generar:tokens` de nuevo.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const RUTA_TOKENS = resolve(__dirname, "../../../design/tokens.json");
const RUTA_SALIDA = resolve(__dirname, "../src/tokens.css");
const TEMA = "noche";

function generar() {
  const tokens = JSON.parse(readFileSync(RUTA_TOKENS, "utf-8"));
  const lineas = [
    "/* Generado desde design/tokens.json por scripts/generar-tokens.mjs. */",
    "/* No editar a mano: correr `npm run generar:tokens` de nuevo. */",
    "",
    ":root {",
  ];

  for (const t of tokens.color.tokens) {
    lineas.push(`  --${t.name}: ${t.value[TEMA]};`);
  }
  lineas.push("");
  for (const t of tokens.shadow.tokens) {
    lineas.push(`  --${t.name}: ${t.value[TEMA]};`);
  }
  lineas.push("");
  lineas.push(`  --font-display: ${tokens.type.families.display};`);
  lineas.push(`  --font-sans: ${tokens.type.families.sans};`);
  lineas.push(`  --font-mono: ${tokens.type.families.mono};`);
  lineas.push("");
  for (const t of tokens.spacing.tokens) {
    lineas.push(`  --${t.name}: ${t.value};`);
  }
  lineas.push("");
  for (const t of tokens.radius.tokens) {
    lineas.push(`  --${t.name}: ${t.value};`);
  }
  lineas.push("}");
  lineas.push("");

  // Tema Claro: los mismos nombres con los valores «dia» del DS.
  lineas.push('/* Tema Claro: los valores «dia» del Design System. */');
  lineas.push(':root[data-tema="claro"] {');
  for (const t of tokens.color.tokens) {
    if (t.value.dia) lineas.push(`  --${t.name}: ${t.value.dia};`);
  }
  for (const t of tokens.shadow.tokens) {
    if (t.value.dia) lineas.push(`  --${t.name}: ${t.value.dia};`);
  }
  lineas.push("}");
  lineas.push("");

  writeFileSync(RUTA_SALIDA, lineas.join("\n"));
  console.log(`Escrito ${RUTA_SALIDA}`);
}

generar();
