"use client";
// Inicio de INV3RZA Suite: tu único paso de hoy, el Norte, Remi y el edificio en pequeño.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Agente } from "@/components/suite/Agente";
import { Marco, fechaLarga } from "@/components/suite/Marco";
import { Pedir } from "@/components/suite/Pedir";
import { Apagado } from "@/components/Apagado";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo } from "@/lib/nucleo";

const dinero = (n?: number) => (n == null ? "" : `US$${n.toLocaleString("es-CO")}`);

export default function Inicio() {
  const { datos, error, recargar } = useCargaNucleo(nucleo.suite);
  const router = useRouter();
  const [empezando, setEmpezando] = useState(false);
  const [luego, setLuego] = useState(false);

  if (error && !datos) return <Apagado ultimaVez={null} onReintentar={recargar} />;
  if (!datos)
    return (
      <Marco color="#5AE4E0">
        <p className="su-cargando">Abriendo el edificio…</p>
      </Marco>
    );

  const { foco, norte, remi, pisos } = datos;
  const avance = norte.actual && norte.escalon ? Math.min(100, Math.round((norte.actual / norte.escalon) * 100)) : 0;

  async function empezar() {
    setEmpezando(true);
    try {
      await nucleo.abrirBloque(foco.titulo, null);
    } catch {
      // 409: ya hay un bloque abierto. Igual se va a Hoy, donde está el reloj.
    }
    router.push("/hoy");
  }

  return (
    <Marco color="#5AE4E0">
      <p className="su-fecha" style={{ position: "absolute", right: 0, top: 4, margin: 0 }}>{fechaLarga(datos.fecha)}</p>
      <section className="su-paso" aria-label="Tu paso de hoy" style={{ marginTop: 72 }}>
        {luego ? (
          <p>Bien. Queda aquí cuando quieras.</p>
        ) : (
          <>
            <h2>{foco.titulo || "Hoy no hay nada urgente."}</h2>
            {foco.contexto ? <p>{foco.contexto}</p> : null}
          </>
        )}
        {norte.escalon ? (
          <div className="su-norte">
            <span>Norte</span>
            <span className="barra" aria-hidden><i style={{ width: `${avance}%` }} /></span>
            <span>
              {dinero(norte.actual)} de {dinero(norte.escalon)} al mes
            </span>
          </div>
        ) : null}
        {!luego && foco.titulo ? (
          <div className="su-acc">
            <button className="su-btn" type="button" onClick={empezar} disabled={empezando}>
              {empezando ? "Abriendo…" : "Empezar 50 minutos"}
            </button>
            <button className="su-no" type="button" onClick={() => setLuego(true)}>
              Ahora no
            </button>
          </div>
        ) : null}
      </section>

      <section className="su-oscuro su-mini" aria-label="El edificio">
        <div className="su-mini-remi">
          <Agente forma={remi.forma} color="#5AE4E0" estado={remi.estado} tam={44} />
          <div>
            <b>Remi</b>
            <em>{remi.ahora || "Listo para lo que necesites"}</em>
          </div>
          <Pedir agente="remi" nombre="Remi" />
        </div>
        {pisos.map((p) => (
          <Link key={p.id} href={`/d/${p.id}`} className="su-fila" style={{ ["--c" as string]: p.color }}>
            {p.luz ? <span className="su-fila-luz" aria-hidden /> : null}
            <span className="n">{p.nombre}</span>
            <span className="g">
              {p.agentes.map((a) => (
                <Agente key={a.id} forma={a.forma} color={p.color} estado={a.estado} tam={30} />
              ))}
            </span>
            <span className="p">{p.paso.titulo?.replace(/\.$/, "") || ""}</span>
          </Link>
        ))}
      </section>
      <p style={{ marginTop: 20, fontSize: 15 }}>
        <Link href="/edificio" style={{ color: "#48484A" }}>Ver el edificio completo</Link>
      </p>
    </Marco>
  );
}
