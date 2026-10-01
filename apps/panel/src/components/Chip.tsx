import type { ReactNode } from "react";

export function Chip({ children, mono, punto }: { children: ReactNode; mono?: boolean; punto?: string }) {
  return (
    <span className={`chip ${mono ? "chip-mono" : ""}`}>
      {punto ? <i className="chip-punto" style={{ background: punto }} /> : null}
      {children}
    </span>
  );
}
