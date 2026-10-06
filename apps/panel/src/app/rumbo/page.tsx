"use client";
// Rumbo (R1.5): «¿a dónde voy y por qué esto primero?». Arriba, la
// escalera (un escalón por estado, nunca relleno de tarjeta); después la
// meta, si ya existe. «Contar mi visión» abre un flujo de voz y texto
// (R1.2): Remi propone una meta y SOLO se confirma con el sí explícito —
// nunca cambia sola (Biblia, «Cómo entra la visión»). El punto de partida
// vive aparte, en /rumbo/partida.
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { Bionica } from "@/components/Bionica";
import { Chip } from "@/components/Chip";
import { ProgressBar } from "@/components/ProgressBar";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import {
  nucleo,
  NucleoApagado,
  type ApuestaVista,
  type CaminoHoras,
  type EscalonVista,
  type PropuestaVisionVista,
  type VistaCuenta,
  type VistaRumbo,
} from "@/lib/nucleo";
import { fechaCorta } from "@/lib/formato";

async function cargarRumbo() {
  const [rumbo, cuenta, apuestas] = await Promise.all([nucleo.rumbo(), nucleo.rumboCuenta(), nucleo.rumboApuestas()]);
  return { rumbo, cuenta, apuestas };
}

export default function PaginaRumbo() {
  const { datos, error, recargar } = useCargaNucleo(cargarRumbo);

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
        <div className="contenedor"><p className="body-muted">Cargando…</p></div>
      </div>
    );
  }

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "8px 16px", flexWrap: "wrap", paddingTop: 8 }}>
          <h1 className="display-xl" style={{ fontSize: 40, lineHeight: "42px" }}>Rumbo</h1>
          <Link href="/rumbo/partida" className="btn btn-secundario">Ver el punto de partida</Link>
        </div>

        <Escalera escalera={datos.rumbo.escalera} />
        <Meta datos={datos.rumbo} onCambio={recargar} />
        <Cuenta cuenta={datos.cuenta} />
        <Apuestas apuestas={datos.apuestas} />
        <VerAnalisisDeCamino />

        <p className="voz"><Bionica texto="A dónde vas y por qué esto primero. La certeza sube con la evidencia, no con la confianza." /></p>
      </div>
      <TabBar />
    </div>
  );
}

// — La escalera: un escalón por estado, nunca relleno de tarjeta —

function colorDeEscalon(estado: EscalonVista["estado"]): { borde: string; fondo: string; texto: string; glow?: string; punteado?: boolean } {
  switch (estado) {
    case "conquistado":
      return { borde: "var(--luz)", fondo: "var(--luz)", texto: "var(--ink)" };
    case "ahora":
      return { borde: "var(--brasa)", fondo: "var(--brasa)", texto: "var(--ink)", glow: "var(--glow-brasa)" };
    case "sigue":
      return { borde: "var(--line)", fondo: "transparent", texto: "var(--ink)" };
    case "luego":
      return { borde: "var(--line)", fondo: "transparent", texto: "var(--ink-faint)" };
    case "norte":
      return { borde: "var(--ink-muted)", fondo: "transparent", texto: "var(--ink-muted)", punteado: true };
  }
}

function Escalera({ escalera }: { escalera: EscalonVista[] }) {
  if (escalera.length === 0) {
    return (
      <section aria-label="Escalera" className="card">
        <div className="label">Escalera</div>
        <p className="body-muted" style={{ margin: "8px 0 0" }}>Todavía no hay escalones. Cuenta tu visión para empezar.</p>
      </section>
    );
  }
  return (
    <section aria-label="Escalera" className="card">
      <div className="label">Escalera</div>
      <ol style={{ listStyle: "none", margin: "14px 0 0", padding: 0, display: "flex", overflowX: "auto", gap: 4 }}>
        {escalera.map((escalon) => {
          const color = colorDeEscalon(escalon.estado);
          return (
            <li
              key={escalon.n}
              aria-current={escalon.estado === "ahora" ? "step" : undefined}
              style={{ flex: "1 1 0", minWidth: 110, display: "flex", flexDirection: "column", alignItems: "center", gap: 8, padding: "0 4px" }}
            >
              <span
                aria-hidden
                style={{
                  width: 20, height: 20, borderRadius: "var(--radius-pill)",
                  background: color.fondo, border: `2px ${color.punteado ? "dashed" : "solid"} ${color.borde}`,
                  boxShadow: color.glow,
                }}
              />
              <span className="mono-sm" style={{ color: color.texto, textAlign: "center" }}>
                {escalon.estado === "norte" ? "norte" : escalon.texto}
              </span>
              <span className="body-muted" style={{ fontSize: 12, textAlign: "center" }}>{escalon.criterio}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

// — La meta, si ya existe, y el botón que abre el flujo de la visión —

function textoMeta(meta: VistaRumbo["meta"]): string | null {
  if (!meta) return null;
  const moneda = (v: number) => `$${Math.round(v).toLocaleString("es-CO")}`;
  const rango = meta.monto_min && meta.monto_max
    ? `${moneda(meta.monto_min)} a ${moneda(meta.monto_max)}/mes`
    : meta.monto_max
      ? `${moneda(meta.monto_max)}/mes`
      : meta.monto_min
        ? `${moneda(meta.monto_min)}/mes`
        : null;
  const partes = [rango, meta.meses_seguidos ? `${meta.meses_seguidos} meses seguidos` : null, meta.limites].filter(Boolean);
  return partes.length > 0 ? partes.join(" · ") : null;
}

function Meta({ datos, onCambio }: { datos: VistaRumbo; onCambio: () => void }) {
  const [abierto, setAbierto] = useState(false);
  const texto = textoMeta(datos.meta);

  return (
    <section aria-label="Meta" className="card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: "8px 16px", flexWrap: "wrap" }}>
        <div className="label">Meta</div>
        {!abierto ? (
          <button type="button" className="btn btn-brasa" onClick={() => setAbierto(true)}>Contar mi visión</button>
        ) : null}
      </div>
      {datos.vision ? <p className="body-muted" style={{ margin: 0 }}>Lo que contaste: «{datos.vision}»</p> : null}
      {texto ? <p className="body-txt" style={{ margin: 0, color: "var(--dinero)" }}>{texto}</p> : !abierto ? (
        <p className="body-muted" style={{ margin: 0 }}>Todavía no hay meta confirmada.</p>
      ) : null}
      {abierto ? <ContarVision onCerrar={() => setAbierto(false)} onCambio={onCambio} /> : null}
    </section>
  );
}

// — Contar la visión: hablando o escribiendo. Remi propone; la meta solo
//   cambia con el sí explícito. —

type VistaVision =
  | { modo: "escribiendo" }
  | { modo: "propuesta"; propuesta: PropuestaVisionVista; voz: string }
  | { modo: "confirmada"; voz: string };

function ContarVision({ onCerrar, onCambio }: { onCerrar: () => void; onCambio: () => void }) {
  const [vista, setVista] = useState<VistaVision>({ modo: "escribiendo" });
  const [texto, setTexto] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const [grabando, setGrabando] = useState(false);

  // Dictado opcional: solo donde el navegador lo ofrece (Safari/Chrome de
  // escritorio); sin tipos de DOM para la API todavía experimental, por
  // eso el `any` acotado a esta única función.
  function grabar() {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const Reconocedor = (window as any).webkitSpeechRecognition;
    if (!Reconocedor) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const r = new Reconocedor();
    r.lang = "es-CO";
    r.interimResults = false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    r.onresult = (e: any) => {
      const dicho = e.results?.[0]?.[0]?.transcript ?? "";
      setTexto((t) => (t ? `${t} ${dicho}` : dicho));
    };
    r.onend = () => setGrabando(false);
    r.onerror = () => setGrabando(false);
    setGrabando(true);
    r.start();
  }

  async function contar(evento: FormEvent) {
    evento.preventDefault();
    if (!texto.trim()) return;
    setOcupado(true);
    setAviso(null);
    try {
      const resultado = await nucleo.contarVision(texto.trim());
      setVista({ modo: "propuesta", propuesta: resultado.propuesta, voz: resultado.voz });
    } catch {
      setAviso("No pude mandarlo. Sigue escrito acá; vuelve a tocar «Contar» en un momento.");
    } finally {
      setOcupado(false);
    }
  }

  async function confirmar() {
    if (vista.modo !== "propuesta") return;
    setOcupado(true);
    setAviso(null);
    try {
      await nucleo.fijarMeta({ ...vista.propuesta, confirmada: true });
      setVista({ modo: "confirmada", voz: "Meta confirmada. Queda guardada." });
      onCambio();
    } catch {
      setAviso("No pude guardar la meta. Vuelve a tocar «Confirmar».");
    } finally {
      setOcupado(false);
    }
  }

  if (vista.modo === "confirmada") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <p className="voz" role="status"><Bionica texto={vista.voz} /></p>
        <button type="button" className="btn btn-secundario" style={{ width: "fit-content" }} onClick={onCerrar}>Cerrar</button>
      </div>
    );
  }

  if (vista.modo === "propuesta") {
    const p = vista.propuesta;
    const moneda = (v: number) => `$${Math.round(v).toLocaleString("es-CO")}`;
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <p className="voz" role="status"><Bionica texto={vista.voz} /></p>
        <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 4 }}>
          <li className="body-muted">Rango: {p.monto_min ? moneda(p.monto_min) : "—"} a {p.monto_max ? moneda(p.monto_max) : "—"} /mes</li>
          <li className="body-muted">Meses seguidos: {p.meses_seguidos ?? "—"}</li>
          <li className="body-muted">Límites: {p.limites ?? "—"}</li>
        </ul>
        {aviso ? <p className="body-muted" role="status" style={{ color: "var(--ink)" }}>{aviso}</p> : null}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button type="button" className="btn btn-luz" disabled={ocupado} onClick={confirmar}>Confirmar meta</button>
          <button type="button" className="btn btn-secundario" disabled={ocupado} onClick={() => setVista({ modo: "escribiendo" })}>Volver a contarla</button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={contar} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <textarea
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        placeholder="Cuánto quieres al mes, por cuánto tiempo, qué es «estable» y qué límites hay."
        rows={3}
        className="vision-campo"
        aria-label="Cuenta tu visión"
      />
      {aviso ? <p className="body-muted" role="status" style={{ color: "var(--ink)" }}>{aviso}</p> : null}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <button type="submit" className="btn btn-brasa" disabled={ocupado || !texto.trim()}>Contar</button>
        <button type="button" className="btn btn-secundario" disabled={ocupado} onClick={grabar}>{grabando ? "Escuchando…" : "Hablar"}</button>
        <button type="button" className="btn btn-secundario" disabled={ocupado} onClick={onCerrar}>Cancelar</button>
      </div>
    </form>
  );
}

// — R2.5: la cuenta hacia atrás (forma R) y el reparto de horas de la
//   semana. Baja la meta a lo que se hace esta semana (Biblia, «La cuenta
//   hacia atrás»). —

function moneda(v: number): string {
  return `$${Math.round(v).toLocaleString("es-CO")}`;
}

const COLOR_DE_CAMINO = ["var(--dinero)", "var(--pensar)", "var(--brasa)", "var(--luz)", "var(--ink-muted)"];

function Cuenta({ cuenta }: { cuenta: VistaCuenta }) {
  const conMeta = cuenta.meta_mes !== null && cuenta.ticket !== null && cuenta.necesarias !== null;
  return (
    <section aria-label="Cuenta hacia atrás" className="card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="label">Cuenta hacia atrás</div>
      {conMeta ? (
        <div>
          <p className="body-txt" style={{ margin: 0 }}>
            Necesitas {cuenta.necesarias} mensualidad{cuenta.necesarias === 1 ? "" : "es"} de {moneda(cuenta.ticket!)} para {moneda(cuenta.meta_mes!)}/mes. Tienes {cuenta.tienes}.
          </p>
          <div style={{ marginTop: 8 }}>
            <ProgressBar pct={cuenta.necesarias! > 0 ? (cuenta.tienes / cuenta.necesarias!) * 100 : 0} etiqueta={`${cuenta.tienes} de ${cuenta.necesarias} mensualidades`} />
          </div>
        </div>
      ) : (
        <p className="body-muted" style={{ margin: 0 }}>Todavía no hay meta confirmada para calcular la cuenta.</p>
      )}
      <div>
        <p className="body-txt" style={{ margin: 0 }}>
          Esta semana: {cuenta.hechas_semana} de {cuenta.propuestas_semana} propuesta{cuenta.propuestas_semana === 1 ? "" : "s"}.
        </p>
        <div style={{ marginTop: 8 }}>
          <ProgressBar
            pct={cuenta.propuestas_semana > 0 ? (cuenta.hechas_semana / cuenta.propuestas_semana) * 100 : 0}
            color="var(--brasa)"
            etiqueta={`${cuenta.hechas_semana} de ${cuenta.propuestas_semana} propuestas de la semana`}
          />
        </div>
      </div>
      <p className="body-muted" style={{ margin: 0 }}>
        Cierras {Math.round(cuenta.cierre.p * 10)} de cada 10 propuestas, con {cuenta.cierre.origen === "propia" ? `tu propio dato (${cuenta.cierre.base_n})` : "el dato general"}.
      </p>
      {cuenta.horas_semana.length > 0 ? <HorasDeLaSemana horas={cuenta.horas_semana} /> : null}
    </section>
  );
}

function HorasDeLaSemana({ horas }: { horas: CaminoHoras[] }) {
  return (
    <div>
      <div className="label">Tus horas</div>
      <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 10 }}>
        {horas.map((h, i) => (
          <div key={h.camino} style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 8, alignItems: "baseline", fontSize: 14 }}>
            <span className="body-muted" style={{ color: "var(--ink)" }}>{h.camino}</span>
            <span className="mono-sm">{h.pct}%</span>
            <div style={{ gridColumn: "1 / -1" }}>
              <ProgressBar pct={h.pct} color={COLOR_DE_CAMINO[i % COLOR_DE_CAMINO.length]} etiqueta={`${h.camino}: ${h.pct}% de la semana`} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// — Apuestas (forma O): dos o tres pruebas de dos semanas, tope de horas y
//   plata, señal para seguir y para pausar, y en qué va el progreso. —

function Apuestas({ apuestas }: { apuestas: ApuestaVista[] }) {
  if (apuestas.length === 0) {
    return (
      <section aria-label="Apuestas" className="card">
        <div className="label">Apuestas</div>
        <p className="body-muted" style={{ margin: "8px 0 0" }}>Ninguna apuesta abierta todavía.</p>
      </section>
    );
  }
  return (
    <section aria-label="Apuestas" className="card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div className="label">Apuestas</div>
      {apuestas.map((a) => <FilaApuesta key={a.id} apuesta={a} />)}
    </section>
  );
}

function FilaApuesta({ apuesta }: { apuesta: ApuestaVista }) {
  const pct = apuesta.progreso.meta > 0 ? (apuesta.progreso.hecho / apuesta.progreso.meta) * 100 : 0;
  return (
    <div role="group" aria-label={apuesta.camino} style={{ display: "flex", flexDirection: "column", gap: 8, borderTop: "1px solid var(--line)", paddingTop: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: "6px 12px", flexWrap: "wrap" }}>
        <span className="body-txt">{apuesta.camino}</span>
        <span className="mono-sm">{fechaCorta(apuesta.inicio)} a {fechaCorta(apuesta.fin)}</span>
      </div>
      <ProgressBar pct={pct} etiqueta={`${apuesta.progreso.hecho} de ${apuesta.progreso.meta}`} />
      <div className="mono-sm">
        {apuesta.gastado_horas} de {apuesta.tope_horas} h
        {apuesta.tope_plata > 0 ? ` · ${moneda(apuesta.gastado_plata)} de ${moneda(apuesta.tope_plata)}` : ""}
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {apuesta.senal_sigue ? <Chip punto="var(--luz)">sigue</Chip> : null}
        {apuesta.senal_pausa ? <Chip punto="var(--ink-muted)">pausa</Chip> : null}
        {apuesta.resultado ? <Chip mono>{apuesta.resultado}</Chip> : null}
      </div>
    </div>
  );
}

// — R3.5: entrada a «el análisis de un camino» (/rumbo/caminos/[id]). El
//   núcleo todavía no expone una lista de caminos con análisis — mientras
//   no la tenga, se entra por el id de la idea (decisión sin preguntar,
//   anotada en la bitácora). —

function VerAnalisisDeCamino() {
  const router = useRouter();
  const [id, setId] = useState("");

  function ir(evento: FormEvent) {
    evento.preventDefault();
    if (!id.trim()) return;
    router.push(`/rumbo/caminos/${encodeURIComponent(id.trim())}`);
  }

  return (
    <section aria-label="Ver el análisis de un camino" className="card">
      <div className="label">El análisis de un camino</div>
      <form onSubmit={ir} className="pregunta-fila" style={{ marginTop: 10 }}>
        <input
          type="text"
          value={id}
          onChange={(e) => setId(e.target.value)}
          aria-label="Id del camino"
          placeholder="Id del camino"
          className="pregunta-campo"
        />
        <div className="pregunta-botones">
          <button type="submit" className="btn btn-secundario" disabled={!id.trim()}>Ver análisis</button>
        </div>
      </form>
    </section>
  );
}
