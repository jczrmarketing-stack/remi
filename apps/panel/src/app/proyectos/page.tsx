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
  const librosOrdenados = [...datos.libros].sort((a, b) =>
    a.tema === abiertoTema ? -1 : b.tema === abiertoTema ? 1 : 0
  );

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

function FilaLibro({
  libro,
  abierto,
  seleccionado,
  onTocar,
}: {
  libro: Libro;
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
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12 }}>
        <h3 className="display-md" style={{ fontSize: 20 }}>{libro.titulo}</h3>
        {abierto ? <Chip punto="var(--brasa)">Abierto ahora</Chip> : null}
      </div>
      <p className="body-muted">{libro.resumen}</p>
      <p style={{ fontSize: 14, color: "var(--ink)" }}>
        {libro.proximo_paso || <span className="body-muted">sin Estado todavía</span>}
      </p>
    </button>
  );
}
