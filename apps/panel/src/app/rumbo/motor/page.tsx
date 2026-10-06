"use client";
// R5, tablero 9: el motor como sistema. El latido (forma S) dice si el
// reloj, los pronósticos o la cuenta dejaron de recibir datos — una vez,
// sin culpa, sin rojo (ley 3: nada se marca como falla).
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { Bionica } from "@/components/Bionica";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado, type LatidoPieza } from "@/lib/nucleo";
import { diaDelInstante } from "@/lib/formato";

const NOMBRE_DE_PIEZA: Record<string, string> = {
  reloj: "El reloj",
  pronosticos: "Los pronósticos",
  cuenta: "La cuenta de la semana",
};

export default function PaginaMotor() {
  const { datos, error, recargar } = useCargaNucleo(() => nucleo.latido());

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

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <Link href="/rumbo" className="body-muted" style={{ display: "inline-flex", alignItems: "center", gap: 4, width: "fit-content" }}>
          <ChevronLeft size={16} strokeWidth={1.75} aria-hidden />
          Rumbo
        </Link>
        <h1 className="display-xl" style={{ fontSize: 40, lineHeight: "42px" }}>El motor</h1>

        {datos.length === 0 ? (
          <p className="body-muted">Todavía no hay piezas del Rumbo en marcha.</p>
        ) : (
          <section aria-label="Latido" className="card" style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {datos.map((pieza, i) => <FilaLatido key={pieza.pieza} pieza={pieza} primera={i === 0} />)}
          </section>
        )}

        <p className="voz"><Bionica texto="Si dejo de ver tus datos dos días, te lo digo una vez, sin culpa." /></p>
      </div>
      <TabBar />
    </div>
  );
}

function FilaLatido({ pieza, primera }: { pieza: LatidoPieza; primera: boolean }) {
  const nombre = NOMBRE_DE_PIEZA[pieza.pieza] ?? pieza.pieza;
  const callado = pieza.callado_dias >= 2;
  return (
    <div className="fila" style={{ borderTop: primera ? "none" : undefined }}>
      <i className="punto" style={{ background: callado ? "var(--ink-muted)" : "var(--dormido)" }} />
      <span style={{ flexGrow: 1 }}>{nombre}</span>
      <span className="mono-sm">
        {pieza.ultimo_dato ? `último dato: ${diaDelInstante(pieza.ultimo_dato)}` : "sin dato todavía"}
        {callado ? ` · callado ${pieza.callado_dias} días` : ""}
      </span>
    </div>
  );
}
