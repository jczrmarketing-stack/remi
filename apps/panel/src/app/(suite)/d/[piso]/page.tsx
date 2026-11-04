"use client";
// Un piso del edificio: arriba tu paso, en el medio la oficina con sus agentes, abajo lo que entra.
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Agente, ESTADO_TEXTO } from "@/components/suite/Agente";
import { Lista } from "@/components/suite/Lista";
import { Marco } from "@/components/suite/Marco";
import { Pedir } from "@/components/suite/Pedir";
import { Apagado } from "@/components/Apagado";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, type PisoSuite } from "@/lib/nucleo";

const NOTION_NEWSLETTER = "https://www.notion.so/1cd0f10d6b65441fa7154e60cc04d537";

function Paso({ piso }: { piso: PisoSuite }) {
  const [resp, setResp] = useState("");
  const [luego, setLuego] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const { titulo, contexto, accion, ruta } = piso.paso;
  async function actuar() {
    setEnviando(true);
    try {
      const r = await nucleo.abrirDesdeTexto(`${accion}: ${titulo}`);
      setResp(r.texto || "Remi lo tiene.");
    } catch {
      setResp("No pude llegar al núcleo. Revisa que Remi esté encendido en el Mac.");
    } finally {
      setEnviando(false);
    }
  }
  if (luego) return <section className="su-paso"><p>Bien. Queda aquí cuando quieras.</p></section>;
  return (
    <section className="su-paso" aria-label="Tu paso">
      <h2>{titulo}</h2>
      {contexto ? <p>{contexto}</p> : null}
      <div className="su-acc">
        {ruta && accion ? (
          <Link className="su-btn" href={ruta}>{accion}</Link>
        ) : accion === "Leer en Notion" ? (
          <a className="su-btn" href={NOTION_NEWSLETTER} target="_blank" rel="noreferrer">Leer en Notion</a>
        ) : accion ? (
          <button className="su-btn" type="button" onClick={actuar} disabled={enviando}>{enviando ? "Enviando a Remi…" : accion}</button>
        ) : null}
        <button className="su-no" type="button" onClick={() => setLuego(true)}>Ahora no</button>
      </div>
      {resp ? <p className="su-respuesta" role="status">{resp}</p> : null}
    </section>
  );
}

export default function PaginaPiso() {
  const { piso: id } = useParams<{ piso: string }>();
  const { datos, error, recargar } = useCargaNucleo(nucleo.suite);
  if (error && !datos) return <Apagado ultimaVez={null} onReintentar={recargar} />;
  const piso = datos?.pisos.find((p) => p.id === id);
  if (datos && !piso)
    return (
      <Marco color="#5AE4E0" volver={{ href: "/edificio", texto: "Edificio" }}>
        <p className="su-cargando">Ese piso no existe. Vuelve al edificio para elegir otro.</p>
      </Marco>
    );
  return (
    <Marco color={piso?.color ?? "#5AE4E0"} volver={{ href: "/edificio", texto: "Edificio" }}>
      {!piso ? (
        <p className="su-cargando">Subiendo al piso…</p>
      ) : (
        <>
          <div className="su-tit">
            <h1>{piso.nombre}</h1>
            <p>{piso.para}</p>
          </div>
          <Paso key={piso.id} piso={piso} />
          <section className="su-oscuro su-of" style={{ ["--c" as string]: piso.color }} aria-label="La oficina">
            {piso.luz ? <div className="su-of-luz" aria-hidden /> : null}
            <h3>La oficina</h3>
            <div className="su-gente">
              {piso.agentes.map((a) => (
                <div className="su-ag" key={a.id}>
                  <Agente forma={a.forma} color={piso.color} estado={a.estado} tam={64} />
                  <b>{a.nombre}</b>
                  <div className={`est${a.estado === "error" ? " error" : ""}`}>{a.ahora || ESTADO_TEXTO[a.estado]}</div>
                  <div className="ult">{a.ultimo ? `Último trabajo: ${a.ultimo}` : a.hace}</div>
                  {a.existe ? (
                    <Pedir agente={a.id} nombre={a.nombre} />
                  ) : (
                    <Link className="crear" href="/d/ingenieria">Crearlo con el Programador</Link>
                  )}
                </div>
              ))}
            </div>
          </section>
          <section className="su-en" aria-label="Lo que entra">
            {piso.entra.map((l) => (
              <Lista key={l.titulo} lista={l} mandarDesde={piso.id === "inteligencia" && l.titulo === "Temas del Editor" ? "Inteligencia" : undefined} />
            ))}
          </section>
          {piso.id === "ingenieria" ? (
            <p style={{ marginTop: 32, fontSize: 15, color: "#6E6E73" }}>
              Las pantallas de antes siguen aquí: <Link href="/hoy">Hoy</Link>, <Link href="/proyectos">Proyectos</Link>, <Link href="/metas">Metas</Link>, <Link href="/bandeja">Bandeja</Link> y <Link href="/coding">Programador</Link>.
            </p>
          ) : null}
        </>
      )}
    </Marco>
  );
}
