"use client";
// Constelación de proyectos (README del diseño): el panel no tiene hoy
// ninguna ruta que liste los libros/temas que existen (solo /camino/{tema},
// que ya necesita el tema). Sin esa ruta no hay de dónde sacar la
// constelación completa sin inventar datos — así que esta página muestra
// el único proyecto del que sí hay datos reales: el del bloque abierto.
// Documentado en la bitácora como duda abierta para quien siga.
import { useState } from "react";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { MoneyRow } from "@/components/MoneyRow";
import { ProjectPath } from "@/components/ProjectPath";
import { Bionica } from "@/components/Bionica";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado, type Camino } from "@/lib/nucleo";
import { cargarHoy } from "@/lib/hoy";

async function cargarProyectos() {
  const [hoy, plata] = await Promise.all([cargarHoy(), nucleo.plata()]);
  return { hoy, plata: plata };
}

export default function PaginaProyectos() {
  const { datos, error, recargar } = useCargaNucleo(cargarProyectos);
  const [caminoManual, setCaminoManual] = useState<{ tema: string; camino: Camino | null } | null>(null);
  const [temaBuscado, setTemaBuscado] = useState("");

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

  // `caminoManual.camino` puede ser null de verdad (ese tema no tiene
  // libro): con `??` un null explícito cae al bloque abierto por error.
  // Una vez que se buscó a mano, manda la búsqueda, resultado o no.
  const tema = caminoManual ? caminoManual.tema : (datos.hoy.bloque?.tema ?? null);
  const camino = caminoManual ? caminoManual.camino : (datos.hoy.bloque?.camino ?? null);
  const titulo = datos.hoy.bloque?.tarea.tarea.titulo ?? null;

  async function buscar() {
    const tema = temaBuscado.trim();
    if (!tema) return;
    const c = await nucleo.camino(tema); // null si no hay libro con ese tema
    setCaminoManual({ tema, camino: c });
  }

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <MoneyRow plata={datos.plata} />

        <section aria-label="Proyecto activo" className="card" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="label">Proyectos · sin lista completa todavía</div>
          <p className="body-muted">
            El núcleo no expone aún un listado de proyectos — solo <code>/camino/&#123;tema&#125;</code>. Esto muestra el del bloque abierto; para otro, escribí su tema (el mismo nombre del libro en <code>conocimiento/proyectos/</code>).
          </p>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              value={temaBuscado}
              onChange={(e) => setTemaBuscado(e.target.value)}
              placeholder="tema del libro, p. ej. upvisuals"
              aria-label="Buscar camino por tema"
              style={{ flexGrow: 1, maxWidth: 320, height: 44, borderRadius: "var(--radius-pill)", padding: "0 16px", border: "1px solid var(--line)", background: "var(--surface-2)", color: "var(--ink)" }}
            />
            <button type="button" className="btn btn-secundario" onClick={buscar}>Ver camino</button>
          </div>
        </section>

        {camino ? (
          <section id="camino" aria-label={`Camino de ${tema}`} className="card" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 16 }}>
              <h2 className="display-md">{titulo && tema === datos.hoy.bloque?.tema ? `${tema} · ${titulo}` : tema}</h2>
            </div>
            <ProjectPath hitos={camino.hitos} />
            <p className="voz"><Bionica texto="Un solo paso encendido. Lo recorrido queda en luz; el futuro, apagado. Nunca un árbol." /></p>
          </section>
        ) : (
          <section className="card">
            <p className="body-muted">
              {tema ? "Ese tema no tiene un libro con ## Camino." : "No hay un bloque abierto ahora mismo: abrí uno desde la ventanita o buscá un tema arriba."}
            </p>
          </section>
        )}

        <p className="body-muted">Remi ordena el día así: entregas con dinero → bugs en producción → propuestas → mejoras → ideas.</p>
      </div>
      <TabBar />
    </div>
  );
}
