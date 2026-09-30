// El LED de estado de Remi: reposo (dormido), o un color de la rampa
// cuando corresponda. El panel no tiene "escuchando" (eso es la ventanita);
// acá solo importa si el núcleo está sano.
export function StatusDot({ sano }: { sano: boolean }) {
  return (
    <span
      aria-label={sano ? "Remi en reposo" : "Remi no responde"}
      title={sano ? "Remi en reposo" : "Remi no responde"}
      style={{
        width: 10,
        height: 10,
        borderRadius: "var(--radius-pill)",
        background: sano ? "var(--dormido)" : "var(--alerta)",
        display: "inline-block",
      }}
    />
  );
}
