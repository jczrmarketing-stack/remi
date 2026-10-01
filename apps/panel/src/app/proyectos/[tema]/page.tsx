"use client";
// Un proyecto por dentro: en qué fase va y cuánto se cobró, el camino del
// SOP con el hito encendido, las fases de la propuesta, lo que falta y el
// Estado del libro. Todo sale del libro en la bóveda; lo que el libro no
// dice, no se inventa acá.
import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { Chip } from "@/components/Chip";
import { ProjectPath } from "@/components/ProjectPath";
import { Tramo } from "@/components/Tramo";
import { Bionica } from "@/components/Bionica";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado, type Fase, type LibroDetalle } from "@/lib/nucleo";
import { hitoDe } from "@/lib/lider";
import { diaDelInstante, enFrase, fechaCorta, nombreCorto } from "@/lib/formato";
import { enlaceObsidian, partesDelEstado, tonoDeFase } from "@/lib/proyecto";
import { formatoMoneda } from "@/lib/hoy";

type Datos = { libro: LibroDetalle | null; hayBloque: boolean; abiertoTema: string | null };

export default function PaginaProyecto() {
  const params = useParams<{ tema: string }>();
  const tema = decodeURIComponent(params.tema);
  const { datos, error, recargar } = useCargaNucleo<Datos>(async () => {
    const [libro, tareas] = await Promise.all([nucleo.libro(tema), nucleo.hoy()]);
    const abierta = tareas.flatMap((t) => t.sesiones).find((s) => s.fin === null) ?? null;
    return { libro, hayBloque: abierta !== null, abiertoTema: abierta?.app_contexto ?? null };
  });

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
  if (!datos.libro) {
    return (
      <div className="shell">
        <Header />
        <div className="contenedor">
          <section className="card" style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}>
            <p className="voz">No tengo un libro con ese nombre.</p>
            <Link href="/proyectos" className="btn btn-secundario">Volver a Proyectos</Link>
          </section>
        </div>
        <TabBar />
      </div>
    );
  }

  const libro = datos.libro;
  const esElAbierto = datos.hayBloque && datos.abiertoTema === libro.tema;

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <Titulo libro={libro} />
        <FaseYPlata libro={libro} />
        {libro.hitos.length > 0 ? <CaminoDelProyecto libro={libro} esElAbierto={esElAbierto} recargar={recargar} /> : null}
        {libro.fases.length > 0 || libro.siguientes.length > 0 ? (
          <div className="rejilla-dos" style={{ gap: "var(--space-6)", alignItems: "start" }}>
            {libro.fases.length > 0 ? <FasesDeLaPropuesta fases={libro.fases} /> : null}
            {libro.siguientes.length > 0 ? <QueFalta libro={libro} /> : null}
          </div>
        ) : null}
        <EstadoDelLibro libro={libro} />
      </div>
      <TabBar />
    </div>
  );
}

function etiquetaDeTipo(libro: LibroDetalle): string {
  if (libro.tipo === "cliente") return libro.cliente ? `Cliente · ${libro.cliente}` : "Proyecto de cliente";
  if (libro.tipo === "propio") return "Proyecto propio";
  return "Proyecto";
}

function Titulo({ libro }: { libro: LibroDetalle }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap", paddingTop: 8 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
        <Link href="/proyectos" aria-label="Volver a Proyectos" title="Volver a Proyectos" className="icon-btn" style={{ flex: "none" }}>
          <ChevronLeft size={20} strokeWidth={1.75} aria-hidden />
        </Link>
        <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
          <div className="label">{etiquetaDeTipo(libro)}</div>
          <h1 className="display-md" style={{ letterSpacing: "-0.01em" }}>{libro.titulo}</h1>
        </div>
      </div>
      <a href={enlaceObsidian(libro.tema)} className="btn btn-secundario solo-escritorio">Ver el libro en Obsidian</a>
    </div>
  );
}

function ChipDeFase({ estado }: { estado: string }) {
  const tono = tonoDeFase(estado);
  return (
    <span className="chip" style={{ color: tono.apagada || tono.punto === "var(--baja)" ? "var(--ink-muted)" : "var(--ink)" }}>
      {tono.punto ? <i className="chip-punto" style={{ background: tono.punto }} /> : null}
      {estado}
    </span>
  );
}

// La fase en la que está el proyecto y su plata. Sin fases (un proyecto
// propio, o un libro que todavía no las tiene) queda el paso del camino.
function FaseYPlata({ libro }: { libro: LibroDetalle }) {
  const n = libro.fase_actual_n;
  const fase = n ? libro.fases[n - 1] : null;
  const hito = hitoDe(libro);
  const entrega = libro.entrega_cercana;

  if (!fase) {
    return (
      <section aria-label="Dónde va" className="card" style={{ padding: "var(--space-8)", display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="label">{libro.fases.length > 0 ? "Fases" : "Dónde va"}</div>
        <h2 className="display-xl">
          {libro.fases.length > 0 ? "Fases entregadas" : hito ? `Paso ${hito.n} de ${hito.total}` : "Sin camino todavía"}
        </h2>
        <p className="body-txt" style={{ margin: 0, color: "var(--ink-muted)" }}>{libro.resumen}</p>
        {entrega ? (
          <p className="mono-sm" style={{ margin: 0 }}>
            próxima entrega: <span style={{ color: "var(--dinero)" }}>{fechaCorta(entrega.fecha)}</span> · {formatoMoneda(entrega.monto)}
          </p>
        ) : null}
      </section>
    );
  }

  const monto = fase.monto;
  const cobrado = fase.cobrado;
  const pct = monto && cobrado ? Math.min(100, Math.round((cobrado / monto) * 100)) : 0;
  return (
    <section aria-label="Fase actual y plata" className="card rejilla-dos" style={{ padding: "var(--space-8)", alignItems: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 12, minWidth: 0 }}>
        <div className="label">Fase actual</div>
        <h2 className="display-xl">Fase {n} de {libro.fases.length}</h2>
        <p className="body-txt" style={{ margin: 0, color: "var(--ink-muted)" }}>{fase.alcance || fase.nombre}</p>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          {monto != null ? <span className="num-lg" style={{ color: "var(--dinero)" }}>{formatoMoneda(monto)}</span> : null}
          {fase.estado ? <ChipDeFase estado={fase.estado} /> : null}
        </div>
        {monto != null ? (
          <>
            <div
              role="img"
              aria-label={cobrado ? `Cobrado de ${fase.nombre}: ${formatoMoneda(cobrado)} de ${formatoMoneda(monto)}` : `Cobrado de ${fase.nombre}: sin cobros registrados`}
              style={{ height: 8, borderRadius: "var(--radius-pill)", background: "var(--line)", overflow: "hidden" }}
            >
              <div style={{ width: `${pct}%`, height: "100%", borderRadius: "var(--radius-pill)", background: "var(--dinero)" }} />
            </div>
            <div className="mono-sm" style={{ display: "flex", flexDirection: "column", gap: 6, fontVariantNumeric: "tabular-nums" }}>
              {cobrado ? (
                <span>cobrado <span style={{ color: "var(--ink)" }}>{formatoMoneda(cobrado)}</span> de {formatoMoneda(monto)}</span>
              ) : cobrado === 0 ? (
                <span>sin cobros registrados todavía</span>
              ) : null}
              {entrega ? (
                <span>próxima entrega: <span style={{ color: "var(--dinero)" }}>{fechaCorta(entrega.fecha)}</span> · {formatoMoneda(entrega.monto)}</span>
              ) : null}
            </div>
          </>
        ) : null}
      </div>
    </section>
  );
}

function CaminoDelProyecto({ libro, esElAbierto, recargar }: { libro: LibroDetalle; esElAbierto: boolean; recargar: () => void }) {
  const router = useRouter();
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  // El último hito que se cerró desde acá, para poder deshacerlo.
  const [recienCerrado, setRecienCerrado] = useState<{ n: number; texto: string } | null>(null);
  const nombre = nombreCorto(libro.titulo);
  const hito = hitoDe(libro);
  const actual = libro.hito_actual;
  const recorridos = libro.hitos.filter((h) => h.hecho).map((h) => enFrase(h.texto));
  const sop = libro.tipo === "cliente" ? " · SOP de cliente" : libro.tipo === "propio" ? " · SOP propio" : "";

  async function seguir() {
    if (!hito) return;
    if (esElAbierto) {
      router.push("/");
      return;
    }
    setOcupado(true);
    try {
      await nucleo.abrirBloque(`${nombre} · ${hito.texto}`, libro.tema);
      router.push("/");
    } catch (error) {
      setAviso(
        error instanceof NucleoApagado && error.status === 409
          ? "Hay otro bloque abierto. Ciérralo en Hoy y seguimos con este."
          : "No pude abrirlo ahora. Vuelve a tocar en un momento.",
      );
    } finally {
      setOcupado(false);
    }
  }

  async function marcar(n: number, texto: string, hecho: boolean) {
    setOcupado(true);
    setAviso(null);
    try {
      await nucleo.marcarHito(libro.tema, n, hecho);
      setRecienCerrado(hecho ? { n, texto } : null);
      recargar();
    } catch {
      setAviso("No pude guardarlo en el libro. Vuelve a tocar en un momento.");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <section aria-label={`Camino de ${nombre}`} className="card" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 16, flexWrap: "wrap" }}>
        <div className="label">Camino{sop}</div>
        <span className="mono-sm">
          {hito ? <>hito <span style={{ color: "var(--brasa)" }}>{hito.n}</span> de {hito.total}</> : "camino completo"}
        </span>
      </div>

      <div className="solo-escritorio" style={{ flexDirection: "column" }}>
        <ProjectPath hitos={libro.hitos} />
      </div>
      <div className="solo-telefono" style={{ flexDirection: "column", gap: 14 }}>
        <Tramo hitos={libro.hitos} brillo />
        {recorridos.length > 0 ? <p className="body-muted" style={{ margin: 0 }}>Recorrido: {recorridos.join(", ")}.</p> : null}
      </div>

      {actual ? (
        <div className="rejilla-dos" style={{ borderTop: "1px solid var(--line)", paddingTop: 20 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }}>
            <div className="label">Ahora</div>
            <h3 className="display-md" style={{ letterSpacing: "-0.01em" }}>{actual.texto}</h3>
            {actual.detalle ? <p className="body-txt" style={{ margin: 0, color: "var(--ink-muted)" }}>{actual.detalle}</p> : null}
          </div>
          {libro.paso_remi ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }}>
              <div className="label">Remi en este paso</div>
              <p className="voz"><Bionica texto={libro.paso_remi} /></p>
            </div>
          ) : null}
        </div>
      ) : (
        <p className="voz"><Bionica texto="Este camino está completo. Lo que sigue se decide en la revisión." /></p>
      )}

      {aviso ? <p className="voz" role="status"><Bionica texto={aviso} /></p> : null}

      {hito ? (
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button type="button" className="btn btn-brasa" disabled={ocupado} onClick={seguir}>
            {esElAbierto ? "Volver al bloque abierto" : `Seguir con ${enFrase(hito.texto)}`}
          </button>
          <button type="button" className="btn btn-secundario" disabled={ocupado} onClick={() => marcar(hito.n, hito.texto, true)}>
            Cerrar hito
          </button>
        </div>
      ) : null}

      {recienCerrado ? (
        <p className="mono-sm" role="status" style={{ margin: 0, display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <span>Cerrado: <span style={{ color: "var(--ink)" }}>{recienCerrado.texto}</span>. Quedó anotado en el libro.</span>
          <button
            type="button"
            className="btn btn-secundario"
            style={{ height: 32, padding: "0 12px", fontSize: 12 }}
            disabled={ocupado}
            onClick={() => marcar(recienCerrado.n, recienCerrado.texto, false)}
          >
            Deshacer
          </button>
        </p>
      ) : null}
    </section>
  );
}

function FasesDeLaPropuesta({ fases }: { fases: Fase[] }) {
  const conAlcance = fases.reduce((suma, f) => suma + (f.monto ?? 0), 0);
  return (
    <section aria-label="Fases de la propuesta" className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 16 }}>
        <div className="label">Fases de la propuesta</div>
        {conAlcance > 0 ? (
          <span className="mono-sm">con alcance: <span style={{ color: "var(--dinero)" }}>{formatoMoneda(conAlcance)}</span></span>
        ) : null}
      </div>
      <div style={{ marginTop: 12, display: "flex", flexDirection: "column" }}>
        {fases.map((fase, i) => {
          const tono = tonoDeFase(fase.estado);
          const ultima = i === fases.length - 1;
          return (
            <div key={i} style={{ padding: ultima ? "16px 0 0" : "16px 0", borderTop: "1px solid var(--line)", display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <span style={{ fontFamily: "var(--font-display)", fontSize: 22, lineHeight: "26px", color: tono.apagada ? "var(--ink-muted)" : "var(--ink)" }}>
                    {fase.nombre || `Fase ${i + 1}`}
                  </span>
                  {fase.estado ? <ChipDeFase estado={fase.estado} /> : null}
                </div>
                <span className="mono-sm" style={{ color: tono.punto === "var(--dinero)" ? "var(--dinero)" : undefined, fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>
                  {fase.monto != null ? formatoMoneda(fase.monto) : "sin monto"}
                </span>
              </div>
              {fase.alcance ? (
                <p className="body-muted" style={{ margin: 0, color: tono.apagada ? "var(--ink-muted)" : "var(--ink)" }}>{fase.alcance}</p>
              ) : null}
              {tono.apagada ? null : (
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <span className="label">Listo cuando</span>
                  <span className="body-muted">{fase.listo_cuando || "Falta en el libro."}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

// Los tres hitos que siguen al de ahora — nunca el camino entero otra vez.
function QueFalta({ libro }: { libro: LibroDetalle }) {
  const indiceActual = libro.hitos.findIndex((h) => !h.hecho);
  const despues = libro.hitos.slice(indiceActual + 1 + libro.siguientes.length).map((h) => enFrase(h.texto));
  return (
    <section aria-label="Qué falta" className="card primero-en-telefono">
      <div className="label">Qué falta · {libro.siguientes.length === 1 ? "el que sigue" : `los ${["dos", "tres"][libro.siguientes.length - 2] ?? libro.siguientes.length} que siguen`}</div>
      <ol style={{ listStyle: "none", margin: "12px 0 0", padding: 0, display: "flex", flexDirection: "column" }}>
        {libro.siguientes.map((h, i) => (
          <li key={i} style={{ display: "grid", gridTemplateColumns: "28px minmax(0, 1fr)", gap: 12, padding: "12px 0", borderTop: "1px solid var(--line)" }}>
            <span className="mono-sm" style={{ paddingTop: 4, fontVariantNumeric: "tabular-nums" }}>{String(indiceActual + 2 + i).padStart(2, "0")}</span>
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <span className="body-txt">{h.texto}</span>
              {h.detalle ? <span className="body-muted">{h.detalle}</span> : null}
            </div>
          </li>
        ))}
      </ol>
      {despues.length > 0 ? (
        <p className="body-muted" style={{ margin: 0, paddingTop: 12, borderTop: "1px solid var(--line)" }}>Después: {despues.join(", ")}.</p>
      ) : null}
    </section>
  );
}

function EstadoDelLibro({ libro }: { libro: LibroDetalle }) {
  const partes = partesDelEstado(libro.estado_completo);
  const columnas = [
    { titulo: "Quedaste", texto: partes.quedaste },
    { titulo: "Decisiones", texto: partes.decisiones },
    { titulo: "Próximo paso", texto: partes.proximo },
  ].filter((c) => c.texto);
  const dia = diaDelInstante(libro.ultimo_estado_en);
  return (
    <section aria-label="Estado" className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 16 }}>
        <div className="label">Estado</div>
        {dia ? <span className="mono-sm">del libro · {dia}</span> : null}
      </div>
      {columnas.length > 0 ? (
        <div className="rejilla-tres" style={{ marginTop: 16 }}>
          {columnas.map((c) => (
            <div key={c.titulo} style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
              <span className="label">{c.titulo}</span>
              <p className="body-txt" style={{ margin: 0 }}>{c.texto}</p>
            </div>
          ))}
        </div>
      ) : partes.suelto ? (
        <p className="body-txt" style={{ margin: "16px 0 0" }}>{partes.suelto}</p>
      ) : (
        <p className="body-muted" style={{ margin: "16px 0 0" }}>Este libro todavía no tiene Estado. Se escribe solo al cerrar una sesión del proyecto.</p>
      )}
    </section>
  );
}
