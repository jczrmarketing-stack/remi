"use client";
import { useEffect, useMemo, useState } from "react";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { Chip } from "@/components/Chip";
import { MoneyRow } from "@/components/MoneyRow";
import { NudgeCard } from "@/components/NudgeCard";
import { Reloj } from "@/components/Reloj";
import { Bionica } from "@/components/Bionica";
import { usePreferencias } from "@/hooks/PreferenciasContext";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { cargarHoy, formatoDuracion, formatoMoneda, minutosDesde } from "@/lib/hoy";
import { nucleo, NucleoApagado } from "@/lib/nucleo";

const MINUTOS_PARA_FOCO = 20;

export default function PaginaHoy() {
  const { prefs } = usePreferencias();
  const { datos, error, recargar } = useCargaNucleo(cargarHoy);
  const [ahoraMs, setAhoraMs] = useState(() => Date.now());
  const [foco, setFoco] = useState(false);
  const [celebrando, setCelebrando] = useState(false);
  const [cerrado, setCerrado] = useState<{ voz: string; minutos: number } | null>(null);
  const [cerrando, setCerrando] = useState(false);
  const [cliente, setCliente] = useState("");
  const [copiado, setCopiado] = useState(false);

  async function copiarMensaje() {
    if (!cliente.trim()) return;
    const respuesta = await nucleo.leerParaCliente(`me escribió ${cliente}: avisale que cerré este hito`);
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
    setCerrando(true);
    try {
      const respuesta = await nucleo.cerrarBloque();
      setCelebrando(true);
      setTimeout(() => setCelebrando(false), 900);
      setCerrado({ voz: respuesta.voz, minutos });
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
    return (
      <div className="shell" style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 24, textAlign: "center" }}>
        <div className="label">{datos.bloque.tema ?? "Hoy"} · una sola cosa</div>
        <p className="voz" style={{ color: "var(--ink-muted)", fontSize: 26, lineHeight: "27px" }}>{tarea.titulo}</p>
        <div className="num-lg" style={{ fontSize: 96, lineHeight: "96px", color: "var(--dinero)" }}>
          {String(Math.floor(minutos / 60)).padStart(2, "0")}:{String(minutos % 60).padStart(2, "0")}:00
        </div>
        <div className="mono-sm">
          la última vez: <span style={{ color: "var(--dinero)" }}>{datos.bloque.tarea.ultima_vez_min != null ? formatoDuracion(datos.bloque.tarea.ultima_vez_min) : "sin dato"}</span>
        </div>
        <div style={{ width: 320, height: 1, background: "var(--line)", margin: "16px 0" }} />
        {siguiente ? (
          <p className="body-muted" style={{ maxWidth: "46ch" }}>
            Después: <span style={{ color: "var(--ink)" }}>{siguiente.tarea.titulo}</span>. Nada más existe hasta entonces.
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

        {cerrado ? (
          <PantallaCerrado voz={cerrado.voz} minutos={cerrado.minutos} celebrando={celebrando} />
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
          <SinNadaAbierto plata={datos.plata} />
        )}

        {!cerrado && datos.nudge ? <NudgeCard nudge={datos.nudge} onRespondido={recargar} /> : null}

        {cerrado ? (
          <div className="card-grid-2">
            <ListaDeCierre cliente={cliente} setCliente={setCliente} copiado={copiado} onCopiar={copiarMensaje} />
            <LoQueSigue siguiente={datos.demasHoy[0] ?? null} onSiguiente={() => { setCerrado(null); recargar(); }} />
          </div>
        ) : (
          <div className="card-grid-2">
            <ListaDemasHoy tareas={datos.demasHoy} />
            <ListaVence plata={datos.plata} />
          </div>
        )}

        {datos.ideasFrias.length > 0 ? (
          <a href="/bandeja" style={{ display: "flex", alignItems: "center", gap: 12, minHeight: 44, padding: "8px 4px" }} className="body-muted">
            <i className="punto" style={{ background: "var(--pensar)", boxShadow: "var(--glow-pensar)" }} />
            <span style={{ flexGrow: 1 }}>{datos.ideasFrias.length} ideas frías esperan la revisión</span>
            <span className="mono-sm">ver →</span>
          </a>
        ) : null}

        <p className="body-txt" style={{ maxWidth: "72ch" }}>
          <Bionica texto="Remi ordena el día así: entregas con dinero, luego bugs en producción, luego propuestas, mejoras e ideas. Una locura por pantalla; lo demás, en voz baja." />
        </p>
      </div>
      <TabBar />
    </div>
  );
}

function BloqueActivo({ bloque, minutos, piel, cerrando, onCerrar, onFoco }: {
  bloque: NonNullable<import("@/lib/hoy").DatosHoy["bloque"]>;
  minutos: number;
  piel: import("@/hooks/PreferenciasContext").PielReloj;
  cerrando: boolean;
  onCerrar: () => void;
  onFoco: () => void;
}) {
  const tarea = bloque.tarea.tarea;
  const hitoTotal = bloque.camino?.hitos.length ?? 1;
  // JSON.parse no conserva identidad de objeto: comparar `siguiente` por
  // referencia contra `hitos` siempre da -1. Se busca por `hecho`.
  const hitoActual = bloque.camino ? bloque.camino.hitos.findIndex((h) => !h.hecho) + 1 || hitoTotal : 1;

  return (
    <section aria-label="Lo único de ahora" className="card" style={{ position: "relative", padding: 32, display: "grid", gridTemplateColumns: "168px minmax(0, 1fr)", gap: 32, alignItems: "center" }}>
      <Reloj minutos={minutos} hitoActual={hitoActual} hitoTotal={hitoTotal} piel={piel} />
      <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
        <div className="label">{bloque.tema ?? "Hoy"}</div>
        <h1 className="display-xl">{tarea.titulo}</h1>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Chip mono>{minutos}&apos; del bloque</Chip>
          {bloque.tarea.ultima_vez_min != null ? <Chip mono>la última vez: {formatoDuracion(bloque.tarea.ultima_vez_min)}</Chip> : null}
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 6 }}>
          <button type="button" className="btn btn-luz" disabled={cerrando} onClick={onCerrar}>Cerrar hito</button>
          <button type="button" className="btn btn-secundario" onClick={onFoco}>Modo foco</button>
        </div>
      </div>
    </section>
  );
}

function SinNadaAbierto({ plata }: { plata: import("@/lib/nucleo").Plata }) {
  async function empezar() {
    if (!plata.proximo) return;
    await nucleo.cerrarBloque().catch(() => undefined); // por si quedó algo colgado
    await fetch(`${(await import("@/config")).URL_NUCLEO}/mensaje`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto: `entrega de ${plata.proximo.cliente}` }),
    });
    location.reload();
  }
  return (
    <section aria-label="Nada abierto" className="card" style={{ padding: "48px 32px", display: "flex", flexDirection: "column", gap: 20, alignItems: "flex-start" }}>
      <div className="label">Nada abierto</div>
      <h1 className="display-xl" style={{ color: "var(--ink-muted)" }}>Nada abierto.</h1>
      {plata.proximo ? (
        <>
          <p className="voz">
            <Bionica texto={`¿Qué es lo único de hoy? Por orden, la entrega de ${plata.proximo.cliente} va primero: trae ${formatoMoneda(plata.proximo.monto)}.`} />
          </p>
          <div style={{ display: "flex", gap: 10 }}>
            <button type="button" className="btn btn-brasa" onClick={empezar}>Empezar con eso</button>
            <button type="button" className="btn btn-secundario">Otra cosa</button>
          </div>
        </>
      ) : (
        <p className="voz">No hay una entrega con fecha cerca. Elegí algo y empezá — la próxima vez Remi lo recuerda.</p>
      )}
    </section>
  );
}

function PantallaCerrado({ voz, minutos, celebrando }: {
  voz: string; minutos: number; celebrando: boolean;
}) {
  return (
    <section
      aria-label="Hito cerrado"
      className="card"
      style={{
        position: "relative", overflow: "hidden", padding: 32, display: "grid", gridTemplateColumns: "168px minmax(0, 1fr)", gap: 32, alignItems: "center",
        background: "var(--luz)", borderColor: "var(--luz)", color: "var(--on-luz)",
        transition: "background 900ms, color 900ms",
        opacity: celebrando ? 1 : 1,
      }}
    >
      <Reloj minutos={minutos} hitoActual={1} hitoTotal={1} piel="instrumento" cerrado />
      <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
        <p className="voz-grande" style={{ color: "var(--on-luz)" }}>{voz}</p>
        <p className="voz" style={{ color: "var(--on-luz)", opacity: 0.75 }}>Eso tomó {formatoDuracion(minutos)}. Lo anoto para la próxima.</p>
      </div>
    </section>
  );
}

function ListaDeCierre({ cliente, setCliente, copiado, onCopiar }: {
  cliente: string; setCliente: (v: string) => void; copiado: boolean; onCopiar: () => void;
}) {
  return (
    <section className="card">
      <div className="label">Lista de cierre · Remi la llena, vos decidís</div>
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
            placeholder="¿a quién avisás?"
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

function LoQueSigue({ siguiente, onSiguiente }: { siguiente: import("@/lib/nucleo").TareaConHistorial | null; onSiguiente: () => void }) {
  return (
    <section className="card">
      <div className="label">Lo que sigue</div>
      <div style={{ marginTop: 12 }}>
        {siguiente ? (
          <div className="fila">
            <i className="punto" style={{ background: "var(--brasa)" }} />
            <span style={{ flexGrow: 1 }}>{siguiente.tarea.titulo}</span>
          </div>
        ) : (
          <p className="body-muted">Nada más anotado para hoy.</p>
        )}
      </div>
      <div style={{ marginTop: 16, display: "flex", gap: 10 }}>
        <button type="button" className="btn btn-brasa" onClick={onSiguiente}>Empezar el siguiente</button>
        <button type="button" className="btn btn-secundario" onClick={onSiguiente}>Respirar 10 min</button>
      </div>
    </section>
  );
}

function ListaDemasHoy({ tareas }: { tareas: import("@/lib/nucleo").TareaConHistorial[] }) {
  return (
    <section className="card">
      <div className="label">Además hoy · máximo tres</div>
      <div style={{ marginTop: 12 }}>
        {tareas.length === 0 ? (
          <p className="body-muted" style={{ marginTop: 12 }}>Nada más por hoy.</p>
        ) : (
          tareas.map((t) => (
            <div key={t.tarea.id} className="fila">
              <i className="punto" style={{ background: "var(--brasa)" }} />
              <span style={{ flexGrow: 1 }}>{t.tarea.titulo}</span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function ListaVence({ plata }: { plata: import("@/lib/nucleo").Plata }) {
  return (
    <section className="card">
      <div className="label">Vence</div>
      <div style={{ marginTop: 12 }}>
        {plata.proximo ? (
          <div className="fila">
            <i className="punto" style={{ background: "var(--dinero)" }} />
            <span style={{ flexGrow: 1 }}>Entrega {plata.proximo.cliente}</span>
            <span className="mono-sm" style={{ color: "var(--dinero)" }}>{formatoMoneda(plata.proximo.monto)}</span>
          </div>
        ) : (
          <p className="body-muted">Nada con fecha por ahora.</p>
        )}
      </div>
      <p className="body-muted" style={{ marginTop: 14 }}>El rojo solo habla de tiempo. Nunca de vos.</p>
    </section>
  );
}
