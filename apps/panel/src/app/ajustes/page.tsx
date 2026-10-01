"use client";
import { Header } from "@/components/Header";
import { Bionica } from "@/components/Bionica";
import { usePreferencias, type PielReloj } from "@/hooks/PreferenciasContext";

const EJEMPLO = "Llevás 42 minutos en distribución. La factura de Alfonso vence a las 3 de la tarde.";

export default function PaginaAjustes() {
  const { prefs, actualizar } = usePreferencias();

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <h1 className="display-xl" style={{ fontSize: 40, lineHeight: "42px" }}>Ajustes de lectura</h1>

        <section className="card">
          <div className="label">Lectura · se guarda en este dispositivo</div>
          <div style={{ marginTop: 8 }}>
            <Fila titulo="Tema" texto="Noche de siempre. Día para exteriores; luz pasa a oro oscuro para leerse sobre blanco.">
              <Segmentado>
                {(["noche", "dia"] as const).map((t) => (
                  <button key={t} type="button" className="pref-toggle" aria-pressed={prefs.tema === t} onClick={() => actualizar({ tema: t })}>
                    {t === "noche" ? "Noche" : "Día"}
                  </button>
                ))}
              </Segmentado>
            </Fila>

            <Fila titulo="Lectura biónica" texto="El inicio de cada palabra en negrita, el resto fino. El ojo salta de ancla en ancla. Solo en lo que escribe Remi; nunca en botones, campos ni código.">
              <button
                type="button" role="switch" aria-checked={prefs.bionica} aria-label={prefs.bionica ? "Lectura biónica activada" : "Lectura biónica desactivada"}
                onClick={() => actualizar({ bionica: !prefs.bionica })}
                style={{ position: "relative", width: 56, height: 32, borderRadius: "var(--radius-pill)", border: 0, background: prefs.bionica ? "var(--dinero)" : "var(--line)" }}
              >
                <span aria-hidden style={{ position: "absolute", top: 4, left: prefs.bionica ? 28 : 4, width: 24, height: 24, borderRadius: "var(--radius-pill)", background: prefs.bionica ? "var(--on-dinero)" : "var(--surface)", transition: "left 150ms" }} />
              </button>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12, marginTop: 12 }}>
                {[["1–3 letras", "ancla de 1"], ["4 letras", "ancla de 2"], ["5 o más", "la mitad (impar: mitad + 1)"]].map(([a, b]) => (
                  <div key={a} style={{ padding: "12px 14px", borderRadius: "var(--radius-sm)", background: "var(--surface-2)", border: "1px solid var(--line)" }}>
                    <div className="mono-sm" style={{ color: "var(--dinero)" }}>{a}</div>
                    <div className="body-muted" style={{ marginTop: 4 }}>{b}</div>
                  </div>
                ))}
              </div>
            </Fila>

            <Fila titulo="Intensidad" texto="Cuánto se aclara el resto de la palabra.">
              <div style={{ display: "flex", flexDirection: "column", gap: 8, maxWidth: 420 }}>
                <label htmlFor="intensidad" className="mono-sm" style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>suave</span><span>fuerte</span>
                </label>
                <input
                  id="intensidad" type="range" min={55} max={85} value={prefs.intensidad}
                  onChange={(e) => actualizar({ intensidad: Number(e.target.value) })}
                  style={{ width: "100%", accentColor: "var(--dinero)" }}
                />
              </div>
              <p className="body-txt" style={{ maxWidth: "62ch", marginTop: 12, lineHeight: 1.7 }}>
                <Bionica texto={EJEMPLO} />
              </p>
            </Fila>

            <Fila titulo="Aire" texto="Interlineado y párrafos cortos.">
              <Segmentado>
                {([1.6, 1.7, 1.8] as const).map((a) => (
                  <button key={a} type="button" className="pref-toggle" aria-pressed={prefs.aire === a} onClick={() => actualizar({ aire: a })}>
                    {a.toFixed(1)}
                  </button>
                ))}
              </Segmentado>
            </Fila>

            <Fila titulo="Piel del Reloj" texto="Mismos datos, distinto dibujo.">
              <Segmentado>
                {([["instrumento", "Instrumento"], ["brasa", "Brasa"], ["terminal", "Terminal"]] as [PielReloj, string][]).map(([v, label]) => (
                  <button key={v} type="button" className="pref-toggle" aria-pressed={prefs.pielReloj === v} onClick={() => actualizar({ pielReloj: v })}>
                    {label}
                  </button>
                ))}
              </Segmentado>
            </Fila>

            <Fila titulo="Presupuesto de silencio" texto="Remi interrumpe con datos medidos, nunca por reloj.">
              <ul style={{ margin: 0, paddingLeft: 18 }} className="body-txt">
                <li>Máximo 5 nudges al día, 45 minutos entre dos.</li>
                <li>Nada mientras hay una sesión de Claude Code abierta, salvo un cambio de rumbo.</li>
                <li>«Ahora no» calla esa regla dos horas.</li>
                <li>Uno a la vez, con salida amable que nunca se registra como fallo.</li>
              </ul>
            </Fila>
          </div>
        </section>

        <p className="voz"><Bionica texto="Para vos se siente como alivio. Por eso existe." /></p>
      </div>
    </div>
  );
}

function Fila({ titulo, texto, children }: { titulo: string; texto: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "220px minmax(0, 1fr)", gap: 24, padding: "20px 0", borderTop: "1px solid var(--line)" }}>
      <div>
        <div className="display-md">{titulo}</div>
        <p className="body-muted" style={{ marginTop: 6 }}>{texto}</p>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>{children}</div>
    </div>
  );
}

function Segmentado({ children }: { children: React.ReactNode }) {
  return <div style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "flex-start" }}>{children}</div>;
}
