"use client";
// Núcleo caído: sin rojo, sin alarma. Reintenta cada 30 s, sin ruido.
import { useEffect, useState } from "react";

export function Apagado({ ultimaVez, onReintentar }: { ultimaVez: string | null; onReintentar: () => void }) {
  const [segundos, setSegundos] = useState(30);

  useEffect(() => {
    const id = setInterval(() => {
      setSegundos((s) => {
        if (s <= 1) {
          onReintentar();
          return 30;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [onReintentar]);

  return (
    <div className="contenedor">
      <section className="card" style={{ padding: "48px 32px", display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}>
        <span aria-hidden style={{ width: 12, height: 12, borderRadius: "var(--radius-pill)", background: "var(--dormido)" }} />
        <h1 className="display-md" style={{ fontSize: 40, lineHeight: "42px", color: "var(--ink-muted)" }}>Remi no responde.</h1>
        <p className="voz">
          {ultimaVez ? `Última vez que hablamos: ${ultimaVez}. ` : ""}Reintento en {segundos} segundos, sin ruido.
        </p>
        <div className="mono-sm" style={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: "var(--radius-sm)", padding: "10px 14px" }}>
          Si sigue así: <span style={{ color: "var(--ink)" }}>scripts/doctor.sh</span> revisa las diez piezas y dice cuál.
        </div>
        <button type="button" className="btn btn-secundario" onClick={() => { setSegundos(30); onReintentar(); }}>
          Reintentar ahora
        </button>
      </section>
      <p className="body-muted">Sin rojo, sin alarma: un núcleo caído es un dato, no una falla tuya.</p>
    </div>
  );
}
