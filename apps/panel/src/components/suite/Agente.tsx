// Los agentes de INV3RZA: formas propias y minimalistas, una por agente. El color es el de su piso;
// el estado se lee en la cara: ojos abiertos (esperando), flotando (trabajando), ojos cerrados
// (durmiendo), punteado gris (por crear). Solo el que trabaja se mueve.
import type { ReactElement } from "react";
import type { EstadoAgente, FormaAgente } from "@/lib/nucleo";

const FORMAS: Record<FormaAgente, { d: ReactElement; cx: number; cy: number }> = {
  orbe: { d: <circle cx="32" cy="34" r="22" />, cx: 32, cy: 32 },
  tri: { d: <path d="M32 10L56 54H8z" strokeLinejoin="round" />, cx: 32, cy: 40 },
  glifo: { d: <path d="M14 12h36v42H14v-8h26v-6H18v-8h22v-6H14z" />, cx: 26, cy: 16.5 },
  cuadro: { d: <rect x="11" y="13" width="42" height="42" rx="13" />, cx: 32, cy: 32 },
  rombo: { d: <path d="M32 8l24 26-24 26L8 34z" strokeLinejoin="round" />, cx: 32, cy: 32 },
  media: { d: <path d="M8 50a24 24 0 0 1 48 0z" />, cx: 32, cy: 40 },
  hex: { d: <path d="M32 9l22 12.5v25L32 59 10 46.5v-25z" strokeLinejoin="round" />, cx: 32, cy: 32 },
  pildora: { d: <rect x="17" y="8" width="30" height="50" rx="15" />, cx: 32, cy: 26 },
};

function Ojos({ estado, cx, cy, gap }: { estado: EstadoAgente; cx: number; cy: number; gap: number }) {
  const a = cx - gap / 2;
  const b = cx + gap / 2;
  if (estado === "durmiendo")
    return <path d={`M${a - 3.5} ${cy}h7M${b - 3.5} ${cy}h7`} stroke="#141416" strokeWidth={2.6} strokeLinecap="round" />;
  if (estado === "por_crear")
    return (
      <>
        <circle cx={a} cy={cy} r={2} fill="#6E6E73" />
        <circle cx={b} cy={cy} r={2} fill="#6E6E73" />
      </>
    );
  return (
    <>
      <rect x={a - 2.3} y={cy - 5} width={4.6} height={10} rx={2.3} fill="#141416" />
      <rect x={b - 2.3} y={cy - 5} width={4.6} height={10} rx={2.3} fill="#141416" />
    </>
  );
}

export function Agente({ forma, color, estado, tam = 60 }: { forma: FormaAgente; color: string; estado: EstadoAgente; tam?: number }) {
  const f = FORMAS[forma] ?? FORMAS.orbe;
  const crear = estado === "por_crear";
  const relleno = crear
    ? { fill: "none", stroke: "#5A5A5F", strokeWidth: 2, strokeDasharray: "4 4" }
    : { fill: estado === "error" ? "#FF6B6B" : color, opacity: estado === "durmiendo" ? 0.45 : 1 };
  return (
    <svg className={estado === "trabajando" ? "su-sh-trab" : undefined} width={tam} height={tam} viewBox="0 0 64 64" aria-hidden>
      <g {...relleno}>{f.d}</g>
      <Ojos estado={estado} cx={f.cx} cy={f.cy} gap={forma === "glifo" ? 9 : 10} />
    </svg>
  );
}

export const ESTADO_TEXTO: Record<EstadoAgente, string> = {
  trabajando: "Trabajando",
  esperando: "Esperando",
  durmiendo: "Durmiendo",
  error: "Con un problema",
  por_crear: "Por crear",
};
