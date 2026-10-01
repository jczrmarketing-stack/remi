import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { PreferenciasProvider } from "@/hooks/PreferenciasContext";
import "./globals.css";

export const metadata: Metadata = {
  title: "Panel de Remi",
  description: "Hoy, Proyectos, Metas y Bandeja — el panel de Remi.",
  manifest: "/manifest.json",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#151112",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap"
        />
      </head>
      <body>
        <PreferenciasProvider>{children}</PreferenciasProvider>
      </body>
    </html>
  );
}
