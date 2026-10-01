import type { Plata } from "@/lib/nucleo";
import { accionCorta } from "@/lib/formato";
import { formatoMoneda } from "@/lib/hoy";

// La plata de la semana: $X de $Y, lo que falta del mes y la acción que lo
// cierra. Nunca el número solo (Biblia, Parte VII).
export function MoneyRow({ plata }: { plata: Plata }) {
  return (
    <section aria-label="La plata de la semana" style={{ display: "flex", alignItems: "baseline", gap: 16, flexWrap: "wrap" }}>
      <div className="label">Esta semana</div>
      <div className="num-lg">
        {formatoMoneda(plata.semana.cobrado)}{" "}
        <span style={{ fontFamily: "var(--font-sans)", fontSize: 14, fontWeight: 400, letterSpacing: 0, color: "var(--ink-muted)" }}>
          de {formatoMoneda(plata.semana.meta_semanal)}
        </span>
      </div>
      {plata.mes.faltan > 0 ? (
        <div className="mono-sm">
          faltan <span style={{ color: "var(--dinero)" }}>{formatoMoneda(plata.mes.faltan)}</span> este mes · {accionCorta(plata)}
        </div>
      ) : (
        <div className="mono-sm">meta del mes cumplida</div>
      )}
    </section>
  );
}
