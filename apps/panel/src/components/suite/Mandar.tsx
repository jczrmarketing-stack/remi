"use client";
// Al final de una fila: «Mandar» despliega en línea los pisos a los que puede ir la idea.
// Al elegir, la idea queda en el cajón de ese piso (POST /suite/guardar) y aquí solo se confirma con texto.
import { useEffect, useRef, useState } from "react";
import { nucleo } from "@/lib/nucleo";

const DESTINOS = [
  { id: "oferta", nombre: "Oferta" },
  { id: "marketing", nombre: "Marketing" },
  { id: "ventas", nombre: "Ventas" },
];

export function Mandar({ texto, desde }: { texto: string; desde: string }) {
  const [abierto, setAbierto] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState("");
  const boton = useRef<HTMLButtonElement>(null);
  const primero = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (abierto) primero.current?.focus();
  }, [abierto]);

  function cerrar() {
    setAbierto(false);
    boton.current?.focus();
  }

  async function mandar(piso: string, nombre: string) {
    setEnviando(true);
    try {
      await nucleo.suiteGuardar(piso, texto, desde);
      setAviso(`Guardado en ${nombre}`);
      setAbierto(false);
      boton.current?.focus();
    } catch {
      setAviso("No pude guardarlo. Revisa que Remi esté encendido en el Mac.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      <button
        ref={boton}
        className="su-mandar"
        type="button"
        aria-expanded={abierto}
        aria-label={`Mandar «${texto}» a otro piso`}
        onClick={() => (abierto ? cerrar() : (setAviso(""), setAbierto(true)))}
      >
        Mandar
      </button>
      {abierto ? (
        <div className="su-destinos" role="group" aria-label="Mandar a" onKeyDown={(e) => e.key === "Escape" && cerrar()}>
          Mandar a{" "}
          {DESTINOS.map((d, i) => (
            <span key={d.id}>
              <button ref={i === 0 ? primero : undefined} className="su-mandar" type="button" disabled={enviando} onClick={() => mandar(d.id, d.nombre)}>
                {d.nombre}
              </button>
              {i < DESTINOS.length - 1 ? ", " : ""}
            </span>
          ))}
        </div>
      ) : null}
      {aviso ? (
        <p className="su-guardado" role="status">
          {aviso}
        </p>
      ) : null}
    </>
  );
}
