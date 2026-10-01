"use client";
// Revisión semanal (README del diseño): guion estático por ahora — el
// núcleo no tiene una ruta de resumen semanal todavía (queda anotado en
// la bitácora). La plata sí es real (viene de /plata); el resto son las
// cinco preguntas fijas del guion, más el temporizador de 20 minutos.
import { useEffect, useState } from "react";
import { Header } from "@/components/Header";
import { Apagado } from "@/components/Apagado";
import { Bionica } from "@/components/Bionica";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado } from "@/lib/nucleo";
import { formatoMoneda } from "@/lib/hoy";

const VEINTE_MIN = 20 * 60;

const PREGUNTAS_FIJAS = [
  { titulo: "Lo cerrado", texto: "Lo que se terminó esta semana. Se celebra una vez y se pasa." },
  { titulo: "Lo aplazado", texto: "Lo que no avanzó. Sin contador: se reprograma y ya." },
  { titulo: "Ideas frías", texto: "Lo que espera en la Bandeja. Soltar, mantener o hacer tarea." },
  { titulo: "La locura de la semana", texto: "Una sola. La que más importa, dicha en voz baja." },
];

export default function PaginaSemana() {
  const { datos: plata, error, recargar } = useCargaNucleo(nucleo.plata);
  const [segundos, setSegundos] = useState(VEINTE_MIN);
  const [corriendo, setCorriendo] = useState(false);

  useEffect(() => {
    if (!corriendo) return;
    const id = setInterval(() => setSegundos((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [corriendo]);

  if (error instanceof NucleoApagado) {
    return (
      <div className="shell">
        <Header sano={false} />
        <Apagado ultimaVez={null} onReintentar={recargar} />
      </div>
    );
  }

  const m = String(Math.floor(segundos / 60)).padStart(2, "0");
  const s = String(segundos % 60).padStart(2, "0");

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <section className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 16 }}>
            <div className="label">Revisión semanal · lunes · 20 minutos</div>
            <button type="button" className="num-lg" style={{ fontSize: 40, color: "var(--dinero)", background: "transparent", border: 0 }} onClick={() => setCorriendo((c) => !c)} aria-label={corriendo ? "Pausar" : "Empezar"}>
              {m}:{s}
            </button>
          </div>
          <div style={{ marginTop: 12 }}>
            <div style={{ display: "grid", gridTemplateColumns: "44px minmax(0, 1fr)", gap: 16, padding: "16px 0", borderTop: "1px solid var(--line)" }}>
              <span style={{ width: 44, height: 44, borderRadius: "var(--radius-pill)", display: "grid", placeContent: "center", fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 500, background: "var(--luz)", color: "var(--on-luz)", border: "1px solid var(--luz)" }}>1</span>
              <div>
                <div className="display-md">La plata del mes</div>
                {plata ? (
                  <p className="body-muted" style={{ marginTop: 6 }}>
                    {formatoMoneda(plata.mes.cobrado)} de {formatoMoneda(plata.mes.meta)}. {plata.mes.faltan > 0 ? `Brecha: ${formatoMoneda(plata.mes.faltan)}. ¿Qué la cierra esta semana?` : "Meta cumplida."}
                  </p>
                ) : (
                  <p className="body-muted" style={{ marginTop: 6 }}>Cargando…</p>
                )}
              </div>
            </div>
            {PREGUNTAS_FIJAS.map((p, i) => (
              <div key={p.titulo} style={{ display: "grid", gridTemplateColumns: "44px minmax(0, 1fr)", gap: 16, padding: "16px 0", borderTop: "1px solid var(--line)" }}>
                <span style={{ width: 44, height: 44, borderRadius: "var(--radius-pill)", display: "grid", placeContent: "center", fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 500, background: "var(--surface-2)", color: "var(--ink-muted)", border: "1px solid var(--line)" }}>{i + 2}</span>
                <div>
                  <div className="display-md">{p.titulo}</div>
                  <p className="body-muted" style={{ marginTop: 6 }}>{p.texto}</p>
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16, display: "flex", gap: 10 }}>
            <a href="/" className="btn btn-brasa">Siguiente paso</a>
            <a href="/" className="btn btn-secundario">Guardar y cerrar</a>
          </div>
        </section>
        <p className="voz"><Bionica texto="Remi guía; vos decidís. Veinte minutos, cinco preguntas, una locura." /></p>
      </div>
    </div>
  );
}
