/* Generado desde contratos/contratos.json por scripts/generar-contratos.mjs. */
/* No editar a mano: correr `npm run generar:contratos` de nuevo. */

export type UUID = string;
export type ISODateString = string;

export interface Tarea {
  id: UUID;
  titulo: string;
  proyecto_id: UUID | null;
  estado: "hoy" | "camino" | "hecha";
  paso_minimo: string;
  estimado_min: number | null;
  real_min: number | null;
  compartible: boolean;
}

export interface Idea {
  id: UUID;
  texto: string;
  origen: "voz" | "texto";
  creada_en: ISODateString;
  enfria_hasta: ISODateString;
  estado: "enfriando" | "lista" | "proyecto" | "soltada";
  problema_vision: number | null;
}

export interface Sesion {
  id: UUID;
  tarea_id: UUID;
  inicio: ISODateString;
  fin: ISODateString | null;
  real_min: number;
  app_contexto: string | null;
}

export interface Nudge {
  id: UUID;
  tipo: "cuerpo" | "ritual" | "encoger";
  voz: string;
  salida_amable: boolean;
  respuesta: "listo" | "ahora_no" | null;
}

export interface Entrega {
  id: UUID;
  cliente: string;
  proyecto_id: UUID;
  fecha: ISODateString;
  monto: number | null;
  estado: "camino" | "entregada" | "pagada";
  compartible: boolean;
}
