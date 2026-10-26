"use client";
// Coding · la bóveda delante, Claude Max detrás. Una sola locura: la tarea.
// Al empezar se abre un bloque con tema "coding" (así la ley 1 mide cuánto
// tomó) y el núcleo corre bóveda → spec → builder → revisor por `claude -p`.
// El builder propone un diff; aplicarlo es de Juan Camilo. Debajo, la
// bóveda: buscar y las últimas lecciones de coding.
import { useEffect, useState, type FormEvent } from "react";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { Bionica } from "@/components/Bionica";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado, type CorridaCoding, type EstadoCorrida, type LeccionVista } from "@/lib/nucleo";

const PASOS: { estado: EstadoCorrida; texto: string }[] = [
  { estado: "consultando", texto: "bóveda" },
  { estado: "spec", texto: "spec" },
  { estado: "builder", texto: "builder" },
  { estado: "revisor", texto: "revisor" },
];
const TERMINADA: EstadoCorrida[] = ["aprobado", "rechazado", "fallo"];
const CADA_MS = 3000;

async function cargarCoding() {
  const [estado, ultimas] = await Promise.all([nucleo.codingEstado(), nucleo.codingLecciones()]);
  return { estado, ultimas };
}

export default function PaginaCoding() {
  const { datos, error, recargar } = useCargaNucleo(cargarCoding);
  const [corrida, setCorrida] = useState<CorridaCoding | null>(null);

  // Si el panel se abre con una corrida ya en marcha, la retoma.
  const enCurso = datos?.estado.corrida_en_curso ?? null;
  useEffect(() => {
    if (enCurso && !corrida) nucleo.codingCorrida(enCurso).then(setCorrida).catch(() => undefined);
  }, [enCurso, corrida]);

  // Mientras corre, pregunta cada 3 s. Al terminar, recarga la bóveda: puede
  // haber una lección nueva.
  useEffect(() => {
    if (!corrida || TERMINADA.includes(corrida.estado)) return;
    const reloj = setTimeout(() => {
      nucleo
        .codingCorrida(corrida.id)
        .then((siguiente) => {
          setCorrida(siguiente);
          if (TERMINADA.includes(siguiente.estado)) recargar();
        })
        .catch(() => undefined);
    }, CADA_MS);
    return () => clearTimeout(reloj);
  }, [corrida, recargar]);

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

  const { estado } = datos;

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "8px 16px", flexWrap: "wrap", paddingTop: 8 }}>
          <h1 className="display-xl" style={{ fontSize: 40, lineHeight: "42px" }}>Coding</h1>
          <span className="chip chip-mono" aria-label="Motor y bóveda">
            <i className="chip-punto" style={{ background: "var(--pensar)" }} />
            Usando Claude Max + bóveda (ahorro de tokens) · {estado.lecciones_en_boveda}
          </span>
        </div>

        {corrida ? (
          <Corrida corrida={corrida} onOtra={() => setCorrida(null)} />
        ) : (
          <NuevaTarea onEmpezo={setCorrida} />
        )}

        <Boveda ultimas={datos.ultimas} />

        <p className="voz"><Bionica texto="Primero miro lo que ya aprendimos. Así Claude no lo busca dos veces." /></p>
        <p className="body-muted">
          Spec, builder y revisor van por tu sesión de Max (claude -p): sin clave, sin cobro aparte; OpenRouter y Venice no tocan código. Antes de cada llamada entra lo que la bóveda ya sabe. Si el revisor encuentra un error o un acierto nuevo, queda guardado.
        </p>
      </div>
      <TabBar />
    </div>
  );
}

function NuevaTarea({ onEmpezo }: { onEmpezo: (c: CorridaCoding) => void }) {
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  async function empezar(evento: FormEvent) {
    evento.preventDefault();
    const tarea = texto.trim();
    if (!tarea) return;
    setEnviando(true);
    setAviso(null);
    try {
      await nucleo.abrirBloque(tarea, "coding");
    } catch (e) {
      setEnviando(false);
      setAviso(e instanceof NucleoApagado && e.status === 409 ? "Ya hay un bloque abierto. Ciérralo y vuelvo aquí contigo." : "No pude abrir el bloque.");
      return;
    }
    try {
      onEmpezo(await nucleo.codingCorrer(tarea));
    } catch (e) {
      setAviso(e instanceof NucleoApagado && e.status === 409 ? "Ya estoy en otra tarea de código. Termino y sigo." : "No pude empezar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="card" aria-label="Nueva tarea de código">
      <div className="label">Nueva tarea</div>
      <form onSubmit={empezar} style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="¿qué hay que construir o arreglar?"
          aria-label="Tarea de código"
          style={{ flexGrow: 1, minWidth: 200, height: 44, borderRadius: "var(--radius-pill)", padding: "0 16px", border: "1px solid var(--line)", background: "var(--surface-2)", color: "var(--ink)" }}
        />
        <button type="submit" className="btn btn-brasa" disabled={enviando || !texto.trim()}>
          {enviando ? "Abriendo…" : "Empezar"}
        </button>
      </form>
      {aviso ? <p className="voz" style={{ marginTop: 14, fontSize: 20, lineHeight: "24px" }}>{aviso}</p> : null}
    </section>
  );
}

function Corrida({ corrida, onOtra }: { corrida: CorridaCoding; onOtra: () => void }) {
  const terminada = TERMINADA.includes(corrida.estado);
  const actual = PASOS.findIndex((p) => p.estado === corrida.estado);
  const tono = corrida.estado === "aprobado" ? "var(--luz)" : corrida.estado === "rechazado" ? "var(--brasa)" : "var(--ink-muted)";

  return (
    <section className="card" aria-label="Tarea en curso" aria-live="polite">
      <div className="label">{terminada ? "Terminó" : "Trabajando"}</div>
      <div className="body-txt" style={{ marginTop: 8 }}>{corrida.tarea}</div>

      <ol aria-label="Pasos" style={{ display: "flex", gap: 16, flexWrap: "wrap", listStyle: "none", padding: 0, margin: "14px 0 0" }}>
        {PASOS.map((paso, i) => {
          const hecho = terminada || i < actual;
          const ahora = !terminada && i === actual;
          return (
            <li key={paso.estado} className="mono-sm" style={{ display: "inline-flex", alignItems: "center", gap: 6, color: ahora ? "var(--ink)" : undefined }}>
              <i className="punto" style={{ background: ahora ? "var(--pensar)" : hecho ? "var(--ink-muted)" : "var(--line)" }} />
              {paso.texto}
            </li>
          );
        })}
      </ol>

      <p className="mono-sm" style={{ marginTop: 12 }}>
        {corrida.lecciones.length
          ? `${corrida.lecciones.length} lección${corrida.lecciones.length === 1 ? "" : "es"} de la bóveda en el prompt`
          : "la bóveda no tenía nada sobre esto"}
        {corrida.tokens ? ` · ${corrida.tokens.toLocaleString("es-CO")} tokens` : ""}
        {corrida.segundos != null ? ` · ${Math.max(1, Math.round(corrida.segundos / 60))} min` : ""}
      </p>
      {corrida.lecciones.length ? (
        <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
          {corrida.lecciones.map((t) => <li key={t} className="body-muted">{t}</li>)}
        </ul>
      ) : null}

      {terminada ? (
        <div style={{ marginTop: 16, borderLeft: `2px solid ${tono}`, paddingLeft: 12 }}>
          <div className="body-txt">{corrida.estado === "aprobado" ? "El revisor lo aprobó." : corrida.estado === "rechazado" ? "El revisor pidió otra vuelta." : "Se detuvo."}</div>
          {corrida.motivo ? <p className="body-muted" style={{ margin: "4px 0 0" }}>{corrida.motivo}</p> : null}
          {corrida.leccion_guardada ? <p className="mono-sm" style={{ marginTop: 6 }}>lección nueva en la bóveda · {corrida.leccion_guardada}</p> : null}
        </div>
      ) : null}

      {corrida.spec ? <Desplegable titulo="Spec" texto={corrida.spec} /> : null}
      {corrida.cambio ? <Desplegable titulo="Cambio propuesto (diff, sin aplicar)" texto={corrida.cambio} /> : null}

      {terminada ? (
        <button type="button" className="btn btn-secundario" style={{ marginTop: 16 }} onClick={onOtra}>Otra tarea</button>
      ) : null}
    </section>
  );
}

function Desplegable({ titulo, texto }: { titulo: string; texto: string }) {
  return (
    <details style={{ marginTop: 12, borderTop: "1px solid var(--line)", paddingTop: 10 }}>
      <summary className="mono-sm" style={{ cursor: "pointer" }}>{titulo}</summary>
      <pre style={{ margin: "10px 0 0", whiteSpace: "pre-wrap", overflowWrap: "anywhere", fontFamily: "var(--font-mono)", fontSize: 12, lineHeight: "18px", color: "var(--ink)" }}>{texto}</pre>
    </details>
  );
}

function Boveda({ ultimas }: { ultimas: LeccionVista[] }) {
  const [q, setQ] = useState("");
  const [encontradas, setEncontradas] = useState<LeccionVista[] | null>(null);
  const [buscando, setBuscando] = useState(false);

  async function buscar(evento: FormEvent) {
    evento.preventDefault();
    if (!q.trim()) {
      setEncontradas(null);
      return;
    }
    setBuscando(true);
    try {
      setEncontradas(await nucleo.codingLecciones(q));
    } catch {
      setEncontradas([]);
    } finally {
      setBuscando(false);
    }
  }

  const lista = encontradas ?? ultimas;

  return (
    <section aria-label="Bóveda de lecciones" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <form onSubmit={buscar} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            if (!e.target.value.trim()) setEncontradas(null);
          }}
          placeholder="buscar en la bóveda"
          aria-label="Buscar en la bóveda"
          type="search"
          style={{ flexGrow: 1, minWidth: 180, height: 40, borderRadius: "var(--radius-pill)", padding: "0 14px", border: "1px solid var(--line)", background: "var(--surface)", color: "var(--ink)" }}
        />
        <button type="submit" className="btn btn-secundario" style={{ height: 40 }} disabled={buscando}>{buscando ? "…" : "Buscar"}</button>
      </form>
      <div className="label">{encontradas ? "Lo que encontré" : "Últimas lecciones de coding"}</div>
      {lista.length === 0 ? (
        <p className="body-muted">{encontradas ? "Nada sobre eso en la bóveda." : "Todavía no hay lecciones de coding."}</p>
      ) : (
        <div>
          {lista.map((l) => (
            <div key={`${l.titulo}-${l.ultima_vez}`} className="fila" style={{ alignItems: "flex-start" }}>
              <i className="punto" style={{ marginTop: 8, background: l.clase === "error" ? "var(--brasa)" : "var(--luz)" }} aria-label={l.clase} />
              <div style={{ minWidth: 0, flexGrow: 1 }}>
                <div className="body-txt">{l.titulo}</div>
                <div className="body-muted">{l.resumen}</div>
              </div>
              <span className="mono-sm" style={{ flex: "none" }}>{l.ultima_vez}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
