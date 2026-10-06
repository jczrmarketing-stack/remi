"use client";
// Punto de partida (R1.3): recursos, habilidades, lo que cuesta y lo que
// prefiere, cada línea con su origen (medido · dicho · pregunta) y, en una
// habilidad, el dominio (cirujano · sabe · aprendiz) con su evidencia.
// Pantalla aparte, enlazada desde Rumbo — nunca se inventa un valor.
import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { Chip } from "@/components/Chip";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado, type ItemPartida } from "@/lib/nucleo";

const TITULO_DEL_TIPO: Record<string, string> = {
  recurso: "Recursos",
  habilidad: "Habilidades",
  cuesta: "Lo que cuesta",
  preferencia: "Lo que prefieres",
};

const ORDEN_DE_TIPO = ["recurso", "habilidad", "cuesta", "preferencia"];

const COLOR_DE_ORIGEN: Record<ItemPartida["origen"], string> = {
  medido: "var(--dinero)",
  dicho: "var(--ink-muted)",
  pregunta: "var(--pensar)",
};

const COLOR_DE_DOMINIO: Record<string, string> = {
  cirujano: "var(--luz)",
  sabe: "var(--brasa)",
  aprendiz: "var(--ink-muted)",
};

function agrupar(partida: ItemPartida[]): Map<string, ItemPartida[]> {
  const mapa = new Map<string, ItemPartida[]>();
  for (const item of partida) {
    const lista = mapa.get(item.tipo) ?? [];
    lista.push(item);
    mapa.set(item.tipo, lista);
  }
  return mapa;
}

export default function PaginaPartida() {
  const { datos, error, recargar } = useCargaNucleo(() => nucleo.rumbo());

  if (error instanceof NucleoApagado) {
    return (
      <div className="shell">
        <Header sano={false} />
        <Apagado ultimaVez={null} onReintentar={recargar} />
        <TabBar />
      </div>
    );
  }
  if (!datos) {
    return (
      <div className="shell">
        <Header />
        <div className="contenedor"><p className="body-muted">Cargando…</p></div>
      </div>
    );
  }

  const porTipo = agrupar(datos.partida);

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <Link href="/rumbo" className="body-muted" style={{ display: "inline-flex", alignItems: "center", gap: 4, width: "fit-content" }}>
          <ChevronLeft size={16} strokeWidth={1.75} aria-hidden />
          Rumbo
        </Link>
        <h1 className="display-xl" style={{ fontSize: 40, lineHeight: "42px" }}>Punto de partida</h1>
        {datos.partida.length === 0 ? (
          <p className="body-muted">Todavía no hay nada medido ni dicho. Se llena solo con lo que mides y lo que cuentas.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {ORDEN_DE_TIPO.filter((tipo) => porTipo.has(tipo)).map((tipo) => (
              <SeccionTipo key={tipo} tipo={tipo} items={porTipo.get(tipo)!} />
            ))}
          </div>
        )}
      </div>
      <TabBar />
    </div>
  );
}

function SeccionTipo({ tipo, items }: { tipo: string; items: ItemPartida[] }) {
  return (
    <section aria-label={TITULO_DEL_TIPO[tipo] ?? tipo} className="card">
      <div className="label">{TITULO_DEL_TIPO[tipo] ?? tipo}</div>
      <ul style={{ listStyle: "none", margin: "12px 0 0", padding: 0, display: "flex", flexDirection: "column", gap: 10 }}>
        {items.map((item, i) => (
          <li key={i} className="fila" style={{ borderTop: i === 0 ? "none" : undefined, paddingTop: i === 0 ? 0 : 10 }}>
            <i className="punto" style={{ background: COLOR_DE_ORIGEN[item.origen] }} />
            <span style={{ flexGrow: 1, minWidth: 0 }}>{item.texto}</span>
            <span className="mono-sm">{item.valor}</span>
            <Chip mono>{item.origen}</Chip>
            {item.dominio ? (
              <Chip punto={COLOR_DE_DOMINIO[item.dominio]}>{item.dominio}</Chip>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
