"use client";
// Proyectos. En escritorio: la constelación (tamaño = prioridad, arco =
// camino recorrido) y, debajo, el camino del elegido. En el teléfono no
// hay constelación: una lista de caminos, el de plata arriba.
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { Constelacion, CUPO_CONSTELACION } from "@/components/Constelacion";
import { ProjectPath } from "@/components/ProjectPath";
import { Tramo } from "@/components/Tramo";
import { Bionica } from "@/components/Bionica";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado, type Libro, type Plata } from "@/lib/nucleo";
import { escalonDe, faseDe, hitoDe, liderDe, ordenDelLider, tonoDe } from "@/lib/lider";
import { enFrase, fechaCorta, nombreCorto } from "@/lib/formato";
import { enlaceObsidian, ultimaCobradaDe } from "@/lib/proyecto";
import { formatoMoneda } from "@/lib/hoy";

async function cargarProyectos() {
  const [tareas, plata, libros] = await Promise.all([nucleo.hoy(), nucleo.plata(), nucleo.libros()]);
  const abierta = tareas.flatMap((t) => t.sesiones).find((s) => s.fin === null) ?? null;
  return { hayBloque: abierta !== null, abiertoTema: abierta?.app_contexto ?? null, plata, libros };
}

export default function PaginaProyectos() {
  const { datos, error, recargar } = useCargaNucleo(cargarProyectos);
  const [elegidoAMano, setElegidoAMano] = useState<string | null>(null);

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

  const { abiertoTema, hayBloque, plata } = datos;
  const lider = liderDe(datos.libros);
  const libros = ordenDelLider(datos.libros, abiertoTema);
  // Sin elegir a mano, manda el bloque abierto; sin bloque, el primero del orden.
  const elegido =
    libros.find((l) => l.tema === elegidoAMano) ?? libros.find((l) => l.tema === abiertoTema) ?? libros[0] ?? null;
  const fueraDeLaConstelacion = libros.slice(CUPO_CONSTELACION);

  if (libros.length === 0) {
    return (
      <div className="shell">
        <Header />
        <div className="contenedor">
          <section className="card"><p className="body-muted">Todavía no hay ningún libro en la bóveda.</p></section>
        </div>
        <TabBar />
      </div>
    );
  }

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <div className="solo-escritorio" style={{ flexDirection: "column", gap: "var(--space-8)" }}>
          <Constelacion libros={libros} lider={lider} abiertoTema={abiertoTema} elegido={elegido?.tema ?? null} onElegir={setElegidoAMano} />
          {fueraDeLaConstelacion.length > 0 ? (
            <p className="body-muted">
              También:{" "}
              {fueraDeLaConstelacion.map((libro, i) => (
                <span key={libro.tema}>
                  {i > 0 ? ", " : ""}
                  <Link href={`/proyectos/${encodeURIComponent(libro.tema)}`} style={{ color: "var(--ink)" }}>{nombreCorto(libro.titulo)}</Link>
                </span>
              ))}
              .
            </p>
          ) : null}
          {elegido ? <CaminoDelElegido libro={elegido} plata={plata} abiertoTema={abiertoTema} hayBloque={hayBloque} /> : null}
          <p className="body-muted">
            Remi ordena el día así: <span style={{ color: "var(--dinero)" }}>entregas con dinero</span> → bugs en producción → propuestas → mejoras → ideas. Una locura por pantalla; lo demás, en voz baja.
          </p>
        </div>

        <div className="solo-telefono" style={{ flexDirection: "column", gap: 20, paddingTop: 8 }}>
          <h1 className="display-md" style={{ fontSize: 34, lineHeight: "36px" }}>Caminos</h1>
          <ul aria-label="Caminos" style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 20 }}>
            {libros.map((libro) => (
              <li key={libro.tema}>
                <FilaCamino libro={libro} tono={tonoDe(libro, escalonDe(libro, lider, abiertoTema), abiertoTema)} />
              </li>
            ))}
          </ul>
          <p className="body-muted">En el teléfono no hay constelación: una lista de caminos, el de plata arriba.</p>
        </div>
      </div>
      <TabBar />
    </div>
  );
}

// El camino del proyecto elegido en la constelación, con la única acción
// que importa: seguir con el hito encendido.
function CaminoDelElegido({ libro, plata, abiertoTema, hayBloque }: { libro: Libro; plata: Plata; abiertoTema: string | null; hayBloque: boolean }) {
  const router = useRouter();
  const [aviso, setAviso] = useState<string | null>(null);
  const [abriendo, setAbriendo] = useState(false);
  const nombre = nombreCorto(libro.titulo);
  const fase = faseDe(libro);
  const hito = hitoDe(libro);
  const faltan = libro.hitos.filter((h) => !h.hecho).length;
  const cobrada = ultimaCobradaDe(libro, plata);
  const esElAbierto = hayBloque && libro.tema === abiertoTema;

  async function seguir() {
    if (!hito) return;
    if (esElAbierto) {
      router.push("/");
      return;
    }
    setAbriendo(true);
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
      setAbriendo(false);
    }
  }

  return (
    <section id="camino" aria-label={`Camino de ${nombre}`} className="card" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 16, flexWrap: "wrap" }}>
        <h2 className="display-md">
          <Link href={`/proyectos/${encodeURIComponent(libro.tema)}`}>{fase ? `${nombre} · ${fase}` : nombre}</Link>
        </h2>
        {libro.hitos.length > 0 ? (
          <span className="mono-sm">
            {faltan > 0 ? <>Faltan <span style={{ color: "var(--dinero)" }}>{faltan}</span></> : "Camino completo"}
            {cobrada ? <> · última entrega cobrada: <span style={{ color: "var(--dinero)" }}>{formatoMoneda(cobrada.monto)}</span></> : null}
          </span>
        ) : null}
      </div>
      {libro.hitos.length > 0 ? (
        <>
          <ProjectPath hitos={libro.hitos} />
          <p className="voz"><Bionica texto="Un solo paso encendido. Lo recorrido queda en luz; el futuro, apagado. Nunca un árbol." /></p>
        </>
      ) : (
        <p className="body-muted">«{nombre}» todavía no tiene camino.</p>
      )}
      {aviso ? <p className="voz" role="status"><Bionica texto={aviso} /></p> : null}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {hito ? (
          <button type="button" className="btn btn-brasa" disabled={abriendo} onClick={seguir}>
            {esElAbierto ? "Volver al bloque abierto" : `Seguir con ${enFrase(hito.texto)}`}
          </button>
        ) : null}
        <Link href={`/proyectos/${encodeURIComponent(libro.tema)}`} className="btn btn-secundario">Ver el proyecto</Link>
        <a href={enlaceObsidian(libro.tema)} className="btn btn-secundario">Ver el libro en Obsidian</a>
      </div>
    </section>
  );
}

// Una fila de la lista del teléfono: el nombre, cuándo entrega, el camino
// en tramos y el paso de ahora. Tocarla abre el proyecto.
function FilaCamino({ libro, tono }: { libro: Libro; tono: string }) {
  const hito = hitoDe(libro);
  const faltan = libro.hitos.filter((h) => !h.hecho).length;
  const entrega = libro.entrega_cercana;
  return (
    <Link
      href={`/proyectos/${encodeURIComponent(libro.tema)}`}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 10,
        padding: 16,
        borderRadius: "var(--radius-md)",
        background: "var(--surface)",
        border: "1px solid var(--line)",
        borderLeft: `3px solid ${tono}`,
        color: "var(--ink)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12 }}>
        <span style={{ fontFamily: "var(--font-display)", fontSize: 22, lineHeight: "26px" }}>{nombreCorto(libro.titulo)}</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.06em", color: "var(--ink-muted)", whiteSpace: "nowrap" }}>
          {entrega ? fechaCorta(entrega.fecha) : (libro.tipo ?? "")}
        </span>
      </div>
      {libro.hitos.length > 0 ? <Tramo hitos={libro.hitos} /> : null}
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, fontSize: 14, lineHeight: "20px", color: "var(--ink-muted)" }}>
        {hito ? (
          <span>Ahora: <span style={{ color: "var(--ink)" }}>{hito.texto}</span></span>
        ) : libro.hitos.length > 0 ? (
          <span>Camino completo</span>
        ) : (
          <span>Sin camino todavía</span>
        )}
        {entrega ? (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--dinero)", whiteSpace: "nowrap" }}>{formatoMoneda(entrega.monto)}</span>
        ) : faltan > 0 ? (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, whiteSpace: "nowrap" }}>faltan {faltan}</span>
        ) : null}
      </div>
    </Link>
  );
}
