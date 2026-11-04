import type { ListaSuite } from "@/lib/nucleo";
import { Mandar } from "./Mandar";

// `mandarDesde`: cada fila puede mandarse a otro piso (los temas del Editor en Inteligencia).
export function Lista({ lista, mandarDesde }: { lista: ListaSuite; mandarDesde?: string }) {
  return (
    <div>
      <h3>
        {lista.titulo}
        {lista.fuente ? <span>{lista.fuente}</span> : null}
      </h3>
      {lista.filas.length ? (
        <ul>
          {lista.filas.map(([a, b], i) =>
            mandarDesde ? (
              <li key={i} className="su-tema">
                <span className="t">{a}</span>
                {b ? <span>{b}</span> : null}
                <Mandar texto={a} desde={mandarDesde} />
              </li>
            ) : (
              <li key={i}>
                {a}
                <span>{b}</span>
              </li>
            ),
          )}
        </ul>
      ) : (
        <p className="vacio">{lista.vacio || "Nada todavía."}</p>
      )}
    </div>
  );
}
