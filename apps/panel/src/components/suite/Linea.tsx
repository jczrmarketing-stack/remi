"use client";
// La línea de la fábrica en el piso Ingeniería (diseño B, aprobado el 6-nov;
// mockup en docs/fabrica/mockup-la-linea.html). Seis estaciones en fila y, abajo,
// lo que ve, hace, piensa y por qué la estación elegida. Lee el expediente y
// eventos.jsonl por el núcleo; mientras la línea corre, pide lo nuevo cada 2 s.
import { useEffect, useMemo, useRef, useState } from "react";
import { Eye, FileText, FlaskConical, GitPullRequest, ShieldCheck, Wrench, type LucideIcon } from "lucide-react";
import { nucleo, type EstacionId, type EstadoEstacion, type EventoFabrica, type LineaSuite, type PedidoFabrica } from "@/lib/nucleo";

const ORDEN: EstacionId[] = ["spec", "tests", "construir", "verificar", "revisar", "pr"];
const NOMBRE: Record<EstacionId, string> = { spec: "Spec", tests: "Tests", construir: "Construir", verificar: "Verificar", revisar: "Revisar", pr: "PR" };
const ICONO: Record<EstacionId, LucideIcon> = { spec: FileText, tests: FlaskConical, construir: Wrench, verificar: ShieldCheck, revisar: Eye, pr: GitPullRequest };
const QUIEN: Record<EstacionId, string> = { spec: "Planificador", tests: "Tester", construir: "Constructor", verificar: "Verificador · sin IA", revisar: "Revisor", pr: "La línea · sin IA" };
const SECCION: Partial<Record<EstacionId, string>> = { spec: "Spec", tests: "Tests", construir: "Construcción", revisar: "Revisión", pr: "Decisión" };
const SIN_IA: EstacionId[] = ["verificar", "pr"];
const LEEN = ["Read", "Grep", "Glob"];
const NEGADO = /requires approval|denied|not allowed|Portero|Output redirection|Contains brace|niega|negad/i;
const POR_QUE_SIN_IA: Record<string, string[]> = {
  verificar: ["Nada llega al PR si algo nuevo falla. Si falla, vuelve al Constructor con el informe, hasta 2 vueltas.", "salida 0 · pasa", "salida 1 · vuelve al Constructor", "salida 2 · falta una herramienta, se detiene"],
};

type Fila = { hora: string; que: string; res: string; clase?: "ok" | "no" | "negado" | "ahora" };

function hora(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function duracion(seg: number) {
  if (seg < 60) return `${Math.max(1, Math.round(seg))} s`;
  return `${Math.round(seg / 60)} min`;
}

function corto(texto: string | undefined, id: string, max = 90) {
  const t = (texto ?? "").split(`/.worktrees/pedido-${id}/`).pop() ?? "";
  const linea = t.split("\n").find((l) => l.trim()) ?? "";
  return linea.length > max ? `${linea.slice(0, max - 1)}…` : linea;
}

// Cada evento a su estación. El Revisor no anota estación propia: sus eventos llegan después de verificar.
function porEstacion(eventos: EventoFabrica[]) {
  const mapa = new Map<EstacionId, EventoFabrica[]>();
  let actual: EstacionId | null = null;
  for (const e of eventos) {
    let k: EstacionId | null = actual;
    if (e.tipo === "estacion" && ORDEN.includes(e.texto as EstacionId)) k = actual = e.texto as EstacionId;
    else if (e.rol === "revisor") k = "revisar";
    if (!k) continue;
    mapa.set(k, [...(mapa.get(k) ?? []), e]);
  }
  return mapa;
}

function ultimaEstacion(eventos: EventoFabrica[]): EstacionId | null {
  let actual: EstacionId | null = null;
  for (const e of eventos) {
    if (e.tipo === "estacion" && ORDEN.includes(e.texto as EstacionId)) actual = e.texto as EstacionId;
    else if (e.rol === "revisor") actual = "revisar";
  }
  return actual;
}

// Cuánto duró cada estación: desde su primer evento hasta que arranca la siguiente con eventos.
function duraciones(mapa: Map<EstacionId, EventoFabrica[]>) {
  const t = (iso: string) => new Date(iso).getTime();
  const conEventos = ORDEN.filter((k) => mapa.get(k)?.length);
  const salida: Partial<Record<EstacionId, number>> = {};
  conEventos.forEach((k, i) => {
    const evs = mapa.get(k) ?? [];
    // La spec termina con el Planificador: lo que sigue es tu aprobación, no trabajo de la línea.
    const sigue = conEventos[i + 1] && k !== "spec" ? mapa.get(conEventos[i + 1])?.[0] : undefined;
    const fin = sigue ? t(sigue.en) : t(evs[evs.length - 1].en);
    salida[k] = Math.max(0, (fin - t(evs[0].en)) / 1000);
  });
  return salida;
}

function lineas(texto: string | undefined, max = 8) {
  return (texto ?? "")
    .split("\n")
    .filter((l) => l.trim() && !l.startsWith("```") && !l.startsWith("## "))
    .map((l) => l.replace(/\*\*/g, "").replace(/^[-*]\s+/, "").trim())
    .slice(0, max);
}

// Los controles del verificador, tal como la línea los escribe en «Escáneres».
function escaneres(texto: string | undefined): Fila[] {
  const filas: Fila[] = [];
  for (const l of (texto ?? "").split("\n")) {
    const m = l.match(/^- (\S+)\s+\*\*(.+?)\*\*:\s*(.+)$/);
    if (m) filas.push({ hora: "", que: m[2], res: m[3], clase: m[1] === "✓" ? "ok" : "no" });
    const o = l.match(/^Escenarios ocultos: salida (\d+)/);
    if (o) filas.push({ hora: "", que: "Tests ocultos", res: o[1] === "0" ? "pasan" : "alguno falla", clase: o[1] === "0" ? "ok" : "no" });
  }
  return filas;
}

export function Linea({ linea }: { linea: LineaSuite }) {
  const [pedido, setPedido] = useState<PedidoFabrica | null>(null);
  const [eventos, setEventos] = useState<EventoFabrica[]>([]);
  const [elegida, setElegida] = useState<EstacionId | null>(null);
  const [sinNucleo, setSinNucleo] = useState(false);
  const siguiente = useRef(0);

  useEffect(() => {
    let vivo = true;
    siguiente.current = 0;
    setEventos([]);
    async function traer() {
      try {
        const [p, ev] = await Promise.all([nucleo.fabricaPedido(linea.id), nucleo.fabricaEventos(linea.id, siguiente.current)]);
        if (!vivo) return;
        setPedido(p);
        siguiente.current = ev.siguiente;
        if (ev.eventos.length) setEventos((ant) => [...ant, ...ev.eventos]);
        setSinNucleo(false);
      } catch {
        if (vivo) setSinNucleo(true);
      }
    }
    void traer();
    const reloj = linea.corriendo ? window.setInterval(traer, 2000) : undefined;
    return () => {
      vivo = false;
      if (reloj) window.clearInterval(reloj);
    };
  }, [linea.id, linea.corriendo]);

  const estado = pedido?.meta.estado ?? linea.estado;
  const terminado = estado === "pr" || estado === "cerrado";
  const corriendo = linea.corriendo && !terminado;
  const mapa = useMemo(() => porEstacion(eventos), [eventos]);
  const tiempos = useMemo(() => duraciones(mapa), [mapa]);

  // Mientras corre, la estación activa sale de los eventos; si no, de lo que calculó el núcleo.
  const estados = useMemo<Record<EstacionId, EstadoEstacion>>(() => {
    const base = Object.fromEntries(linea.estaciones.map((e) => [e.id, e.estado])) as Record<EstacionId, EstadoEstacion>;
    if (terminado) return Object.fromEntries(ORDEN.map((k) => [k, "hecha"])) as Record<EstacionId, EstadoEstacion>;
    if (!corriendo) return base;
    const actual = ultimaEstacion(eventos);
    if (!actual) return base;
    const i = ORDEN.indexOf(actual);
    return Object.fromEntries(ORDEN.map((k, n) => [k, n < i ? "hecha" : n === i ? "activa" : "por_venir"])) as Record<EstacionId, EstadoEstacion>;
  }, [linea.estaciones, terminado, corriendo, eventos]);

  const activa = ORDEN.find((k) => estados[k] === "activa") ?? null;
  const ultimaHecha = [...ORDEN].reverse().find((k) => estados[k] === "hecha") ?? "spec";
  const vista: EstacionId = elegida && estados[elegida] !== "por_venir" ? elegida : activa ?? ultimaHecha;
  const enVivo = vista === activa && corriendo;

  const evs = mapa.get(vista) ?? [];
  const vuelta = Number(evs.find((e) => e.tipo === "estacion" && e.vuelta != null)?.vuelta ?? 0);
  const totalSeg = ORDEN.reduce((s, k) => s + (tiempos[k] ?? 0), 0);
  const tope = pedido?.tope ?? 0;
  const tokens = pedido?.tokens ?? 0;

  // Qué ve
  let ve: { ruta: string; nota: string }[];
  if (SIN_IA.includes(vista)) {
    ve = [...(pedido?.meta.toca ?? []).map((r) => ({ ruta: r, nota: " · diff" })), { ruta: `base ${pedido?.meta.base ?? ""}`, nota: "" }];
  } else {
    const vistos = evs.filter((e) => e.tipo === "herramienta" && LEEN.includes(e.herramienta ?? "")).map((e) => ({ ruta: corto(e.texto, linea.id, 70), nota: e.herramienta === "Read" ? "" : ` · ${e.herramienta}` }));
    ve = vistos.filter((v, i) => vistos.findIndex((w) => w.ruta === v.ruta) === i).slice(-6);
  }

  // Qué hace
  let hace: Fila[];
  if (vista === "verificar") {
    hace = escaneres(pedido?.secciones["Escáneres"]);
    if (enVivo && !hace.length) hace = [{ hora: hora(evs[0]?.en), que: "scripts/verificar.sh --todo", res: "corriendo…", clase: "ahora" }];
  } else if (vista === "pr") {
    const fin = evs.find((e) => e.tipo === "fin" && e.texto?.startsWith("http"));
    hace = [
      { hora: hora(evs[0]?.en), que: "git commit · Fábrica INV3RZA", res: "con la identidad de la fábrica" },
      { hora: hora(evs[0]?.en), que: "git push", res: "el gancho pre-push corre el verificador otra vez" },
      ...(fin ? [{ hora: hora(fin.en), que: "gh pr create --draft", res: `PR #${fin.texto?.split("/").pop() ?? ""}` }] : []),
    ];
  } else {
    hace = [];
    const sinResultado: Fila[] = []; // varias herramientas seguidas: los resultados llegan en el mismo orden
    for (const e of evs) {
      if (e.tipo === "herramienta") {
        const fila: Fila = { hora: hora(e.en), que: `${e.herramienta ?? ""} ${corto(e.texto, linea.id, 70)}`.trim(), res: "" };
        hace.push(fila);
        sinResultado.push(fila);
      } else if (e.tipo === "resultado") {
        const fila = sinResultado.shift();
        if (!fila) continue;
        fila.res = corto(e.texto, linea.id);
        if (NEGADO.test(fila.res)) fila.clase = "negado";
      }
    }
    hace = hace.slice(-8);
    if (enVivo && hace.length && !hace[hace.length - 1].clase) hace[hace.length - 1].clase = "ahora";
  }

  // Qué piensa
  const piensa = SIN_IA.includes(vista)
    ? ["Es código, no un modelo: no piensa ni gasta tokens.", vista === "verificar" ? "Compara contra la base. Solo cuenta lo que este cambio rompe." : "Commit, push y PR los hace la línea, nunca un agente."]
    : evs.filter((e) => ["texto", "pensamiento", "fin"].includes(e.tipo) && e.rol !== "linea" && e.texto).map((e) => corto(e.texto, linea.id, 220)).slice(-3);

  // Por qué
  const porQue = POR_QUE_SIN_IA[vista] ?? lineas(pedido?.secciones[SECCION[vista] ?? ""]);

  const titulo = vista === "construir" ? `${QUIEN.construir} · vuelta ${vuelta + 1}/2` : QUIEN[vista];

  return (
    <section className="su-li" aria-label="La línea">
      <div className="su-li-cab">
        <div>
          <h3>La línea</h3>
          <p className="idea">{linea.idea}</p>
          <div className="id">
            {linea.id}
            {pedido ? ` · base ${pedido.meta.base} · riesgo ${pedido.meta.riesgo}` : ""}
          </div>
        </div>
        {pedido ? (
          <div className="gasto" aria-label="Tokens y tiempo del pedido">
            <div className="n">
              <b>{tokens.toLocaleString("es-CO")}</b> de {tope.toLocaleString("es-CO")} tokens
            </div>
            <div className="barra">
              <i style={{ width: `${tope ? Math.min(100, (tokens / tope) * 100) : 0}%` }} />
            </div>
            <div className="t">
              {totalSeg ? `${corriendo ? "lleva " : ""}${duracion(totalSeg)} de trabajo` : ""}
              {terminado ? ` · ${pedido.meta.vueltas ? `${pedido.meta.vueltas} vueltas extra` : "0 vueltas extra"}` : ""}
            </div>
          </div>
        ) : null}
      </div>

      <ol className="su-li-est" aria-label="Estaciones del pedido">
        {ORDEN.map((k) => {
          const Icono = ICONO[k];
          const s = estados[k];
          const seg = tiempos[k] ?? 0;
          const det = s === "activa" ? (seg ? `${duracion(seg)} · corriendo` : "corriendo") : s === "hecha" && seg ? duracion(seg) : s === "hecha" ? "hecha" : "después";
          return (
            <li key={k} className={s}>
              <button type="button" className="est" aria-pressed={vista === k} disabled={s === "por_venir"} onClick={() => setElegida(k)}>
                <span className="punto">
                  <Icono size={20} strokeWidth={1.75} aria-hidden />
                </span>
                <span className="nom">{NOMBRE[k]}</span>
                <span className="det">{det}</span>
              </button>
            </li>
          );
        })}
      </ol>

      <section className="su-li-vivo" aria-live="polite">
        <div className="vivo-cab">
          <b>
            {titulo}
            {estados[vista] === "hecha" ? " · hecho" : ""}
          </b>
          <span className={enVivo ? "en-vivo" : undefined}>{sinNucleo ? "sin núcleo" : enVivo ? "en vivo · cada 2 s" : evs.length ? `registro · ${hora(evs[0].en)}` : ""}</span>
        </div>
        <div className="cuatro">
          <div className="caja ve">
            <h4>Qué ve</h4>
            <ul>
              {ve.length ? ve.map((v, i) => (
                <li key={i}>
                  {v.ruta}
                  <small>{v.nota}</small>
                </li>
              )) : <li className="vacio">Nada todavía.</li>}
            </ul>
          </div>
          <div className="caja hace">
            <h4>Qué hace</h4>
            <ul>
              {hace.length ? hace.map((f, i) => (
                <li key={i} className={f.clase}>
                  <time>{f.hora}</time>
                  <code>{f.que}</code>
                  {f.res ? <span className="res">{f.res}</span> : null}
                </li>
              )) : <li className="vacio">Nada todavía.</li>}
            </ul>
          </div>
          <div className={`caja piensa${SIN_IA.includes(vista) ? " sin-ia" : ""}`}>
            <h4>Qué piensa</h4>
            {piensa.length ? piensa.map((p, i) => <p key={i}>{p}</p>) : <p className="vacio">Nada todavía.</p>}
          </div>
          <div className="caja porque">
            <h4>Por qué</h4>
            {porQue.length ? (
              <ul>
                {porQue.map((l, i) => (
                  <li key={i} className={/^\[(alto|medio|bajo)\]/.test(l) ? "h" : undefined}>{l}</li>
                ))}
              </ul>
            ) : <p className="vacio">Nada todavía.</p>}
          </div>
        </div>
        {estado === "pr" ? <p className="voz">Solo esto: leer el PR. Diez minutos.</p> : null}
      </section>
    </section>
  );
}

// La fila de Ingeniería en el edificio: las seis estaciones en chico.
export function LineaMini({ linea }: { linea: LineaSuite }) {
  return (
    <div className="su-li-mini" aria-label={`Estaciones de «${linea.idea}»`}>
      {linea.estaciones.map((e, i) => (
        <div key={e.id} className="paso-mini">
          {i ? <span className="r" aria-hidden /> : null}
          <div className={`m ${e.estado}`}>
            <i aria-hidden />
            <b>{NOMBRE[e.id]}</b>
            <em>{e.estado === "hecha" ? "hecho" : e.estado === "activa" ? "ahora" : "después"}</em>
          </div>
        </div>
      ))}
    </div>
  );
}
