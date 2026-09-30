"use client";
// Metas · la plata (README del diseño): meta → número del mes → brecha →
// acción. El mockup muestra varias metas nombradas con plazos (Vivir
// solo, Carro) y un desglose por línea de negocio — eso no existe en el
// contrato Entrega ni en config/plata.json (solo meta_mensual y moneda),
// así que esta página se queda en la única meta real que el núcleo sabe:
// la mensual, con sus números reales.
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { MoneyRow } from "@/components/MoneyRow";
import { Bionica } from "@/components/Bionica";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado } from "@/lib/nucleo";
import { formatoMoneda } from "@/lib/hoy";

export default function PaginaMetas() {
  const { datos: plata, error, recargar } = useCargaNucleo(nucleo.plata);

  if (error instanceof NucleoApagado) {
    return (
      <div className="shell">
        <Header sano={false} />
        <Apagado ultimaVez={null} onReintentar={recargar} />
      </div>
    );
  }
  if (!plata) {
    return (
      <div className="shell">
        <Header />
        <div className="contenedor"><p className="body-muted">Cargando…</p></div>
      </div>
    );
  }

  const porcentaje = plata.mes.meta > 0 ? Math.round((plata.mes.cobrado / plata.mes.meta) * 100) : 0;
  const r = 50;
  const circunferencia = 2 * Math.PI * r;
  const avance = Math.min(100, porcentaje);

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <MoneyRow plata={plata} />

        <section aria-label="Meta del mes" className="card" style={{ display: "grid", gridTemplateColumns: "120px minmax(0, 1fr)", gap: 24, alignItems: "center" }}>
          <svg width={120} height={120} viewBox="0 0 120 120" role="img" aria-label={`${porcentaje} por ciento de la meta`}>
            <circle cx="60" cy="60" r={r} fill="none" stroke="var(--line)" strokeWidth="8" />
            <circle
              cx="60" cy="60" r={r} fill="none" stroke="var(--dinero)" strokeWidth="8" strokeLinecap="round"
              pathLength="100" strokeDasharray={`${avance} 100`} transform="rotate(-90 60 60)"
            />
            <text x="60" y="66" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="16" fill="var(--ink)">{porcentaje}%</text>
          </svg>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div className="label">Meta · mensual</div>
            <h2 className="display-xl" style={{ fontSize: 40, lineHeight: "42px" }}>{formatoMoneda(plata.mes.meta)}/mes</h2>
            <div className="mono-sm">
              este mes vas en <span style={{ color: "var(--dinero)" }}>{formatoMoneda(plata.mes.cobrado)}</span>
            </div>
            {plata.mes.faltan > 0 ? (
              <p className="body-txt">Brecha: <strong>{formatoMoneda(plata.mes.faltan)}</strong>.{" "}
                {plata.proximo ? `La entrega de ${plata.proximo.cliente} (${formatoMoneda(plata.proximo.monto)}) la reduce.` : ""}
              </p>
            ) : (
              <p className="body-txt">Meta del mes cumplida.</p>
            )}
          </div>
        </section>

        <section className="card">
          <div className="label">Próxima entrega con dinero</div>
          {plata.proximo ? (
            <div className="fila" style={{ marginTop: 12 }}>
              <i className="punto" style={{ background: "var(--dinero)" }} />
              <span style={{ flexGrow: 1 }}>{plata.proximo.cliente}</span>
              <span className="mono-sm" style={{ color: "var(--dinero)" }}>{formatoMoneda(plata.proximo.monto)} · {new Date(plata.proximo.fecha).toLocaleDateString("es-CO", { day: "numeric", month: "short" })}</span>
            </div>
          ) : (
            <p className="body-muted" style={{ marginTop: 12 }}>No hay ninguna entrega con monto pendiente todavía.</p>
          )}
        </section>

        <p className="voz"><Bionica texto="Meta → número del mes → brecha → acción. Nunca un porcentaje solo." /></p>
      </div>
      <TabBar />
    </div>
  );
}
