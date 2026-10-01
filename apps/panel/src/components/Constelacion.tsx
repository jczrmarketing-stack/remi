// La constelación de proyectos (solo escritorio): el tamaño de cada uno es
// su prioridad en el orden del líder y el arco, el camino que lleva
// recorrido. Tocar uno muestra su camino debajo.
import type { Libro } from "@/lib/nucleo";
import { escalonDe, recorridoDe, tonoDe } from "@/lib/lider";
import { nombreCorto } from "@/lib/formato";
import { datosDe } from "@/lib/proyecto";

// Ocho lugares fijos, del más grande al más chico: `x` en % del ancho (la
// constelación se estira con la página), `y` y `d` en px. Están puestos a
// mano para que ningún círculo ni su línea de datos pise a otro.
const LUGARES = [
  { x: 12.5, y: 56, d: 128 },
  { x: 41.7, y: 48, d: 104 },
  { x: 62.5, y: 140, d: 88 },
  { x: 81.25, y: 36, d: 80 },
  { x: 3.75, y: 258, d: 76 },
  { x: 33.3, y: 218, d: 72 },
  { x: 49, y: 262, d: 72 },
  { x: 82.3, y: 212, d: 72 },
];

export const CUPO_CONSTELACION = LUGARES.length;

export function Constelacion({
  libros,
  lider,
  abiertoTema,
  elegido,
  onElegir,
}: {
  // Ya en el orden del líder.
  libros: Libro[];
  lider: Libro | null;
  abiertoTema: string | null;
  elegido: string | null;
  onElegir: (tema: string) => void;
}) {
  return (
    <section
      aria-label="Constelación de proyectos"
      style={{ position: "relative", height: 380, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-md)", overflow: "hidden" }}
    >
      <div className="label" style={{ position: "absolute", left: 24, top: 20 }}>
        Proyectos · tamaño = prioridad · arco = camino recorrido
      </div>
      {libros.slice(0, LUGARES.length).map((libro, i) => {
        const { x, y, d } = LUGARES[i];
        const nombre = nombreCorto(libro.titulo);
        const recorrido = recorridoDe(libro);
        const pct = recorrido ? Math.round((recorrido.hechos / recorrido.total) * 100) : 0;
        const tono = tonoDe(libro, escalonDe(libro, lider, abiertoTema), abiertoTema);
        const marcado = libro.tema === elegido;
        const datos = datosDe(libro);
        return (
          <div key={libro.tema} style={{ position: "absolute", left: `${x}%`, top: y, width: d }}>
            <button
              type="button"
              onClick={() => onElegir(libro.tema)}
              aria-pressed={marcado}
              aria-label={`${nombre}: ver su camino`}
              style={{
                position: "relative",
                display: "grid",
                placeContent: "center",
                width: d,
                height: d,
                padding: 8,
                borderRadius: "var(--radius-pill)",
                background: marcado ? "var(--surface-2)" : "var(--surface)",
                border: `2px solid ${tono}`,
                color: "var(--ink)",
                fontFamily: "var(--font-display)",
                fontSize: d >= 88 ? 18 : d >= 80 ? 15 : 13,
                lineHeight: 1.1,
                textAlign: "center",
              }}
            >
              {pct > 0 ? (
                <svg aria-hidden width={d + 16} height={d + 16} viewBox={`0 0 ${d + 16} ${d + 16}`} style={{ position: "absolute", left: -10, top: -10, pointerEvents: "none" }}>
                  <circle
                    cx={d / 2 + 8}
                    cy={d / 2 + 8}
                    r={d / 2 + 6}
                    fill="none"
                    stroke="var(--luz)"
                    strokeWidth={3}
                    strokeLinecap="round"
                    pathLength={100}
                    strokeDasharray={`${pct} 100`}
                    transform={`rotate(-90 ${d / 2 + 8} ${d / 2 + 8})`}
                  />
                </svg>
              ) : null}
              <span>{nombre}</span>
            </button>
            {datos ? (
              <span
                style={{
                  position: "absolute",
                  top: d + 12,
                  left: "50%",
                  transform: "translateX(-50%)",
                  whiteSpace: "nowrap",
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  letterSpacing: "0.06em",
                  color: "var(--ink-muted)",
                }}
              >
                {datos}
              </span>
            ) : null}
          </div>
        );
      })}
    </section>
  );
}
