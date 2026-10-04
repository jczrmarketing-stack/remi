"use client";
// Ajustes → Conexiones: llaves y tokens. El valor nunca vuelve completo
// del núcleo (conexiones.py lo prohíbe) — el campo siempre arranca
// vacío; lo que se ve puesto es `termina_en` como marcador de posición.
// Sin lectura biónica acá: ni en etiquetas, ni en campos, ni en botones.
import { useEffect, useState } from "react";
import { nucleo, type Conexion, type ConexionesEstado, type ConfigGasto, type Prueba } from "@/lib/nucleo";

type Definicion = { nombre: string; etiqueta: string; secreto: boolean; ayuda: string };

const DEFINICIONES: Definicion[] = [
  { nombre: "TELEGRAM_TOKEN", etiqueta: "Telegram · token del bot", secreto: true, ayuda: "De BotFather, con /newbot." },
  { nombre: "TELEGRAM_CHAT_ID", etiqueta: "Telegram · chat_id", secreto: false, ayuda: "El que avisa /start en el log del bot." },
  { nombre: "NOTION_TOKEN", etiqueta: "Notion · token de integración", secreto: true, ayuda: "El secret de la integración interna." },
  { nombre: "NOTION_PAGINA_ID", etiqueta: "Notion · id de la página", secreto: false, ayuda: "La página raíz donde vive el espejo." },
  { nombre: "NOTION_VUELTA", etiqueta: "Notion · lectura de vuelta", secreto: false, ayuda: "«1» prende la lectura de campos de operación; vacío, solo de ida." },
  { nombre: "OPENROUTER_API_KEY", etiqueta: "OpenRouter", secreto: true, ayuda: "Respaldo de charla y trastienda." },
  { nombre: "GROQ_API_KEY", etiqueta: "Groq", secreto: true, ayuda: "Trastienda gratis: resumen, claves, títulos." },
  { nombre: "VENICE_API_KEY", etiqueta: "Venice", secreto: true, ayuda: "Motor manual, pago." },
];

export function Conexiones() {
  const [estado, setEstado] = useState<ConexionesEstado | null>(null);
  const [metaMensual, setMetaMensual] = useState<number | null>(null);
  const [configGasto, setConfigGasto] = useState<ConfigGasto | null>(null);
  const [error, setError] = useState(false);

  const cargar = () => {
    nucleo.conexiones().then(setEstado).catch(() => setError(true));
    nucleo.plata().then((p) => setMetaMensual(p.mes.meta)).catch(() => undefined);
    nucleo.configGasto().then(setConfigGasto).catch(() => undefined);
  };

  useEffect(cargar, []);

  return (
    <section className="card">
      <div className="label">Conexiones · nunca por el túnel, solo desde este Mac</div>
      <div style={{ marginTop: 8 }}>
        <FilaConexion
          titulo="Claude"
          ayuda="Por tu suscripción, sin llave."
          contenido={<span className="mono-sm" style={{ color: "var(--ink-muted)" }}>sin configurar: no hace falta</span>}
        />

        {error ? (
          <p className="body-muted" style={{ padding: "20px 0" }}>No pude leer las conexiones del núcleo.</p>
        ) : !estado ? (
          <p className="body-muted" style={{ padding: "20px 0" }}>Cargando…</p>
        ) : (
          DEFINICIONES.map((def) => (
            <FilaConexion
              key={def.nombre}
              titulo={def.etiqueta}
              ayuda={def.ayuda}
              contenido={<CampoConexion definicion={def} conexion={estado[def.nombre]} onGuardado={cargar} />}
            />
          ))
        )}

        <FilaConexion
          titulo="Meta mensual"
          ayuda="La misma meta que usa /plata — ningún otro lugar la cambia."
          contenido={
            metaMensual != null ? <CampoMetaMensual valorInicial={metaMensual} onGuardado={cargar} /> : <span className="body-muted">Cargando…</span>
          }
        />

        <FilaConexion
          titulo="Tope de gasto"
          ayuda="Antes de una llamada a Venice u OpenRouter: si el día o el mes ya llegaron al tope, Remi sigue con Groq. Claude por tu suscripción no cuenta."
          contenido={
            configGasto != null ? <CampoGasto config={configGasto} onGuardado={cargar} /> : <span className="body-muted">Cargando…</span>
          }
        />
      </div>
    </section>
  );
}

function FilaConexion({ titulo, ayuda, contenido }: { titulo: string; ayuda: string; contenido: React.ReactNode }) {
  return (
    <div className="fila-ajuste">
      <div>
        <div className="display-md">{titulo}</div>
        <p className="body-muted" style={{ marginTop: 6 }}>{ayuda}</p>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>{contenido}</div>
    </div>
  );
}

function CampoConexion({ definicion, conexion, onGuardado }: { definicion: Definicion; conexion: Conexion; onGuardado: () => void }) {
  const [valor, setValor] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [probando, setProbando] = useState(false);
  const [prueba, setPrueba] = useState<Prueba | null>(conexion.ultima_prueba);

  async function guardar() {
    setGuardando(true);
    try {
      await nucleo.guardarConexion(definicion.nombre, valor);
      setValor("");
      setPrueba(null);
      onGuardado();
    } finally {
      setGuardando(false);
    }
  }

  async function probar() {
    setProbando(true);
    try {
      setPrueba(await nucleo.probarConexion(definicion.nombre));
    } finally {
      setProbando(false);
    }
  }

  return (
    <>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <input
          type={definicion.secreto ? "password" : "text"}
          value={valor}
          onChange={(e) => setValor(e.target.value)}
          placeholder={conexion.puesta ? `puesta · termina en ${conexion.termina_en ?? "····"}` : "sin configurar"}
          aria-label={definicion.etiqueta}
          style={{ flexGrow: 1, minWidth: 160, height: 44, borderRadius: "var(--radius-pill)", padding: "0 16px", border: "1px solid var(--line)", background: "var(--surface-2)", color: "var(--ink)" }}
        />
        <button type="button" className="btn btn-secundario" style={{ height: 40 }} disabled={guardando || !valor} onClick={guardar}>
          {guardando ? "Guardando…" : "Guardar"}
        </button>
        <button type="button" className="btn btn-secundario" style={{ height: 40 }} disabled={probando || !conexion.puesta} onClick={probar}>
          {probando ? "Probando…" : "Probar"}
        </button>
      </div>
      {prueba ? (
        <span className="mono-sm" style={{ color: prueba.ok ? "var(--dinero)" : "var(--alerta)" }}>
          {prueba.ok ? "✓ " : "✗ "}{prueba.mensaje_humano}
        </span>
      ) : null}
    </>
  );
}

function CampoGasto({ config, onGuardado }: { config: ConfigGasto; onGuardado: () => void }) {
  const [topeDia, setTopeDia] = useState(String(config.tope_dia_usd));
  const [topeMes, setTopeMes] = useState(String(config.tope_mes_usd));
  const [activo, setActivo] = useState(config.activo);
  const [guardando, setGuardando] = useState(false);

  async function guardar(cambios: Partial<{ tope_dia_usd: number; tope_mes_usd: number; activo: boolean }>) {
    const nuevo = {
      tope_dia_usd: cambios.tope_dia_usd ?? Number(topeDia),
      tope_mes_usd: cambios.tope_mes_usd ?? Number(topeMes),
      activo: cambios.activo ?? activo,
    };
    if (!(nuevo.tope_dia_usd >= 0) || !(nuevo.tope_mes_usd >= 0)) return;
    setGuardando(true);
    try {
      await nucleo.guardarConfigGasto(nuevo);
      onGuardado();
    } finally {
      setGuardando(false);
    }
  }

  return (
    <>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <button
          type="button" role="switch" aria-checked={activo} aria-label={activo ? "Tope de gasto activado" : "Tope de gasto desactivado"}
          onClick={() => {
            const nuevoActivo = !activo;
            setActivo(nuevoActivo);
            guardar({ activo: nuevoActivo });
          }}
          style={{ position: "relative", width: 56, height: 32, borderRadius: "var(--radius-pill)", border: 0, background: activo ? "var(--dinero)" : "var(--line)" }}
        >
          <span aria-hidden style={{ position: "absolute", top: 4, left: activo ? 28 : 4, width: 24, height: 24, borderRadius: "var(--radius-pill)", background: activo ? "var(--on-dinero)" : "var(--surface)", transition: "left 150ms" }} />
        </button>
        <input
          type="number" min={0} step="0.5"
          value={topeDia}
          onChange={(e) => setTopeDia(e.target.value)}
          onBlur={() => guardar({})}
          aria-label="Tope de gasto por día, en dólares"
          style={{ width: 100, height: 44, borderRadius: "var(--radius-pill)", padding: "0 16px", border: "1px solid var(--line)", background: "var(--surface-2)", color: "var(--ink)", fontFamily: "var(--font-mono)" }}
        />
        <span className="body-muted">USD / día</span>
        <input
          type="number" min={0} step="1"
          value={topeMes}
          onChange={(e) => setTopeMes(e.target.value)}
          onBlur={() => guardar({})}
          aria-label="Tope de gasto por mes, en dólares"
          style={{ width: 100, height: 44, borderRadius: "var(--radius-pill)", padding: "0 16px", border: "1px solid var(--line)", background: "var(--surface-2)", color: "var(--ink)", fontFamily: "var(--font-mono)" }}
        />
        <span className="body-muted">USD / mes{guardando ? " · guardando…" : ""}</span>
      </div>
      <span className="mono-sm" style={{ color: "var(--ink-muted)" }}>
        gastado: {config.gastado_dia_usd.toFixed(2)} hoy · {config.gastado_mes_usd.toFixed(2)} este mes
      </span>
    </>
  );
}

function CampoMetaMensual({ valorInicial, onGuardado }: { valorInicial: number; onGuardado: () => void }) {
  const [valor, setValor] = useState(String(valorInicial));
  const [guardando, setGuardando] = useState(false);

  async function guardar() {
    const numero = Number(valor);
    if (!(numero > 0)) return;
    setGuardando(true);
    try {
      await nucleo.guardarMetaMensual(numero);
      onGuardado();
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
      <input
        type="number" min={1} step="1"
        value={valor}
        onChange={(e) => setValor(e.target.value)}
        aria-label="Meta mensual"
        style={{ width: 140, height: 44, borderRadius: "var(--radius-pill)", padding: "0 16px", border: "1px solid var(--line)", background: "var(--surface-2)", color: "var(--ink)", fontFamily: "var(--font-mono)" }}
      />
      <button type="button" className="btn btn-secundario" style={{ height: 40 }} disabled={guardando} onClick={guardar}>
        {guardando ? "Guardando…" : "Guardar"}
      </button>
    </div>
  );
}
