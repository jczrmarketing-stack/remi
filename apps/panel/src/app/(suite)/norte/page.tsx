"use client";
// El Norte de INV3RZA, guiado: una pregunta por pantalla. Cada respuesta se guarda al instante en
// mente/negocio/norte.md (POST /suite/norte), así que «Ahora no» nunca pierde nada y se retoma donde quedó.
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Marco } from "@/components/suite/Marco";
import { Apagado } from "@/components/Apagado";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo } from "@/lib/nucleo";

const COLOR = "#FF2D55";
const VOLVER = "/d/direccion";

export default function PaginaNorte() {
  const router = useRouter();
  const { datos, error, recargar } = useCargaNucleo(nucleo.norte);
  const [n, setN] = useState<number | null>(null);
  const [texto, setTexto] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState("");

  // Al llegar: la primera sin responder; si ya está completo, desde la 1 para revisarlo.
  useEffect(() => {
    if (datos && n === null) {
      const inicio = datos.siguiente ?? 1;
      setN(inicio);
      setTexto(datos.preguntas[inicio - 1]?.respuesta ?? "");
    }
  }, [datos, n]);

  if (error && !datos) return <Apagado ultimaVez={null} onReintentar={recargar} />;
  const total = datos?.preguntas.length ?? 6;
  const actual = datos && n ? datos.preguntas[n - 1] : null;

  async function guardar(e?: React.FormEvent) {
    e?.preventDefault();
    const t = texto.trim();
    if (!t || !n || guardando) return;
    setGuardando(true);
    setAviso("");
    try {
      const r = await nucleo.guardarNorte(n, t);
      const sig = n < total ? (r.preguntas.slice(n).find((p) => !p.respuesta)?.n ?? n + 1) : null;
      if (sig === null || (r.completo && n === total)) {
        router.push(VOLVER);
        return;
      }
      setN(sig);
      setTexto(r.preguntas[sig - 1]?.respuesta ?? "");
    } catch {
      setAviso("No pude guardarla. Revisa que Remi esté encendido en el Mac; lo que escribiste sigue aquí.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Marco color={COLOR} volver={{ href: VOLVER, texto: "Dirección" }}>
      {!actual || !n ? (
        <p className="su-cargando">Abriendo tu Norte…</p>
      ) : (
        <>
          <div className="su-avance" role="progressbar" aria-label="Avance del Norte" aria-valuemin={0} aria-valuemax={total} aria-valuenow={n - 1}>
            <i style={{ width: `${((n - 1) / total) * 100}%` }} />
          </div>
          <form className="su-pregunta" onSubmit={guardar}>
            <small>Pregunta {n} de {total}</small>
            <h1 id="su-pregunta">{actual.pregunta}</h1>
            <textarea
              key={n}
              className="su-area"
              aria-labelledby="su-pregunta"
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) guardar();
              }}
              placeholder="Con tus palabras, como se lo dirías a un amigo."
              autoFocus
              disabled={guardando}
            />
            <div className="su-acc">
              <button className="su-btn" type="submit" disabled={guardando || !texto.trim()}>
                {guardando ? "Guardando…" : n === total ? "Guardar y terminar" : "Guardar y seguir"}
              </button>
              <button className="su-no" type="button" onClick={() => router.push(VOLVER)}>
                Ahora no
              </button>
            </div>
            {aviso ? <p className="su-respuesta" role="status">{aviso}</p> : null}
          </form>
        </>
      )}
    </Marco>
  );
}
