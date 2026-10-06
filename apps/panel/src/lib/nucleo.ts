// Cliente del núcleo: fetch simples contra las rutas reales de servidor.py.
// Nada de mocks acá — tests/ trae su propio núcleo falso para Playwright.
// En producción, "/nucleo" es mismo origen: next.config.mjs reenvía
// /nucleo/:path* al núcleo real (127.0.0.1:puerto, de config/nucleo.json),
// cabeceras incluidas — así el panel sirve desde el teléfono sin CORS ni la
// IP del Mac a mano. NEXT_PUBLIC_URL_NUCLEO solo manda en Playwright.
import type { Entrega, Idea, ISODateString, Nudge, Pregunta, Sesion, Tarea } from "@/contratos";

const BASE = process.env.NEXT_PUBLIC_URL_NUCLEO || "/nucleo";

export class NucleoApagado extends Error {
  status?: number;
}

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  let respuesta: Response;
  try {
    respuesta = await fetch(`${BASE}${ruta}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch (error) {
    throw new NucleoApagado(`no pude llegar a ${ruta}: ${(error as Error).message}`);
  }
  if (!respuesta.ok) {
    const error = new NucleoApagado(`${ruta} devolvió ${respuesta.status}`);
    error.status = respuesta.status;
    throw error;
  }
  if (respuesta.status === 204) return undefined as T;
  return (await respuesta.json()) as T;
}

export type TareaConHistorial = { tarea: Tarea; sesiones: Sesion[]; ultima_vez_min: number | null };
export type Salud = { ok: boolean; db: boolean };
// `destacada`: la idea de la semana (forma E del plan); sin definir mientras
// el núcleo no lo sirva.
export type IdeaBandeja = { idea: Idea; fria: boolean; destacada?: boolean };
// `detalle`: la línea del SOP que explica ese paso (forma A del plan). Un
// núcleo que todavía no la sirve la deja sin definir; "" si el hito no es del SOP.
// `cerrado_por` (forma K, B3.4): cómo se cerró solo. undefined en un núcleo
// viejo; null si está abierto o se marcó a mano antes de B3.
export type CerradoPor = { tipo: string; ref: string; en: string };
export type Hito = { texto: string; hecho: boolean; detalle?: string; cerrado_por?: CerradoPor | null };
export type Camino = { hitos: Hito[]; siguiente: Hito | null };
export type EntregaCercana = { cliente: string; fecha: string; monto: number };
// Una fase de la propuesta, tal como está en el frontmatter del libro.
// `cobrado`: lo pagado del proyecto repartido en cascada entre las fases
// (forma A); sin definir mientras el núcleo no lo sirva.
export type Fase = { nombre: string; alcance: string; monto: number | null; listo_cuando: string; estado: string; cobrado?: number; minutos_estimados?: number | null };
export type Libro = {
  tema: string;
  titulo: string;
  resumen: string;
  compartible: boolean;
  // Vacíos si el libro no tiene ## Estado todavía — nunca ausentes.
  quedaste: string;
  proximo_paso: string;
  hitos: Hito[];
  // La entrega viva (con dinero) más cercana de este libro, para el orden
  // del líder en Proyectos.
  entrega_cercana: EntregaCercana | null;
  // mtime del archivo del libro (ISO): el último escalón de ese orden.
  ultimo_estado_en: string;
  // El camino sale del SOP: «propio» | «cliente» | null si el libro no lo dice.
  tipo: string | null;
  // El nombre del cliente, del frontmatter del libro (forma A).
  cliente?: string | null;
  fases: Fase[];
  // La fase en la que está, contando desde 1. null sin fases.
  fase_actual_n: number | null;
  // El primer hito sin marcar y hasta tres que vienen después.
  hito_actual: Hito | null;
  siguientes: Hito[];
  // Qué hace Remi en el paso actual, según el SOP. "" si no aplica.
  paso_remi: string;
};
export type UltimoEpisodio = { titulo: string; resumen: string; archivo: string };
// B6 (tablero 5, la ficha de cliente): gastado agrupado por concepto
// (incluye la parte de los comunes), minutos desde siempre y por_hora.
export type GastoDeLibro = { concepto: string; monto: number; id?: string | null };
// B6.3/B6.4: lo acordado, lo que pasó y a qué está atento Remi — sin IA.
export type LineaDeEvidencia = { texto: string; origen: string; hace_min: number };
// GET /libros/{tema}: lo mismo, más el Estado entero, el último episodio
// y la ficha.
export type LibroDetalle = Libro & {
  estado_completo: string;
  ultimo_episodio: UltimoEpisodio | null;
  gastado: number;
  gastos: GastoDeLibro[];
  minutos_total: number;
  por_hora: number | null;
  decisiones: string[];
  entregas_futuras: string[];
  lo_que_paso: LineaDeEvidencia[];
  atento_a: string[];
};
// GET /hoy/agenda: lo que la base sabe de fechas.
export type Vencimiento = { titulo: string; fecha: string; monto: number | null; origen: "tarea" | "entrega"; vence_hoy: boolean };
export type AgendaDeHoy = { manana: Tarea[]; vence: Vencimiento[] };
export type Meta = { nombre: string; horizonte_meses: number | null; monto_mes: number; activa: boolean; activa_desde_pct: number | null };
export type RevisionFria = { dia: string; hora: string; minutos: number | null };
export type EntregaCobrada = { cliente: string; fecha: string; monto: number };
// Lo que trajo cada línea de ingreso en el mes y los minutos que se le
// dedicaron (forma C del plan): una por línea de config/plata.json.
export type LineaDelMes = { id: string; nombre: string; cobrado_mes: number; minutos_mes: number };
export type Plata = {
  semana: { cobrado: number; meta_semanal: number };
  mes: { cobrado: number; meta: number; faltan: number; entregas: EntregaCobrada[] };
  proximo: { cliente: string; fecha: string; monto: number } | null;
  metas: Meta[];
  revision_fria: RevisionFria | null;
  // Sin definir mientras el núcleo no lo sirva.
  por_linea?: LineaDelMes[];
  // B6: lo común de este mes, antes de repartirse por minutos del mes.
  gastos_comunes_mes?: number;
};
// GET /semana (forma D del plan): la semana desde el lunes, para la revisión.
// `aplazado` es una lista corta, nunca un contador.
export type Semana = {
  desde: string;
  cerrado: { titulo: string; tema: string | null; real_min: number | null }[];
  aplazado: { titulo: string; tema: string | null }[];
  ideas_frias: number;
  destacada: { id: string; texto: string; tema: string | null } | null;
};
// Lo que Remi pregunta cuando le falta un dato: el contrato `Pregunta`
// (Biblia v3.9, forma F del plan). `campo` dice qué dato es: «tipo»,
// «cliente», «fase.2.listo_cuando», «fase.1.cobrado»…
export type { Pregunta } from "@/contratos";
export type RespuestaMensaje = { tipo: string; texto: string; voz: string; tarea: Tarea | null; sesion: Sesion | null };

// nucleo/conexiones.py: no es un contrato (contratos/contratos.json no
// las tiene), son los tipos propios de esa ruta.
export type Prueba = { ok: boolean; mensaje_humano: string };
export type Conexion = { puesta: boolean; termina_en: string | null; ultima_prueba: Prueba | null };
export type ConexionesEstado = Record<string, Conexion>;

// nucleo/gasto.py (B1): tampoco es un contrato — el tope de gasto en los
// motores pagados (Venice, OpenRouter).
export type ConfigGasto = {
  tope_dia_usd: number;
  tope_mes_usd: number;
  activo: boolean;
  gastado_dia_usd: number;
  gastado_mes_usd: number;
};

// nucleo/aldia.py (B2, forma J): tampoco es un contrato — Al día se
// actualiza sola, sin que Juan Camilo marque nada.
export type Evidencia = { tipo: string; ref: string };
export type EstamosEn = { tema: string; fase_n: number; paso: string };
export type LoUltimo = { texto: string; hace_min: number; evidencia: Evidencia };
export type Sigue = { texto: string; borrador: string | null };
export type MientrasNoEstabas = { texto: string; tema: string | null; hora: string; evidencia: Evidencia };
export type AlDia = {
  estamos_en: EstamosEn | null;
  lo_ultimo: LoUltimo | null;
  sigue: Sigue | null;
  mientras_no_estabas: MientrasNoEstabas[];
};

// --- R1-R5: Rumbo (formas N, R, O, Q) --------------------------------

export type EscalonVista = { n: number; texto: string; criterio: string; estado: "conquistado" | "ahora" | "sigue" | "luego" | "norte" };
export type ItemPartida = { tipo: string; texto: string; valor: string; origen: "medido" | "dicho" | "pregunta"; dominio: "cirujano" | "sabe" | "aprendiz" | null };
export type MetaVista = { monto_min: number | null; monto_max: number | null; meses_seguidos: number | null; limites: string | null };
export type VistaRumbo = { vision: string | null; meta: MetaVista | null; escalera: EscalonVista[]; partida: ItemPartida[] };
export type PropuestaVisionVista = { monto_min: number | null; monto_max: number | null; meses_seguidos: number | null; limites: string | null };

export type CuentaCierre = { p: number; base_n: number; origen: "propia" | "general" };
export type CaminoHoras = { camino: string; pct: number };
export type VistaCuenta = {
  meta_mes: number | null;
  ticket: number | null;
  necesarias: number | null;
  tienes: number;
  cierre: CuentaCierre;
  propuestas_semana: number;
  hechas_semana: number;
  horas_semana: CaminoHoras[];
};

export type ApuestaProgreso = { hecho: number; meta: number };
export type ApuestaVista = {
  id: string;
  camino: string;
  inicio: ISODateString;
  fin: ISODateString;
  tope_horas: number;
  tope_plata: number;
  gastado_horas: number;
  gastado_plata: number;
  senal_sigue: boolean;
  senal_pausa: boolean;
  progreso: ApuestaProgreso;
  resultado: string | null;
};

// R5.2, forma S: si el reloj, los pronósticos o la cuenta dejan de recibir
// datos, el latido lo dice una vez, sin culpa. `ultimo_dato`: ISO, o null
// si esa pieza nunca recibió nada todavía.
export type LatidoPieza = { pieza: string; ultimo_dato: ISODateString | null; callado_dias: number };

export type FuenteVista = { id: string; url: string; fecha: ISODateString; fragmento: string; verificada: boolean; tipo: string | null };
export type VistaAnalisisCamino = {
  estado: "investigando" | "listo" | "fallo";
  mercado: string | null;
  competidores: string | null;
  juego: string | null;
  a_favor: string | null;
  en_contra: string | null;
  dominio: string | null;
  base: { texto: string; fuente_id: string | null } | null;
  palancas: string | null;
  objeciones: string | null;
  prueba: string | null;
  fuentes: FuenteVista[];
};

export const nucleo = {
  salud: () => pedir<Salud>("/salud"),
  // Un núcleo que todavía no tiene esta ruta (B2) responde 404: null, no
  // una excepción que tumbe toda la pantalla de Hoy.
  alDia: async (): Promise<AlDia | null> => {
    try {
      return await pedir<AlDia>("/hoy/aldia");
    } catch (error) {
      if (error instanceof NucleoApagado && error.status === 404) return null;
      throw error;
    }
  },
  hoy: () => pedir<TareaConHistorial[]>("/hoy"),
  ultimaVez: () => pedir<{ minutos: number | null }>("/ultima-vez"),
  entregas: () => pedir<Entrega[]>("/entregas"),
  bandeja: () => pedir<IdeaBandeja[]>("/bandeja"),
  nudgePendiente: () => pedir<Nudge | null>("/nudges/pendiente"),
  plata: () => pedir<Plata>("/plata"),
  libros: () => pedir<Libro[]>("/libros"),
  agenda: () => pedir<AgendaDeHoy>("/hoy/agenda"),
  // 404 acá es un dato legítimo (ese tema no tiene libro), no el núcleo
  // caído: null, no una excepción.
  libro: async (tema: string): Promise<LibroDetalle | null> => {
    try {
      return await pedir<LibroDetalle>(`/libros/${encodeURIComponent(tema)}`);
    } catch (error) {
      if (error instanceof NucleoApagado && error.status === 404) return null;
      throw error;
    }
  },

  // Un núcleo que todavía no tiene la ruta responde 404: null, y la página
  // muestra el guion sin datos en vez de romperse.
  semana: async (): Promise<Semana | null> => {
    try {
      return await pedir<Semana>("/semana");
    } catch (error) {
      if (error instanceof NucleoApagado && error.status === 404) return null;
      throw error;
    }
  },

  // Las preguntas pendientes de un libro, tres como mucho y en el orden del
  // líder. Un núcleo que todavía no pregunta responde 404: ninguna.
  preguntas: async (tema: string): Promise<Pregunta[]> => {
    try {
      return await pedir<Pregunta[]>(`/preguntas?tema=${encodeURIComponent(tema)}`);
    } catch (error) {
      if (error instanceof NucleoApagado && error.status === 404) return [];
      throw error;
    }
  },
  // `voz` es lo que Remi dice: la confirmación, o la repregunta con el
  // formato si no entendió (y entonces `pregunta.estado` sigue «pendiente»).
  responderPregunta: (id: string, texto: string) =>
    pedir<{ pregunta: Pregunta; voz: string }>(`/preguntas/${id}/respuesta`, { method: "POST", body: JSON.stringify({ texto }) }),
  dejarPreguntaParaDespues: (id: string) => pedir<Pregunta>(`/preguntas/${id}/despues`, { method: "POST" }),

  responderNudge: (id: string, respuesta: "listo" | "ahora_no") =>
    pedir<Nudge>(`/nudges/${id}/respuesta`, { method: "POST", body: JSON.stringify({ respuesta }) }),

  revisarIdea: (id: string, decision: "soltar" | "mantener" | "tarea") =>
    pedir<{ idea: Idea; tarea: Tarea | null }>(`/idea/${id}/revision`, {
      method: "POST",
      body: JSON.stringify({ decision }),
    }),

  // La idea de la semana: una sola. Destacar otra reemplaza a la anterior.
  destacarIdea: (id: string, destacada: boolean) =>
    pedir<IdeaBandeja>(`/idea/${id}/destacar`, { method: "POST", body: JSON.stringify({ destacada }) }),

  cerrarBloque: () =>
    pedir<RespuestaMensaje>("/mensaje", { method: "POST", body: JSON.stringify({ texto: "listo" }) }),

  abrirDesdeTexto: (texto: string) =>
    pedir<RespuestaMensaje>("/mensaje", { method: "POST", body: JSON.stringify({ texto }) }),

  // Un botón del panel abre un bloque sin pasar por el clasificador. 409 si
  // ya hay otro abierto: una cosa a la vez.
  abrirBloque: (titulo: string, tema: string | null) =>
    pedir<{ tarea: Tarea; sesion: Sesion }>("/bloque", { method: "POST", body: JSON.stringify({ titulo, tema }) }),

  // Marca o desmarca el hito número `n` (desde 1) del camino de ese libro.
  // El núcleo edita solo esa línea y deja un commit en la bóveda.
  marcarHito: (tema: string, n: number, hecho: boolean) =>
    pedir<Camino>(`/libros/${encodeURIComponent(tema)}/camino/${n}`, { method: "POST", body: JSON.stringify({ hecho }) }),

  // Forma K (B3.4): un hito que se cerró solo, devuelto a abierto.
  deshacerHito: (tema: string, n: number) =>
    pedir<LibroDetalle>(`/libros/${encodeURIComponent(tema)}/camino/${n}/deshacer`, { method: "POST" }),

  // B6.5: la ficha de cliente — un gasto que se corrige a mano.
  corregirGasto: (gastoId: string, monto: number) =>
    pedir<GastoDeLibro>(`/gastos/${encodeURIComponent(gastoId)}`, { method: "PATCH", body: JSON.stringify({ monto }) }),

  pasoMinimo: (tareaId: string, paso_minimo: string) =>
    pedir<Tarea>(`/tarea/${tareaId}/paso-minimo`, { method: "POST", body: JSON.stringify({ paso_minimo }) }),

  // Remi redacta, nunca envía: la respuesta se copia, no sale sola.
  leerParaCliente: (texto: string) =>
    pedir<RespuestaMensaje>("/mensaje", {
      method: "POST",
      body: JSON.stringify({ texto, think: true }),
    }),

  // Ajustes → Conexiones. Solo funciona desde el Mac: con una cabecera
  // Cf-* (vino por el túnel) el núcleo responde 403.
  conexiones: () => pedir<ConexionesEstado>("/config/conexiones"),
  guardarConexion: (nombre: string, valor: string) =>
    pedir<Conexion>(`/config/conexiones/${encodeURIComponent(nombre)}`, {
      method: "PUT",
      body: JSON.stringify({ valor }),
    }),
  probarConexion: (nombre: string) =>
    pedir<Prueba>(`/config/conexiones/${encodeURIComponent(nombre)}/probar`, { method: "POST" }),
  guardarMetaMensual: (meta_mensual: number) =>
    pedir<{ meta_mensual: number; moneda: string }>("/config/plata", {
      method: "PUT",
      body: JSON.stringify({ meta_mensual }),
    }),

  // Ajustes → tope de gasto (B1).
  configGasto: () => pedir<ConfigGasto>("/config/gasto"),
  guardarConfigGasto: (config: { tope_dia_usd: number; tope_mes_usd: number; activo: boolean }) =>
    pedir<ConfigGasto>("/config/gasto", { method: "PUT", body: JSON.stringify(config) }),

  // Rumbo (R1-R5): visión/meta/escalera/partida, cuenta hacia atrás,
  // apuestas y el análisis de un camino.
  rumbo: () => pedir<VistaRumbo>("/rumbo"),
  contarVision: (texto: string) =>
    pedir<{ propuesta: PropuestaVisionVista; voz: string }>("/rumbo/vision", { method: "POST", body: JSON.stringify({ texto }) }),
  fijarMeta: (meta: { monto_min: number | null; monto_max: number | null; meses_seguidos: number | null; limites: string | null; confirmada: boolean }) =>
    pedir<MetaVista | null>("/rumbo/meta", { method: "POST", body: JSON.stringify(meta) }),
  rumboCuenta: () => pedir<VistaCuenta>("/rumbo/cuenta"),
  rumboApuestas: () => pedir<ApuestaVista[]>("/rumbo/apuestas"),
  // 404: esa idea todavía no tiene un análisis pedido — la pantalla lo dice,
  // no rompe.
  analisisCamino: async (id: string): Promise<VistaAnalisisCamino | null> => {
    try {
      return await pedir<VistaAnalisisCamino>(`/rumbo/caminos/${encodeURIComponent(id)}`);
    } catch (error) {
      if (error instanceof NucleoApagado && error.status === 404) return null;
      throw error;
    }
  },
  // R5.2 (forma S): un núcleo que todavía no la sirve responde 404 — el
  // motor lo dice sin romperse, no como un núcleo caído.
  latido: async (): Promise<LatidoPieza[]> => {
    try {
      return await pedir<LatidoPieza[]>("/rumbo/latido");
    } catch (error) {
      if (error instanceof NucleoApagado && error.status === 404) return [];
      throw error;
    }
  },
};
