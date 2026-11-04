"use client";
// Una caja para pedirle algo a un agente. El Programador corre una tarea de código de verdad
// (/coding/corrida); los demás le llegan a Remi con el nombre del agente, y la respuesta se ve aquí mismo.
import { useState } from "react";
import { nucleo } from "@/lib/nucleo";

export function Pedir({ agente, nombre, clase }: { agente: string; nombre: string; clase?: string }) {
  const [texto, setTexto] = useState("");
  const [resp, setResp] = useState("");
  const [enviando, setEnviando] = useState(false);
  const articulo = agente === "remi" ? "a" : "al";
  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    const t = texto.trim();
    if (!t || enviando) return;
    setEnviando(true);
    setResp("");
    try {
      if (agente === "programador") {
        await nucleo.codingCorrer(t);
        setResp("El Programador empezó. Lo ves en Ingeniería cuando termine.");
      } else {
        const r = await nucleo.abrirDesdeTexto(agente === "remi" ? t : `Para el ${nombre}: ${t}`);
        setResp(r.texto || "Recibido.");
      }
      setTexto("");
    } catch (err) {
      const status = (err as { status?: number }).status;
      setResp(status === 409 ? "Ya hay un trabajo en curso. Cuando termine, le pides el siguiente." : "No pude llegar al núcleo. Revisa que Remi esté encendido en el Mac.");
    } finally {
      setEnviando(false);
    }
  }
  return (
    <>
      <form onSubmit={enviar} className={clase}>
        <input
          className="su-in"
          type="text"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          aria-label={`Pedirle algo ${articulo} ${nombre}`}
          placeholder={enviando ? "Enviando…" : `Pedirle algo ${articulo} ${nombre}`}
          disabled={enviando}
        />
      </form>
      {resp ? <div className="resp" role="status">{resp}</div> : null}
    </>
  );
}
