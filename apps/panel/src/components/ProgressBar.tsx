// Una barra, sin relleno de tarjeta: el avance en un color de la rampa
// sobre la pista `line`. Usada donde Rumbo mide avance — horas de la
// semana, apuestas, cuenta hacia atrás.
export function ProgressBar({ pct, color = "var(--dinero)", etiqueta }: { pct: number; color?: string; etiqueta: string }) {
  const ancho = Math.max(0, Math.min(100, Math.round(pct)));
  return (
    <div
      role="img"
      aria-label={etiqueta}
      style={{ height: 6, borderRadius: "var(--radius-pill)", background: "var(--line)", overflow: "hidden" }}
    >
      <i style={{ display: "block", height: "100%", width: `${ancho}%`, borderRadius: "var(--radius-pill)", background: color }} />
    </div>
  );
}
