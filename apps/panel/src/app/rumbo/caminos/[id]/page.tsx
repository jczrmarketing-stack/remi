"use client";
// R3.5, tablero 7: el análisis de un camino. Seis preguntas en orden
// (Biblia, «Lo que se ve en la pantalla»): ¿hay a quién venderle? ¿quién ya
// lo hace? ¿quién más mueve fichas? ¿qué tienes a favor y en contra? ¿qué
// tan probable es? ¿qué objetó otro modelo? Termina en la prueba que
// responde la duda. Las jugadas que salen de esto a la Bandeja quedan en
// ESPERA D1 — no se tocan acá.
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { Chip } from "@/components/Chip";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado, type FuenteVista, type VistaAnalisisCamino } from "@/lib/nucleo";
import { diaDelInstante } from "@/lib/formato";

const COLOR_DE_ESTADO: Record<VistaAnalisisCamino["estado"], string> = {
  investigando: "var(--pensar)",
  listo: "var(--luz)",
  fallo: "var(--ink-muted)",
};
const TEXTO_DE_ESTADO: Record<VistaAnalisisCamino["estado"], string> = {
  investigando: "investigando",
  listo: "listo",
  fallo: "no se pudo investigar",
};

export default function PaginaCamino() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id);
  const { datos, error, recargar } = useCargaNucleo(async () => ({ camino: await nucleo.analisisCamino(id) }));

  if (error instanceof NucleoApagado) {
    return (
      <div className="shell">
        <Header sano={false} />
        <Apagado ultimaVez={null} onReintentar={recargar} />
        <TabBar />
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
        {!datos ? (
          <p className="body-muted">Cargando…</p>
        ) : datos.camino === null ? (
          <section className="card" style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}>
            <p className="voz">Todavía no pedí un análisis para este camino.</p>
            <Link href="/rumbo" className="btn btn-secundario">Volver a Rumbo</Link>
          </section>
        ) : (
          <AnalisisCamino camino={datos.camino} />
        )}
      </div>
      <TabBar />
    </div>
  );
}

const PREGUNTAS: { titulo: string; campo: keyof VistaAnalisisCamino }[] = [
  { titulo: "¿Hay a quién venderle?", campo: "mercado" },
  { titulo: "¿Quién ya lo hace?", campo: "competidores" },
  { titulo: "¿Quién más mueve fichas?", campo: "juego" },
  { titulo: "¿Qué tienes a favor?", campo: "a_favor" },
  { titulo: "¿Qué tienes en contra?", campo: "en_contra" },
  { titulo: "¿Qué objetó otro modelo?", campo: "objeciones" },
];

function AnalisisCamino({ camino }: { camino: VistaAnalisisCamino }) {
  return (
    <>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "8px 16px", flexWrap: "wrap" }}>
        <h1 className="display-xl" style={{ fontSize: 40, lineHeight: "42px" }}>El análisis de un camino</h1>
        <Chip punto={COLOR_DE_ESTADO[camino.estado]}>{TEXTO_DE_ESTADO[camino.estado]}</Chip>
      </div>

      {camino.estado === "investigando" ? (
        <p className="body-muted">Remi lo está investigando. Vuelve en un rato.</p>
      ) : camino.estado === "fallo" ? (
        <p className="body-muted">No se pudo completar. Vuelve a pedirlo desde la Bandeja.</p>
      ) : null}

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {PREGUNTAS.map(({ titulo, campo }) => {
          const valor = camino[campo] as string | null;
          if (!valor) return null;
          return (
            <section key={campo} aria-label={titulo} className="card">
              <div className="label">{titulo}</div>
              <p className="body-txt" style={{ margin: "8px 0 0" }}>{valor}</p>
            </section>
          );
        })}

        {camino.dominio ? (
          <section aria-label="Qué tan probable es" className="card">
            <div className="label">¿Qué tan probable es?</div>
            <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <Chip>{camino.dominio}</Chip>
              {camino.base ? <p className="body-txt" style={{ margin: 0 }}>{camino.base.texto}</p> : null}
            </div>
          </section>
        ) : null}

        {camino.palancas ? (
          <section aria-label="Palancas" className="card">
            <div className="label">Qué lo cambiaría</div>
            <p className="body-txt" style={{ margin: "8px 0 0" }}>{camino.palancas}</p>
          </section>
        ) : null}

        {camino.prueba ? (
          <section aria-label="La prueba que responde la duda" className="card" style={{ borderColor: "var(--brasa)" }}>
            <div className="label">La prueba que responde la duda</div>
            <p className="voz" style={{ margin: "8px 0 0" }}>{camino.prueba}</p>
          </section>
        ) : null}

        {camino.fuentes.length > 0 ? <Fuentes fuentes={camino.fuentes} /> : null}
      </div>
    </>
  );
}

function Fuentes({ fuentes }: { fuentes: FuenteVista[] }) {
  return (
    <section aria-label="Fuentes" className="card">
      <div className="label">Fuentes</div>
      <ul style={{ listStyle: "none", margin: "12px 0 0", padding: 0, display: "flex", flexDirection: "column", gap: 10 }}>
        {fuentes.map((f) => (
          <li key={f.id} className="fila" style={{ alignItems: "flex-start" }}>
            <i className="punto" style={{ marginTop: 6, background: f.verificada ? "var(--luz)" : "var(--ink-faint)" }} />
            <div style={{ minWidth: 0, flexGrow: 1 }}>
              <p className="body-muted" style={{ margin: 0, color: "var(--ink)" }}>{f.fragmento}</p>
              <a href={f.url} target="_blank" rel="noreferrer" className="mono-sm" style={{ textDecoration: "underline" }}>
                {f.url}
              </a>
              <span className="mono-sm" style={{ marginLeft: 8 }}>{diaDelInstante(f.fecha)}</span>
            </div>
            <Chip mono>{f.verificada ? "verificada" : "supuesto"}</Chip>
          </li>
        ))}
      </ul>
    </section>
  );
}
