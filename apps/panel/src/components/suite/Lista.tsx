import type { ListaSuite } from "@/lib/nucleo";

export function Lista({ lista }: { lista: ListaSuite }) {
  return (
    <div>
      <h3>
        {lista.titulo}
        {lista.fuente ? <span>{lista.fuente}</span> : null}
      </h3>
      {lista.filas.length ? (
        <ul>
          {lista.filas.map(([a, b], i) => (
            <li key={i}>
              {a}
              <span>{b}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="vacio">{lista.vacio || "Nada todavía."}</p>
      )}
    </div>
  );
}
