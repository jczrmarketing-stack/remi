/* Generado desde contratos/contratos.json por scripts/generar-contratos.mjs. */
/* No editar a mano: correr `npm run generar:contratos` de nuevo. */

export type UUID = string;
export type ISODateString = string;

export interface Tarea {
  id: UUID;
  titulo: string;
  proyecto_id: UUID | null;
  estado: "hoy" | "camino" | "hecha" | "archivada";
  paso_minimo: string;
  estimado_min: number | null;
  real_min: number | null;
  hora: string | null;
  fecha_limite: ISODateString | null;
  tipo: string | null;
  compartible: boolean;
}

export interface Idea {
  id: UUID;
  texto: string;
  origen: "voz" | "texto" | "rumbo";
  creada_en: ISODateString;
  enfria_hasta: ISODateString;
  estado: "enfriando" | "lista" | "proyecto" | "soltada" | "archivada";
  problema_vision: number | null;
  tema: string | null;
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
  tipo: "cuerpo" | "ritual" | "encoger" | "rumbo";
  voz: string;
  salida_amable: boolean;
  respuesta: "listo" | "ahora_no" | null;
}

export interface Memoria {
  id: UUID;
  titulo: string;
  resumen: string;
  tema: string;
  fecha: ISODateString;
  cuerpo: string;
  fuente: "conversacion" | "manual" | "ollama";
  claves: string | null;
  nivel: number | null;
  tipo: "decision" | null;
}

export interface Pregunta {
  id: UUID;
  tema: string;
  campo: string;
  voz: string;
  estado: "pendiente" | "respondida" | "despues";
  creada_en: ISODateString;
  disponible_desde: ISODateString;
}

export interface Entrega {
  id: UUID;
  cliente: string;
  proyecto_id: UUID;
  fecha: ISODateString;
  monto: number | null;
  estado: "camino" | "entregada" | "pagada";
  linea: string | null;
  compartible: boolean;
}

export interface Vision {
  id: UUID;
  texto: string;
  creada_en: ISODateString;
}

export interface Meta {
  id: UUID;
  monto_min: number | null;
  monto_max: number | null;
  meses_seguidos: number | null;
  limites: string | null;
  confirmada: boolean;
  creada_en: ISODateString;
}

export interface Escalon {
  id: UUID;
  n: number;
  texto: string;
  criterio: string;
  estado: "conquistado" | "ahora" | "sigue" | "luego" | "norte";
}

export interface Partida {
  id: UUID;
  tipo: "recurso" | "habilidad" | "cuesta" | "preferencia";
  texto: string;
  valor: string;
  origen: "medido" | "dicho" | "pregunta";
  dominio: "cirujano" | "sabe" | "aprendiz" | null;
  calculada_en: ISODateString;
}

export interface Propuesta {
  id: UUID;
  cliente: string;
  monto: number;
  fecha: ISODateString;
  estado: "pendiente" | "cerrada" | "perdida";
}

export interface Apuesta {
  id: UUID;
  camino: string;
  inicio: ISODateString;
  fin: ISODateString;
  tope_horas: number;
  tope_plata: number;
  resultado: "sigue" | "pausa" | "extender" | null;
}

export interface AnalisisCamino {
  id: UUID;
  idea_id: UUID;
  estado: "investigando" | "listo" | "fallo";
  mercado: string | null;
  competidores: string | null;
  juego: string | null;
  a_favor: string | null;
  en_contra: string | null;
  dominio: string | null;
  base_texto: string | null;
  base_fuente_id: UUID | null;
  palancas: string | null;
  objeciones: string | null;
  prueba: string | null;
  creada_en: ISODateString;
}

export interface Fuente {
  id: UUID;
  analisis_id: UUID;
  url: string;
  fecha: ISODateString;
  fragmento: string;
  verificada: boolean;
  tipo: string | null;
}

export interface Pronostico {
  id: UUID;
  que: string;
  p: number;
  vence: ISODateString;
  regla_si_no: string;
  tipo: "mundo" | "conducta";
  origen: string;
  resultado: boolean | null;
  creada_en: ISODateString;
}
