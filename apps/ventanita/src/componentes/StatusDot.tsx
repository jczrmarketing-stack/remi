import type { Estado } from "../tipos";
import "./StatusDot.css";

interface Props {
  estado: Estado;
}

export function StatusDot({ estado }: Props) {
  return <div className="status-dot" data-estado={estado} aria-hidden="true" />;
}
