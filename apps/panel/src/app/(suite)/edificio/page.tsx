"use client";
// El edificio: cada piso es un departamento. Donde hay luz, hay trabajo en curso.
import Link from "next/link";
import { Agente, ESTADO_TEXTO } from "@/components/suite/Agente";
import { Marco } from "@/components/suite/Marco";
import { Apagado } from "@/components/Apagado";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo } from "@/lib/nucleo";

export default function Edificio() {
  const { datos, error, recargar } = useCargaNucleo(nucleo.suite);
  if (error && !datos) return <Apagado ultimaVez={null} onReintentar={recargar} />;
  return (
    <Marco color="#5AE4E0" volver={{ href: "/", texto: "Inicio" }}>
      <div className="su-tit">
        <h1>El edificio</h1>
        <p>Cada piso es un departamento. Donde hay luz, hay trabajo en curso.</p>
      </div>
      {!datos ? (
        <p className="su-cargando">Abriendo el edificio…</p>
      ) : (
        <>
          <div className="su-techo">
            <Agente forma={datos.remi.forma} color="#5AE4E0" estado={datos.remi.estado} tam={72} />
            <div>
              <b>Remi</b>
              <span>Tu Jarvis. Sube y baja por todos los pisos.{datos.remi.ahora ? ` Ahora: ${datos.remi.ahora}.` : ""}</span>
            </div>
          </div>
          <div className="su-oscuro su-torre">
            {datos.pisos.map((p) => (
              <Link key={p.id} href={`/d/${p.id}`} className="su-piso" style={{ ["--c" as string]: p.color }} aria-label={`${p.nombre}: ${p.paso.titulo ?? ""}`}>
                {p.luz ? <span className="su-piso-luz" aria-hidden /> : null}
                <div className="nombre">
                  <h2>{p.nombre}</h2>
                  <p>{p.para}</p>
                </div>
                <div className="gente">
                  {p.agentes.map((a) => (
                    <div className="ag" key={a.id}>
                      <Agente forma={a.forma} color={p.color} estado={a.estado} />
                      <b>{a.nombre}</b>
                      <em>{a.ahora || ESTADO_TEXTO[a.estado]}</em>
                    </div>
                  ))}
                </div>
                <div className="tu">
                  <small>Tu paso</small>
                  {p.paso.titulo?.replace(/\.$/, "")}
                </div>
              </Link>
            ))}
          </div>
          <div className="su-suelo" />
        </>
      )}
    </Marco>
  );
}
