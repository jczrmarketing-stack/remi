"use client";
// Constelación de proyectos: todos los libros de /libros, el del bloque
// abierto primero y marcado. Tocar uno abre su camino debajo.
import { useState } from "react";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { MoneyRow } from "@/components/MoneyRow";
import { ProjectPath } from "@/components/ProjectPath";
import { Chip } from "@/components/Chip";
import { Bionica } from "@/components/Bionica";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado, type Camino, type Libro } from "@/lib/nucleo";
import { cargarHoy } from "@/lib/hoy";

async function cargarProyectos() {
  const [hoy, plata, libros] = await Promise.all([cargarHoy(), nucleo.plata(), nucleo.libros()]);
  return { hoy, plata, libros };
}

export default function PaginaProyectos() {
  const { datos, error, recargar } = useCargaNucleo(cargarProyectos);
  const [caminoManual, setCaminoManual] = useState<{ tema: string; camino: Camino | null } | null>(null);

  if (error instanceof NucleoApagado) {
    return (
      <div className="shell">
        <Header sano={false} />
        <Apagado ultimaVez={null} onReintentar={recargar} />
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

  const abiertoTema = datos.hoy.bloque?.tema ?? null;

  // El orden del líder: 1) el libro con la entrega con dinero más cercana
  // (una sola — la de fecha más próxima entre todos los que tienen una);
  // 2) el del bloque abierto, si no es ya el líder; 3) el resto, por fecha
  // de último Estado (más reciente primero). El tamaño del título sigue
  // esta misma prioridad, en tres escalas.
  const conEntrega = datos.libros.filter((l) => l.entrega_cercana);
  const lider = conEntrega.length
    ? conEntrega.reduce((a, b) =>
        new Date(a.entrega_cercana!.fecha).getTime() <= new Date(b.entrega_cercana!.fecha).getTime() ? a : b
      )
    : null;

  function prioridad(libro: Libro): 1 | 2 | 3 {
    if (lider && libro.tema === lider.tema) return 1;
    if (libro.tema === abiertoTema) return 2;
    return 3;
  }

  const librosOrdenados = [...datos.libros].sort((a, b) => {
    const diferencia = prioridad(a) - prioridad(b);
    if (diferencia !== 0) return diferencia;
    // Dentro del mismo escalón 3, el Estado tocado más reciente primero.
    return new Date(b.ultimo_estado_en).getTime() - new Date(a.ultimo_estado_en).getTime();
  });

  // `caminoManual.camino` puede ser null de verdad (ese libro no tiene ##
  // Camino): con `??` un null explícito volvería al del bloque abierto por
  // error. Sin selección manual, manda el bloque abierto.
  const tema = caminoManual ? caminoManual.tema : abiertoTema;
  const camino = caminoManual ? caminoManual.camino : (datos.hoy.bloque?.camino ?? null);
  const libroDelCamino = tema ? librosOrdenados.find((l) => l.tema === tema) ?? null : null;

  async function abrirCamino(libroTema: string) {
    if (libroTema === abiertoTema) {
      setCaminoManual(null); // el del bloque abierto ya está cargado
      return;
    }
    const c = await nucleo.camino(libroTema);
    setCaminoManual({ tema: libroTema, camino: c });
  }

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <MoneyRow plata={datos.plata} />

        <section aria-label="Constelación de proyectos" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div className="label">Proyectos</div>
          {librosOrdenados.length === 0 ? (
            <p className="body-muted">Todavía no hay ningún libro en la bóveda.</p>
          ) : (
            librosOrdenados.map((libro) => (
              <FilaLibro
                key={libro.tema}
                libro={libro}
                prioridad={prioridad(libro)}
                abierto={libro.tema === abiertoTema}
                seleccionado={libro.tema === tema}
                onTocar={() => abrirCamino(libro.tema)}
              />
            ))
          )}
        </section>

        {camino ? (
          <section id="camino" aria-label={`Camino de ${tema}`} className="card" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <h2 className="display-md">{libroDelCamino ? libroDelCamino.titulo : tema}</h2>
            <ProjectPath hitos={camino.hitos} />
            <p className="voz"><Bionica texto="Un solo paso encendido. Lo recorrido queda en luz; el futuro, apagado. Nunca un árbol." /></p>
          </section>
        ) : tema ? (
          <section className="card">
            <p className="body-muted">«{libroDelCamino?.titulo ?? tema}» todavía no tiene ## Camino.</p>
          </section>
        ) : null}

        <p className="body-muted">Remi ordena el día así: entregas con dinero → bugs en producción → propuestas → mejoras → ideas.</p>
      </div>
      <TabBar />
    </div>
  );
}

// Tres escalas de título, una por escalón de prioridad — nunca un cuarto tamaño.
const TAMANO_TITULO: Record<1 | 2 | 3, number> = { 1: 26, 2: 21, 3: 17 };

function FilaLibro({
  libro,
  prioridad,
  abierto,
  seleccionado,
  onTocar,
}: {
  libro: Libro;
  prioridad: 1 | 2 | 3;
  abierto: boolean;
  seleccionado: boolean;
  onTocar: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onTocar}
      className="card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 6,
        textAlign: "left",
        width: "100%",
        borderColor: seleccionado ? "var(--brasa)" : "var(--line)",
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <h3 className="display-md" style={{ fontSize: TAMANO_TITULO[prioridad] }}>{libro.titulo}</h3>
        <div style={{ display: "flex", gap: 8 }}>
          {prioridad === 1 && libro.entrega_cercana ? (
            <Chip punto="var(--dinero)">
              {libro.entrega_cercana.cliente} · ${Math.round(libro.entrega_cercana.monto).toLocaleString("es-CO")}
            </Chip>
          ) : null}
          {abierto ? <Chip punto="var(--brasa)">Abierto ahora</Chip> : null}
        </div>
      </div>
      <p className="body-muted">{libro.resumen}</p>
      <p style={{ fontSize: 14, color: "var(--ink)" }}>
        {libro.proximo_paso || <span className="body-muted">sin Estado todavía</span>}
      </p>
    </button>
  );
}
