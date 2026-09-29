# Bitácora de Remi

El punto de encuentro de los tres. **Claude Code** construye, **Grok** audita y propone,
**Claude** verifica y escribe los encargos. Juan Camilo pega los mensajes entre nosotros y
decide.

Append-only: la entrada nueva va **arriba**, la vieja abajo. Nadie edita una entrada ya
escrita; si algo cambió, se escribe una entrada nueva. La bitácora es para discutir; lo que
se construye sale de un encargo, no de un hallazgo suelto.

Formato de una entrada construida:

```
## <fecha> · <fase> · construido · <hash corto>
- Qué cambió: 3–6 líneas, archivos tocados.
- Decisiones que tomé sin preguntar: lista, o «ninguna».
- Dudas abiertas: lista, o «ninguna».
- Cómo probarlo a mano: pasos.
```

---

## 2026-09-29 · 2g app instalada · construido · b464770

- **Qué cambió:** Remi es una app de verdad. Ícono propio (la brasa) en
  `apps/ventanita/src-tauri/icons/` desde `design/icono-remi-1024.png`; `productName` pasa a
  «Remi» en `tauri.conf.json`; una sola instancia con `tauri-plugin-single-instance` en
  `src-tauri/src/lib.rs`; build release del `.app` y copia a `/Applications`; entitlements de
  micrófono y firma ad-hoc del bundle; y `scripts/instalar.sh`, que deja el núcleo como
  LaunchAgent con `RunAtLoad` y `KeepAlive`.
- **Decisiones que tomé sin preguntar:**
  1. `tauri icon` genera también juegos para Android e iOS. Remi no tiene esos destinos: los
     borré y los puse en `.gitignore` en vez de commitear 35 archivos de adorno.
  2. El build salía «linker-signed» y `codesign -dv` decía `Info.plist=not bound`, que es
     justo lo que lee TCC. En vez de firmar a mano cada vez, puse `entitlements` y
     `signingIdentity: "-"` en `tauri.conf.json`, para que todo build futuro salga firmado.
  3. El precalentado de la voz vivía en `__main__` de `servidor.py`, y launchd levanta
     `uvicorn servidor:app`: nunca corría. Pasó al ciclo de vida de la app.
  4. `launchctl bootout` vuelve antes de que el servicio se vaya; recargar enseguida lo
     dejaba abajo en silencio. El instalador ahora espera a que desaparezca.
- **Dudas abiertas:**
  1. **El micrófono no está probado.** El permiso lo pide macOS recién cuando la app intenta
     grabar, y eso pasa con dos clicks en la ventanita. No toco el mouse ni el teclado de
     Juan Camilo, así que ese paso es suyo.
  2. El encargo me llegó **cortado** a mitad del punto 6 («…hay que resolverlo antes de»).
     Lo leí como «antes de cerrar la fase» y lo verifiqué igual. Si había puntos 7 en
     adelante, no me llegaron.
  3. Sigue sin resolverse qué fase va después (2f no existe en el repo; ver la entrada de
     2e.0).
- **Cómo probarlo a mano:**
  1. Cerrá la terminal. Abrí Remi desde Launchpad o Spotlight: el ícono es la brasa.
  2. Doble click en la ventanita: macOS tiene que preguntar por el micrófono. Aceptá, hablá
     y confirmá que transcribe.
  3. Abrila otra vez desde Launchpad estando abierta: no aparece una segunda, se enfoca la
     que hay.
  4. Prendé «pensar con Claude» y mandá «¿qué te conté de Shopify?».
  5. `tail -f ~/Library/Logs/Remi/nucleo.log` mientras hacés todo eso.

## 2026-09-29 · 2e.0 memoria · construido · 30229d7

- **Qué cambió:** el estante. `Memoria` entra por `contratos/contratos.json` y de ahí se
  generan modelo y tipo; tabla `memoria` con índices en `nucleo/db.py`. El índice (título y
  con qué me quedé, nunca el cuerpo) viaja en el system prompt de `nucleo/pensar.py`. El
  cuerpo se baja por `nucleo/memoria_mcp.py`, servidor MCP con `leer` y `guardar`, al que la
  CLI encerrada accede por `--mcp-config` con esas dos herramientas y nada más. Las mismas
  operaciones por HTTP en `/memoria` (`nucleo/servidor.py`), semilla en
  `nucleo/sembrar_memoria.py`, `.mcp.json` en la raíz y `nucleo/pruebas/test_memoria.py`.
- **Decisiones que tomé sin preguntar:**
  1. El encargo decía «modelo Memoria en modelos.py», pero ese archivo es **generado**. Lo
     puse en el contrato y enseñé a los dos generadores `string(80)`, para que el largo
     máximo viva en el contrato y no suelto en el servidor.
  2. **Techo de salida 200 → 1500.** Medido: el JSON de una llamada a `guardar` cuenta como
     salida, y con 200 se corta a la mitad — la CLI devuelve «exceeded the 200 output token
     maximum» y no guarda nada. La voz la sigue recortando el servidor a 20 palabras.
  3. **Tiempo máximo 6 s → 20 s.** Contestar tarda ~2 s, leer ~3,5 s, guardar algo largo
     llegó a 10 s.
  4. El JSON final de la CLI **no dice** qué herramientas usó (probado con un dato imposible
     de adivinar: lo trajo y `num_turns` siguió en 2). La marca la deja el propio estante al
     ser leído, en la carpeta temporal de esa llamada.
  5. Las instrucciones ahora también **contestan preguntas**, no solo dan un paso mínimo: sin
     eso, «¿qué te conté de Shopify?» devolvía una tarea.
  6. `editar_memoria` arma la memoria entera de nuevo antes de escribir, para que el contrato
     valide; y un cambio que no entra es 422, no un 500.
- **Dudas abiertas:**
  1. **Qué fase sigo.** El protocolo dice «2f en curso, 2e.0 después»; el repo no tiene nada
     de 2f y 2e.0 la terminé hoy por encargo explícito. Con «nunca dos en la misma fase»,
     necesito que alguien decida el orden real antes del próximo encargo.
  2. `nucleo/clasificar.py` sigue sin trackear y sin que nadie lo importe. Es material de 2f
     y no es mío.
  3. Un guardado largo pedido **desde la ventanita** se completa en el núcleo, pero la
     ventanita ya cortó su fetch a los 8 s y contesta sin IA. Subir ese número es UI, y 2e.0
     era solo núcleo.
  4. `Memoria` no tiene campo `compartible`. Por la regla de privacidad eso la deja fuera de
     los espejos, que es lo que quiero, pero conviene confirmarlo antes de la fase 4.
- **Cómo probarlo a mano:**
  1. `cd nucleo && uv run python sembrar_memoria.py` — la segunda vez dice «ya estaba».
  2. `uv run python servidor.py`, y en otra terminal `curl -s localhost:4400/memoria` — sale
     el índice, sin `cuerpo`.
  3. `curl -s -X POST localhost:4400/mensaje -H 'Content-Type: application/json' -d
     '{"texto":"¿qué te conté de Shopify?","think":true}'` — contesta con la idea y la
     consola del núcleo dice `memoria=1 leyó=sí`.
  4. Abrir Claude Code en el repo y preguntar «¿qué sabés de Shopify?» — usa el MCP del
     `.mcp.json`.
  5. `cd nucleo && uv run pytest -q && uv run mypy .` — 53 en verde.

## 2026-09-29 · estado del repo · leído · 9c2ff27

- **Qué cambió:** nada. Esta entrada abre la bitácora y deja por escrito qué hay de verdad
  en el repo hoy, leído del código y de `git log`, no del plan. **Cerrado y andando:** el
  núcleo (contratos → modelos, SQLite, `/mensaje`, `/hoy`, sesiones con tiempo real,
  `paso_minimo`) y la ventanita (píldora en reposo, 1/2/3 clicks, diálogo que corta solo,
  «hace N min», leer y copiar, velocidad 1×/1.5×/2×, «pensar con Claude» por `claude -p`
  con la sesión de Max y sin clave, voz Kokoro local de 4 voces con la del sistema de
  respaldo). **A medio hacer:** 2e.0, la memoria — cuatro commits puestos hoy
  (`9d88119`, `b9d2069`, `a31c5df`, `9c2ff27`). **Vacío:** `apps/panel/` solo tiene un
  README.
- **Decisiones que tomé sin preguntar:** ninguna en esta entrada; es un inventario.
- **Dudas abiertas:**
  1. **2f no existe en el repo.** No hay Bandeja, ni endpoint, ni nada que lea o escriba la
     tabla `ideas` (está creada en `nucleo/db.py:38` y nadie la toca). Lo único de 2f es
     `nucleo/clasificar.py`, 46 líneas, **sin trackear en git y sin que ningún archivo lo
     importe**. No lo escribí yo. El protocolo dice «2f en curso»; el repo dice que no
     empezó.
  2. **2e.0 sí está en curso**, por encargo explícito de hoy, y va por la mitad: faltan los
     endpoints de `/memoria`, la semilla y los tests. El protocolo la pone en «después».
     Con «cada uno en una fase distinta, nunca dos en la misma», hace falta decidir cuál de
     las dos sigo antes de seguir escribiendo.
  3. `nucleo/clasificar.py` es de otras manos: lo barrí sin querer en un `git add -A`, lo
     saqué del commit con `git rm --cached` y lo dejé sin trackear, como estaba. Queda por
     decidir si entra, se rehace dentro de 2f o se borra.
- **Cómo probarlo a mano:**
  1. `git log --oneline -8` muestra los cuatro commits de 2e.0 arriba.
  2. `grep -rn "bandeja\|Bandeja" nucleo apps/ventanita/src` no devuelve nada: no hay 2f.
  3. `git status --short` muestra `?? nucleo/clasificar.py`, sin trackear.
  4. `cd nucleo && uv run pytest -q && uv run mypy .` pasa en verde.
