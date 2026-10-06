"use client";
// Rumbo (R1.5): «¿a dónde voy y por qué esto primero?». Arriba, la
// escalera (un escalón por estado, nunca relleno de tarjeta); después la
// meta, si ya existe. «Contar mi visión» abre un flujo de voz y texto
// (R1.2): Remi propone una meta y SOLO se confirma con el sí explícito —
// nunca cambia sola (Biblia, «Cómo entra la visión»). El punto de partida
// vive aparte, en /rumbo/partida.
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { Bionica } from "@/components/Bionica";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado, type EscalonVista, type PropuestaVisionVista, type VistaRumbo } from "@/lib/nucleo";

async function cargarRumbo() {
  return nucleo.rumbo();
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

        <Escalera escalera={datos.escalera} />
        <Meta datos={datos} onCambio={recargar} />

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
