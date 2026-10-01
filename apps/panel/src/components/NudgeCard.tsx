"use client";
import { useState } from "react";
import type { Nudge } from "@/contratos";
import { Bionica } from "@/components/Bionica";
import { nucleo } from "@/lib/nucleo";

export function NudgeCard({ nudge, onRespondido }: { nudge: Nudge; onRespondido: () => void }) {
  const [enviando, setEnviando] = useState(false);

  async function responder(respuesta: "listo" | "ahora_no") {
    setEnviando(true);
    try {
      await nucleo.responderNudge(nudge.id, respuesta);
      onRespondido();
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section aria-label="Nudge de Remi" className="nudge">
      <div className="label">Remi · nudge tipo {nudge.tipo}</div>
      <p className="body-txt" style={{ maxWidth: "62ch", lineHeight: 1.7 }}>
        <Bionica texto={nudge.voz} />
      </p>
      <div style={{ display: "flex", gap: 10 }}>
        <button type="button" className="btn btn-brasa" disabled={enviando} onClick={() => responder("listo")}>Listo</button>
        <button type="button" className="btn btn-secundario" disabled={enviando} onClick={() => responder("ahora_no")}>Ahora no</button>
      </div>
    </section>
  );
}
