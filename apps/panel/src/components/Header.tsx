"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, Compass, Inbox, LineChart, Settings, SunMoon, Target } from "lucide-react";
import { StatusDot } from "@/components/StatusDot";
import { usePreferencias } from "@/hooks/PreferenciasContext";

const VISTAS = [
  { href: "/", etiqueta: "Hoy", Icono: Bot },
  { href: "/proyectos", etiqueta: "Proyectos", Icono: LineChart },
  { href: "/metas", etiqueta: "Metas", Icono: Target },
  { href: "/rumbo", etiqueta: "Rumbo", Icono: Compass },
  { href: "/bandeja", etiqueta: "Bandeja", Icono: Inbox },
  { href: "/semana", etiqueta: "Semana", Icono: SunMoon },
];

export function Header({ sano = true }: { sano?: boolean }) {
  const ruta = usePathname();
  const { prefs, actualizar } = usePreferencias();

  return (
    <header className="header">
      <Link href="/" className="logo">
        Re<em>mi</em>
      </Link>
      <nav aria-label="Vistas" className="nav">
        {VISTAS.map(({ href, etiqueta, Icono }) => {
          // La pantalla de un proyecto (/proyectos/<tema>) sigue siendo «Proyectos».
          const activa = href === "/" ? ruta === "/" : ruta === href || ruta.startsWith(`${href}/`);
          return (
            <Link key={href} href={href} aria-current={activa ? "page" : "false"} className={`nav-link ${activa ? "nav-link--active" : ""}`}>
              <Icono size={20} strokeWidth={1.75} aria-hidden />
              <span>{etiqueta}</span>
            </Link>
          );
        })}
      </nav>
      <div className="header-tools">
        <button
          type="button"
          role="switch"
          aria-checked={prefs.bionica}
          aria-label="Lectura biónica"
          title="Lectura biónica"
          className={`icon-btn ${prefs.bionica ? "icon-btn--on" : ""}`}
          onClick={() => actualizar({ bionica: !prefs.bionica })}
        >
          <b style={{ fontWeight: 700 }}>A</b>
          <span style={{ fontWeight: 400 }}>a</span>
        </button>
        <Link href="/ajustes" aria-label="Ajustes de lectura" title="Ajustes" className="icon-btn">
          <Settings size={18} strokeWidth={1.75} aria-hidden />
        </Link>
        <StatusDot sano={sano} />
      </div>
    </header>
  );
}
