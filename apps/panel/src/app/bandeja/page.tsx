"use client";
// Bandeja · 48 h: cada idea nace en lavanda (se piensa) y a las 48 h pasa a
// ámbar (se decide). Solo la fila lista tiene botones. Cada idea dice de qué
// tema es —o que está suelta— y la destacada de la semana va arriba. Nunca
// DELETE: las tres decisiones las maneja POST /idea/{id}/revision.
import { useState, type CSSProperties } from "react";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { Bionica } from "@/components/Bionica";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado, type IdeaBandeja } from "@/lib/nucleo";
import { cuandoEsLaRevision } from "@/lib/formato";

const HORA_MS = 3600000;

function horasEntre(desdeMs: number, hastaMs: number): number {
  return Math.max(0, Math.round((hastaMs - desdeMs) / HORA_MS));
}

// La destacada arriba; después lo que ya se puede decidir; después lo que
// enfría, lo que sale antes primero.
function ordenar(filas: IdeaBandeja[]): IdeaBandeja[] {
  const peso = (f: IdeaBandeja) => (f.destacada ? 0 : f.fria ? 1 : 2);
  return [...filas].sort((a, b) => {
    const diferencia = peso(a) - peso(b);
    if (diferencia !== 0) return diferencia;
    if (a.fria && b.fria) return new Date(a.idea.creada_en).getTime() - new Date(b.idea.creada_en).getTime();
    return new Date(a.idea.enfria_hasta).getTime() - new Date(b.idea.enfria_hasta).getTime();
  });
}

async function cargarBandeja() {
  const [filas, plata] = await Promise.all([nucleo.bandeja(), nucleo.plata()]);
  return { filas, revision: plata.revision_fria };
}

export default function PaginaBandeja() {
  const { datos, error, recargar } = useCargaNucleo(cargarBandeja);

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

  const filas = ordenar(datos.filas);
  const listas = filas.filter((f) => f.fria).length;
  const enfriando = filas.length - listas;
  const cuando = cuandoEsLaRevision(datos.revision);
  const ahoraMs = Date.now();

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "8px 16px", flexWrap: "wrap", paddingTop: 8 }}>
          <h1 className="display-xl" style={{ fontSize: 40, lineHeight: "42px" }}>
            Bandeja{" "}
            <span className="solo-escritorio-en-linea" style={{ color: "var(--ink-muted)" }}>
              · {enfriando} enfriándose · {listas} lista{listas === 1 ? "" : "s"}
            </span>
          </h1>
          {cuando ? (
            <span className="mono-sm">
              revisión en frío · {cuando}
              {datos.revision?.minutos ? ` · ${datos.revision.minutos} min` : ""}
            </span>
          ) : null}
        </div>

        <section aria-label="Bandeja de ideas" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {filas.length === 0 ? (
            <p className="body-muted">Nada en la Bandeja ahora mismo.</p>
          ) : (
            filas.map((fila) => <FilaIdea key={fila.idea.id} fila={fila} ahoraMs={ahoraMs} onCambio={recargar} />)
          )}
        </section>

        <p className="voz"><Bionica texto="Una idea no es un proyecto hasta pasar 48 horas aquí. Soltar es una decisión, no un fallo." /></p>
        <p className="body-muted">Cada idea nace en lavanda (se piensa) y a las 48 h pasa a ámbar (se decide). Solo la fila lista tiene botones. Ningún contador de fallos, ninguna racha.</p>
      </div>
      <TabBar />
    </div>
  );
}

// «organic-cash» → «organic cash». Sin tema, la idea está suelta.
function temaDe(fila: IdeaBandeja): string {
  return fila.idea.tema ? fila.idea.tema.replace(/-/g, " ") : "suelta";
}

function FilaIdea({ fila, ahoraMs, onCambio }: { fila: IdeaBandeja; ahoraMs: number; onCambio: () => void }) {
  const [enviando, setEnviando] = useState<string | null>(null);
  const destacada = fila.destacada === true;
  const color = fila.fria ? "var(--dinero)" : "var(--pensar)";
  const edad = horasEntre(new Date(fila.idea.creada_en).getTime(), ahoraMs);
  const faltan = horasEntre(ahoraMs, new Date(fila.idea.enfria_hasta).getTime());
  // El estado, en pocas palabras: una pastilla a la derecha en escritorio;
  // en el teléfono baja debajo del texto (.idea-estado en globals.css).
  const estado = destacada ? "destacada" : fila.fria ? "lista · revisar" : `enfriando · ${faltan} h`;
  // De qué tema es y, mientras la idea es nueva, cuánto lleva. Una idea que
  // ya esperó de más no carga un contador encima (ley 3).
  const detalle = [
    temaDe(fila),
    destacada ? "destacada de la semana" : edad <= 96 ? `${edad} h` : null,
    destacada && fila.fria ? "lista para revisar" : null,
  ]
    .filter(Boolean)
    .join(" · ");

  async function decidir(decision: "soltar" | "mantener" | "tarea") {
    setEnviando(decision);
    try {
      await nucleo.revisarIdea(fila.idea.id, decision);
      onCambio();
    } catch {
      // 409 si por alguna carrera ya no está fría: recargar deja verla tal cual quedó.
      onCambio();
    } finally {
      setEnviando(null);
    }
  }

  return (
    <div
      role="group"
      aria-label={fila.idea.texto}
      className="idea-fila"
      style={{
        border: `1px solid ${destacada ? "var(--pensar)" : "var(--line)"}`,
        boxShadow: destacada ? "var(--glow-pensar)" : undefined,
      }}
    >
      <i className="punto" style={{ width: 10, height: 10, background: destacada ? "var(--pensar)" : color }} />
      <div style={{ minWidth: 0 }}>
        <div className="body-txt">{fila.idea.texto}</div>
        <div className="mono-sm" style={{ fontSize: 11, letterSpacing: "0.06em" }}>{detalle}</div>
      </div>
      <span className="idea-estado" style={{ "--tono": destacada ? "var(--pensar)" : color } as CSSProperties}>{estado}</span>
      {fila.fria ? (
        <div style={{ gridColumn: "1 / -1", display: "flex", gap: 8, paddingTop: 4, flexWrap: "wrap" }}>
          <button type="button" className="btn btn-secundario idea-boton" disabled={!!enviando} onClick={() => decidir("soltar")}>
            {enviando === "soltar" ? "Soltando…" : "Soltar"}
          </button>
          <button type="button" className="btn btn-secundario idea-boton" disabled={!!enviando} onClick={() => decidir("mantener")}>
            {enviando === "mantener" ? "…" : <><span className="solo-escritorio-en-linea">Mantener 48 h más</span><span className="solo-telefono-en-linea">Mantener</span></>}
          </button>
          <button type="button" className="btn btn-brasa idea-boton" disabled={!!enviando} onClick={() => decidir("tarea")}>
            {enviando === "tarea" ? "…" : <><span className="solo-escritorio-en-linea">Hacer tarea</span><span className="solo-telefono-en-linea">Tarea</span></>}
          </button>
        </div>
      ) : null}
    </div>
  );
}
