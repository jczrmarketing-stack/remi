// El camino en una sola línea de tramos, para el teléfono: lo recorrido en
// luz, el paso de ahora en brasa, lo que falta apagado.
import type { Hito } from "@/lib/nucleo";

const ORDINALES = ["primero", "segundo", "tercero", "cuarto", "quinto", "sexto", "séptimo", "octavo", "noveno", "décimo"];

function descripcion(hitos: Hito[]): string {
  const actual = hitos.findIndex((h) => !h.hecho);
  if (actual < 0) return `Camino completo: ${hitos.length} de ${hitos.length} hitos.`;
  const ordinal = ORDINALES[actual] ?? `número ${actual + 1}`;
  return `${actual} de ${hitos.length} hitos recorridos; el ${ordinal} está encendido.`;
}

export function Tramo({ hitos, brillo = false }: { hitos: Hito[]; brillo?: boolean }) {
  const actual = hitos.findIndex((h) => !h.hecho);
  return (
    <div role="img" aria-label={descripcion(hitos)} style={{ display: "flex", gap: 4 }}>
      {hitos.map((hito, i) => (
        <i
          key={i}
          style={{
            flex: "1 1 0",
            height: 6,
            borderRadius: "var(--radius-pill)",
            background: hito.hecho ? "var(--luz)" : i === actual ? "var(--brasa)" : "var(--line)",
            boxShadow: brillo && i === actual ? "var(--glow-brasa)" : undefined,
          }}
        />
      ))}
    </div>
  );
}
