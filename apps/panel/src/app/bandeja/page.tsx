"use client";
// Bandeja · 48 h (README del diseño): lavanda mientras enfría, ámbar
// cuando está lista. Solo la fila lista tiene botones. Nunca DELETE —
// las tres decisiones las maneja bandeja.py/POST /idea/{id}/revision.
import { useState } from "react";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { Bionica } from "@/components/Bionica";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado, type IdeaBandeja } from "@/lib/nucleo";

function horasDesde(iso: string): number {
  return Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 3600000));
}

export default function PaginaBandeja() {
  const { datos: filas, error, recargar } = useCargaNucleo(nucleo.bandeja);

  if (error instanceof NucleoApagado) {
    return (
      <div className="shell">
        <Header sano={false} />
        <Apagado ultimaVez={null} onReintentar={recargar} />
      </div>
    );
  }
  if (!filas) {
    return (
      <div className="shell">
        <Header />
        <div className="contenedor"><p className="body-muted">Cargando…</p></div>
      </div>
    );
  }

  const listas = filas.filter((f) => f.fria).length;
  const enfriando = filas.length - listas;

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <h1 className="display-xl" style={{ fontSize: 40, lineHeight: "42px" }}>
            Bandeja <span style={{ color: "var(--ink-muted)" }}>· {enfriando} enfriándose · {listas} lista{listas === 1 ? "" : "s"}</span>
          </h1>
        </div>

        <section aria-label="Bandeja de ideas" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {filas.length === 0 ? (
            <p className="body-muted">Nada en la Bandeja ahora mismo.</p>
          ) : (
            filas.map((fila) => <FilaIdea key={fila.idea.id} fila={fila} onCambio={recargar} />)
          )}
        </section>

        <p className="voz"><Bionica texto="Una idea no es un proyecto hasta pasar 48 horas aquí. Soltar es una decisión, no un fallo." /></p>
        <p className="body-muted">Cada idea nace en lavanda (se piensa) y a las 48 h pasa a ámbar (se decide). Solo la fila lista tiene botones. Ningún contador de fallos, ninguna racha.</p>
      </div>
      <TabBar />
    </div>
  );
}

function FilaIdea({ fila, onCambio }: { fila: IdeaBandeja; onCambio: () => void }) {
  const [enviando, setEnviando] = useState<string | null>(null);
  const color = fila.fria ? "var(--dinero)" : "var(--pensar)";

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
    <div role="group" aria-label={fila.idea.texto} style={{ display: "grid", gridTemplateColumns: "auto minmax(0, 1fr) auto", gap: 12, alignItems: "center", padding: "14px 16px", borderRadius: 14, border: `1px solid ${fila.fria ? "var(--line)" : color}`, background: "var(--surface)", boxShadow: fila.fria ? undefined : "var(--glow-pensar)" }}>
      <i className="punto" style={{ background: color }} />
      <div>
        <div className="body-txt">{fila.idea.texto}</div>
        <div className="mono-sm">{fila.fria ? "lista · revisar" : `enfriando · ${horasDesde(fila.idea.creada_en)} h`}</div>
      </div>
      {!fila.fria ? (
        <span className="mono-sm" style={{ padding: "3px 9px", borderRadius: "var(--radius-pill)", border: `1px solid ${color}`, color, whiteSpace: "nowrap" }}>enfriando</span>
      ) : (
        <span className="mono-sm" style={{ padding: "3px 9px", borderRadius: "var(--radius-pill)", border: `1px solid ${color}`, color, whiteSpace: "nowrap" }}>lista · revisar</span>
      )}
      {fila.fria ? (
        <div style={{ gridColumn: "1 / -1", display: "flex", gap: 8, paddingTop: 4 }}>
          <button type="button" className="btn btn-secundario" style={{ height: 40 }} disabled={!!enviando} onClick={() => decidir("soltar")}>
            {enviando === "soltar" ? "Soltando…" : "Soltar"}
          </button>
          <button type="button" className="btn btn-secundario" style={{ height: 40 }} disabled={!!enviando} onClick={() => decidir("mantener")}>
            {enviando === "mantener" ? "…" : "Mantener 48 h más"}
          </button>
          <button type="button" className="btn btn-brasa" style={{ height: 40 }} disabled={!!enviando} onClick={() => decidir("tarea")}>
            {enviando === "tarea" ? "…" : "Hacer tarea"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
