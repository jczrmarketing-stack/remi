"use client";
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { Chip } from "@/components/Chip";
import { MoneyRow } from "@/components/MoneyRow";
import { NudgeCard } from "@/components/NudgeCard";
import { Reloj } from "@/components/Reloj";
import { Bionica } from "@/components/Bionica";
import { usePreferencias, type PielReloj } from "@/hooks/PreferenciasContext";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { cargarHoy, formatoDuracion, formatoMoneda, minutosDesde, type BloqueAbierto, type Propuesta } from "@/lib/hoy";
import { cuandoEsLaRevision, diaDeLaSemana, fechaCorta, formatoHora, horaDeISO, nombreCorto, venceTexto } from "@/lib/formato";
import { faseDe, hitoDe } from "@/lib/lider";
import { nucleo, NucleoApagado, type AgendaDeHoy, type AlDia, type RevisionFria, type TareaConHistorial, type Vencimiento } from "@/lib/nucleo";
import type { Tarea } from "@/contratos";

const MINUTOS_PARA_FOCO = 20;

// «UpVisuals · Fase 1 · entrega vie 3»: de qué proyecto es el bloque, en
// qué fase va y cuándo se entrega. Sin libro, queda el tema o «Hoy».
function etiquetaDelBloque(bloque: BloqueAbierto): string {
  const libro = bloque.libro;
  if (!libro) return bloque.tema ?? "Hoy";
  return [
    nombreCorto(libro.titulo),
    faseDe(libro),
    libro.entrega_cercana ? `entrega ${fechaCorta(libro.entrega_cercana.fecha)}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

// El hito encendido del libro del bloque: «hito 5 de 10». Sin camino, 1 de 1.
function hitoDelBloque(bloque: BloqueAbierto): { n: number; total: number } {
  const hitos = bloque.libro?.hitos ?? bloque.camino?.hitos ?? [];
  if (hitos.length === 0) return { n: 1, total: 1 };
  const encendido = hitoDe({ hitos });
  return { n: encendido ? encendido.n : hitos.length, total: hitos.length };
}

export default function PaginaHoy() {
  const { prefs } = usePreferencias();
  const { datos, error, recargar } = useCargaNucleo(cargarHoy);
  const [ahoraMs, setAhoraMs] = useState(() => Date.now());
  const [foco, setFoco] = useState(false);
  const [celebrando, setCelebrando] = useState(false);
  const [cerrado, setCerrado] = useState<{ voz: string; minutos: number; etiqueta: string; hito: { n: number; total: number } } | null>(null);
  const [cerrando, setCerrando] = useState(false);
  const [cliente, setCliente] = useState("");
  const [copiado, setCopiado] = useState(false);

  async function copiarMensaje() {
    if (!cliente.trim()) return;
    const respuesta = await nucleo.leerParaCliente(`me escribió ${cliente}: avísale que cerré este hito`);
    await navigator.clipboard.writeText(respuesta.texto).catch(() => undefined);
    setCopiado(true);
  }

  useEffect(() => {
    if (!datos?.bloque) return;
    const id = setInterval(() => setAhoraMs(Date.now()), 1000);
    return () => clearInterval(id);
  }, [datos?.bloque]);

  const minutos = useMemo(
    () => (datos?.bloque ? minutosDesde(datos.bloque.inicioISO, ahoraMs) : 0),
    [datos?.bloque, ahoraMs],
  );

  useEffect(() => {
    if (minutos >= MINUTOS_PARA_FOCO) setFoco(true);
  }, [minutos]);

  async function cerrarHito() {
    if (!datos?.bloque) return;
    const bloque = datos.bloque;
    setCerrando(true);
    try {
      const respuesta = await nucleo.cerrarBloque();
      // A quién avisar: si el bloque era de una entrega, ya se sabe.
      const aQuien = bloque.libro?.entrega_cercana?.cliente;
      if (aQuien) setCliente((actual) => actual || aQuien);
      // La celebración: 900 ms, una sola vez.
      setCelebrando(true);
      setTimeout(() => setCelebrando(false), 900);
      setCerrado({ voz: respuesta.voz, minutos, etiqueta: etiquetaDelBloque(bloque), hito: hitoDelBloque(bloque) });
      setFoco(false);
    } finally {
      setCerrando(false);
    }
  }

  if (error instanceof NucleoApagado) {
    return (
      <div className="shell">
        <Header sano={false} />
        <Apagado ultimaVez={null} onReintentar={recargar} />
        <TabBar />
      </div>
    );
  }

  if (!datos) {
    return (
      <div className="shell">
        <Header />
        <div className="contenedor">
          <p className="body-muted">Cargando…</p>
        </div>
      </div>
    );
  }

  if (foco && datos.bloque) {
    const tarea = datos.bloque.tarea.tarea;
    const siguiente = datos.demasHoy[0];
    const hito = hitoDelBloque(datos.bloque);
    return (
      <div className="shell" style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 24, textAlign: "center" }}>
        <div className="label">{datos.bloque.libro ? nombreCorto(datos.bloque.libro.titulo) : datos.bloque.tema ?? "Hoy"} · una sola cosa</div>
        <p className="voz" style={{ color: "var(--ink-muted)", fontSize: 26, lineHeight: "27px" }}>{tarea.titulo}</p>
        <div className="num-lg" style={{ fontSize: 96, lineHeight: "96px", color: "var(--dinero)" }}>
          {String(Math.floor(minutos / 60)).padStart(2, "0")}:{String(minutos % 60).padStart(2, "0")}:00
        </div>
        <div className="mono-sm">
          la última vez: <span style={{ color: "var(--dinero)" }}>{datos.bloque.tarea.ultima_vez_min != null ? formatoDuracion(datos.bloque.tarea.ultima_vez_min) : "sin dato"}</span>
          {datos.bloque.camino ? ` · hito ${hito.n} de ${hito.total}` : ""}
        </div>
        <div style={{ width: 320, maxWidth: "100%", height: 1, background: "var(--line)", margin: "16px 0" }} />
        {siguiente ? (
          <p className="body-muted" style={{ maxWidth: "46ch" }}>
            Después: <span style={{ color: "var(--ink)" }}>{siguiente.tarea.titulo}</span>
            {siguiente.tarea.hora ? ` a las ${formatoHora(siguiente.tarea.hora)}` : ""}. Nada más existe hasta entonces.
          </p>
        ) : null}
        <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
          <button type="button" className="btn btn-luz" disabled={cerrando} onClick={cerrarHito}>Cerrar hito</button>
          <button type="button" className="btn btn-secundario" onClick={() => setFoco(false)}>Salir del foco</button>
        </div>
        <p className="body-muted" style={{ marginTop: 24 }}>Entra solo a los 20 minutos de bloque. Sale al cerrar.</p>
      </div>
    );
  }

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <MoneyRow plata={datos.plata} />

        <AlDiaStrip alDia={datos.alDia} />

        {cerrado ? (
          <PantallaCerrado cerrado={cerrado} celebrando={celebrando} />
        ) : datos.bloque ? (
          <BloqueActivo
            bloque={datos.bloque}
            minutos={minutos}
            piel={prefs.pielReloj}
            cerrando={cerrando}
            onCerrar={cerrarHito}
            onFoco={() => setFoco(true)}
          />
        ) : (
          <SinNadaAbierto propuesta={datos.propuesta} onEmpezado={recargar} />
        )}

        {!cerrado && datos.nudge ? <NudgeCard nudge={datos.nudge} onRespondido={recargar} /> : null}

        {cerrado ? (
          <div className="card-grid-2">
            <ListaDeCierre cliente={cliente} setCliente={setCliente} copiado={copiado} onCopiar={copiarMensaje} />
            <LoQueSigue siguiente={datos.demasHoy[0] ?? null} onSiguiente={() => { setCerrado(null); recargar(); }} />
          </div>
        ) : (
          <div className="card-grid-2">
            <ListaDemasHoy tareas={datos.demasHoy} manana={datos.agenda.manana} />
            <ListaVence agenda={datos.agenda} />
          </div>
        )}

        {datos.ideasFrias.length > 0 ? (
          <IdeasFrias cuantas={datos.ideasFrias.length} revision={datos.plata.revision_fria} />
        ) : null}

        <p className="body-txt" style={{ maxWidth: "72ch" }}>
          <Bionica texto="Remi ordena el día así: entregas con dinero, luego bugs en producción, luego propuestas, mejoras e ideas. Una locura por pantalla; lo demás, en voz baja." />
        </p>
      </div>
      <TabBar />
    </div>
  );
}

// B2/B4 (forma J): tres líneas en mono, como el contexto de Claude Code —
// en qué vas, lo último que pasó y el paso que sigue, sin que lo marques.
function AlDiaStrip({ alDia }: { alDia: AlDia | null }) {
  const [copiado, setCopiado] = useState(false);
  if (!alDia) return null;
  const { estamos_en, lo_ultimo, sigue, mientras_no_estabas } = alDia;
  if (!estamos_en && !lo_ultimo && !sigue && mientras_no_estabas.length === 0) return null;

  async function copiarBorrador() {
    if (!sigue?.borrador) return;
    await navigator.clipboard.writeText(sigue.borrador).catch(() => undefined);
    setCopiado(true);
  }

  return (
    <section aria-label="Al día" className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="label">Al día</div>
      <div className="mono-sm" style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {estamos_en ? <div>ESTAMOS EN · {estamos_en.tema} · {estamos_en.paso}</div> : null}
        {lo_ultimo ? <div>LO ÚLTIMO · {lo_ultimo.texto} · hace {lo_ultimo.hace_min} min</div> : null}
        {sigue ? <div>SIGUE · {sigue.texto}</div> : null}
      </div>
      {sigue?.borrador ? (
        <div style={{ display: "flex", gap: 10, alignItems: "flex-start", flexWrap: "wrap", borderTop: "1px solid var(--line)", paddingTop: 12 }}>
          <p className="voz" style={{ margin: 0, flexGrow: 1, minWidth: 200 }}>{sigue.borrador}</p>
          <button type="button" className="btn btn-secundario" onClick={copiarBorrador}>
            {copiado ? "Copiado" : "Copiar mensaje"}
          </button>
        </div>
      ) : null}
      {mientras_no_estabas.length > 0 ? (
        <div aria-label="Mientras no estabas" style={{ borderTop: "1px solid var(--line)", paddingTop: 12 }}>
          <p className="voz" style={{ margin: "0 0 8px" }}>Mientras no estabas</p>
          {mientras_no_estabas.map((e, i) => (
            <div className="fila" key={i}>
              <i className="punto" style={{ background: "var(--brasa)" }} />
              <span style={{ flexGrow: 1 }}>{e.texto}</span>
              <span className="mono-sm">{horaDeISO(e.hora)}</span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function BloqueActivo({ bloque, minutos, piel, cerrando, onCerrar, onFoco }: {
  bloque: BloqueAbierto;
  minutos: number;
  piel: PielReloj;
  cerrando: boolean;
  onCerrar: () => void;
  onFoco: () => void;
}) {
  const [pasoVisible, setPasoVisible] = useState(false);
  const tarea = bloque.tarea.tarea;
  const hito = hitoDelBloque(bloque);
  const entrega = bloque.libro?.entrega_cercana ?? null;

  return (
    <section aria-label="Lo único de ahora" className="card foco-card">
      <Reloj minutos={minutos} hitoActual={hito.n} hitoTotal={hito.total} piel={piel} />
      <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
        <div className="label">{etiquetaDelBloque(bloque)}</div>
        <h1 className="display-xl">{tarea.titulo}</h1>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {entrega ? (
            <>
              <Chip punto="var(--dinero)">Entrega {fechaCorta(entrega.fecha)}</Chip>
              <Chip mono>{formatoMoneda(entrega.monto)}</Chip>
            </>
          ) : null}
          <Chip mono>{minutos}&apos; del bloque</Chip>
          {bloque.tarea.ultima_vez_min != null ? <Chip mono>la última vez: {formatoDuracion(bloque.tarea.ultima_vez_min)}</Chip> : null}
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginTop: 6 }}>
          <button type="button" className="btn btn-brasa" onClick={onFoco}>Modo foco</button>
          <button type="button" className="btn btn-secundario" aria-expanded={pasoVisible} onClick={() => setPasoVisible((v) => !v)}>Paso mínimo</button>
          {/* B4.5: ya no es la acción principal de Hoy — Al día cierra solo
              con evidencia; esto sigue disponible para cuando hace falta. */}
          <button type="button" className="btn btn-secundario" disabled={cerrando} onClick={onCerrar}>Cerrar hito a mano</button>
        </div>
        {/* Ley 3: lo que no arranca se encoge. */}
        {pasoVisible ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div className="label">Paso mínimo · lo más chico que mueve esto</div>
            <p className="voz">{tarea.paso_minimo}</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function vozDeLaPropuesta(propuesta: Propuesta): string {
  if (propuesta.entrega) {
    return `¿Qué es lo único de hoy? Por orden, la entrega de ${propuesta.entrega.cliente} va primero: ${venceTexto(propuesta.entrega.fecha)} y trae ${formatoMoneda(propuesta.entrega.monto)}.`;
  }
  return `¿Qué es lo único de hoy? Por orden sigue ${propuesta.proyecto}: ${propuesta.hito ? propuesta.hito.texto.toLowerCase() : "su próximo paso"}.`;
}

function SinNadaAbierto({ propuesta, onEmpezado }: { propuesta: Propuesta | null; onEmpezado: () => void }) {
  const [empezando, setEmpezando] = useState(false);

  async function empezar() {
    if (!propuesta) return;
    setEmpezando(true);
    try {
      await nucleo.abrirBloque(propuesta.titulo, propuesta.tema);
    } catch {
      // 409: ya había un bloque abierto. Recargar lo muestra tal cual está.
    } finally {
      setEmpezando(false);
      onEmpezado();
    }
  }

  return (
    <section aria-label="Nada abierto" className="card" style={{ padding: "48px 32px", display: "flex", flexDirection: "column", gap: 20, alignItems: "flex-start" }}>
      <div className="label">{diaDeLaSemana()} · nada abierto</div>
      <h1 className="display-xl" style={{ color: "var(--ink-muted)" }}>Nada abierto.</h1>
      {propuesta ? (
        <>
          <p className="voz">{vozDeLaPropuesta(propuesta)}</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {propuesta.entrega ? (
              <>
                <Chip punto="var(--dinero)">Entrega {fechaCorta(propuesta.entrega.fecha)}</Chip>
                <Chip mono>{formatoMoneda(propuesta.entrega.monto)}</Chip>
              </>
            ) : null}
            {propuesta.fase ? <Chip mono>{propuesta.fase}</Chip> : null}
            {propuesta.hito ? <Chip mono>hito {propuesta.hito.n} de {propuesta.hito.total}</Chip> : null}
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button type="button" className="btn btn-brasa" disabled={empezando} onClick={empezar}>Empezar con eso</button>
            <a href="/proyectos" className="btn btn-secundario">Otra cosa</a>
          </div>
        </>
      ) : (
        <p className="voz">No hay una entrega con fecha cerca. Elige algo y empieza — la próxima vez Remi lo recuerda.</p>
      )}
    </section>
  );
}

// Dónde nace cada chispa y hacia dónde sube: ocho, como en el playground de
// la Biblia. Solo se animan con `prefers-reduced-motion: no-preference`.
const CHISPAS: { left: number; top: number; dx: number; dy: number; espera: number }[] = [
  { left: 150, top: 96, dx: -26, dy: -58, espera: 0 },
  { left: 190, top: 88, dx: -10, dy: -72, espera: 60 },
  { left: 230, top: 100, dx: 8, dy: -64, espera: 120 },
  { left: 120, top: 110, dx: 24, dy: -52, espera: 50 },
  { left: 260, top: 104, dx: -38, dy: -40, espera: 140 },
  { left: 205, top: 120, dx: 38, dy: -42, espera: 100 },
  { left: 170, top: 128, dx: -18, dy: -84, espera: 180 },
  { left: 95, top: 116, dx: 16, dy: -88, espera: 200 },
];

function PantallaCerrado({ cerrado, celebrando }: {
  cerrado: { voz: string; minutos: number; etiqueta: string; hito: { n: number; total: number } };
  celebrando: boolean;
}) {
  return (
    <section
      aria-label="Hito cerrado"
      className={`card foco-card ${celebrando ? "celebrando" : ""}`}
      style={{ overflow: "hidden", background: "var(--luz)", borderColor: "var(--luz)", color: "var(--on-luz)" }}
    >
      {CHISPAS.map((c, i) => (
        <i
          key={i}
          aria-hidden
          className="chispa"
          style={{ left: c.left, top: c.top, "--dx": `${c.dx}px`, "--dy": `${c.dy}px`, animationDelay: `${c.espera}ms` } as CSSProperties}
        />
      ))}
      <Reloj minutos={cerrado.minutos} hitoActual={cerrado.hito.n} hitoTotal={cerrado.hito.total} piel="instrumento" cerrado />
      <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
        <div className="label" style={{ color: "var(--on-luz)", opacity: 0.75 }}>{cerrado.etiqueta}</div>
        <p className="voz-grande" style={{ color: "var(--on-luz)" }}>{cerrado.voz}</p>
        <p className="voz" style={{ color: "var(--on-luz)", opacity: 0.75 }}>Eso tomó {formatoDuracion(cerrado.minutos)}. Lo anoto para la próxima.</p>
      </div>
    </section>
  );
}

function ListaDeCierre({ cliente, setCliente, copiado, onCopiar }: {
  cliente: string; setCliente: (v: string) => void; copiado: boolean; onCopiar: () => void;
}) {
  return (
    <section className="card">
      <div className="label">Lista de cierre · Remi la llena, tú decides</div>
      <div style={{ marginTop: 12 }}>
        <div className="fila">
          <span aria-hidden style={{ width: 20, height: 20, borderRadius: 6, flex: "none", display: "grid", placeContent: "center", background: "var(--luz)", border: "1.5px solid var(--luz)", color: "var(--on-luz)", fontFamily: "var(--font-mono)", fontSize: 12 }}>✓</span>
          <span style={{ flexGrow: 1 }}>Commit hecho</span>
          <span className="mono-sm">hook</span>
        </div>
        <div className="fila">
          <span aria-hidden style={{ width: 20, height: 20, borderRadius: 6, flex: "none", display: "grid", placeContent: "center", background: "var(--luz)", border: "1.5px solid var(--luz)", color: "var(--on-luz)", fontFamily: "var(--font-mono)", fontSize: 12 }}>✓</span>
          <span style={{ flexGrow: 1 }}>Estado del libro actualizado</span>
        </div>
        <div className="fila" style={{ gap: 8, flexWrap: "wrap" }}>
          <span aria-hidden style={{ width: 20, height: 20, borderRadius: 6, flex: "none", border: "1.5px solid var(--ink-muted)" }} />
          <input
            value={cliente}
            onChange={(e) => setCliente(e.target.value)}
            placeholder="¿a quién avisas?"
            aria-label="Cliente a avisar"
            className="btn-secundario"
            style={{ flexGrow: 1, minWidth: 140, height: 40, borderRadius: "var(--radius-pill)", padding: "0 14px", border: "1px solid var(--line)", background: "var(--surface-2)", color: "var(--ink)" }}
          />
          <button type="button" className="btn btn-secundario" style={{ height: 40 }} onClick={onCopiar} disabled={!cliente.trim()}>
            {copiado ? "Copiado" : "Copiar mensaje en mi voz"}
          </button>
        </div>
      </div>
      <p className="body-muted" style={{ marginTop: 14 }}>Remi redacta; nunca envía.</p>
    </section>
  );
}

function LoQueSigue({ siguiente, onSiguiente }: { siguiente: TareaConHistorial | null; onSiguiente: () => void }) {
  return (
    <section className="card">
      <div className="label">Lo que sigue</div>
      <div style={{ marginTop: 12 }}>
        {siguiente ? (
          <div className="fila">
            <i className="punto" style={{ background: "var(--brasa)" }} />
            <span style={{ flexGrow: 1 }}>{siguiente.tarea.titulo}</span>
            {siguiente.tarea.hora ? <span className="mono-sm">{formatoHora(siguiente.tarea.hora)}</span> : null}
          </div>
        ) : (
          <p className="body-muted">Nada más anotado para hoy.</p>
        )}
      </div>
      <div style={{ marginTop: 16, display: "flex", gap: 10, flexWrap: "wrap" }}>
        <button type="button" className="btn btn-brasa" onClick={onSiguiente}>Empezar el siguiente</button>
        <button type="button" className="btn btn-secundario" onClick={onSiguiente}>Respirar 10 min</button>
      </div>
    </section>
  );
}

function ListaDemasHoy({ tareas, manana }: { tareas: TareaConHistorial[]; manana: Tarea[] }) {
  const asoma = manana[0] ?? null;
  return (
    <section className="card" aria-label="Además hoy">
      <div className="label">Después, si queda tiempo · máximo tres</div>
      <div style={{ marginTop: 12 }}>
        {tareas.length === 0 && !asoma ? (
          <p className="body-muted" style={{ marginTop: 12 }}>Nada más por hoy.</p>
        ) : null}
        {tareas.map((t) => (
          <div key={t.tarea.id} className="fila">
            <i className="punto" style={{ background: "var(--brasa)" }} />
            <span style={{ flexGrow: 1 }}>{t.tarea.titulo}</span>
            {t.tarea.hora ? <span className="mono-sm">{formatoHora(t.tarea.hora)}</span> : null}
          </div>
        ))}
        {/* Lo de mañana solo asoma: un punto vacío, sin hora que apure. */}
        {asoma ? (
          <div className="fila">
            <i className="punto" style={{ background: "transparent", border: "1px solid var(--ink-faint)" }} />
            <span style={{ flexGrow: 1 }}>Mañana asoma: {asoma.titulo}</span>
            <span className="mono-sm">{asoma.hora ? formatoHora(asoma.hora) : "—"}</span>
          </div>
        ) : null}
      </div>
    </section>
  );
}

// Dinero para lo que trae plata, alerta solo cuando el día llegó, y en voz
// baja todo lo demás. El rojo habla de tiempo; nunca cuenta días.
function colorDe(v: Vencimiento): { punto: string; texto: string } {
  if (v.vence_hoy) return { punto: "var(--alerta)", texto: "var(--alerta)" };
  if (v.monto != null) return { punto: "var(--dinero)", texto: "var(--dinero)" };
  return { punto: "var(--baja)", texto: "var(--ink-muted)" };
}

function ListaVence({ agenda }: { agenda: AgendaDeHoy }) {
  return (
    <section className="card" aria-label="Vence">
      <div className="label">Vence</div>
      <div style={{ marginTop: 12 }}>
        {agenda.vence.length === 0 ? (
          <p className="body-muted">Nada con fecha por ahora.</p>
        ) : (
          agenda.vence.map((v, i) => {
            const color = colorDe(v);
            return (
              <div className="fila" key={`${v.titulo}-${i}`}>
                <i className="punto" style={{ background: color.punto }} />
                <span style={{ flexGrow: 1 }}>{v.titulo}</span>
                <span className="mono-sm" style={{ color: color.texto, whiteSpace: "nowrap" }}>
                  {fechaCorta(v.fecha)}{v.monto != null ? ` · ${formatoMoneda(v.monto)}` : ""}
                </span>
              </div>
            );
          })
        )}
      </div>
      <p className="body-muted" style={{ marginTop: 14 }}>El rojo solo habla de tiempo. Nunca de ti.</p>
    </section>
  );
}

function IdeasFrias({ cuantas, revision }: { cuantas: number; revision: RevisionFria | null }) {
  const cuando = cuandoEsLaRevision(revision);
  const frase = cuantas === 1 ? "1 idea fría espera la revisión" : `${cuantas} ideas frías esperan la revisión`;
  return (
    <a href="/bandeja" style={{ display: "flex", alignItems: "center", gap: 12, minHeight: 44, padding: "8px 4px" }} className="body-muted">
      <i className="punto" style={{ background: "var(--pensar)", boxShadow: "var(--glow-pensar)" }} />
      <span style={{ flexGrow: 1 }}>{frase}{cuando ? ` · ${cuando}` : ""}</span>
      <span className="mono-sm">ver →</span>
    </a>
  );
}
