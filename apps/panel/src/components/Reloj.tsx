"use client";
// El Reloj: mismos datos (minutos del bloque, hito actual/total), tres
// pieles. `instrumento` es la del Design System; `brasa` y `terminal` son
// variantes más simples, elegidas en Ajustes y guardadas en el dispositivo.
import type { PielReloj } from "@/hooks/PreferenciasContext";

const TOPE_MINUTOS_SEGMENTO = 90;

function formatoMin(minutos: number): string {
  return `${minutos}'`;
}

export function Reloj({
  minutos,
  hitoActual,
  hitoTotal,
  piel,
  cerrado,
}: {
  minutos: number;
  hitoActual: number;
  hitoTotal: number;
  piel: PielReloj;
  cerrado?: boolean;
}) {
  const etiqueta = `Reloj: ${minutos} minutos del bloque, hito ${hitoActual} de ${hitoTotal}`;

  if (piel === "terminal") {
    const h = Math.floor(minutos / 60);
    const m = minutos % 60;
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
        <div className="num-lg" style={{ fontSize: 40, color: cerrado ? "var(--luz)" : "var(--brasa)" }} role="img" aria-label={etiqueta}>
          {String(h).padStart(2, "0")}:{String(m).padStart(2, "0")}:00
        </div>
        <span className="mono-sm">hito {hitoActual} de {hitoTotal}</span>
      </div>
    );
  }

  const segmentos = Math.max(hitoTotal, 1);
  const circunferencia = 60;
  const largoSegmento = 377 / segmentos;

  const anillos = Array.from({ length: segmentos }, (_, i) => {
    const num = i + 1;
    const color = num < hitoActual || cerrado ? "var(--luz)" : num === hitoActual ? "var(--brasa)" : "var(--line)";
    const offset = -(largoSegmento * i * 1.06);
    return (
      <circle
        key={i}
        cx="70" cy="70" r={circunferencia}
        fill="none" stroke={color} strokeWidth="7"
        pathLength="377"
        strokeDasharray={`${largoSegmento * 0.9} ${377 - largoSegmento * 0.9}`}
        strokeDashoffset={offset}
        transform="rotate(-90 70 70)"
      />
    );
  });

  if (piel === "brasa") {
    const avance = Math.min(1, minutos / TOPE_MINUTOS_SEGMENTO) * 100;
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
        <svg width={168} height={168} viewBox="0 0 140 140" role="img" aria-label={etiqueta}>
          <circle cx="70" cy="70" r="60" fill="none" stroke="var(--line)" strokeWidth="9" />
          <circle
            cx="70" cy="70" r="60" fill="none" stroke="var(--brasa)" strokeWidth="9"
            strokeLinecap="round" pathLength="100" strokeDasharray={`${avance} 100`}
            transform="rotate(-90 70 70)"
          />
          <text x="70" y="76" textAnchor="middle" className="reloj-num" fontSize="20" fill="var(--ink)">{formatoMin(minutos)}</text>
        </svg>
        <span className="mono-sm">hito {hitoActual} de {hitoTotal}</span>
      </div>
    );
  }

  // instrumento
  const avanceBloque = Math.min(1, minutos / TOPE_MINUTOS_SEGMENTO) * 100;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
      <svg width={168} height={168} viewBox="0 0 140 140" role="img" aria-label={etiqueta}>
        {anillos}
        {cerrado ? (
          <circle cx="70" cy="70" r="26" fill="var(--on-luz)" opacity={0.7} />
        ) : (
          <>
            <circle cx="70" cy="70" r="44" fill="none" stroke="var(--line)" strokeWidth="2" />
            <circle
              cx="70" cy="70" r="44" fill="none" stroke="var(--brasa)" strokeWidth="2.5"
              pathLength="100" strokeDasharray={`${avanceBloque} 100`}
              transform="rotate(-90 70 70)"
            />
            <circle cx="70" cy="70" r="4" fill="var(--ink)" />
            <text x="70" y="94" textAnchor="middle" className="reloj-num">{formatoMin(minutos)}</text>
          </>
        )}
      </svg>
      <span className="mono-sm" style={cerrado ? { color: "var(--on-luz)", opacity: 0.7 } : undefined}>hito {hitoActual} de {hitoTotal}{cerrado ? " · cerrado" : ""}</span>
    </div>
  );
}
