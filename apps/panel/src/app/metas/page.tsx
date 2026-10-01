"use client";
// Metas · la plata: meta → número del mes → brecha → acción. Nunca un
// porcentaje solo. La primera meta es la del mes (config/plata.json le pone
// nombre y horizonte); las demás duermen hasta que la primera pase de su
// umbral. «Por línea» compara lo que trajo cada línea de ingreso y cuánto
// rindió por hora.
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Header } from "@/components/Header";
import { TabBar } from "@/components/TabBar";
import { Apagado } from "@/components/Apagado";
import { MoneyRow } from "@/components/MoneyRow";
import { Bionica } from "@/components/Bionica";
import { useCargaNucleo } from "@/hooks/useCargaNucleo";
import { nucleo, NucleoApagado, type LineaDelMes, type Meta, type Plata } from "@/lib/nucleo";
import { formatoMoneda, proponer, type Propuesta } from "@/lib/hoy";
import { accionDeLaBrecha, fechaCorta } from "@/lib/formato";

async function cargarMetas() {
  const [plata, libros, tareas] = await Promise.all([nucleo.plata(), nucleo.libros(), nucleo.hoy()]);
  const hayBloque = tareas.some((t) => t.sesiones.some((s) => s.fin === null));
  return { plata, hayBloque, propuesta: proponer(libros, plata) };
}

export default function PaginaMetas() {
  const { datos, error, recargar } = useCargaNucleo(cargarMetas);

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

  const { plata } = datos;
  const [principal, ...dormidas] = plata.metas;

  return (
    <div className="shell">
      <Header />
      <div className="contenedor">
        <MoneyRow plata={plata} />
        <MetaPrincipal plata={plata} meta={principal ?? null} hayBloque={datos.hayBloque} propuesta={datos.propuesta} />
        <div className="card-grid-2">
          <PorLinea plata={plata} />
          {dormidas.map((meta) => (
            <OtraMeta key={meta.nombre} meta={meta} principal={principal} />
          ))}
        </div>
        <p className="voz"><Bionica texto="Meta → número del mes → brecha → acción. Nunca un porcentaje solo." /></p>
      </div>
      <TabBar />
    </div>
  );
}

function horizonte(meta: Meta | null): string {
  if (!meta) return "Meta · mensual";
  return meta.horizonte_meses ? `Meta · ${meta.horizonte_meses} meses` : "Meta";
}

function MetaPrincipal({ plata, meta, hayBloque, propuesta }: { plata: Plata; meta: Meta | null; hayBloque: boolean; propuesta: Propuesta | null }) {
  const router = useRouter();
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const porcentaje = plata.mes.meta > 0 ? Math.round((plata.mes.cobrado / plata.mes.meta) * 100) : 0;
  const avance = Math.min(100, porcentaje);
  const nombre = meta?.nombre ?? null;

  // La acción que cierra la brecha, hecha botón: con una entrega con dinero
  // por delante, seguir con esa; sin ninguna, sentarse a armar una propuesta.
  const entrega = propuesta?.entrega ? propuesta : null;
  const etiqueta = hayBloque ? "Volver al bloque abierto" : entrega ? `Seguir con la de ${entrega.entrega!.cliente}` : "Armar una propuesta";

  async function actuar() {
    if (hayBloque) {
      router.push("/");
      return;
    }
    setOcupado(true);
    try {
      if (entrega) await nucleo.abrirBloque(entrega.titulo, entrega.tema);
      else await nucleo.abrirBloque("Armar una propuesta", null);
      router.push("/");
    } catch (error) {
      setAviso(
        error instanceof NucleoApagado && error.status === 409
          ? "Hay otro bloque abierto. Ciérralo en Hoy y seguimos con este."
          : "No pude abrirlo ahora. Vuelve a tocar en un momento.",
      );
    } finally {
      setOcupado(false);
    }
  }

  return (
    <section aria-label={nombre ? `Meta: ${nombre}` : "Meta del mes"} className="card meta-card">
      <svg width={120} height={120} viewBox="0 0 120 120" role="img" aria-label={`${porcentaje} por ciento de la meta`}>
        <circle cx="60" cy="60" r={50} fill="none" stroke="var(--line)" strokeWidth="8" />
        {avance > 0 ? (
          <circle
            cx="60" cy="60" r={50} fill="none" stroke="var(--dinero)" strokeWidth="8" strokeLinecap="round"
            pathLength="100" strokeDasharray={`${avance} 100`} transform="rotate(-90 60 60)"
          />
        ) : null}
        <text x="60" y="66" textAnchor="middle" fontFamily="var(--font-mono)" fontSize="16" fill="var(--ink)">{porcentaje}%</text>
      </svg>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }}>
        <div className="label">{horizonte(meta)}</div>
        <h2 className="display-xl" style={{ fontSize: 40, lineHeight: "42px" }}>{nombre ?? `${formatoMoneda(plata.mes.meta)}/mes`}</h2>
        <div className="mono-sm">
          {nombre ? <>necesitas <span style={{ color: "var(--dinero)" }}>{formatoMoneda(plata.mes.meta)}/mes</span> · </> : null}
          este mes vas en <span style={{ color: "var(--dinero)" }}>{formatoMoneda(plata.mes.cobrado)}</span>
        </div>
        {plata.mes.faltan > 0 ? (
          <p className="body-txt" style={{ margin: "4px 0 0" }}>
            Brecha: <strong>{formatoMoneda(plata.mes.faltan)}</strong>. {accionDeLaBrecha(plata)}
            {plata.proximo ? <span style={{ color: "var(--ink-muted)" }}> Se entrega {fechaCorta(plata.proximo.fecha)}.</span> : null}
          </p>
        ) : (
          <p className="body-txt" style={{ margin: "4px 0 0" }}>Meta del mes cumplida.</p>
        )}
        {aviso ? <p className="voz" role="status"><Bionica texto={aviso} /></p> : null}
        <div style={{ display: "flex", gap: 10, marginTop: 6, flexWrap: "wrap" }}>
          {plata.mes.faltan > 0 || hayBloque ? (
            <button type="button" className="btn btn-brasa" disabled={ocupado} onClick={actuar}>{etiqueta}</button>
          ) : null}
          <Link href="/proyectos" className="btn btn-secundario">Ver clientes</Link>
        </div>
      </div>
    </section>
  );
}

// «Software (clientes)» → «Software» y «clientes».
function partesDelNombre(nombre: string): { corto: string; entre: string | null } {
  const m = nombre.match(/^(.*?)\s*\((.+)\)\s*$/);
  return m ? { corto: m[1], entre: m[2] } : { corto: nombre, entre: null };
}

function veces(razon: number): string {
  const n = razon >= 3 ? Math.round(razon) : Math.round(razon * 10) / 10;
  return `${String(n).replace(".", ",")}×`;
}

// Qué línea rinde más por hora, con las horas que el núcleo midió. Solo
// compara lo que se puede comparar: plata cobrada y minutos trabajados.
function lecturaPorHora(lineas: LineaDelMes[]): { texto: string; prioriza: string | null } {
  const conRitmo = lineas
    .filter((l) => l.cobrado_mes > 0 && l.minutos_mes > 0)
    .map((l) => ({ ...partesDelNombre(l.nombre), porHora: l.cobrado_mes / (l.minutos_mes / 60) }))
    .sort((a, b) => b.porHora - a.porHora);
  if (conRitmo.length === 0) return { texto: "Todavía no hay cobros con horas medidas este mes.", prioriza: null };
  const [mejor, segunda] = conRitmo;
  const prioriza = mejor.entre ? `Prioriza ${mejor.entre}.` : null;
  if (!segunda) return { texto: `${mejor.corto} trae ${formatoMoneda(mejor.porHora)} por hora este mes.`, prioriza };
  const razon = mejor.porHora / segunda.porHora;
  if (razon < 1.2) return { texto: "Las líneas rinden parecido por hora este mes.", prioriza: null };
  return { texto: `${mejor.corto} rinde ${veces(razon)} más por hora.`, prioriza };
}

const COLOR_DE_LINEA = ["var(--dinero)", "var(--pensar)", "var(--brasa)", "var(--luz)"];

function PorLinea({ plata }: { plata: Plata }) {
  const lineas = plata.por_linea ?? [];
  const lectura = lecturaPorHora(lineas);
  return (
    <section aria-label="Por línea" className="card">
      <div className="label">Por línea · este mes</div>
      {lineas.length > 0 ? (
        <>
          <div style={{ display: "flex", flexDirection: "column", gap: 14, marginTop: 12 }}>
            {lineas.map((linea, i) => {
              const ancho = plata.mes.meta > 0 ? Math.min(100, Math.round((linea.cobrado_mes / plata.mes.meta) * 100)) : 0;
              return (
                <div key={linea.id} style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 8, alignItems: "baseline", fontSize: 16, lineHeight: "24px" }}>
                  <span>{linea.nombre}</span>
                  <span className="mono-sm" style={{ fontVariantNumeric: "tabular-nums" }}>{formatoMoneda(linea.cobrado_mes)}</span>
                  <div
                    role="img"
                    aria-label={`${linea.nombre}: ${formatoMoneda(linea.cobrado_mes)} de ${formatoMoneda(plata.mes.meta)} de la meta del mes`}
                    style={{ gridColumn: "1 / -1", height: 6, borderRadius: "var(--radius-pill)", background: "var(--line)", overflow: "hidden" }}
                  >
                    <i style={{ display: "block", height: "100%", width: `${ancho}%`, borderRadius: "var(--radius-pill)", background: COLOR_DE_LINEA[i % COLOR_DE_LINEA.length] }} />
                  </div>
                </div>
              );
            })}
          </div>
          <p className="body-muted" style={{ margin: "14px 0 0" }}>
            {lectura.texto}
            {lectura.prioriza ? <span style={{ color: "var(--ink)" }}> {lectura.prioriza}</span> : null}
          </p>
        </>
      ) : null}
      {plata.mes.entregas.length > 0 ? (
        <div style={{ marginTop: 14 }}>
          <div className="mono-sm">cobrado este mes</div>
          {plata.mes.entregas.map((entrega, i) => (
            <div className="fila" key={i} style={{ marginTop: i === 0 ? 8 : 0 }}>
              <i className="punto" style={{ background: "var(--dinero)" }} />
              <span style={{ flexGrow: 1 }}>{entrega.cliente}</span>
              <span className="mono-sm">{fechaCorta(entrega.fecha)}</span>
              <span className="mono-sm" style={{ color: "var(--dinero)" }}>{formatoMoneda(entrega.monto)}</span>
            </div>
          ))}
        </div>
      ) : lineas.length === 0 ? (
        <p className="body-muted" style={{ margin: "12px 0 0" }}>Ninguna entrega cobrada todavía este mes.</p>
      ) : null}
    </section>
  );
}

// Una meta que no es la del mes: apagada hasta que la principal pase de su
// umbral. Apagada se dice en voz baja, sin anillo ni número de avance.
function OtraMeta({ meta, principal }: { meta: Meta; principal: Meta | undefined }) {
  const umbral = meta.activa_desde_pct ?? 50;
  const deQuien = principal ? `«${principal.nombre}»` : "la primera meta";
  return (
    <section aria-label={`Meta: ${meta.nombre}`} className="card" style={{ opacity: meta.activa ? 1 : 0.72 }}>
      <div className="label">{horizonte(meta)}</div>
      <h2 className="display-md" style={{ margin: "6px 0" }}>{meta.nombre}</h2>
      <div className="num-lg" style={{ color: meta.activa ? "var(--dinero)" : "var(--ink)" }}>
        {formatoMoneda(meta.monto_mes)}
        <span style={{ fontFamily: "var(--font-sans)", fontSize: 14, fontWeight: 400, letterSpacing: 0, color: "var(--ink-muted)" }}>/mes</span>
      </div>
      <p className="body-muted" style={{ margin: "8px 0 0" }}>
        {meta.activa
          ? `Encendida: ${deQuien} ya pasó de ${umbral} %.`
          : `Empieza cuando ${deQuien} pase de ${umbral} %. Hasta entonces, apagada.`}
      </p>
    </section>
  );
}
