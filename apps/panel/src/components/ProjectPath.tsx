// El camino lineal de un proyecto (nunca un árbol): un solo paso
// encendido, lo recorrido en luz, el futuro apagado.
import type { Hito } from "@/lib/nucleo";

export function ProjectPath({ hitos }: { hitos: Hito[] }) {
  const siguienteIdx = hitos.findIndex((h) => !h.hecho);
  return (
    <div style={{ display: "flex", padding: "10px 0", overflowX: "auto" }}>
      {hitos.map((hito, i) => {
        const actual = i === siguienteIdx;
        const pasado = hito.hecho;
        return (
          <div key={i} style={{ position: "relative", flex: "1 1 0", minWidth: 120, display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
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
            />
            <span style={{ fontSize: 13, lineHeight: "18px", textAlign: "center", color: actual ? "var(--ink)" : "var(--ink-muted)", fontWeight: actual ? 600 : 400 }}>
              {hito.texto}
            </span>
          </div>
        );
      })}
    </div>
  );
}
