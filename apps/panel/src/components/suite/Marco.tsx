"use client";
import Link from "next/link";
import type { ReactNode } from "react";
import { ChevronLeft } from "lucide-react";

export function Marca() {
  return (
    <Link href="/" className="su-marca" aria-label="INVERZA, inicio">
      INV<span>E</span>RZA
    </Link>
  );
}

export function fechaLarga(iso?: string) {
  const d = iso ? new Date(`${iso}T12:00:00`) : new Date();
  const t = d.toLocaleDateString("es-CO", { weekday: "long", day: "numeric", month: "long" });
  return t.charAt(0).toUpperCase() + t.slice(1);
}

export function Marco({ color, volver, children }: { color: string; volver?: { href: string; texto: string }; children: ReactNode }) {
  return (
    <main className="su">
      <div className="su-luz-fondo" style={{ background: color }} aria-hidden />
      <div className="su-marco">
        <header className="su-top">
          {volver ? (
            <Link className="su-volver" href={volver.href}>
              <ChevronLeft size={16} strokeWidth={2} aria-hidden />
              {volver.texto}
            </Link>
          ) : (
            <Marca />
          )}
          {volver ? <Marca /> : null}
        </header>
        {children}
      </div>
    </main>
  );
}
