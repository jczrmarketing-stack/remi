// El carácter pide respuestas sin markdown, pero un modelo a veces igual
// lo manda. La ventanita no lo renderiza: lo limpia. Negritas y cursivas
// quedan como texto, los títulos pierden la «#», las listas pasan a «·».
// Sin librería: son seis reglas y así no hay HTML que inyectar.
export function limpiarMarkdown(texto: string): string {
  return limpiarSinRecortar(texto).trim();
}

// Lo mismo sin recortar los bordes: para limpiar trozos de un renglón que
// van pegados a un link.
function limpiarSinRecortar(texto: string): string {
  return texto
    .replace(/^\s{0,3}#{1,6}\s+/gm, "") // # títulos
    .replace(/^\s{0,3}>\s?/gm, "") // > citas
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // [texto](enlace)
    .replace(/`([^`]+)`/g, "$1") // `código`
    .replace(/\*\*(.+?)\*\*/g, "$1") // **negrita**
    .replace(/__(.+?)__/g, "$1") // __negrita__
    .replace(/(^|[\s(])\*(?!\s)([^*\n]+?)\*(?=[\s).,;:!?]|$)/gm, "$1$2") // *cursiva*
    .replace(/^(\s*)[-*+]\s+/gm, "$1· ") // - listas
    .replace(/\*\*/g, ""); // lo que haya quedado suelto
}

// — Lo que se ve de una respuesta en el chat (3c) —

export type Parte = { tipo: "texto"; texto: string } | { tipo: "enlace"; texto: string; url: string };
export type Bloque = { tipo: "texto"; partes: Parte[] } | { tipo: "encargo"; texto: string };

const ENLACE = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)|(https?:\/\/[^\s)]+)/g;

/** Texto con markdown → trozos limpios y links clicables. */
export function partesConEnlaces(texto: string): Parte[] {
  const partes: Parte[] = [];
  let desde = 0;
  for (const encontrado of texto.matchAll(ENLACE)) {
    const antes = texto.slice(desde, encontrado.index);
    if (antes) partes.push({ tipo: "texto", texto: limpiarSinRecortar(antes) });
    const url = encontrado[2] ?? encontrado[3];
    partes.push({ tipo: "enlace", texto: encontrado[1] ?? url, url });
    desde = (encontrado.index ?? 0) + encontrado[0].length;
  }
  const resto = texto.slice(desde);
  if (resto) partes.push({ tipo: "texto", texto: limpiarSinRecortar(resto) });
  // Bordes del mensaje entero, no de cada trozo.
  if (partes.length > 0 && partes[0].tipo === "texto") partes[0] = { tipo: "texto", texto: partes[0].texto.trimStart() };
  const ultima = partes.length - 1;
  if (ultima >= 0 && partes[ultima].tipo === "texto") {
    partes[ultima] = { tipo: "texto", texto: (partes[ultima] as { texto: string }).texto.trimEnd() };
  }
  return partes.filter((p) => p.tipo === "enlace" || p.texto !== "");
}

/**
 * Una respuesta de Remi en bloques: el texto, y el encargo para Claude Code
 * (desde el renglón «QUÉ», si trae «LISTO CUANDO») o un bloque ``` como
 * tarjeta mono con Copiar.
 */
export function partirRespuesta(texto: string): Bloque[] {
  const bloques: Bloque[] = [];
  const agregarTexto = (t: string) => {
    if (t.trim()) bloques.push({ tipo: "texto", partes: partesConEnlaces(t) });
  };

  const cerco = /```[^\n]*\n([\s\S]*?)```/g;
  let desde = 0;
  let hayCerco = false;
  for (const encontrado of texto.matchAll(cerco)) {
    hayCerco = true;
    agregarTexto(texto.slice(desde, encontrado.index));
    bloques.push({ tipo: "encargo", texto: encontrado[1].replace(/\s+$/, "") });
    desde = (encontrado.index ?? 0) + encontrado[0].length;
  }
  if (hayCerco) {
    agregarTexto(texto.slice(desde));
    return bloques;
  }

  const renglones = texto.split("\n");
  const inicio = renglones.findIndex((r) => r.trim() === "QUÉ");
  const esEncargo = inicio >= 0 && renglones.slice(inicio).some((r) => r.trim() === "LISTO CUANDO");
  if (!esEncargo) {
    agregarTexto(texto);
    return bloques;
  }
  agregarTexto(renglones.slice(0, inicio).join("\n"));
  bloques.push({ tipo: "encargo", texto: renglones.slice(inicio).join("\n").trim() });
  return bloques;
}
