"use client";
// Aplica lectura biónica SOLO a lo que escribe Remi (nudges, propuestas,
// párrafos). Nunca en botones, campos, código ni la voz corta en serif —
// quien use este componente en esos sitios está violando la regla, así
// que no se ofrece una variante para eso.
import type { CSSProperties } from "react";
import { partirBionica, perillasBionica } from "@/bionica";
import { usePreferencias } from "@/hooks/PreferenciasContext";

export function Bionica({ texto, className }: { texto: string; className?: string }) {
  const { prefs } = usePreferencias();
  if (!prefs.bionica) return <span className={className}>{texto}</span>;

  const { pesoAncla, tintaResto, interlineado } = perillasBionica((prefs.intensidad - 55) / 30);
  const estilo: CSSProperties = {
    "--peso-ancla": pesoAncla,
    "--tinta-resto": tintaResto / 100,
    "--interlineado-bionico": prefs.aire ?? interlineado,
  } as CSSProperties;

  return (
    <span className={`bionica ${className ?? ""}`} style={estilo}>
      {partirBionica(texto).map((trozo, i) => {
        if (trozo.tipo === "ancla") return <b key={i}>{trozo.texto}</b>;
        if (trozo.tipo === "resto") return <span className="resto" key={i}>{trozo.texto}</span>;
        return <span key={i}>{trozo.texto}</span>;
      })}
    </span>
  );
}
