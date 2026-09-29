#!/usr/bin/env node
// Genera src/contratos.ts desde contratos/contratos.json.
// No editar a mano: correr `npm run generar:contratos` de nuevo.
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const RUTA_CONTRATOS = resolve(__dirname, "../../../contratos/contratos.json");
const RUTA_SALIDA = resolve(__dirname, "../src/contratos.ts");

const TIPOS_BASE = {
  uuid: "UUID",
  string: "string",
  int: "number",
  number: "number",
};

const RANGO = /^(\d+)-(\d+)$/;
// string(80): el largo máximo vive en el contrato y lo valida el núcleo;
// en TypeScript sigue siendo un string.
const LARGO_MAXIMO = /^string\((\d+)\)$/;

function tipoTS(spec) {
  if (typeof spec === "boolean") {
    return "boolean";
  }

  const alternativas = spec.split("|");
  const opcional = alternativas.includes("null");
  const valores = alternativas.filter((a) => a !== "null");

  let base;
  if (valores.length === 1) {
    const alt = valores[0];
    if (alt in TIPOS_BASE) {
      base = TIPOS_BASE[alt];
    } else if (alt.startsWith("iso")) {
      base = "ISODateString";
    } else if (RANGO.test(alt)) {
      base = "number";
    } else if (LARGO_MAXIMO.test(alt)) {
      base = "string";
    } else {
      base = JSON.stringify(alt);
    }
  } else {
    base = valores.map((v) => JSON.stringify(v)).join(" | ");
  }

  return opcional ? `${base} | null` : base;
}

function generar() {
  const contrato = JSON.parse(readFileSync(RUTA_CONTRATOS, "utf-8"));

  const lineas = [
    "/* Generado desde contratos/contratos.json por scripts/generar-contratos.mjs. */",
    "/* No editar a mano: correr `npm run generar:contratos` de nuevo. */",
    "",
    "export type UUID = string;",
    "export type ISODateString = string;",
  ];

  for (const [entidad, campos] of Object.entries(contrato)) {
    if (entidad.startsWith("$") || typeof campos !== "object" || campos === null) {
      continue;
    }
    lineas.push("");
    lineas.push(`export interface ${entidad} {`);
    for (const [campo, spec] of Object.entries(campos)) {
      lineas.push(`  ${campo}: ${tipoTS(spec)};`);
    }
    lineas.push("}");
  }

  lineas.push("");
  writeFileSync(RUTA_SALIDA, lineas.join("\n"));
  console.log(`Escrito ${RUTA_SALIDA}`);
}

generar();
