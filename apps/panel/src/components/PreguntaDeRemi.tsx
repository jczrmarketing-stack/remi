"use client";
// Remi pregunta lo que le falta (Biblia, Parte VII): cuando a un libro le
// falta un dato, la pregunta espera callada en la pantalla de ese proyecto.
// Una a la vez. «Después» no se cuenta y esa pregunta no vuelve ese día. La
// respuesta la guarda el núcleo donde corresponde (el libro o la base) y
// Remi lo confirma en una frase.
import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { Bionica } from "@/components/Bionica";
import { nucleo, type Pregunta } from "@/lib/nucleo";

// Una pista del formato, según el dato que falta. Solo pista: la etiqueta
// del campo es la pregunta misma.
function pistaDe(campo: string): string {
  // El núcleo nombra los campos del libro sin prefijo («tipo», «cliente», «ruta»).
  const dato = campo.replace(/^libro\./, "");
  if (dato.endsWith(".cobrado")) return "Ej.: 1.500";
  if (dato.endsWith(".listo_cuando")) return "Ej.: la demo corre con datos reales";
  if (dato === "cliente") return "Ej.: Alfonso";
  if (dato === "tipo") return "De un cliente o tuyo";
  if (dato === "ruta") return "Ej.: ~/proyectos/upvisuals";
  return "";
}

type Vista =
  | { modo: "preguntando"; pregunta: Pregunta; voz: string }
  | { modo: "anotado"; voz: string }
  | { modo: "callada" };

export function PreguntaDeRemi({ tema, nombre, onAnotado }: { tema: string; nombre: string; onAnotado: () => void }) {
  const idPregunta = useId();
  const campo = useRef<HTMLInputElement>(null);
  const [cola, setCola] = useState<Pregunta[]>([]);
  const [vista, setVista] = useState<Vista>({ modo: "callada" });
  const [texto, setTexto] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    let vivo = true;
    nucleo
      .preguntas(tema)
      .then((pendientes) => {
        if (!vivo || pendientes.length === 0) return;
        setCola(pendientes.slice(1));
        setVista({ modo: "preguntando", pregunta: pendientes[0], voz: pendientes[0].voz });
      })
      .catch(() => undefined); // sin preguntas no se rompe nada: la tarjeta no aparece
    return () => {
      vivo = false;
    };
  }, [tema]);

  if (vista.modo === "callada") return null;

  async function responder(evento: FormEvent) {
    evento.preventDefault();
    if (vista.modo !== "preguntando") return;
    if (!texto.trim()) {
      campo.current?.focus();
      return;
    }
    setOcupado(true);
    setAviso(null);
    try {
      const resultado = await nucleo.responderPregunta(vista.pregunta.id, texto.trim());
      if (resultado.pregunta.estado === "respondida") {
        setTexto("");
        setVista({ modo: "anotado", voz: resultado.voz });
        onAnotado();
      } else {
        // No se entendió: Remi vuelve a preguntar con el formato y no guardó nada.
        setVista({ modo: "preguntando", pregunta: resultado.pregunta, voz: resultado.voz });
        campo.current?.focus();
      }
    } catch {
      setAviso("No pude guardarlo. Tu respuesta sigue aquí: vuelve a tocar «Responder» en un momento.");
    } finally {
      setOcupado(false);
    }
  }

  async function despues() {
    if (vista.modo !== "preguntando") return;
    setOcupado(true);
    try {
      await nucleo.dejarPreguntaParaDespues(vista.pregunta.id);
    } catch {
      // Si no se pudo avisar al núcleo, igual se calla en esta visita.
    } finally {
      setOcupado(false);
      setTexto("");
      setCola([]);
      setVista({ modo: "callada" });
    }
  }

  function otra() {
    const [siguiente, ...resto] = cola;
    if (!siguiente) {
      setVista({ modo: "callada" });
      return;
    }
    setCola(resto);
    setVista({ modo: "preguntando", pregunta: siguiente, voz: siguiente.voz });
  }

  if (vista.modo === "anotado") {
    return (
      <section aria-label="Remi anotó la respuesta" className="nudge" style={{ borderLeftColor: "var(--luz)" }}>
        <div className="label">Remi · anotado en el libro</div>
        <p className="voz" role="status"><Bionica texto={vista.voz} /></p>
        {cola.length > 0 ? (
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <button type="button" className="btn btn-secundario" onClick={otra}>Tengo otra pregunta</button>
            <span className="mono-sm">Una a la vez. La siguiente espera a que la pidas.</span>
          </div>
        ) : null}
      </section>
    );
  }

  return (
    <section aria-label="Remi pregunta" className="nudge">
      <div className="label">
        Remi pregunta<span className="solo-escritorio-en-linea"> · le falta un dato de este libro</span>
      </div>
      <p id={idPregunta} className="voz"><Bionica texto={vista.voz} /></p>
      <form onSubmit={responder} className="pregunta-fila">
        <input
          ref={campo}
          type="text"
          value={texto}
          onChange={(e) => {
            setTexto(e.target.value);
            if (aviso) setAviso(null);
          }}
          aria-labelledby={idPregunta}
          placeholder={pistaDe(vista.pregunta.campo)}
          autoComplete="off"
          className="pregunta-campo"
        />
        <div className="pregunta-botones">
          <button type="submit" className="btn btn-luz" disabled={ocupado}>Responder</button>
          <button type="button" className="btn btn-secundario" disabled={ocupado} onClick={despues}>Después</button>
        </div>
      </form>
      {aviso ? <p className="body-muted" role="status" style={{ margin: 0, color: "var(--ink)" }}>{aviso}</p> : null}
      <div className="mono-sm">
        <span className="solo-escritorio-en-linea">Lo anoto en el libro de {nombre}. «Después» no se cuenta: vuelvo a preguntar mañana.</span>
        <span className="solo-telefono-en-linea">Lo anoto en el libro. «Después» no se cuenta.</span>
      </div>
    </section>
  );
}
