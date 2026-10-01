"use client";
// Revisión semanal: veinte minutos, cinco preguntas, una locura. Cada
// pregunta llega contestada con lo que el núcleo sabe (la plata por línea,
// lo cerrado y lo aplazado de la semana, las ideas frías, lo que Remi
// propone). Remi guía; la decisión es de quien la mira.
import { useEffect, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { Bionica } from "@/components/Bionica";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado, type IdeaBandeja, type Plata, type Semana } from "@/lib/nucleo";
import { formatoMoneda, proponer, type Propuesta } from "@/lib/hoy";
import { accionDeLaBrecha } from "@/lib/formato";

const VEINTE_MIN = 20 * 60;
const PASOS = 5;

async function cargarSemana() {
  const [plata, semana, bandeja, libros] = await Promise.all([nucleo.plata(), nucleo.semana(), nucleo.bandeja(), nucleo.libros()]);
  return { plata, semana, bandeja, propuesta: proponer(libros, plata) };
}

// «A, B y C».
function enumerar(partes: string[]): string {
  if (partes.length <= 1) return partes.join("");
  return `${partes.slice(0, -1).join(", ")} y ${partes[partes.length - 1]}`;
}

function laPlata(plata: Plata): string {
  const lineas = (plata.por_linea ?? []).map((l) => `${l.nombre.replace(/\s*\(.+\)\s*$/, "")} ${formatoMoneda(l.cobrado_mes)}`);
  const cabeza = lineas.length > 0 ? lineas.join(" · ") : `${formatoMoneda(plata.mes.cobrado)} de ${formatoMoneda(plata.mes.meta)}`;
  if (plata.mes.faltan <= 0) return `${cabeza}. Meta del mes cumplida.`;
  return `${cabeza} · brecha ${formatoMoneda(plata.mes.faltan)}. ¿Qué la cierra esta semana? ${accionDeLaBrecha(plata)}`;
}

// Hasta cinco títulos; si hay más, se dice cuántos sin listarlos todos.
function titulos(filas: { titulo: string }[]): string {
  const vistos = filas.slice(0, 5).map((f) => f.titulo);
  const resto = filas.length - vistos.length;
  return resto > 0 ? `${vistos.join(", ")} y ${resto} más` : enumerar(vistos);
}

// Una idea dictada puede ser un párrafo: acá alcanza con reconocerla.
function recortar(texto: string, tope = 48): string {
  const limpio = texto.trim().replace(/\s+/g, " ").replace(/[.,;:]+$/, "");
  if (limpio.length <= tope) return limpio;
  const corte = limpio.slice(0, tope);
  return `${corte.slice(0, Math.max(corte.lastIndexOf(" "), 24)).replace(/[.,;:]+$/, "")}…`;
}

function lasFrias(frias: IdeaBandeja[]): string {
  if (frias.length === 0) return "Ninguna lista para revisar todavía.";
  const primeras = enumerar(frias.slice(0, 3).map((f) => recortar(f.idea.texto)));
  const cabeza =
    frias.length === 1
      ? `Una lista para revisar: ${primeras}.`
      : frias.length <= 3
        ? `Listas para revisar: ${primeras}.`
        : `${frias.length} listas para revisar; las primeras: ${primeras}.`;
  return `${cabeza} Soltar, mantener o hacer tarea.`;
}

function loCerrado(semana: Semana | null): string {
  if (!semana) return "Lo que se terminó esta semana. Se celebra una vez y se pasa.";
  if (semana.cerrado.length === 0) return "Todavía nada cerrado esta semana.";
  return `${titulos(semana.cerrado)}. Se celebra una vez y se pasa.`;
}

function loAplazado(semana: Semana | null): string {
  if (!semana) return "Lo que no avanzó. Sin contador: se reprograma y ya.";
  if (semana.aplazado.length === 0) return "Nada aplazado esta semana.";
  return `${titulos(semana.aplazado)}. Sin contador: se reprograma${semana.aplazado.length === 1 ? "" : "n"} y ya.`;
}

function laLocura(propuesta: Propuesta | null): string {
  if (!propuesta) return "Una sola. La que más importa, dicha en voz baja.";
  return `Una sola. Remi propone: ${propuesta.titulo}.`;
}

export default function PaginaSemana() {
  const { datos, error, recargar } = useCargaNucleo(cargarSemana);
  const [segundos, setSegundos] = useState(VEINTE_MIN);
  const [corriendo, setCorriendo] = useState(false);
  const [paso, setPaso] = useState(1);

  useEffect(() => {
    if (!corriendo) return;
    const id = setInterval(() => setSegundos((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [corriendo]);

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

  const { plata, semana, bandeja, propuesta } = datos;
  const m = String(Math.floor(segundos / 60)).padStart(2, "0");
  const s = String(segundos % 60).padStart(2, "0");

  function siguiente() {
    setCorriendo(true);
    setPaso((p) => Math.min(PASOS, p + 1));
  }

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <section aria-label="Revisión semanal" className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: "8px 16px", flexWrap: "wrap" }}>
            <div className="label">Revisión semanal · lunes · 20 minutos</div>
            <button
              type="button"
              className="num-lg"
              style={{ fontSize: 40, color: "var(--dinero)", background: "transparent", border: 0, padding: 0 }}
              onClick={() => setCorriendo((c) => !c)}
              aria-label={corriendo ? `Pausar el reloj, quedan ${m}:${s}` : `Empezar el reloj, quedan ${m}:${s}`}
            >
              {m}:{s}
            </button>
          </div>
          <ol style={{ listStyle: "none", margin: "12px 0 0", padding: 0 }}>
            <Pregunta n={1} paso={paso} titulo="La plata del mes">
              <p className="body-muted" style={{ margin: "6px 0 0" }}>{laPlata(plata)}</p>
            </Pregunta>
            <Pregunta n={2} paso={paso} titulo="Lo cerrado">
              <p className="body-muted" style={{ margin: "6px 0 0" }}>{loCerrado(semana)}</p>
            </Pregunta>
            <Pregunta n={3} paso={paso} titulo="Lo aplazado">
              <p className="body-muted" style={{ margin: "6px 0 0" }}>{loAplazado(semana)}</p>
            </Pregunta>
            <Pregunta n={4} paso={paso} titulo="Ideas frías">
              <IdeasFrias bandeja={bandeja} sePuedeDestacar={semana !== null} onCambio={recargar} />
            </Pregunta>
            <Pregunta n={5} paso={paso} titulo="La locura de la semana">
              <p className="body-muted" style={{ margin: "6px 0 0" }}>
                {laLocura(propuesta)}
                {semana?.destacada ? <> La idea destacada: <span style={{ color: "var(--ink)" }}>{semana.destacada.texto}</span>.</> : null}
              </p>
            </Pregunta>
          </ol>
          <div style={{ marginTop: 16, display: "flex", gap: 10, flexWrap: "wrap" }}>
            {paso < PASOS ? (
              <button type="button" className="btn btn-brasa" onClick={siguiente}>Siguiente paso</button>
            ) : null}
            <Link href="/" className={`btn ${paso < PASOS ? "btn-secundario" : "btn-luz"}`}>Guardar y cerrar</Link>
          </div>
        </section>
        <p className="voz"><Bionica texto="Remi guía; tú decides. Veinte minutos, cinco preguntas, una locura." /></p>
      </div>
      <TabBar />
    </div>
  );
}

// Una de las cinco preguntas: el número se enciende cuando ya se pasó por ella.
function Pregunta({ n, paso, titulo, children }: { n: number; paso: number; titulo: string; children: React.ReactNode }) {
  const encendida = n <= paso;
  return (
    <li
      aria-current={n === paso ? "step" : undefined}
      style={{ display: "grid", gridTemplateColumns: "44px minmax(0, 1fr)", gap: 16, padding: "16px 0", borderTop: "1px solid var(--line)" }}
    >
      <span
        aria-hidden
        style={{
          width: 44, height: 44, borderRadius: "var(--radius-pill)", display: "grid", placeContent: "center",
          fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 500,
          background: encendida ? "var(--luz)" : "var(--surface-2)",
          color: encendida ? "var(--on-luz)" : "var(--ink-muted)",
          border: `1px solid ${encendida ? "var(--luz)" : "var(--line)"}`,
        }}
      >
        {n}
      </span>
      <div style={{ minWidth: 0 }}>
        <h2 className="display-md">{titulo}</h2>
        {children}
      </div>
    </li>
  );
}

// Las ideas que ya se pueden decidir (se deciden en la Bandeja) y, entre las
// que hay, cuál se queda como la destacada de la semana: una sola.
function IdeasFrias({ bandeja, sePuedeDestacar, onCambio }: { bandeja: IdeaBandeja[]; sePuedeDestacar: boolean; onCambio: () => void }) {
  const [ocupada, setOcupada] = useState<string | null>(null);
  const frias = bandeja.filter((f) => f.fria);
  // A la vista: la destacada, después las frías, después lo más nuevo. Tres como mucho.
  const peso = (f: IdeaBandeja) => (f.destacada ? 0 : f.fria ? 1 : 2);
  const aLaVista = [...bandeja].sort((a, b) => peso(a) - peso(b)).slice(0, 3);

  async function destacar(fila: IdeaBandeja) {
    setOcupada(fila.idea.id);
    try {
      await nucleo.destacarIdea(fila.idea.id, !fila.destacada);
    } finally {
      setOcupada(null);
      onCambio();
    }
  }

  return (
    <>
      <p className="body-muted" style={{ margin: "6px 0 0" }}>
        {lasFrias(frias)}{" "}
        <Link href="/bandeja" style={{ color: "var(--ink)", textDecoration: "underline", textUnderlineOffset: 3 }}>Abrir la Bandeja</Link>
      </p>
      {sePuedeDestacar && aLaVista.length > 0 ? (
        <ul aria-label="Destacar una idea" style={{ listStyle: "none", margin: "10px 0 0", padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
          {aLaVista.map((fila) => (
            <li key={fila.idea.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
              <span className="body-muted" style={{ color: "var(--ink)", minWidth: 0 }}>{recortar(fila.idea.texto, 72)}</span>
              <button
                type="button"
                className="btn btn-secundario"
                style={{ height: 44, flex: "none", borderColor: fila.destacada ? "var(--pensar)" : "var(--line)", color: fila.destacada ? "var(--pensar)" : "var(--ink)" }}
                aria-pressed={fila.destacada === true}
                disabled={ocupada !== null}
                onClick={() => destacar(fila)}
              >
                {fila.destacada ? "Destacada" : "Destacar"}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </>
  );
}
