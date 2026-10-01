"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, Inbox, LineChart, Target } from "lucide-react";

const VISTAS = [
  { href: "/", etiqueta: "Hoy", Icono: Bot },
  { href: "/proyectos", etiqueta: "Proyectos", Icono: LineChart },
  { href: "/metas", etiqueta: "Metas", Icono: Target },
  { href: "/bandeja", etiqueta: "Bandeja", Icono: Inbox },
];

// Solo Hoy y Proyectos importan de verdad en el teléfono (README del
// diseño), pero Metas y Bandeja entran igual: cuatro pestañas, ninguna de
// menos de 44px de alto (acá 56px).
export function TabBar() {
  const ruta = usePathname();
  return (
    <nav aria-label="Vistas" className="tabbar">
      {VISTAS.map(({ href, etiqueta, Icono }) => (
        <Link key={href} href={href} aria-current={ruta === href ? "page" : "false"} aria-label={etiqueta}>
          <Icono size={22} strokeWidth={1.75} aria-hidden />
          <span>{etiqueta}</span>
        </Link>
      ))}
    </nav>
  );
}
