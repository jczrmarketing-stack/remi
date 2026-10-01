// El camino lineal de un proyecto (nunca un árbol): un solo paso
// encendido, lo recorrido en luz, el futuro apagado.
import type { Hito } from "@/lib/nucleo";

export function ProjectPath({ hitos }: { hitos: Hito[] }) {
  const siguienteIdx = hitos.findIndex((h) => !h.hecho);
  // Un camino largo (los diez pasos del SOP de cliente) va más apretado
  // para que entre en una fila.
  const apretado = hitos.length > 6;
  return (
    <ol style={{ listStyle: "none", margin: 0, padding: "10px 0", display: "flex", overflowX: "auto" }}>
      {hitos.map((hito, i) => {
        const actual = i === siguienteIdx;
        const pasado = hito.hecho;
        return (
          <li
            key={i}
            aria-current={actual ? "step" : undefined}
            style={{ position: "relative", flex: "1 1 0", minWidth: apretado ? 84 : 120, display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}
          >
            {i < hitos.length - 1 ? (
              <span aria-hidden style={{ position: "absolute", top: 11, left: "50%", width: "100%", height: 2, background: pasado ? "var(--luz)" : "var(--line)" }} />
            ) : null}
            <span
              aria-hidden
              style={{
                position: "relative", zIndex: 1, width: 24, height: 24, borderRadius: "var(--radius-pill)",
                background: pasado ? "var(--luz)" : "var(--surface)",
                border: `2px solid ${pasado ? "var(--luz)" : actual ? "var(--brasa)" : "var(--line)"}`,
                boxShadow: actual ? "var(--glow-brasa)" : undefined,
                transform: actual ? "scale(1.25)" : undefined,
              }}
            >
              {actual ? <span style={{ position: "absolute", inset: 5, borderRadius: "var(--radius-pill)", background: "var(--brasa)" }} /> : null}
            </span>
            <span style={{ fontSize: apretado ? 12 : 13, lineHeight: apretado ? "16px" : "18px", padding: "0 4px", textAlign: "center", color: actual ? "var(--ink)" : "var(--ink-muted)", fontWeight: actual ? 600 : 400 }}>
              {hito.texto}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
