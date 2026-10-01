// Lo que comparten Proyectos y la pantalla de un proyecto: el enlace al
// libro, la línea de datos de cada uno y cómo se lee el Estado.
import type { EntregaCobrada, Libro, Plata } from "@/lib/nucleo";
import { fechaCorta } from "@/lib/formato";
import { recorridoDe } from "@/lib/lider";

// La bóveda se llama como su carpeta, y cada libro como su tema.
const BOVEDA = "remi-mente";

export function enlaceObsidian(tema: string): string {
  return `obsidian://open?vault=${encodeURIComponent(BOVEDA)}&file=${encodeURIComponent(`proyectos/${tema}`)}`;
}

// «cliente · vie 3 · 3/6»: de quién es, cuándo entrega y cuánto camino lleva.
// Solo lo que el libro sabe; lo que falta no se rellena.
export function datosDe(libro: Libro, ahora: Date = new Date()): string {
  const recorrido = recorridoDe(libro);
  return [
    libro.tipo,
    libro.entrega_cercana ? fechaCorta(libro.entrega_cercana.fecha, ahora) : null,
    recorrido ? `${recorrido.hechos}/${recorrido.total}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

// La última entrega cobrada de este proyecto en el mes, si se sabe de quién es.
export function ultimaCobradaDe(libro: Libro, plata: Plata): EntregaCobrada | null {
  const cliente = (libro.cliente ?? libro.entrega_cercana?.cliente ?? "").trim().toLowerCase();
  if (!cliente) return null;
  const suyas = plata.mes.entregas.filter((e) => e.cliente.trim().toLowerCase() === cliente);
  if (suyas.length === 0) return null;
  return suyas.reduce((a, b) => (new Date(a.fecha).getTime() >= new Date(b.fecha).getTime() ? a : b));
}

export type PartesDelEstado = { quedaste: string; decisiones: string; proximo: string; suelto: string };

// El Estado de un libro son tres líneas: «Quedaste:», «Decisiones:» y
// «Próximo paso:». Lo que no encaje en ninguna queda en `suelto`, tal cual.
export function partesDelEstado(texto: string): PartesDelEstado {
  const partes: PartesDelEstado = { quedaste: "", decisiones: "", proximo: "", suelto: "" };
  const sueltas: string[] = [];
  for (const cruda of texto.split("\n")) {
    const linea = cruda.trim();
    if (!linea) continue;
    const corte = linea.indexOf(":");
    const clave = corte > 0 ? linea.slice(0, corte).trim().toLowerCase() : "";
    const valor = corte > 0 ? linea.slice(corte + 1).trim() : "";
    if (clave === "quedaste") partes.quedaste = valor;
    else if (clave === "decisiones") partes.decisiones = valor;
    else if (clave === "próximo paso" || clave === "proximo paso") partes.proximo = valor;
    else sueltas.push(linea);
  }
  partes.suelto = sueltas.join(" ");
  return partes;
}

// El punto de color del estado de una fase. `apagada`: una fase que todavía
// no tiene alcance se dice en voz baja.
export function tonoDeFase(estado: string): { punto: string | null; apagada: boolean } {
  const e = estado.trim().toLowerCase();
  if (e.startsWith("sin alcance")) return { punto: null, apagada: true };
  if (e === "pagando" || e === "pagada") return { punto: "var(--dinero)", apagada: false };
  if (e === "en curso" || e === "en marcha" || e === "activa") return { punto: "var(--brasa)", apagada: false };
  if (e === "entregada" || e === "cobrada" || e === "cerrada" || e === "hecha") return { punto: "var(--luz)", apagada: false };
  return { punto: "var(--baja)", apagada: false };
}
