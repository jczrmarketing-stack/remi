// El carácter pide respuestas sin markdown, pero un modelo a veces igual
// lo manda. La ventanita no lo renderiza: lo limpia. Negritas y cursivas
// quedan como texto, los títulos pierden la «#», las listas pasan a «·».
// Sin librería: son seis reglas y así no hay HTML que inyectar.
export function limpiarMarkdown(texto: string): string {
  return texto
    .replace(/^\s{0,3}#{1,6}\s+/gm, "") // # títulos
    .replace(/^\s{0,3}>\s?/gm, "") // > citas
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // [texto](enlace)
    .replace(/`([^`]+)`/g, "$1") // `código`
    .replace(/\*\*(.+?)\*\*/g, "$1") // **negrita**
    .replace(/__(.+?)__/g, "$1") // __negrita__
    .replace(/(^|[\s(])\*(?!\s)([^*\n]+?)\*(?=[\s).,;:!?]|$)/gm, "$1$2") // *cursiva*
    .replace(/^(\s*)[-*+]\s+/gm, "$1· ") // - listas
    .replace(/\*\*/g, "") // lo que haya quedado suelto
    .trim();
}
