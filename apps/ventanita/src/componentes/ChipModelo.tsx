import { registrar } from "../registro";
import type { MotorDePensar } from "../servidor";
import { type Cerebro, type Nivel, NIVELES, tieneNivel } from "../preferencias";
import "./ChipModelo.css";

const NOMBRE: Record<Cerebro, string> = {
  haiku: "Haiku 4.5",
  sonnet: "Sonnet 5.5",
  opus: "Opus 5.5",
  venice: "Venice",
  ollama: "Ollama",
  prompt: "Prompt",
  "sin-pensar": "Sin pensar",
};

const DETALLE: Record<Cerebro, string> = {
  haiku: "rápido",
  sonnet: "el de siempre",
  opus: "piensa antes",
  venice: "pago",
  ollama: "gratis, local",
  prompt: "encargo para Claude Code",
  "sin-pensar": "nada sale del Mac",
};

const NOMBRE_NIVEL: Record<Nivel, string> = { bajo: "Bajo", medio: "Medio", alto: "Alto" };

const GRUPOS: { titulo: string; cerebros: Cerebro[] }[] = [
  { titulo: "Anthropic · Max", cerebros: ["haiku", "sonnet", "opus"] },
  { titulo: "Otros", cerebros: ["venice", "ollama"] },
  { titulo: "Sin respuesta", cerebros: ["prompt", "sin-pensar"] },
];

interface Props {
  cerebro: Cerebro;
  nivel: Nivel;
  // Lo que dice el núcleo de cada motor: Venice sin clave u Ollama apagado
  // salen en el menú, pero apagados, con el porqué.
  motores: MotorDePensar[];
  deshabilitado: boolean;
  onCerebro: (cerebro: Cerebro) => void;
  onNivel: (nivel: Nivel) => void;
}

/**
 * «Opus 5.5 · Medio»: con qué piensa Remi y cuánto. Son dos menús nativos
 * de macOS con el texto encima: el menú se abre fuera de la ventanita, así
 * que no lo corta aunque la ventana mida 200 px de alto.
 */
export function ChipModelo({ cerebro, nivel, motores, deshabilitado, onCerebro, onNivel }: Props) {
  const disponible = (c: Cerebro) => {
    if (c !== "venice" && c !== "ollama") return true;
    return motores.find((m) => m.id === c)?.disponible ?? true;
  };
  const porque = (c: Cerebro) => motores.find((m) => m.id === c)?.detalle;

  return (
    <div className="chip-modelo" data-deshabilitado={deshabilitado ? "si" : "no"}>
      <label className="chip-modelo__parte chip-modelo__modelo" title={porque(cerebro) ?? DETALLE[cerebro]}>
        <span className="body-sm">{NOMBRE[cerebro]}</span>
        <select
          aria-label="Con qué modelo piensa Remi"
          value={cerebro}
          disabled={deshabilitado}
          onChange={(evento) => {
            const nuevo = evento.target.value as Cerebro;
            registrar("cerebro", { elegido: nuevo });
            onCerebro(nuevo);
          }}
        >
          {GRUPOS.map((grupo) => (
            <optgroup key={grupo.titulo} label={grupo.titulo}>
              {grupo.cerebros.map((c) => (
                <option key={c} value={c} disabled={!disponible(c)}>
                  {`${NOMBRE[c]} — ${disponible(c) ? DETALLE[c] : (porque(c) ?? "no disponible")}`}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>
      {tieneNivel(cerebro) && (
        <label className="chip-modelo__parte chip-modelo__nivel" title="Cuánto piensa antes de contestar">
          <span className="body-sm">{NOMBRE_NIVEL[nivel]}</span>
          <select
            aria-label="Cuánto piensa antes de contestar"
            value={nivel}
            disabled={deshabilitado}
            onChange={(evento) => {
              const nuevo = evento.target.value as Nivel;
              registrar("nivel", { elegido: nuevo });
              onNivel(nuevo);
            }}
          >
            {NIVELES.map((n) => (
              <option key={n} value={n}>
                {NOMBRE_NIVEL[n]}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  );
}
