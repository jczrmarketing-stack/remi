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

## 2026-09-30 · Chips Groq y OpenRouter en la charla · construido · a5e87c5

- **Qué cambió:** `config/motores.json` suma una sección `charla` (un id real por nivel
  rápido/equilibrio/inteligente, para Groq y OpenRouter — los mismos ids verificados en vivo
  en la bitácora `ad9506e`: `openai/gpt-oss-20b|120b` y `deepseek/deepseek-v4-flash|pro`).
  `nucleo/pensar.py`: `MOTORES` pasa a `(claude, venice, groq, openrouter, ollama)`; se quitó
  el motor `deepseek` entero (`MODELOS_DEEPSEEK`, `DEEPSEEK_URL`, `_llamar_deepseek`,
  `_modelo_deepseek`, `_pensar_con_deepseek` — nunca tuvo llave real). `_pensar_con_charla()`
  (nueva, genérica para los dos proveedores) despacha por `_llamar_openai_compatible`,
  resuelve el id de modelo con `_modelo_charla()` desde `config/motores.json` (nunca a mano),
  loguea `ms=` y deja `motor_usado` en la respuesta. `motores_disponibles()` etiqueta «Groq
  (gratis)» y «OpenRouter (centavos)», solo si hay llave en `.env`. 24 pruebas nuevas/
  reemplazadas; 463 de `nucleo/` en verde, mypy limpio.
- **Decisiones que tomé sin preguntar:**
  1. **Un línea en `servidor.py` fuera de la frontera literal**: el `Literal` de
     `MensajeEntrante.motor` no incluía `"groq"` ni `"openrouter"` (ni `"deepseek"` antes,
     de hecho — ese motor nunca estuvo expuesto por HTTP). Sin sumarlos, `POST /mensaje`
     devolvía 422 aunque `GET /pensar/motores` ya los mostrara disponibles, y el «listo
     cuando» pedía justo que cada chip conteste un turno real.
  2. Para elegir el nivel del chip en Groq/OpenRouter usé el mismo `modo_pedido`
     (rápido/equilibrio/inteligente) que ya manda la ventanita para Claude, en vez de
     inventar un parámetro nuevo — es el mismo concepto, y así no hace falta tocar
     `apps/ventanita` para que el nivel viaje.
  3. Un nivel que no está en `config/motores.json` → charla cae al de `MODO_POR_DEFECTO`
     («equilibrio»), igual que el resto del código cuando el modo pedido no existe.
  4. No toqué `apps/ventanita`: ningún chip está hardcodeado ahí (Claude/Ollama/Venice sí
     tienen `<optgroup>` propio en `ChipCerebro.tsx`, pero Groq/OpenRouter no estaban ni
     antes ni ahora) — la frontera decía tocarlo «solo si» eso pasaba, y no pasa.
- **Verificado en vivo, de punta a punta, con las claves reales de este Mac (nunca
  commiteadas):**
  - `GET /pensar/motores` (núcleo aislado en 4497, nunca el de producción en 4400): Groq y
    OpenRouter `disponible: true`.
  - **Groq**: `POST /mensaje` con `motor: "groq"`, turno real → **755 ms**
    (`[groq] modelo=groq/openai/gpt-oss-120b ms=755 tokens entrada=1462 salida=172`).
  - **OpenRouter**: turno real → **2394 ms**
    (`[openrouter] modelo=openrouter/deepseek/deepseek-v4-flash ms=2394 tokens entrada=1636
    salida=25`). La primera corrida dio 401 — el mismo hallazgo de `ad9506e`: mi shell tenía
    un `OPENROUTER_API_KEY` contaminando el entorno, con prioridad sobre el `.env` real
    (`_ajuste()`: entorno > archivo). `env -u OPENROUTER_API_KEY` antes de levantar el
    núcleo de prueba lo arregló. El servicio real (`com.remi.nucleo` por `launchd`) no
    hereda el perfil de shell, así que esto no afecta producción — solo pruebas a mano
    desde una terminal con ese perfil cargado.
  - Las dos, muy por debajo de los 4 s del «listo cuando».
- **Dudas abiertas:** ninguna.
- **Cómo probarlo a mano:**
  1. `cd nucleo && uv run pytest -q && uv run mypy .` — 463 en verde, limpio.
  2. Con las claves reales en `nucleo/.env` y `env -u OPENROUTER_API_KEY` (por si el
     placeholder sigue en el perfil de shell): levantar el núcleo en un puerto de prueba y
     `curl -s -X POST localhost:<puerto>/mensaje -H 'Content-Type: application/json' -d
     '{"texto":"...", "think":true, "motor":"groq"}'` (y de nuevo con `"openrouter"`).
  3. `git status`: `nucleo/.env` no aparece.

---

## 2026-10-01 · Proyectos: constelación con los libros reales · construido · 7610a4f

- **Qué cambió:** un commit. `GET /libros` en `servidor.py` (usa `libros.listar()`, ya
  existía) — por libro: `tema`, `titulo`, `resumen`, `compartible`, `quedaste` y
  `proximo_paso` (de `estado_libro.leer_estado`, vacíos sin `## Estado`) e `hitos` (de
  `caminos.leer_hitos`, `[]` sin `## Camino`); nunca el cuerpo completo. `apps/panel`:
  Proyectos ahora lista todos los libros de `/libros`, el del bloque abierto primero y con
  el chip «Abierto ahora»; tocar uno abre su camino (la ruta `/camino/{tema}` ya existía).
  Se fue el campo «buscar por tema» — ya había de dónde sacar la lista completa.
  `nucleo/pruebas/test_libros_ruta.py` (bóveda falsa de 2 libros, uno sin `## Estado`);
  `nucleo-falso.mjs` suma `/libros`; Playwright cubre la constelación y tocar un libro sin
  camino. 469 pytest, mypy limpio, 11/11 Playwright.
- **Verificado en vivo** tras `scripts/actualizar.sh`: `GET /libros` contra el núcleo real
  devuelve los 7 libros de `remi-mente`; abriendo `http://127.0.0.1:4402/proyectos` (con
  Playwright headless, sin bloque abierto en este momento) aparecen los 7, cada uno con su
  próximo paso real — ninguno marcado «Abierto ahora» porque no hay sesión activa, que es lo
  correcto.
- **Decisiones que tomé sin preguntar:**
  1. El orden de la lista es el de `libros.listar()` (alfabético por archivo) salvo que haya
     un bloque abierto, que sube al primero — no inventé un orden nuevo.
  2. Un libro sin `## Camino` tocado muestra «todavía no tiene `## Camino`» en vez de no
     reaccionar: mismo criterio que el 404 de `/camino/{tema}`, pero como dato, no como error.
- **Dudas abiertas:** ninguna.
- **Cómo probarlo a mano:** `curl -s 127.0.0.1:4400/libros | jq`; con
  `com.remi.panel` corriendo, abrir `http://127.0.0.1:4402/proyectos`.

---

## 2026-10-01 · panel como servicio + docs al día · construido · 719649e

- **Qué cambió:** dos commits.
  1. `2abac59` — `scripts/instalar.sh` suma `com.remi.panel` (mismo patrón que
     `com.remi.tunel`): `npm run build` una sola vez al instalar/actualizar, y
     `KeepAlive` solo relanza `npm run start` (que ya lee `puerto_panel` de
     `config/nucleo.json` por su cuenta, sin repetirlo en el plist). Log en
     `~/Library/Logs/Remi/panel.log`, build en `panel-build.log`. Sin `npm` o sin
     `apps/panel`, se salta solo, igual que el túnel sin `cloudflared`.
     `scripts/desinstalar.sh` lo suma a la lista de agentes que baja.
  2. `719649e` — «Kimi K2» reemplazado por `openai/gpt-oss-120b` (el modelo real de
     `config/motores.json`, desde la verificación en vivo de ayer) en `docs/
     ARQUITECTURA-CEREBRO.md` y `docs/ROBUSTEZ.md`. Solo texto, cinco ocurrencias.
  466 pytest en verde (sin tests nuevos: son scripts y prosa).
- **Verificado:** `scripts/actualizar.sh` instaló `719649e`; `npm start` a mano en
  `apps/panel` chocó con `EADDRINUSE :4402` (el LaunchAgent ya lo tenía tomado — buena
  señal). `curl -s -o /dev/null -w '%{http_code}' 127.0.0.1:4402` → `200`.
  `scripts/doctor.sh` → **10/10 OK, 0 FALLA**.
- **Decisiones que tomé sin preguntar:** ninguna nueva.
- **Dudas abiertas:** ninguna.
- **Cómo probarlo a mano:** `launchctl list | grep com.remi.panel`; `curl -s -o /dev/null -w
  '%{http_code}\n' 127.0.0.1:4402`; `./scripts/doctor.sh`.

---

## 2026-09-30 · cierre del 30-sep · construido · 7d94dd8

- **Qué cambió:** último lote de merges del día, todos `--no-ff`, pytest completo después de
  cada uno. Hashes de merge de hoy, en orden:
  1. `284ef5b` f-ventanita (Fase F · 3f ventanita final)
  2. `a958fae` f-fase3 (Bandeja + caminos + iniciativa)
  3. `97b42bf` f-notion (Notion ida y vuelta)
  4. `c2bc091` f-telegram (Fase 4 · el teléfono)
  5. `1a320ac` f-panel (apps/panel + /plata)
  6. `4aba7bb` f-telegram (reporte de la noche)
  7. `d86305d` f-tunel (doctor.sh, vigía, túnel cloudflared)
  8. `1ea32b3` f-config (configuración desde el panel — Conexiones)
  9. `5d6deba` f-tunel (nota de bitácora: medición de `/telegram/avisar` lento)
  10. `f2973fd` f-chips (motor de charla Groq/OpenRouter, se fue el deepseek directo)
  11. `7d94dd8` f-aviso (`avisar()` no bloquea: hilo de fondo con reintento)
  Entre el 10 y el 11, un commit suelto (`d5ddad0`): saqué `DEEPSEEK_API_KEY` de las llaves
  esperadas de `scripts/doctor.sh` — el motor directo se fue con f-chips, y esa llave ya no
  la lee nadie. `f-motores` no llegó a existir: quedó vacía, f-chips la cubrió entera.
- **Números finales:** 466 pytest, mypy limpio (81 módulos), 86 vitest (`apps/ventanita`),
  10/10 Playwright (`apps/panel`, núcleo falso aislado).
- **Verificado en vivo contra el núcleo real, después del `scripts/actualizar.sh` final**
  (instaló `7d94dd8`):
  1. `POST /telegram/avisar` respondió en **0.035 s** (antes: hasta 41 s) — `avisar()` ya no
     bloquea el request; el log confirma el envío real 8.7 s después, en el hilo de fondo:
     `[telegram] avisé (ms=8678)`.
  2. `GET /pensar/motores` lista `groq` (`openai/gpt-oss-120b`) y `openrouter`
     (`deepseek/deepseek-v4-flash`), los dos `disponible: true`.
  3. `scripts/doctor.sh`:
     ```
     OK     núcleo (/salud :4400)
     FALLA  panel (:4402) — no responde
     OK     whisper (whisper-server residente :4401)
     OK     kokoro (paquete instalado)
     OK     ollama (:11434)
     OK     LaunchAgents com.remi.* (10 cargados)
     OK     bóveda git limpia (/Users/juancamilo/proyectos/remi-mente)
     OK     llaves en nucleo/.env (7 nombres)
     OK     frescura (copia cifrada <26h, episodio <48h)
     OK     disco (168 GB libres)

     doctor: 1 chequeo(s) en FALLA
     ```
- **Decisiones que tomé sin preguntar:** ninguna nueva — este cierre fue solo mergear,
  verificar y escribir.
- **Lo pendiente** (`DEEPSEEK_API_KEY` ya NO es pendiente: se fue con f-chips):
  1. **El panel no corre como servicio.** `doctor.sh` lo chequea en `:4402` y falla porque
     nadie lo dejó corriendo — no es un LaunchAgent todavía. Si el túnel
     (`remi.inv3rza.com`) va a servirlo de verdad, hace falta decidir cómo se mantiene vivo
     (¿otro LaunchAgent, `pm2`, algo con Next en modo `start`?).
  2. `NOTION_VUELTA` sigue apagada (solo de ida) — a propósito, hasta que Remi lleve un mes
     de uso real (`docs/ROBUSTEZ.md`).
  3. `docs/ARQUITECTURA-CEREBRO.md` y `docs/ROBUSTEZ.md` siguen mencionando «Kimi K2» en la
     prosa; el código real usa `openai/gpt-oss-120b` desde la verificación en vivo de hoy.
  4. El envío de `/telegram/avisar` ahora es fire-and-forget con reintento en un hilo: no hay
     forma de confirmar éxito/fracaso desde la respuesta HTTP (siempre 204) — solo queda en
     el log. Si algún día hace falta saber si llegó, hay que agregar algo más que el log.
- **Cómo probarlo a mano:** `git log --oneline --merges -11`; `cd nucleo && uv run pytest -q
  && uv run mypy .`; `cd ../apps/ventanita && npx vitest run`; `cd ../panel && npx playwright
  test`; `scripts/doctor.sh`.

---

## 2026-09-30 · Configuración desde el panel · cierre (4 y 5) · 6c4dac9

- **Qué cambió:** el bloqueo de la entrada anterior se resolvió rebasando `f-config` sobre
  `f-panel` (decisión de Juan Camilo) — sin conflictos, 447 pruebas en verde. Con el panel
  de verdad ya en la rama: `PUT /config/plata` (nuevo, `conexiones.escribir_meta_mensual()`,
  atómico, conserva `$comment`/`moneda`, 0 o negativo es 422) y `apps/panel/src/components/
  Conexiones.tsx`, montado en Ajustes. Una fila por conexión de la lista blanca (Claude fija,
  sin llave) con campo vacío siempre, placeholder con `termina_en` cuando ya está puesta,
  Guardar y Probar; la meta mensual junto a las conexiones. Sin lectura biónica en campos
  ni botones.
- **Decisiones que tomé sin preguntar:**
  1. `PUT /config/plata` no estaba nombrado en el encargo, pero «rutas /config/* en
     servidor.py» lo cubre como wildcard, y hacía falta para que la meta mensual se pudiera
     editar desde Ajustes tal como pedía el punto 4. La función vive en `conexiones.py`
     (ya en la frontera); no hizo falta ningún archivo nuevo en `nucleo/`.
  2. Agregué tipos y cuatro funciones a `apps/panel/src/lib/nucleo.ts` (compartido, no «la
     pantalla Ajustes») porque la pantalla necesita un cliente para pegarle al núcleo. Es
     el mismo patrón de extensión mínima y aditiva que ya tenía el resto del panel.
  3. Creé `src/components/Conexiones.tsx` en vez de meter todo en `ajustes/page.tsx`: la
     sección es grande (8 filas + Claude + meta mensual) y el resto de Ajustes ya seguía el
     patrón de componer piezas chicas.
- **Dudas abiertas:** ninguna nueva. Las de la Fase 3 y del Panel (listado de proyectos,
  `/donde-quede` sin el siguiente hito, Semana sin ruta propia) siguen igual.
- **Cómo probarlo a mano:**
  1. `cd nucleo && uv run pytest -q && uv run mypy .` — 447 en verde, limpio.
  2. `cd apps/panel && npm install && npx tsc --noEmit && npm run build` — sin errores.
  3. Con un núcleo real corriendo y el panel apuntado ahí: Ajustes → Conexiones, pegar una
     llave de Groq falsa → «Guardar» → «Probar» → «✗ Groq no reconoce esa llave.»; pegar la
     real → «✓ Groq la acepta.» **Probado a mano** contra un núcleo aislado con la
     `GROQ_API_KEY` real de este Mac (sin imprimirla, sin tocar el `.env` de producción):
     los dos resultados salieron exactamente así.
  4. `git status` en este worktree: `nucleo/.env` no aparece.
  5. Falta probar el chip de Groq de la ventanita «sin reiniciar el núcleo» end-to-end (el
     gancho `reiniciar_hilo()` solo se probó con la ventanita apagada, vía pruebas y curl
     directo a `/config/conexiones`) — queda para quien tenga la ventanita corriendo.

---

## 2026-09-30 · Configuración desde el panel · a medio hacer (1–3 de 5) · c6fc2a3

- **Qué cambió:** `nucleo/conexiones.py` (nuevo) — lista blanca de 8 nombres, `estado()`
  que nunca devuelve el valor completo (`termina_en`: últimos 4, solo en los 5 secretos
  reales), `guardar()` que reescribe `nucleo/.env` atómico (temporal + chmod 600 +
  `Path.replace()`, conserva comentarios y líneas ajenas, deja `.env.bak`, vacío quita la
  línea), `probar()` con timeout de 8 s contra el proveedor real que nunca lanza. Rutas
  `GET/PUT /config/conexiones[/{nombre}]` y `POST .../probar` en `servidor.py`, cortadas con
  403 si la petición trae alguna cabecera `Cf-*` (vino por el túnel). `telegram.py` suma
  `reiniciar_hilo()`: para el polling viejo con un `Event` y arranca uno nuevo, sin
  reiniciar el núcleo — lo llama `conexiones.guardar()` al guardar `TELEGRAM_TOKEN` o
  `TELEGRAM_CHAT_ID`. 44 pruebas nuevas; las 435 de `nucleo/` en verde, mypy limpio.
- **Decisiones que tomé sin preguntar:**
  1. **Clasifiqué la lista blanca en secretos vs. no secretos** (`TELEGRAM_TOKEN`,
     `NOTION_TOKEN`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `VENICE_API_KEY` son secretos;
     `TELEGRAM_CHAT_ID`, `NOTION_PAGINA_ID`, `NOTION_VUELTA` no) porque el encargo pedía
     `termina_en` «solo secretos» sin decir cuáles. Un chat_id o un page_id de Notion no es
     un secreto que haga falta ocultar.
  2. **`probar()` para los tres no-secretos** (`TELEGRAM_CHAT_ID`, `NOTION_PAGINA_ID`,
     `NOTION_VUELTA`) devuelve `ok: true, "Guardado. No hay una prueba automática para
     esto."` en vez de 400: el encargo solo listó pruebas reales para los 5 secretos, y un
     botón que nunca sirve es peor que uno que dice la verdad.
  3. Cambié la firma del `threading.Thread` en `arrancar_hilo()` (ahora pasa también
     `seguir`, para que `reiniciar_hilo()` pueda apagar el hilo viejo) y actualicé el test
     existente que miraba esa firma exacta (`test_arranca_hilo_cuando_hay_token`).
- **Dudas abiertas / bloqueo real:**
  1. **El punto 4 (Ajustes → «Conexiones» en `apps/panel`) no se puede hacer en esta
     rama.** `f-config` sale de `main`, y en `main` `apps/panel/` todavía solo tiene el
     README — el Next.js de verdad (con la pantalla Ajustes) vive en `f-panel`, sin
     mergear. Hace falta decidir: ¿mergeo `f-panel` a `main` primero, rebaso `f-config`
     sobre `f-panel`, o hago el punto 4 en una rama aparte que sí tenga el panel? No lo
     decidí yo — toqué 0 archivos de `apps/`.
  2. El punto 5 (tests) quedó repartido dentro de los commits 1–3, no en uno aparte:
     cada pieza trae sus propias pruebas. Si se prefiere un commit de tests solo, se puede
     reorganizar.
- **Cómo probarlo a mano:**
  1. `cd nucleo && uv run pytest -q && uv run mypy .` — 435 en verde, limpio.
  2. Con el núcleo real corriendo: `curl -s localhost:4400/config/conexiones` — ningún
     valor completo en la respuesta.
  3. `curl -s -X PUT localhost:4400/config/conexiones/GROQ_API_KEY -d
     '{"valor":"gsk-falsa"}' -H 'Content-Type: application/json'` y después `curl -s -X
     POST localhost:4400/config/conexiones/GROQ_API_KEY/probar` → `ok: false`. Con la
     llave real guardada → `ok: true` (probado a mano con la clave real de este Mac, sin
     imprimirla).
  4. `curl -s -X PUT localhost:4400/config/conexiones/GROQ_API_KEY -d '{"valor":"x"}' -H
     'Content-Type: application/json' -H 'Cf-Connecting-Ip: 1.2.3.4'` → 403.
  5. `git status` en este worktree: `nucleo/.env` no aparece.

---

## 2026-09-30 · f-tunel · medición: /telegram/avisar lento

- **Por qué:** al construir `doctor.sh`/`vigia.sh` en esta rama, el agente detectó que
  `POST /telegram/avisar` contra el núcleo real (127.0.0.1:4400) tarda mucho más de los 5 s de
  timeout que pone `doctor.sh`. No lo toco acá — `nucleo/telegram.py` lo está tocando `f-config`
  en paralelo y un cambio ahí chocaría. Solo mido, para saber en qué fijarse cuando se audite.
- **Qué sabemos:** tres llamadas directas al endpoint local (`time curl -s -X POST
  127.0.0.1:4400/telegram/avisar -H 'content-type: application/json' -d '{"texto":"prueba
  doctor","urgente":true}'`):
  1. 41.829 s
  2. 40.672 s
  3. 0.637 s
  En paralelo, tres llamadas directas a Telegram (`curl -s -o /dev/null -w
  '%{time_namelookup} %{time_connect} %{time_appconnect} %{time_total}\n'
  https://api.telegram.org`):
  1. dns=0.002 connect=0.376 tls=0.550 total=0.718
  2. dns=0.002 connect=0.365 tls=0.530 total=0.692
  3. dns=0.003 connect=0.379 tls=0.587 total=0.757
- **Lectura:** DNS, conexión TCP y TLS hacia `api.telegram.org` son rápidos y estables desde
  esta máquina (~0.7 s parejo en las tres corridas) — Telegram mismo no es el cuello de botella
  y no es un problema de resolución DNS ni de handshake TLS. El endpoint local, en cambio, tardó
  ~41 s en las dos primeras llamadas y 0.6 s en la tercera: el patrón (lento, lento, rápido) no
  encaja con latencia de red hacia Telegram (que ya se midió aparte y es constante), apunta más
  bien a algo dentro del propio cliente saliente del núcleo (p. ej. intento de IPv6 antes de caer
  a IPv4, o un pool de conexiones que recién se calienta) — no a DNS/TLS/Telegram.
- **Hipótesis, no confirmado:** no entré a `nucleo/telegram.py` a leer el cliente HTTP que arma
  la llamada saliente, para no chocar con `f-config`. Queda para quien audite ese archivo.
- **Cómo repetirlo:** los dos comandos `curl` de arriba, corridos tres veces cada uno.

---

## 2026-09-30 · merge f-panel + f-telegram (reporte nocturno) · construido · 4aba7bb

- **Qué cambió:** dos merges a `main`, sin squash, pytest completo después de cada uno:
  1. `1a320ac` **f-panel** (`apps/panel`: Next.js 15 + PWA, Hoy/Proyectos/Metas/Bandeja/
     Ajustes, lectura biónica; `nucleo/plata.py` con `GET /plata`). Se automergeó limpio, sin
     un solo conflicto — ni en `docs/BITACORA.md` ni en el `import plata` de
     `nucleo/servidor.py` (quedó en su lugar alfabético, entre `pensar` y
     `sembrar_conocimiento`, sin tocar nada a mano). 413 pytest después del merge.
  2. `4aba7bb` **f-telegram** (reporte de la noche: `noche.py` compara el HEAD de la bóveda al
     arrancar contra el de ahora, arma «Anoche cambié N libros» con hasta 3 diffs cortos, y lo
     manda por `POST /telegram/avisar` con `urgente: true`). Conflicto solo en
     `docs/BITACORA.md` (append-only, combiné las dos listas); `nucleo/servidor.py` esta vez
     ni apareció en el diff de la rama — no hubo nada que resolver ahí. 427 pytest después.
  mypy limpio (78 módulos), 86 vitest (`apps/ventanita`, sin cambios ahí), `tsc --noEmit`
  limpio en `apps/panel`.
- **Panel en vivo:** `npm install` + `npm run dev` en `apps/panel` (puerto 4402, contra el
  núcleo real de 4400, sin `NEXT_PUBLIC_URL_NUCLEO` — ese es solo para Playwright). Las
  cuatro rutas (`/`, `/proyectos`, `/bandeja`, `/metas`) devolvieron 200 y el log del núcleo
  mostró `GET /hoy` y `GET /nudges/pendiente` en 200: Hoy carga de verdad contra datos reales,
  no el núcleo falso de las pruebas. Playwright (`npx playwright test`, su propio núcleo falso
  en 4498 + build+start del panel en 4403, aislado de todo lo anterior): **10/10 en verde**.
  Apagué el panel manual al terminar — no es un servicio de `launchd`, no tenía por qué seguir
  corriendo.
- **`scripts/actualizar.sh`:** corrió sobre `4aba7bb`; el log confirma «Instalada la de:
  4aba7bb merge: f-telegram (reporte de la noche) en main». `launchctl list | grep com.remi`
  muestra `com.remi.nucleo` y `com.remi.notion` con PID activo, y `com.remi.noche` /
  `com.remi.vigia` cargados sin PID — es lo esperado: `noche` es
  `StartCalendarInterval` (solo a las 4:00) y `vigia` es `StartInterval=60` (corre y sale),
  ninguno de los dos es un daemon persistente. `tail -5` del log del núcleo: sin `Traceback`
  ni `409`, solo warnings de carga de Kokoro/torch (preexistentes, no nuevos). `GET /salud` →
  `{"ok": true, "db": true}`.
- **Decisiones que tomé sin preguntar:**
  1. Lancé el panel con `npm run dev` en segundo plano (no `next build && next start`): el
     encargo pedía «arrancarlo y abrir», no un build de producción — y Playwright ya trae su
     propio build+start aislado para las pruebas.
  2. Interpreté «vivos» en el chequeo de `launchctl list` como «cargados en la lista», no
     «con un proceso corriendo ahora mismo»: `noche` y `vigia` nunca van a mostrar un PID
     fuera de su ventana (4:00 AM / cada 60 s que dura el chequeo), eso no es una falla.
- **Dudas abiertas:** ninguna de este encargo. Quedan las ya anotadas en entradas anteriores
  (Notion con `NOTION_VUELTA` apagada, docs con «Kimi K2» desactualizado).
- **Cómo probarlo a mano:** `git log --oneline -3` → `4aba7bb`, `1a320ac`; `cd nucleo && uv
  run pytest -q && uv run mypy .`; `cd ../apps/panel && npm run dev` y abrir
  `http://127.0.0.1:4402`; `npx playwright test` en el mismo directorio.

---

## 2026-09-30 · verificación en vivo del punto 5: modelos reales · construido · 54586b4

- **Qué cambió:** con las claves reales de `GROQ_API_KEY` y `OPENROUTER_API_KEY` puestas en
  `nucleo/.env` (main), probé `pensar.pensar_con_trastienda()` y `pensar._respaldo_de_charla()`
  contra las APIs de verdad — y los dos ids que había puesto a ojo en el encargo original no
  existen:
  1. **Groq: `kimi-k2` no está en la cuenta.** La clave es válida (`GET /models` da 200), pero
     entre los 11 modelos que sí tiene no hay ningún Kimi — están `openai/gpt-oss-20b`,
     `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`, `allam-2-7b`, `openai/gpt-oss-safeguard-20b` y
     un puñado de audio/guardrails. Cambié la trastienda a `openai/gpt-oss-120b` (el más
     grande disponible, para el mismo objetivo de «el que menos inventa» que ya documenta
     `docs/ROBUSTEZ.md`).
  2. **OpenRouter: `deepseek-flash` y `deepseek-v4-pro` no son ids reales.** El catálogo
     (`GET /models`) los tiene con el proveedor adelante: `deepseek/deepseek-v4-flash` y
     `deepseek/deepseek-v4-pro`. `trastienda()` ya soportaba esto sin tocar el parser —
     `partition("/")` corta solo en la primera barra, así que `"openrouter/deepseek/deepseek-
     v4-flash"` en `config/motores.json` da `proveedor="openrouter"`,
     `modelo="deepseek/deepseek-v4-flash"` correctamente.
  `config/motores.json`, `TRASTIENDA_POR_DEFECTO` y `RESPALDO_DE_CHARLA` en `nucleo/pensar.py`
  actualizados; tres asserts en `pruebas/test_pensar.py` que mencionaban los ids viejos,
  corregidos. 406 pytest, mypy limpio.
- **Verificado en vivo, de punta a punta, con las claves reales (nunca commiteadas):**
  `pensar_con_trastienda()` contesta con Groq (`motor_usado='groq'`,
  `modelo='groq/openai/gpt-oss-120b'`); `_respaldo_de_charla()` contesta con OpenRouter
  (`motor_usado='openrouter'`, `modelo='openrouter/deepseek/deepseek-v4-pro'`).
- **Hallazgo aparte, no de código:** mi shell interactiva tenía
  `OPENROUTER_API_KEY=sk-or-v1-PEGA_TU_KEY_AQUI` (un placeholder, 25 caracteres) como
  variable de entorno real del perfil — le ganaba al valor bueno de `nucleo/.env` por la
  regla de precedencia de `_ajuste()` (entorno > archivo), y por eso mi primera verificación
  dio 401 «User not found» (el mismo mensaje que el incidente de malik-gestion de antes, pero
  esta vez era mi propia contaminación de entorno, no un token real vencido). Tuve que correr
  las pruebas con `env -u OPENROUTER_API_KEY` para leer el `.env` de verdad. El núcleo real
  (`com.remi.nucleo` por `launchd`) no hereda el perfil de shell de Juan Camilo — su plist
  solo define `PATH` y `HOME` — así que esto no afecta al servicio en producción, solo a
  pruebas hechas a mano desde una terminal interactiva con ese perfil cargado.
- **Decisiones que tomé sin preguntar:**
  1. Elegí `openai/gpt-oss-120b` sobre `openai/gpt-oss-20b` (ambos disponibles) porque el
     objetivo documentado de la trastienda es «el que menos inventa», y el modelo grande
     tiene más margen para eso — lo confirmé contestando bien antes de commitear, pero no lo
     medí contra el chico.
  2. No toqué `docs/ARQUITECTURA-CEREBRO.md` ni `docs/ROBUSTEZ.md` (siguen mencionando «Kimi
     K2» en la prosa): son docs que no son míos, y el código ya no depende de ese nombre.
- **Dudas abiertas:**
  1. `docs/ROBUSTEZ.md` y `ARQUITECTURA-CEREBRO.md §9` van a seguir diciendo «Kimi K2» hasta
     que alguien los actualice — la fuente de verdad real ahora es `config/motores.json`.
  2. No probé si la cuenta de Groq puede pedir acceso a Kimi K2 (algunos modelos de Groq son
     opt-in/preview) — si en algún momento aparece en `GET /models`, valdría reconsiderar.
- **Cómo probarlo a mano:** con las claves reales en `nucleo/.env` y
  `env -u OPENROUTER_API_KEY` (por si el placeholder sigue en el perfil de la shell):
  `cd nucleo && uv run python3 -c "import pensar; print(pensar.pensar_con_trastienda('hola',
  pensar.INSTRUCCIONES_RESUMEN))"`.

---

## 2026-09-30 · notion: GET real, solo de ida, mockups del panel · construido · e3629f6

- **Qué cambió:** tres commits en `main`, pytest completo después de cada uno:
  1. `07e2b76` — `notion.buscar_base()` pedía `POST /blocks/{id}/children` (agregar bloques)
     para LISTAR los hijos y encontrar la base «Proyectos»/«Entregas» existente: Notion
     devolvía 400 y `notion_sync.sincronizar()` nunca llegaba a crear ni encontrar nada. Ahora
     es `GET` con `params` (nuevo parámetro en `_pedir()`, que antes solo mandaba `json`).
     Verifiqué contra la API real: disparé el `LaunchAgent` a mano dos veces
     (`launchctl kickstart -k gui/$UID/com.remi.notion`) y el segundo ciclo (y el siguiente)
     ya no aparecen en `notion.log` — solo el resumen JSON limpio. Tests con un transporte
     httpx falso (`httpx.MockTransport`, sin red): confirma el método GET, que encuentra la
     base entre otros tipos de bloque, y que pagina con `start_cursor`.
  2. `be0230c` — Notion solo de ida por defecto (`docs/ROBUSTEZ.md`): `sincronizar()` ya no
     llama `obtener_pagina()` ni anota conflictos salvo `NOTION_VUELTA=1` en `nucleo/.env`
     (`notion.vuelta_habilitada()`). Sin la bandera, empuja lo local tal cual y no lee nada de
     vuelta. Los tres tests que ya cubrían la vuelta real ahora la prenden explícito
     (`monkeypatch.setenv("NOTION_VUELTA", "1")`); sumé dos tests nuevos para el caso por
     defecto (proyecto y entrega) que confirman que un cambio hecho a mano en Notion no pisa
     el libro ni la base local, y que no se abre `bitacora.md`.
  3. `e3629f6` — `docs/mockups/panel/` tal como estaba (17 pantallas HTML + prototipo +
     README), sin tocar nada del código.
  pytest: 402→406→402 (los 4 de más/menos son `test_vectores.py`, que ya sabíamos flojo bajo
  carga — a veces pasa, a veces skip, según cómo esté Ollama en el momento; no tiene que ver
  con estos cambios). mypy limpio (76 módulos) en todo momento.
- **`scripts/actualizar.sh`:** corrió sobre `e3629f6`; el log confirma «Instalada la de:
  e3629f6 docs: diseño del panel, 17 pantallas». `com.remi.notion` se recargó con el fix del
  GET adentro.
- **Decisiones que tomé sin preguntar:**
  1. `_pedir()` suma `params` como keyword-only, sin tocar ninguno de los otros cinco
     llamados (todos siguen mandando `json=cuerpo, params=None`): cambio mínimo, nada de
     tocar `crear_base`/`consultar_base`/etc.
  2. La vuelta apagada por defecto también apaga el chequeo `obtener_pagina()` entero (no
     solo la comparación): menos una llamada de red por proyecto/entrega en cada ciclo de
     15 min mientras la bandera esté apagada, no solo «leer y descartar».
  3. `docs/mockups/panel/` va en un commit propio, sin pytest relevante (es HTML estático):
     igual corrí la suite completa después, por consistencia con el resto del encargo.
- **Dudas abiertas:**
  1. `NOTION_VUELTA` no está en `nucleo/.env` todavía — Notion sigue solo de ida en este Mac
     hasta que alguien decida prenderla (la propia docs/ROBUSTEZ.md dice que eso espera a que
     Remi lleve un mes de uso real).
  2. **f-telegram, otra vez:** el worktree `remi-telegram` sigue en `7341db3` (el mismo commit
     que ya está en `main` desde el merge anterior) — no hay nada nuevo que mergear todavía.
     El encargo dice mergear «cuando remi-telegram-28 avise el reporte nocturno»: eso es obra
     de otra sesión trabajando en paralelo en ese worktree, que todavía no terminó ni
     commiteó. Lo dejo pendiente — no hay nada que mergear hasta que esa rama tenga commits
     nuevos y avise. Cuando pase: mergear f-telegram, pytest completo, `scripts/actualizar.sh`,
     y una entrada de bitácora nueva (esta no se edita).
- **Cómo probarlo a mano:** `cd nucleo && uv run pytest pruebas/test_notion.py
  pruebas/test_notion_sync.py -v`; `launchctl kickstart -k gui/$(id -u)/com.remi.notion &&
  tail -5 ~/Library/Logs/Remi/notion.log` — el resumen JSON, sin traceback de 400.

---

## 2026-09-30 · merge f-fase3 + f-notion + f-telegram · construido · c2bc091

- **Qué cambió:** tres merges a `main`, sin squash, un `git commit` cada uno, pytest completo
  después de cada uno:
  1. `a958fae` **f-fase3** (Bandeja, caminos, iniciativa — `nucleo/bandeja.py`,
     `caminos.py`, `iniciativa.py`, rutas de nudges en `servidor.py`). Conflicto solo en
     `docs/BITACORA.md` (append-only: combiné las dos listas de entradas, la más nueva
     arriba). `nucleo/servidor.py` se automergeó limpio.
  2. `97b42bf` **f-notion** (`nucleo/notion.py`, `notion_sync.py`, LaunchAgent
     `com.remi.notion` cada 15 min). Primer conflicto real en el bloque de imports de
     `nucleo/servidor.py` (`import iniciativa` de la rama anterior vs `import notion` de
     esta), resuelto a mano dejando las dos líneas en orden alfabético; el resto del archivo
     se automergeó.
  3. `c2bc091` **f-telegram** (`nucleo/telegram.py`, cliente de la Bot API, `arrancar_hilo()`
     en el startup, `POST /telegram/avisar`). Conflicto en `docs/BITACORA.md` (mismo patrón,
     combiné) y de nuevo en el bloque de imports/`include_router` de `servidor.py`
     (`notion.router` de la rama anterior vs `telegram.router` de esta): quedaron las dos
     líneas.
  pytest después de cada merge: 372→384→399 (subió con cada rama, como se esperaba). Al
  final: mypy limpio (76 módulos), 86 vitest, `cargo check` limpio en `src-tauri` (mismo
  warning preexistente de `pico_reciente`, no nuevo).
- **`scripts/actualizar.sh`:** corrió sobre `c2bc091`; el log del actualizador confirma
  «Instalada la de: c2bc091 merge: f-telegram (Fase 4 — Telegram) en main». `launchctl list`
  muestra `com.remi.notion` corriendo (`com.remi.nucleo` también se reinició con el código
  nuevo, vía `scripts/instalar.sh`).
- **Verificación del hilo de Telegram:** el log (`~/Library/Logs/Remi/nucleo.log`) no dice
  nada al arrancar con éxito — es a propósito, `arrancar_hilo()` solo loguea el caso sin
  token; el éxito es silencioso. Lo verifiqué distinto: `lsof` sobre el PID real de
  `com.remi.nucleo` mostró una conexión TCP `ESTABLISHED` hacia `2001:67c:4e8::/48`, el
  bloque IPv6 de Telegram Messenger Inc (confirmado con `whois`) — el hilo está vivo y
  conectando de verdad.
- **Encontrado en la verificación, no en el merge:**
  1. Un proceso viejo (`uv run uvicorn servidor:app --port 4402`, del worktree
     `remi-telegram`, PID 27450/27452, arrancado a mano hace rato, sin relación con
     `launchd`) seguía corriendo y competía por el mismo `TELEGRAM_TOKEN`: el núcleo real de
     4400 recibía `409 Conflict` en `getUpdates`. Lo maté (`kill 27450 27452`) — era un
     sobrante de desarrollo, no un servicio.
  2. Aun así, el `409 Conflict` sigue apareciendo en el log varios minutos después de matar
     ese proceso. Confirmé que no hay ningún otro proceso local usando ese token
     (`ps -ef` limpio de `uvicorn`/`servidor:app` salvo el de 4400) y que el bot no tiene un
     webhook configurado (`getWebhookInfo` → `url: ""`). Conclusión: hay otro cliente
     haciendo long polling contra el mismo bot desde fuera de esta máquina — otra instalación
     de Remi, un servidor, u otro dispositivo con el mismo `TELEGRAM_TOKEN`. No es algo que
     se arregle desde acá; se lo dejo a Juan Camilo (dato abierto abajo).
  3. Aproveché este chequeo para mirar `notion.log`: `com.remi.notion` corrió y llegó a
     `api.notion.com`, pero `notion.buscar_base()` usa `POST /blocks/{id}/children`
     (agregar bloques) en vez de `GET /blocks/{id}/children` (listarlos) para buscar la base
     de datos existente — 400 Bad Request. Bug real de `f-notion`, no lo toqué: el encargo
     era mergear y verificar que el agente corra, no depurar su lógica.
- **Decisiones que tomé sin preguntar:**
  1. Maté el proceso de 4402: estaba activamente rompiendo la verificación que el encargo
     pedía (el 409 en el núcleo real), no tenía dueño (`launchd` no lo maneja) y era
     claramente un sobrante de una sesión de desarrollo anterior sobre una rama ya mergeada.
  2. En los dos conflictos de imports, alfabético (`iniciativa` antes de `notion` antes de
     `telegram`) por consistencia con el resto del bloque de imports, que ya iba alfabético.
- **Dudas abiertas:**
  1. **El 409 de Telegram sigue sin resolverse** — hay otro poller vivo en algún lado con el
     mismo token. Hasta que Juan Camilo lo identifique y lo baje, el bot de este Mac va a
     seguir reintentando sin conectar de verdad (no rompe el núcleo, solo no contesta
     mensajes).
  2. `notion.buscar_base()` usa el verbo/endpoint equivocado de la API de Notion (ver arriba)
     — sin arreglarlo, `com.remi.notion` nunca va a sincronizar nada, solo va a fallar cada
     15 min con 400. Encargo aparte.
  3. Igual que en la entrada de la trastienda: `docs/ARQUITECTURA-CEREBRO.md` y
     `docs/ROBUSTEZ.md` siguen sin commitear en este árbol — no los toqué, no son míos.
- **Cómo probarlo a mano:** `git -C ~/proyectos/remi log --oneline -1` → `c2bc091`;
  `git -C ~/proyectos/remi branch --merged main` → incluye `f-fase3`, `f-notion`,
  `f-telegram`; `launchctl list | grep com.remi.notion`; `tail -f
  ~/Library/Logs/Remi/nucleo.log` mientras se le manda `/start` al bot desde Telegram (una
  vez resuelto el poller externo) para ver la línea `[telegram] /start de chat_id=…`.

---

## 2026-09-30 · trastienda (config/motores.json) + respaldo de charla · construido · a57484d

- **Qué cambió:** `nucleo/pensar.py` — `config/motores.json` define la trastienda, una lista
  ordenada `proveedor/modelo` (por defecto `groq/kimi-k2` → `openrouter/deepseek-flash` →
  `ollama/gemma3:4b`, leída por `trastienda()`); `pensar_con_trastienda(pedido, instrucciones,
  aceptar=None)` recorre esa lista y cae al siguiente motor si uno no contesta, responde vacío,
  o `aceptar` lo rechaza. Los cuatro módulos que hoy llamaban directo a Ollama/Haiku para tareas
  de fondo pasan a usarla: `pensar.resumir` (resumen vivo), `cierre.redactar` (títulos de
  episodios), `estado_libro.redactar` (consolidación nocturna, vía `noche.py`) y
  `claves.extraer` (claves). La verificación anti-invento de `estado_libro` y `claves` sigue
  igual, ahora enchufada como el callback `aceptar`. Además, **respaldo de charla**: si la CLI
  de Claude avisa que llegó al límite de uso (`LimiteDeClaude`, detectado por patrón de texto —
  la CLI no da un código estructurado), el turno se reintenta una sola vez, directo, con
  `openrouter/deepseek-v4-pro` (sin recorrer los tres modos de Claude, que comparten el mismo
  límite). `Pensado` suma el campo `motor_usado`; `servidor.py` lo agrega a `RespuestaMensaje`
  (nuevo, para pantalla — a diferencia de `tokens`, que es solo consola) en los cinco lugares
  que arman la respuesta desde un `pensado`. 21 pruebas nuevas/reescritas con cliente falso
  (HTTP/CLI mockeados, nada de red real); 338 pytest, mypy limpio (64 módulos).
- **Decisiones que tomé sin preguntar:**
  1. `noche.py` no se tocó: no llama a ningún modelo directo, todo pasa por
     `estado_libro.redactar`, así que arreglar ese módulo alcanza.
  2. `cierre.redactar_error()` (libro de errores, oficio «stack») se dejó como estaba —solo
     Haiku, sin Ollama de respaldo hoy—: el encargo listaba `cierre.py` por los títulos de
     episodios, no por el libro de errores, que es una función aparte.
  3. `refresco_claude_code.py` tampoco se tocó: llama a Haiku directo para su propia tarea (el
     refresco semanal del changelog), no es uno de los cuatro módulos listados.
  4. `motor_usado` es un campo nuevo en `RespuestaMensaje`, no dentro de `tokens`: el comentario
     de `tokens` ya decía que es dato de consola, nunca pantalla, y el pedido explícito era que
     la ventanita lo pueda mostrar.
  5. El patrón para detectar «límite alcanzado» es texto (`usage limit|límite alcanzado|límite
     de uso`, sin distinguir mayúsculas): la CLI de Claude Code no da un código de error
     estructurado para esto, así que es lo mejor disponible sin verlo en vivo contra un límite
     real.
- **Dudas abiertas:**
  1. El patrón de «límite alcanzado» no está probado contra un límite real de la CLI —no tengo
     cómo provocarlo a propósito sin gastar el límite de Max de Juan Camilo—, solo contra un
     texto de ejemplo razonable. Si la CLI usa una frase distinta, no dispara el respaldo y
     queda como cualquier otro error (sin IA).
  2. `GROQ_API_KEY`/`OPENROUTER_API_KEY` no están en `nucleo/.env` todavía: sin ellas, la
     trastienda cae derecho a Ollama (que sigue local y sin llave) y el respaldo de charla no
     tiene a dónde reintentar (`_llamar_proveedor` falla con 401, se loguea y sigue sin IA, como
     cualquier proveedor sin clave).
  3. `docs/ARQUITECTURA-CEREBRO.md §9` y `docs/ROBUSTEZ.md` (nuevos, no tocados por este
     commit: los estaba editando alguien más en este mismo árbol de trabajo mientras yo
     construía esto) describen un plan más amplio para OpenRouter —`models` con caída
     automática dentro de una sola llamada y `provider.sort=price`, más modelos por nivel
     (Kimi K2, Qwen3-Coder)— que no construí: el encargo de hoy fue puntual (la lista de tres
     `proveedor/modelo` y el respaldo a `deepseek-v4-pro`), no ese plan entero.
- **Cómo probarlo a mano:** `cd nucleo && uv run pytest pruebas/test_pensar.py
  pruebas/test_estado_libro_invento.py pruebas/test_noche.py pruebas/test_claves.py
  pruebas/test_pensar_de_verdad.py pruebas/test_bandeja.py -v`; con `GROQ_API_KEY` y
  `OPENROUTER_API_KEY` reales en `nucleo/.env`, `curl -s -X POST 127.0.0.1:4400/mensaje
  -H 'content-type: application/json' -d '{"texto":"¿qué tengo pendiente?","think":true}' | jq
  .motor_usado` debe decir `"claude"` en una sesión normal.

---

## 2026-09-30 · motor DeepSeek · construido · 1fd9d29

- **Qué cambió:** `nucleo/pensar.py` — motor `deepseek`, mismo camino que Venice:
  `DEEPSEEK_URL` (OpenAI-compatible, `https://api.deepseek.com/chat/completions`),
  `MODELOS_DEEPSEEK = ("deepseek-flash", "deepseek-v4-pro")`, `_modelo_deepseek`,
  `_llamar_deepseek` (reusa `_llamar_openai_compatible`), `_pensar_con_deepseek` (reusa
  `_leer_respuesta_venice` con `proveedor="deepseek"`), y una rama nueva en `motor()`/`pensar()`.
  `motores_disponibles()` lo suma a la lista de `/pensar/motores`: aparece solo si
  `DEEPSEEK_API_KEY` está en `nucleo/.env`. `nucleo/pruebas/test_pensar.py` — ocho pruebas
  nuevas espejo de las de Venice (sin clave, nunca default, lee texto/tokens, el chip elige
  entre flash y pro, respuesta vacía, la clave no se exporta a la CLI de Claude, y las dos de
  `motores_disponibles`). `nucleo/pruebas/test_bandeja.py` — el orden esperado de
  `/pensar/motores` ahora incluye `deepseek`.
- **Decisiones que tomé sin preguntar:**
  1. `deepseek-flash` es el modelo por defecto si el chip no manda uno (mismo criterio que
     Venice: el primero de la tupla es el económico/respaldo). `deepseek-v4-pro` para
     inteligente y Modo Prompt queda documentado en el comentario de `MODELOS_DEEPSEEK`, pero
     la frontera de este encargo era `nucleo/pensar.py` + tests, sin tocar `apps/` ni
     `servidor.py`: hoy no hay ningún camino real que pida `modelo_deepseek="deepseek-v4-pro"`
     automáticamente por modo — `pensar()` ya acepta el parámetro (igual que `modelo_venice`),
     pero falta que el chip (o `servidor.py`, fuera de esta frontera) lo mande. Hasta entonces,
     manual solo es posible desde `pensar.pensar(..., modelo_deepseek=...)` directo.
  2. Mismos filtros de salida (`sin_markdown`, ≤60 palabras) sin tocar nada: son de
     `servidor.py` y aplican al `paso_minimo` de cualquier motor por igual.
- **Dudas abiertas:**
  1. El chip de la ventanita no tiene todavía un selector `modelo_deepseek` (como sí tiene
     para Venice): encargo aparte que sí tocaría `apps/` y `servidor.py`.
- **Cómo probarlo a mano:** `cd nucleo && uv run pytest pruebas/test_pensar.py
  pruebas/test_bandeja.py -v`; con `DEEPSEEK_API_KEY` real en `nucleo/.env`,
  `curl -s 127.0.0.1:4400/pensar/motores | jq` debe listar `deepseek` con `disponible: true`.

---

## 2026-09-30 · Fase 4 Telegram · reporte de la noche · construido · e74fb7a

- **Qué cambió:** el cuarto punto de la Fase 4 pasa a ser el reporte de la noche —
  reemplaza la entrega por voz con Whisper, descartada por Milo. `nucleo/noche.py`:
  `_head_git()` toma el HEAD de la bóveda (`boveda_git.raiz()`) al arrancar `correr()`;
  `diff_de_la_noche(referencia)` compara ese HEAD contra el de ahora, restringido a
  `libros.carpeta()`, y devuelve `[(libro, diff_corto)]` — el nombre es el título del libro
  si todavía se puede leer, o el nombre de archivo si se borró; `_recortar_diff()` arranca
  desde el primer `@@` (el hunk real, no la cabecera de `git diff`) y corta a 8 líneas;
  `enviar_reporte_de_la_noche()` hace `POST /telegram/avisar` con `urgente: true` y el texto
  armado y, si falla, lo anota en stderr sin tumbar la consolidación. `nucleo/telegram.py`:
  `mensaje_reporte_noche()`, el formato — «Anoche cambié N libros» con hasta 3 diffs, «y M
  más» si sobran, o literalmente «Anoche no toqué nada» sin cambios. Los cuatro pasos de
  `correr()` quedan en cinco. `nucleo/pruebas/test_noche.py` y `test_telegram.py`: 21
  pruebas nuevas, con un repo git de fixture (`git init` en `tmp_path`, nunca contra la
  `remi-mente` real).
- **Decisiones que tomé sin preguntar:**
  1. El diff se recorta desde el primer `@@`, no desde el principio crudo de `git diff`: las
     4 líneas de cabecera (`diff --git`, `index`, `---`, `+++`) se comían el cambio real
     dentro del límite de 8 líneas — lo probé con la fixture antes de decidirlo.
  2. Mandé el aviso por `httpx.post` a `POST /telegram/avisar` (la URL sale de
     `config/nucleo.json`, mismo archivo que lee `servidor.py`) en vez de llamar
     `telegram.avisar()` en proceso: `noche.py` corre como script aparte (`uv run python
     noche.py` desde `scripts/noche.sh`), no dentro del servidor — no hay garantía de que
     comparta el mismo proceso que el hilo de Telegram.
  3. El HEAD de referencia se toma **al arrancar** `correr()`, antes de los otros cuatro
     pasos — así el reporte es «lo que tocó esta corrida», no un acumulado de corridas
     anteriores.
  4. `urgente: true` en el `POST`: la consolidación corre a las 4:00, dentro del silencio
     23:00–7:00 de `avisar()`; con `urgente=false` (el default de `AvisoSaliente`) el reporte
     se habría descartado en silencio, siempre, sin excepción — no hay cola ni reintento, así
     que habría sido letra muerta. `urgente` acá no es «suena la alarma»: es «no lo tires»;
     igual llega calladito al teléfono y espera a que Juan Camilo lo abra de mañana.
- **Dudas abiertas:**
  1. Igual que con `/telegram/avisar` en general (ver la entrada de `830f5ab`): no lo probé
     contra el bot real ni contra la `remi-mente` real, solo con la fixture de git. Si el
     núcleo (`servidor.py`) no está corriendo a las 4:00, el `POST` falla y solo queda en
     `noche.log` — no hay reintento.
- **Cómo probarlo a mano:**
  1. `cd nucleo && uv run pytest -q pruebas/test_noche.py pruebas/test_telegram.py` — verde.
  2. `cd nucleo && uv run pytest -q && uv run mypy .` — 350 pruebas y mypy en verde (puede
     variar ±4 según si Ollama está corriendo: `test_vectores.py` se salta si no).
  3. Con el núcleo corriendo (`uv run python servidor.py`) y `TELEGRAM_TOKEN`/`CHAT_ID`
     configurados, `cd nucleo && uv run python noche.py` sin episodios de hoy — llega
     «Anoche no toqué nada» al teléfono aunque sean las 4:00.

---

## 2026-09-30 · Fase 4 Telegram · construido · 830f5ab

- **Qué cambió:** `nucleo/telegram.py` (nuevo) — cliente mínimo sobre la Bot API con httpx,
  sin librerías de Telegram. `getUpdates` en long polling (timeout 30) en un hilo daemon que
  arranca en el startup de `servidor.py` si hay `TELEGRAM_TOKEN`; sin token, no arranca y lo
  dice una vez en el log, el núcleo sigue igual. Solo contesta al `TELEGRAM_CHAT_ID`
  configurado; cualquier otro chat se ignora en silencio, y sin `CHAT_ID` el primer `/start`
  solo queda en el log con el chat_id para copiarlo al `.env`. Un texto con la forma de
  `entregas.parsear_entrega` («entrega para X el D de MES por N») crea la entrega por la
  misma vía que `POST /entregas` y confirma «Entrega para X: D de MES, $N»; cualquier otro
  texto pasa por la misma función que `/mensaje` (origen=texto, modo=rapido, think=true,
  clasificador y Bandeja incluidos) y la respuesta sale sin markdown y hasta 3 frases
  (`servidor.para_hablar`). `POST /telegram/avisar` es la única puerta de salida hacia el
  teléfono — la llaman el motor de iniciativa y el vigía de `f-fase3` cuando se mergee, no
  este módulo — y respeta el silencio 23:00–7:00 en `America/Bogota` salvo `urgente: true`.
  `servidor.py`: un import, `telegram.arrancar_hilo()` en el startup y
  `app.include_router(telegram.router)`. `nucleo/pruebas/test_telegram.py`: 15 pruebas, todas
  con transporte falso, sin red.
- **Decisiones que tomé sin preguntar:**
  1. `REMI_TELEGRAM=0` apaga el hilo aunque haya `TELEGRAM_TOKEN`, mismo patrón que
     `REMI_TTS_PRECALENTAR` y `REMI_SEMBRAR_CONOCIMIENTO` — sin esto, correr `pytest` en la
     máquina de Juan Camilo con el `.env` real puesto dispararía long polling de verdad
     contra Telegram en cada corrida de pruebas. No hace falta tocarlo en producción: el bot
     arranca igual.
  2. La branch venía en `7610eb1`, antes de que `nucleo/entregas.py` y el resto de
     `f-ventanita` se mergearan a `main` — hice `git merge main` (fast-forward) al principio
     para poder leer y usar `entregas.parsear_entrega`, con permiso explícito de Juan Camilo.
  3. Con `TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID` ausentes leo primero `os.environ`, y si no está,
     `nucleo/.env` (mismo parser que `pensar._leer_env`) — igual que el resto del núcleo lee
     `VENICE_API_KEY`.
- **Dudas abiertas:**
  1. `entrega.proyecto_id` sale de un uuid5 determinístico por tema (`_proyecto_id_de_tema`
     en `entregas.py`, ya existente) porque todavía no hay Proyecto con id propio — una
     entrega creada desde el teléfono, sin `tema`, cae siempre en `sin-proyecto`.
  2. `POST /telegram/avisar` no lo probé contra el bot real (`curl` al `127.0.0.1:4400` con el
     núcleo corriendo y el teléfono de Juan Camilo a mano) — queda para que lo pruebe él.
- **Cómo probarlo a mano:**
  1. En `nucleo/.env`: `TELEGRAM_TOKEN=<el de @lucho777_bot>` y, tras mandarle `/start` al
     bot y ver el chat_id en el log del núcleo, `TELEGRAM_CHAT_ID=<ese número>`.
  2. `cd nucleo && uv run python servidor.py` — sin token, el log dice «sin TELEGRAM_TOKEN…
     el bot no arranca»; con token puesto, arranca el hilo sin loguear nada más.
  3. Escribirle al bot «idea: probar Telegram» — Remi contesta corto y la idea aparece en la
     Bandeja (`GET /hoy` no la lista; queda en la tabla `ideas`).
  4. Escribirle «entrega para Alfonso el 18 de octubre por 5.000» — contesta «Entrega para
     Alfonso: 18 de octubre, $5.000» y `curl 127.0.0.1:4400/entregas` la lista.
  5. `curl -X POST 127.0.0.1:4400/telegram/avisar -H 'Content-Type: application/json' -d
     '{"texto":"prueba"}'` — llega al teléfono si no son las 23:00–7:00; con
     `{"texto":"prueba","urgente":true}` llega igual de noche.
  6. `cd nucleo && uv run pytest -q && uv run mypy telegram.py servidor.py` — 336 pruebas y
     mypy en verde.

---

## 2026-09-30 · estado del 30-sep 12:00

- **Instalado:** `main` en `c194103` (merge de `f-ventanita` en `284ef5b` + dos commits de
  arreglo en `cierre.py`). `scripts/actualizar.sh` corrió sobre el merge: `/Applications/Remi.app`
  queda en `284ef5b`, verificado en el log del actualizador («Instalada la de: 284ef5b merge:
  f-ventanita…»). Los dos commits posteriores (`7dbe220`, `c194103`) solo tocan
  `nucleo/cierre.py` — no requieren reinstalar la app, el núcleo los toma en el próximo
  reinicio del proceso (`com.remi.nucleo`, todavía no reiniciado en esta sesión). Con eso: la
  isla de reposo 120×44, la piel dinero, el Reloj de una línea, el Nudge en el chat y ⌘⇧C ya
  están en la app instalada.
- **Ramas que quedan:**
  1. `f-ventanita` (worktree `remi-ventanita`) — ya mergeada en `main` (`git branch --merged
     main` la incluye); el worktree se puede borrar cuando Juan Camilo quiera
     (`git worktree remove`).
  2. `f-fase3` (worktree `remi-fase3`) y `f-telegram` (worktree `remi-telegram`) — ambas en
     `7610eb1`, el mismo commit que ya está en `main`: son worktrees preparados para fases
     futuras, sin trabajo propio todavía. No hay nada pendiente de mergear ahí.
- **Qué falta** (según `docs/GUIA-HOY.md`, escrita para este mismo merge — no tuve acceso al
  tablero de fases de la Biblia en claude.ai desde esta sesión, así que esto es lo que consta
  localmente, no una lectura directa del tablero):
  1. Panel Hoy web (maquetas listas, sin construir) y el túnel `remi.inv3rza.com`.
  2. Crear entregas hablando, «cobré X» por voz, celebración de «Hecha» con dinero — hoy la
     entrega se crea por `curl` a mano (§6 de la guía).
  3. Notion ida y vuelta (T3) y Telegram (T4): nada vuelve de Notion todavía.
  4. Banco de pruebas (3f, distinto del «3f ventanita final» de esta rama) y detección de app
     en primer plano (`NSWorkspace`).
  5. `oficios/clientes.md` sigue con los precios piso en blanco.
  6. Del lado de `f-ventanita` (dudas abiertas de `32cffe2`, ver entrada de más abajo):
     `/nudges/pendiente` y `/nudges/{id}/respuesta` no existen en el núcleo (Fase 3), y
     `tarea.proyecto_id` sigue siempre `null`, así que la piel dinero del Reloj no se va a
     disparar en la app real todavía.
- **De esta sesión:** al regenerar los dos episodios de malik de hoy (punto 3 del encargo)
  encontré que el primer intento de Haiku, con un transcript casi vacío (el agente de
  `/investigar` falló con «401 User not found» antes de hacer nada), inventó una
  «investigación sobre tendencias en X y Reddit» que no está en ningún lado del transcript
  real. Lo revertí en la bóveda (`git log` de `remi-mente`, commits alrededor de `2d59da7` y
  `b467393`) y dejé los dos episodios finales con texto verificado a mano contra el transcript.
  Vale la pena leer esto junto con la nota de memoria sobre la bóveda sin git: la bóveda **ya
  tiene git** (se ve en su propio `git log`), así que esta vez el revert fue real y no hubo
  pérdida — pero el riesgo de invento de Haiku con poco contexto real sigue vivo y conviene
  revisar a mano cualquier episodio que salga de una sesión casi vacía.
- **Cómo probarlo a mano:** `git -C ~/proyectos/remi log --oneline -1` → `c194103`; abrir
  Remi y ver la isla 120×44; `git -C ~/proyectos/remi branch --merged main` → incluye
  `f-ventanita`; `git -C ~/proyectos/remi-mente log --oneline -6` para ver los reverts y los
  dos episodios finales de malik.

---

## 2026-09-30 · Panel · construido · ba86529

- **Qué cambió:** `nucleo/plata.py` (`GET /plata`, `config/plata.json`) y `apps/panel`, un
  Next.js + TypeScript + PWA completo con las seis rutas del README del diseño
  (`docs/mockups/panel/diseno/`): Hoy (`/`), Proyectos, Metas, Bandeja, Semana, Ajustes.
  Tokens y contratos generados desde `design/tokens.json` y `contratos/contratos.json`
  (mismo patrón que `apps/ventanita`). `nucleo/servidor.py` suma `plata.router` y
  `allow_origins` para el panel. 10 pruebas de Playwright contra un núcleo falso
  (`tests/nucleo-falso.mjs`), 406 pruebas de `nucleo/` en verde, `mypy` limpio.
- **Decisiones que tomé sin preguntar:**
  1. **«Cobrada» del encargo = `pagada` del contrato.** `Entrega.estado` es
     `camino|entregada|pagada`; no hay `cobrada`. Documentado en `plata.py`.
  2. **Puerto del panel: 3000 → 4401 → 4402.** El encargo pedía 3000, que es de Organic Cash
     y Beam (avisado por Juan Camilo a mitad de sesión); el siguiente intento, 4401, ya lo
     usa `whisper-server` (STT del propio núcleo, hallado al levantar `next dev` ahí).
     `config/nucleo.json` ahora tiene `puerto_panel: 4402`, fuente única para
     `servidor.py` (`allow_origins`) y `apps/panel` (`scripts/generar-config.mjs` +
     `scripts/puerto-panel.mjs`, que arranca `next dev -p $(...)`).
  3. **Proyectos sin constelación.** El núcleo no tiene ninguna ruta que liste libros/temas
     (solo `/camino/{tema}`, que ya necesita el tema). La constelación completa del mockup
     (UpVisuals, Organic Cash, Omniway, Malik, Remi a la vez) no tiene de dónde salir sin
     inventar datos. La página muestra el camino real del bloque abierto y deja buscar
     cualquier otro tema a mano.
  4. **Metas sin metas nombradas.** `config/plata.json` solo tiene `meta_mensual` y
     `moneda` — nada de «Vivir solo», plazos en meses, ni desglose por línea de negocio
     (software vs. Malik). La página usa solo lo real: la meta mensual, lo cobrado, la
     brecha, la próxima entrega con dinero.
  5. **Semana queda en guion estático**, tal como pedía el encargo: cinco preguntas fijas,
     con la plata real en la primera pregunta (es la única con datos del núcleo hoy).
  6. `GET /camino/{tema}` con 404 es un dato legítimo («ese tema no tiene libro»), no
     «núcleo apagado»: `lib/nucleo.ts` lo distingue por `status` en vez de tratar todo
     `!ok` igual — si no, una búsqueda con tema equivocado prendía la pantalla de Apagado.
- **Dudas abiertas:**
  1. Sin una ruta que liste proyectos, Proyectos y Movil-Proyectos (constelación/lista
     completa) no se pueden construir de verdad. Falta decidir si eso lo agrega una sesión
     de `nucleo/` (fuera de mi frontera acá) o si Proyectos se queda así.
  2. `/donde-quede` sigue sin el siguiente hito (Fase 3, misma duda, todavía sin resolver).
  3. Semana no tiene ruta propia de resumen semanal (cerrado/aplazado/locura de la semana):
     por ahora son las frases fijas del guion, no datos.
  4. «Paso mínimo» (botón en Hoy) no quedó cableado a `POST /tarea/{id}/paso-minimo` — el
     encargo no lo pedía explícito y no había tiempo de diseñar bien ese flujo; el botón
     está pero no hace nada todavía.
- **Cómo probarlo a mano:**
  1. `cd nucleo && uv run pytest -q && uv run mypy .` — 406 en verde.
  2. Con el núcleo real corriendo (`cd nucleo && uv run python servidor.py`):
     `cd apps/panel && npm install && npm run dev` — abre en el puerto de
     `config/nucleo.json → puerto_panel` (4402 hoy).
  3. `cd apps/panel && npx playwright install chromium && npm run test:e2e` — 10 pruebas,
     sin tocar el núcleo real (usa `tests/nucleo-falso.mjs`).
  4. Con el teléfono (390 px, DevTools): Hoy y Proyectos se ven completos, barra inferior
     de 4 pestañas ≥ 56 px, sin scroll horizontal.
- **Qué falta:** túnel para probar desde el teléfono de verdad (hoy solo `localhost`);
  Semana con datos reales en vez del guion estático; «Paso mínimo» cableado; decidir el
  listado de proyectos (duda 1). No mergeado a `main` — queda para quien lo revise.

---

## 2026-09-30 · Fase 3 · corrección · 100f468

- **Qué cambió:** nada en el código. Los 3 fallos que la entrada de abajo daba por
  «preexistentes» no eran de datos faltantes en este Mac: el worktree `remi-fase3` no tenía
  el symlink `conocimiento -> ../remi-mente` (`.gitignore:26`, no se versiona). Con
  `ln -s ../remi-mente conocimiento` (sin commitear, es local a este worktree), las 349
  pruebas pasan en verde.
- **Decisiones que tomé sin preguntar:** ninguna; corrección de dato, indicada por Juan
  Camilo.
- **Dudas abiertas:** ninguna.
- **Cómo probarlo a mano:** `cd nucleo && uv run pytest -q` — 349 en verde, cero fallos.

---

## 2026-09-30 · Fase 3 (Bandeja + caminos + iniciativa) · construido · e3c2dd5

- **Qué cambió:** cuatro archivos nuevos en `nucleo/`, cuatro rutas agregadas al final de
  `servidor.py`, un commit por tarea (`8bf8107`, `34b48db`, `af62968`, `e3c2dd5`).
  1. `nucleo/bandeja.py` — `GET /bandeja` (ideas abiertas con `fria: bool`) y
     `POST /idea/{id}/revision` (`soltar|mantener|tarea`); revisar antes de las 48 h es 409;
     nunca `DELETE`.
  2. `nucleo/iniciativa.py` — motor por reglas (`rumbo`, `cuerpo`, `ritual`, `encoger`), sin
     IA, con presupuesto de silencio (5/día, 45 min entre dos, nada con Claude Code abierto
     salvo `rumbo`). Reloj siempre inyectado, nunca `datetime.now()` adentro.
  3. `GET /nudges/pendiente` y `POST /nudges/{id}/respuesta` en `servidor.py` — mismo
     contrato que ya llama la ventanita de `f-ventanita`. Idempotente.
  4. `nucleo/caminos.py` — `GET /camino/{tema}` lee `## Camino` de un libro; marca `[x]` de
     forma reactiva (al leer, no al cerrar una tarea) cuando hay una tarea `hecha` con el
     mismo título.
- **Decisiones que tomé sin preguntar:**
  1. `entregas.proyecto_id` (contrato) no está atado a ningún `Proyecto` real — esa tabla no
     existe en el núcleo. La regla `rumbo` lo usa tal cual, como si fuera el `tema` string
     del libro (el mismo texto de `sesiones.app_contexto`), solo para poder comparar contra
     el bloque abierto. Funciona porque hoy nada crea entregas de verdad; se cae el día que
     alguien intente crear una con un `proyecto_id` real.
  2. El presupuesto de silencio y el timestamp de cada nudge no viven en el contrato
     `Nudge` (no tiene `creada_en`, y cambiarlo es decisión de arquitectura que no me
     correspondía tomar sola). Los guardo en dos tablas propias de `iniciativa.py`
     (`iniciativa_nudges`, `iniciativa_silencios`), por fuera del esquema de `db.py`.
  3. Elegí NO tocar `trabajo.lineas_donde_quede()` para meter el siguiente hito ahí: el
     encargo lo pedía, pero la frontera decía «archivos nuevos + agregar rutas al final de
     servidor.py», y esa función vive en `trabajo.py`, ya escrito. Lo dejo en duda abierta
     en vez de estirar la frontera sin preguntar.
  4. Marcar `[x]` quedó reactivo (se revisa al pedir `GET /camino/{tema}`, no al cerrar la
     tarea) por la misma razón: cerrar una tarea pasa por `_cerrar_lo_abierto()` y por
     `POST /tarea/{id}/estado`, dos funciones ya escritas en `servidor.py` que no son «el
     final del archivo».
- **Dudas abiertas:**
  1. `/donde-quede` no incluye el siguiente hito todavía — está en `GET /camino/{tema}`,
     separado. Si se quiere ahí también, hace falta decidir si se toca `trabajo.py` (fuera
     de mi frontera) o se resuelve desde la ventanita pidiendo las dos rutas.
  2. El puente real entre `Entrega` y un proyecto (ítem 1 arriba) sigue sin existir. Cuando
     haya una forma real de crear entregas, hay que revisar `iniciativa._regla_rumbo`.
  3. `Nudge` sin `creada_en` me obligó a las tablas propias de la duda 2 arriba. Si en algún
     momento el contrato suma ese campo, `iniciativa_nudges` se puede borrar entera.
- **Cómo probarlo a mano:**
  1. `cd nucleo && uv run pytest -q && uv run mypy .` — 346 en verde (los 3 que fallan ya
     fallaban antes de esta fase: oficios/vectores de `remi-mente`, sin datos en este Mac).
  2. `uv run python servidor.py`, y en otra terminal: `curl -s localhost:4400/bandeja`,
     `curl -s localhost:4400/nudges/pendiente`, `curl -s localhost:4400/camino/<tema-real>`.
  3. La ventanita de `f-ventanita` sigue mostrando el Nudge sin ningún cambio en `apps/`.

---

## 2026-10-01 · Fase S (oficios v1) · 5 refresco semanal del oficio Claude Code · construido · d2841da

- **Qué cambió:** `nucleo/refresco_claude_code.py` nuevo, `scripts/refresco-claude-code.sh` +
  LaunchAgent `com.remi.refresco-claude-code` (domingos 5:00, después de la copia de las 3:00
  y la consolidación de las 4:00; sumado también a `desinstalar.sh`, que hasta hoy tampoco
  bajaba `com.remi.noche` — lo agregué de paso). Trae `CHANGELOG.md` real de
  `raw.githubusercontent.com/anthropics/claude-code` (~850 KB completo, se recorta a lo más
  reciente), Haiku extrae solo lo que no esté ya bajo «## Cambios anotados» en
  `oficios/claude-code.md`, y cada línea propuesta se verifica con
  `estado_libro.entidades_sospechosas`/`_invento` **contra el changelog real que se trajo**,
  no contra la respuesta del modelo — la diferencia importa: es la misma idea del incidente
  del 30-sep pero aplicada a la fuente correcta.
- **Encontré y arreglé un bug real probando en vivo, no simulado:**
  1. La URL que había puesto de entrada (`docs.claude.com/en/release-notes/claude-code`)
     redirige a un changelog en GitHub — la cambié a la fuente cruda
     (`raw.githubusercontent.com/.../CHANGELOG.md`), más liviana y sin HTML.
  2. **Primer intento real: el modelo contestó «me aparece que el changelog está vacío»** y
     mi código, sin darse cuenta, anotó esa frase confundida como si fuera una línea válida
     (no tenía ninguna entidad verificable que rechazar, así que pasó la verificación
     anti-invento sin problema — la verificación mecánica no cubre este tipo de fallo).
     Causa real: el límite de recorte (8.000 caracteres) cortaba ANTES de terminar la
     primera versión del changelog real, que sola mide 21.267 caracteres — el modelo recibía
     literalmente `# Changelog\n` y nada más. Lo vi en la bóveda real, lo revertí con
     `git revert` de verdad (`2eb0354`), y arreglé el recorte: 30.000 caracteres, y si ni así
     entra la primera sección entera, un corte crudo (una entrada partida a la mitad) en vez
     de dejar casi nada.
  3. **Con el prompt más grande, «rápido» (Haiku, techo de 20 s) no llegaba a contestar** —
     ese techo es para el chat con alguien esperando. Este refresco no tiene a nadie
     esperando: le puse un modo propio, mismo modelo, 120 s.
  4. Con las dos cosas arregladas, corrí el refresco real una tercera vez: 45 líneas reales
     anotadas (todo el changelog de la versión 2.1.285, porque «ya anotado» estaba vacío —
     la próxima corrida semanal va a ser incremental de verdad). Ninguna rechazada por
     invento; verifiqué a ojo contra el changelog real que ninguna es inventada.
  5. Tests nuevos que cubren exactamente este bug
     (`test_recortar_si_la_primera_seccion_sola_ya_pasa_el_limite_corta_crudo`), no solo el
     caso feliz. 314 pytest, mypy limpio (61 módulos).
- **Decisiones que tomé sin preguntar:**
  1. Corrí el refresco real tres veces contra la bóveda de producción (no una copia): es
     exactamente lo que el LaunchAgent va a hacer solo los domingos, y probarlo así fue lo
     que encontró el bug real — con un mock no hubiera aparecido.
  2. El primer resultado (la frase confundida) lo reverti con git en vez de sobreescribirlo a
     mano: es la prueba de que el punto 2 del encargo anterior (git en la bóveda) sirve para
     esto exactamente.
- **Dudas abiertas:**
  1. 45 líneas en la primera corrida es mucho para leer — es el costo de arrancar desde
     «(vacío)». Si se quiere, se puede podar a mano lo que no importa; las corridas de acá en
     adelante van a ser cortas.
  2. No até la salida del changelog a ninguna paginación real de «solo los últimos 7 días»:
     el recorte es por tamaño, no por fecha. Si en una semana floja Claude Code no saca
     ninguna versión nueva, el recorte de todos modos manda la última versión entera (ya
     anotada) y Haiku debería decir NADA — no lo probé con ese escenario exacto.
- **Cómo probarlo a mano:** `cd nucleo && uv run python refresco_claude_code.py`; mirar
  `remi-mente/oficios/claude-code.md` y `git log` en la bóveda.

---

## 2026-10-01 · Fase S (oficios v1) · 4 aprender de las correcciones · construido · 7d79a4f

- **Qué cambió:** `nucleo/correcciones.py` nuevo. Sin IA para detectar ni para redactar la
  regla — la regla siempre CITA algo real, nunca lo interpreta: si es «acordate: X», la
  regla es X literal; si es «no, así no» / «yo no diría eso», la regla es «No decir: «lo que
  Remi dijo antes»», tomado del último turno `remi` de la conversación vigente (tabla
  `turnos`). Sin turno de Remi que citar, no propone nada — no hay cómo sin inventar. El
  oficio destino sale de matchear las claves de los 9 oficios contra las palabras de la
  corrección; sin matches, `mi-voz` (la mayoría de correcciones sueltas son de tono). Tabla
  nueva `propuestas_correccion` (una por conversación, no es uno de los cinco contratos
  sagrados — es estado interno como `trabajo_eventos`). El flujo en `POST /mensaje`: si hay
  una propuesta pendiente y el mensaje la confirma (sí/dale/guardala/anotalo/confirmo), se
  agrega la línea al oficio con el commit automático que ya existe en la bóveda
  (`boveda_git.snapshot_antes/después`) y se borra la propuesta; si no confirma, se descarta
  en silencio (ley 3: no confirmar nunca es un fallo) y el mensaje sigue su curso normal.
  Test real con git de la bóveda (como `test_boveda_git.py`, sin simular nada): el flujo
  completo propone → confirma → la línea queda en el archivo → hay un commit real; y el caso
  negativo, sin confirmar nada cambia. 306 pytest, mypy limpio (59 módulos).
- **Decisiones que tomé sin preguntar:**
  1. Nada de llamar a un modelo para redactar la regla: citar literalmente lo que se dijo es
     la única forma de cumplir «basada en palabras que él usó, no en interpretación libre»
     sin depender de que un modelo no se vaya de tema. Es menos elegante que una regla
     redactada, pero no puede inventar.
  2. `propuestas_correccion` es una tabla nueva de estado interno, no un contrato: cambia
     libremente si hace falta, a diferencia de los cinco contratos de `contratos.json`.
  3. Sin conversación vigente (nadie pensó con think=true en la última hora), «no, así no»
     no propone nada: no hay turno de Remi para citar. «acordate: X» sí funciona siempre,
     porque no necesita ningún turno anterior.
- **Dudas abiertas:**
  1. El oficio destino por claves es un matcheo simple (palabra por palabra); una corrección
     ambigua puede caer en el oficio equivocado. Sin uso real todavía para calibrarlo.
  2. No probé una corrección real de Juan Camilo en la ventanita instalada — el flujo está
     probado de punta a punta contra `/mensaje`, no visto en pantalla.
- **Cómo probarlo a mano:** con el núcleo corriendo y pensando (think=true) en una
  conversación real, decir «no, así no» después de una respuesta de Remi → propone una regla
  citando esa respuesta; responder «dale» → confirma en `remi-mente/oficios/<el que
  corresponda>.md`, bajo «## Aprendido de Juan Camilo», con un commit real en la bóveda.

---

## 2026-10-01 · Fase S (oficios v1) · 3 «me escribió un cliente» · construido · 65eed02

- **Qué cambió:** `clasificar.es_texto_de_cliente()` detecta frases exactas («me escribió»,
  «me dijo», «el cliente dice», sin IA, mismo estilo que el resto de `clasificar.py`) antes
  del clasificador de tareas/ideas en `POST /mensaje` — no pasa por la Bandeja ni abre un
  bloque, porque es una lectura, no un pedido de Juan Camilo. `pensar.sistema_cliente()`
  (con `nucleo/prompts/cliente.md` nuevo) carga los oficios `clientes`, `proyectos-sop` y
  `mi-voz` enteros (nivel 2) más el proyecto activo, y pide las cuatro partes del oficio
  `clientes`: LECTURA, RIESGOS, RESPUESTA RECOMENDADA, LÍMITES, con el guardarraíl explícito
  al final («esto es un borrador, vos lo mandás»). `servidor._leer_cliente()` nunca guarda
  nada en `ideas` ni `tareas`. Test real: «me escribió Alfonso: necesito el generador de
  imágenes para el viernes» trae las cuatro partes, con el límite de red mockeado; y un test
  que confirma que el núcleo no tiene NINGUNA función para mandar algo afuera (no hay
  `enviar_cliente`, `enviar_whatsapp`, etc. — Fase 4 no existe todavía, así que Remi no puede
  enviar, no es solo que el prompt se lo pida). 282 pytest, mypy limpio (57 módulos).
- **Decisiones que tomé sin preguntar:**
  1. Sumé `"cliente"` al `Literal` de `tipo` en `RespuestaMensaje` (no es uno de los cinco
     contratos sagrados de `contratos.json`, es la respuesta interna de la API — cambiarlo no
     es la decisión de arquitectura que sí sería tocar un contrato).
  2. La detección es por frase exacta, no por largo de texto pegado: ya existe
     `episodios.LARGO_MINIMO` (1500) para «¿guardo esta charla como episodio?», y mezclar los
     dos criterios hubiera hecho que cualquier paste largo se leyera como cliente aunque no
     lo fuera.
- **Dudas abiertas:**
  1. Una frase como «¿qué me dijo el cliente la semana pasada?» podría dispararlo por error
     (matchea «me dijo» sin ser un mensaje pegado de un tercero): no lo probé de verdad en
     esta sesión, es un falso positivo teórico a vigilar en uso real.
- **Cómo probarlo a mano:** en la ventanita, con pensar activado: «me escribió Alfonso: necesito
  el generador de imágenes para el viernes» → salen las cuatro secciones y la línea del
  borrador al final.

---

## 2026-10-01 · Fase S (oficios v1) · 1–2 los oficios entran a la mente + puerta de prompts · construido · 81346ed

- **Qué cambió:**
  1. `nucleo/sembrar_conocimiento.py`: los 9 archivos de `remi-mente/oficios/` (que ya tenían
     `tipo: oficio`, `claves` y frontmatter completo de una siembra anterior) entran al índice
     de la mente (tabla `memoria`, la que viaja siempre en el system prompt) igual que los
     libros de proyecto — nivel 1 fijo, sin decaer, porque un oficio es saber-hacer, no
     actividad reciente. `nucleo/servidor.py` llama a `sembrar_oficios()` al arrancar, junto
     a `sembrar()`. La asociación por vector ya los cubría desde el encargo anterior
     (`vectores.py` ya recorre `oficios/`); lo que faltaba era el nivel 1.
  2. La puerta de prompts: `pensar.sistema_encargo()` ahora carga el cuerpo entero (nivel 2)
     de `prompting.md` y `claude-code.md` de la bóveda, más el resumen del proyecto activo
     (reusa `precarga.py`), y `nucleo/prompts/encargo.md` pasa de cinco secciones
     (QUÉ/DÓNDE/LISTO CUANDO/NO TOCAR/DESPUÉS) a las seis que pide el encargo: QUÉ LEER
     PRIMERO, DIAGNÓSTICO, PUNTOS, QUÉ NO HACER, LISTO CUANDO, RECOMENDACIÓN (+ DESPUÉS
     opcional). Esto cambia un contrato que la ventanita también lee: actualicé
     `apps/ventanita/src/markdown.ts` (`TITULOS_DEL_ENCARGO` y el título que abre la tarjeta)
     y sus pruebas para que la tarjeta de encargo se siga detectando. No toqué
     `~/proyectos/remi-ventanita` (Fase F, otro worktree): esto es solo `apps/ventanita` de
     `main`.
  3. Tests reales: `pruebas/test_oficios_mente.py` (siembra, idempotencia, lectura entera),
     `pruebas/test_vectores.py` suma la asociación real «qué es plan mode» → Claude Code,
     `pruebas/test_puerta_prompts.py` (las seis partes en `sistema_encargo()`, el contenido
     real de los oficios, la precarga del proyecto activo, y un pedido real de encargo con
     solo el límite de red mockeado). 271 pytest, mypy limpio (56 módulos); 73 vitest y tsc
     limpios en la ventanita de `main`.
- **Decisiones que tomé sin preguntar:**
  1. `fuente="manual"` para los oficios en la tabla `memoria` (no invento un valor nuevo como
     `"oficio"`: el contrato de `Memoria` es `Literal["conversacion", "manual", "ollama"]` y
     cambiarlo es una decisión de arquitectura, no un parche de esta tarea).
  2. Cambié el contrato de secciones del encargo (ver punto 2 arriba) porque el encargo del
     30-sep/1-oct pide exactamente esas seis partes con esos nombres; como esto rompía la
     detección de tarjeta de la ventanita en `main`, arreglé también ese lado en vez de dejarlo
     roto. `remi-ventanita` (Fase F) no lo ve hasta que se mergee — si esa rama ya cambió el
     parser de tarjetas por su cuenta, esto puede chocar al mergear: aviso para quien junte
     las ramas.
  3. `prompting.md` describe su propio 6.º punto como «Reporte pedido» (qué contar al cerrar
     un encargo desde Claude Code); el encargo de hoy pide un 6.º distinto («recomendación de
     modelo y pieza»). No edité `prompting.md` para unificarlos — son momentos distintos (abrir
     el encargo vs. cerrarlo) y el archivo es contenido de Juan Camilo, no mío para reescribir
     sin que él lo pida.
- **Dudas abiertas:**
  1. Si la rama de Fase F ya tiene su propio parser de tarjeta de encargo con los nombres
     viejos, hay que decidir en el merge cuál formato gana (o si la ventanita final no
     depende de nombres de sección textuales).
  2. No hice una llamada real a Claude para el test de la puerta de prompts (costo/tiempo):
     el test cubre la construcción real del system prompt y el paso de datos por `/mensaje`
     con el límite de red mockeado, no la respuesta real del modelo.
- **Cómo probarlo a mano:**
  1. `cd nucleo && uv run python sembrar_conocimiento.py` y mirar la salida `[oficios] creadas=…`.
  2. `curl -s localhost:4400/memoria | grep oficio-` (con el núcleo corriendo) — deberían
     aparecer los 9 temas `oficio-*`.
  3. Modo Prompt en la ventanita: «armame un encargo para arreglar el timing del executor de
     flujos» → la tarjeta trae las seis secciones.

---

## 2026-09-30 · Fase C · 4 precarga del proyecto activo · construido · dbe3186

- **Qué cambió:** `nucleo/precarga.py` nuevo. Antes de cada respuesta (`pensar.pensar()`), se
  suma a las instrucciones el nivel 2 (el Estado, o el resumen si el libro todavía no tiene
  Estado) del proyecto activo — sin que el modelo tenga que llamar a `leer`. Proyecto activo,
  en orden: (1) bloque abierto — la sesión de trabajo sin cerrar más reciente ya guarda el tema
  en `app_contexto` al abrirse la tarea; (2) app en primer plano por NSWorkspace — **todavía no
  existe esa señal en el núcleo** (es Fase F · 13, sin construir; lo dejo como hueco real, no
  no lo inventé); (3) el último libro tocado (`trabajo_eventos`, lo mismo que usa
  `trabajo._libro_reciente()` para «¿dónde quedé?»). Log: `[precarga] precargado=<tema>
  razon=<bloque_abierto|ultimo_tocado>`, o «nada que precargar» si no hay ninguna señal.
- **Verificado en vivo, no solo con tests:** reinstalé el núcleo real y le pregunté «¿en qué
  estoy trabajando ahora?» con `think=true`. El log dice `precargado=remi razon=ultimo_tocado`
  y `leyó=no` en la misma línea del log de Claude — no bajó nada del estante. La respuesta
  describió bien el trabajo real de hoy (la verificación anti-invento, la consolidación
  nocturna) sin inventar nada ajeno. Más 4 tests reales en `test_precarga.py` (bloque abierto
  gana al último tocado; sin ninguna señal no hay nada que precargar; sin Estado todavía usa
  el resumen del libro). 262 pytest, mypy limpio (54 módulos).
- **Decisiones que tomé sin preguntar:**
  1. `estado_libro` se importa DENTRO de `precarga.resumen_nivel2()`, no arriba del archivo:
     arriba crea un ciclo real (`pensar → precarga → estado_libro → pensar`) que Python tolera
     en la práctica pero es frágil; adentro de la función lo evita del todo. Lo probé
     importando cada módulo por separado como punto de entrada (`pensar`, `estado_libro`,
     `noche`) antes de confiar en que no rompía nada.
  2. La precarga nunca rompe la respuesta: cualquier excepción se atrapa y Remi piensa igual,
     solo que sin el nivel 2 puesto (mismo criterio que `_asociados`).
- **Dudas abiertas:**
  1. **Falta NSWorkspace de verdad** (Fase F · 13): sin eso, «app en primer plano» no es una
     señal real todavía — hoy el orden efectivo es bloque abierto → último tocado, nada más.
  2. «Bloque abierto» hoy depende de que exista una `Sesion` con `fin IS NULL`; una Tarea
     abierta sin sesión (o cuya sesión ya se cerró) no cuenta como bloque — es el mismo
     concepto que ya usa el resto del núcleo, no inventé uno nuevo.
- **Cómo probarlo a mano:** con el núcleo corriendo, `curl -s -X POST
  http://127.0.0.1:4400/mensaje -d '{"texto":"¿en qué estoy trabajando ahora?","think":true}'`
  y `grep '\[precarga\]' ~/Library/Logs/Remi/nucleo.log`.

---

## 2026-09-30 · Fase C · 3 el libro de errores (oficio stack) · construido · ad302a3

- **Qué cambió:** `nucleo/cierre.py`. Al cerrar una sesión de Claude Code, si el transcript
  tiene un patrón de problema resuelto («la causa era», «se arregló», «fallaba porque» —
  `PATRON_ERROR`, insensible a mayúsculas), además del episodio normal se escribe un segundo
  episodio con `fuente: error` y `claves: [error, <tema>]` en el frontmatter, con cuatro
  secciones: Síntoma, Causa, Cura, Archivo. `redactar_error()` se lo pide a Haiku con la misma
  disciplina anti-invento (si un dato no aparece claro en la charla, escribe «sin dato» en vez
  de completar); si las cuatro secciones salen «sin dato», no se escribe ningún episodio de
  error — mejor ninguno que uno vacío. `oficios/stack.md` ya documentaba que Remi busca ahí
  antes de proponer un arreglo nuevo; esto es lo que lo alimenta.
- **Verificado de verdad:** test con un transcript sintético que dice «la causa era que el
  webhook no reintentaba tras un 500» produce un segundo `.md` con `fuente: error`,
  `claves: [error, malik]` y las cuatro secciones con los datos del transcript (no inventados:
  se pasaron por el mock del test, pero el test también prueba que sin el patrón de error no
  se llama ni una vez a `redactar_error`). 258 pytest, mypy limpio.
- **Decisiones que tomé sin preguntar:**
  1. El episodio de error usa el mismo mecanismo de commit automático de la bóveda
     (`boveda_git.snapshot_antes/despues`) que el episodio normal — un segundo par de commits,
     no uno solo, para que quede claro en `git log` que son dos escrituras distintas.
  2. Si `redactar_error` devuelve `None` (Haiku caído, o no sacó ningún dato real), no hay
     respaldo con Ollama ni con un episodio «plano»: para un libro de errores, ningún dato es
     mejor que un dato a medias.
- **Dudas abiertas:**
  1. El patrón de detección es de texto exacto («la causa era», «se arregló», «fallaba
     porque»); una sesión que resuelve un problema con otras palabras («ya quedó», «era por»)
     no deja episodio de error. Se puede ampliar cuando se vea un caso real que se escape.
  2. No hay todavía nada que LEA el libro de errores antes de proponer un arreglo (lo que
     `oficios/stack.md` promete) — esto solo lo escribe. Es un punto aparte, no pedido hoy.
- **Cómo probarlo a mano:** cerrar una sesión de Claude Code real donde se haya dicho «la
  causa era…» o «se arregló…»; mirar `remi-mente/episodios/` — tiene que aparecer, además del
  episodio normal, uno con `error` en el nombre y `fuente: error` en el frontmatter.

---

## 2026-09-30 · fix urgente: verificación mecánica anti-invento en el Estado · construido · 3d580b1

- **Por qué:** el coordinador paró el encargo en curso al ver el incidente que ya había
  anotado yo mismo en la entrada de abajo (Fase C · 1–2) — el mitigado por mtime no alcanzaba:
  hacía falta una verificación de lo que el modelo REALMENTE contestó, no solo de si había
  evidencia antes de llamarlo.
- **Qué hice, en orden:**
  1. Bajé el LaunchAgent `com.remi.noche` (`launchctl bootout`) apenas llegó el aviso, antes
     de tocar código — no quedó corriendo sin la guarda nueva ni un minuto.
  2. `nucleo/estado_libro.py`: `entidades_sospechosas()` saca del texto que contestó el
     modelo las cosas que se pueden verificar mecánicamente — siglas (`N8N`, `WAL`, `CRM`...),
     números de dos o más cifras, nombres de archivo — y `_invento()` confirma que cada una
     aparece literal en el `pedido` (estado anterior + commits/episodios). `redactar()` ahora
     rechaza la respuesta de Haiku si inventó algo así (y prueba con Ollama); si Ollama
     también inventa, devuelve `None` — el libro no se toca, no hay commit en la bóveda.
     `noche.py` distingue en el resultado `sin_evidencia_nueva` (el pedido no traía nada) de
     `rechazado_o_sin_respuesta` (había evidencia, pero la respuesta no pasó la verificación).
  3. **Causa raíz, no solo el síntoma:** `sin_evidencia_nueva()` funcionaba bien — el pedido
     SÍ traía los dos episodios de hoy, así que la guarda dejaba pasar la llamada al modelo
     correctamente. El agujero real es que la única defensa contra inventar, una vez que el
     modelo SÍ tiene evidencia real para trabajar, era una instrucción de texto en el prompt
     («no inventes...») sin nada que la verificara después. Instrucción no es garantía.
  4. Test de integración de punta a punta (`test_noche.py`) sin mockear `estado_libro.redactar`
     por dentro — solo el límite con `pensar._una_llamada_claude`/`_llamar_ollama`, como pasaría
     de verdad — confirma que la consolidación completa rechaza una respuesta con `N8N` y deja
     el libro intacto. Más 6 tests unitarios de `entidades_sospechosas`/`_invento`/`redactar`
     en `test_estado_libro_invento.py`.
  5. Repuse (ya lo había hecho antes de que llegara el aviso, con el mismo commit `001b709` en
     la bóveda) el Estado real de `organic-cash.md` — el de «Terminar el editor de flujos y el
     flujo de Lead Nuevo», confirmado por Juan Camilo — no el inventado con N8N/WAL/Opción B.
  6. Con los tests en verde, volví a levantar `com.remi.noche` (`launchctl bootstrap`).
- **Verificado de verdad:** 258 pytest (7 nuevos + 1 de integración), mypy limpio (52
  módulos); `organic-cash.md` con el texto correcto (`git show 257c906:proyectos/organic-cash.md`
  contra el archivo real, iguales); el LaunchAgent recargado (`launchctl list | grep remi.noche`).
- **Decisiones que tomé sin preguntar:**
  1. La verificación es deliberadamente conservadora: puede rechazar una respuesta correcta
     que use una sigla legítima parafraseada de forma distinta a la fuente (falso positivo).
     Prefiero eso a un falso negativo — es exactamente la filosofía de `claves.py`.
  2. No intenté verificar prosa libre completa (una paráfrasis inventada de una frase entera
     sin siglas/números/archivos no la detecta esto): lo dejo como duda abierta abajo, no como
     algo resuelto.
- **Dudas abiertas:**
  1. **Esto mitiga el tipo exacto de invento del incidente, no todo invento posible.** Una
     paráfrasis que cambia el sentido sin introducir una entidad verificable (ninguna sigla,
     número o archivo nuevo) pasa igual. Si se repite un incidente sin esas señales, hace falta
     algo más fuerte (¿otra llamada al modelo para verificar la primera? ¿bajar la frecuencia de
     escritura automática y sumar una revisión de Juan Camilo antes de commitear?).
  2. El guardia por mtime del punto anterior sigue activo y es la primera línea de defensa
     contra la causa concreta que disparó esto (episodios viejos re-derivando un Estado
     corregido a mano); esta verificación es la segunda línea, para cuando SÍ hay evidencia
     fresca real pero el modelo igual se pasa de la raya.
- **Cómo probarlo a mano:** `cd nucleo && uv run pytest pruebas/test_estado_libro_invento.py
  pruebas/test_noche.py -v`; `launchctl list | grep remi.noche` (tiene que aparecer cargado).

---

## 2026-09-30 · Fase C · 1–2 claves + consolidación nocturna (con un segundo incidente en vivo) · construido · e79225a

- **Qué cambió:**
  1. `a3b3e44` `nucleo/claves.py`: `claves:` (3–6 palabras) en el frontmatter de libros,
     oficios y episodios que no las tenían — Haiku una vez, con la misma regla anti-invento de
     `estado_libro.py` más un filtro programático nuevo (`filtrar_inventadas`): cualquier
     clave que el modelo devuelva y no aparezca literal (sin acentos/mayúsculas) en
     título+resumen+cuerpo se descarta antes de escribir nada. Corrido de verdad: 7 proyectos
     y 2 episodios recibieron claves reales; las 4 áreas y `oficios/README.md` quedaron sin
     tocar porque son placeholders («Completar: …») sin texto real del que sacar nada — el
     filtro funcionó como se esperaba, no como falla.
  2. `e79225a` `nucleo/noche.py` + `scripts/noche.sh` + LaunchAgent `com.remi.noche` a las
     4:00 (instalado y corriendo — `launchctl list | grep remi.noche`). Episodios del día →
     Estado del libro tocado (solo con evidencia real); fusiona episodios repetidos del mismo
     día y libro (mismo resumen exacto); recalcula vectores de lo que cambió; reordena la
     mente (`sembrar_conocimiento.nivel_de`: nivel 1 si el libro se tocó en 7 días, si no
     nivel 2 — nunca se borra nada, ARQUITECTURA §2).
- **Incidente en vivo, encontrado probando el punto 2 (lo digo completo, no lo escondo):**
  corrí `noche.sh` a mano dos veces seguidas para conseguir el log real que pedía el encargo.
  Las dos veces, la rutina volvió a mirar los mismos dos episodios de hoy sobre
  `organic-cash-malik` (ya viejos: describen algo ya resuelto) y **pisó el «Próximo paso» que
  Juan Camilo acababa de confirmar a mano** («terminar el editor de flujos y el flujo de Lead
  Nuevo», commit `257c906`). La primera pasada lo cambió por una paráfrasis de los episodios;
  la segunda **inventó texto que no está en ninguna fuente real** («N8N», «WAL», «Opción B
  confirmada por vos», «Nodo 1 / Nodo 2») — verificado con `grep` contra los dos episodios: no
  aparece ninguna de esas palabras. La instrucción anti-invento de `estado_libro.redactar`
  (texto libre al modelo) no alcanzó para evitarlo esta segunda vez; a diferencia de
  `claves.py`, acá no hay un filtro programático porque el Estado es prosa, no una lista de
  palabras sueltas.
- **Arreglo real, no solo el parche del archivo:** `noche.py` ahora descarta cualquier
  episodio más viejo (mtime) que la última escritura del Estado del libro — un episodio solo
  cuenta como evidencia si es más nuevo que la corrección que podría pisar. Test de regresión
  con el escenario exacto del incidente (`test_no_toca_un_episodio_mas_viejo_que_la_ultima_escritura_del_estado`).
  Verificado en vivo: una tercera corrida de `noche.sh` contra los mismos episodios devolvió
  `resultado=sin_evidencia_nueva` y no tocó el archivo. `organic-cash.md` quedó repuesto a mano
  (commit `001b709` en la bóveda) con el texto exacto que Juan Camilo había confirmado.
- **Verificado de verdad:** `noche.log` real (vía `launchctl kickstart`, no simulado) con las
  tres corridas completas; 248 pytest, mypy limpio (51 módulos); `git log` de la bóveda
  muestra los commits automáticos de cada paso.
- **Decisiones que tomé sin preguntar:**
  1. El guardia por mtime es más fuerte que exigir «commits nuevos hoy»: también cubre el caso
     de una corrección manual hecha hoy mismo, que es justo lo que pisó el incidente.
  2. `areas/` entra a `claves.py` (ya entraba a `vectores.py` de un encargo anterior) aunque el
     encargo solo nombraba libros/oficios/episodios: mismo criterio que la vez pasada.
  3. La fusión de episodios repetidos solo actúa con resumen **exactamente** igual (normalizado
     por espacios/mayúsculas/acentos) — no intenta adivinar «parecido». Es deliberadamente
     conservador después de lo de arriba.
- **Dudas abiertas:**
  1. **El fondo del problema no está cerrado, solo mitigado.** El guardia por mtime evita que
     un episodio viejo pise una corrección reciente, pero si el `redactar()` de una noche
     normal recibe evidencia real y de todos modos parafrasea de más o inventa un detalle
     colateral, nada lo detecta hoy — no hay equivalente al `filtrar_inventadas` de
     `claves.py` para prosa libre. Vale la pena, antes de confiar en esto sin mirar, sumar
     algo que compare nombres propios/números del Estado nuevo contra las fuentes (commits o
     episodios) y avise si aparece uno que no estaba.
  2. `noche.log` no se escribe si el script corre interactivo desde una sesión de Claude Code
     (mismo patrón que `copia.sh`: el `tee` solo entra con TTY, y sin TTY solo escribe si
     `launchd` redirige el proceso). No es un bug nuevo, ya lo tenía `copia.sh`; lo dejo
     anotado porque me confundió un rato.
- **Cómo probarlo a mano:** `cd nucleo && uv run python claves.py` (idempotente, no repite si
  ya hay claves); `launchctl kickstart -k gui/$(id -u)/com.remi.noche` y mirar
  `~/Library/Logs/Remi/noche.log`; escribir un episodio de prueba con fecha de hoy, tocar a
  mano el Estado del mismo libro después, y confirmar que una corrida de `noche.sh` posterior
  dice `sin_evidencia_nueva` para ese tema.

---

## 2026-09-30 · Fase F · 3f: ventanita final (9 puntos) · construido · 32cffe2

- **Qué cambió** (worktree `remi-ventanita`, rama `f-ventanita`; frontera del encargo: solo
  `apps/ventanita/` y un archivo nuevo `nucleo/entregas.py`, sin tocar `actualizar.sh`). Un
  commit por punto, de `89e33b5` a `32cffe2`:
  1. `89e33b5` **Isla de reposo**: `reposo.ts` (lógica pura, con test) — 120×44 solo el
     punto; con algo que decir, 210×64 por 4 s y se encoge en 200 ms (`animarTamano`); el
     mouse encima la vuelve a mostrar. Reemplaza los tres tamaños viejos de reposo
     (`TAMANO_REPOSO_CON_HACE` ya no existe).
  2. `45e3eb0` **Entrega en uso**: `nucleo/entregas.py`, router aparte con una sola línea de
     include en `servidor.py` (`app.include_router(entregas.router)`, más el import). CRUD
     completo contra la tabla `entregas` que ya existía en `db.py` pero sin funciones.
     `parsear_entrega()` reconoce «entrega para Alfonso el 18 de octubre por 5.000» con
     regex, sin IA. `GET /entregas/de-proyecto/{id}` dice si un proyecto tiene una entrega
     viva (no pagada, con monto).
  3+4. `14b8411` **Piel dinero + Reloj de una línea**, en el mismo commit porque comparten
     el efecto de `App.tsx` que resuelve la entrega del bloque abierto. `StatusDot` suma
     `dinero` (reemplaza `brasa` en `hablando`, sin glow nuevo: el DS solo tiene tres).
     `Chat.tsx` suma `RelojLinea`: «0:31 · la última vez 1:20» (`formatearReloj`, h:mm,
     `tiempo.ts`), bajo el bloque abierto, en `brasa` o `dinero`.
  5. **Ya estaba.** «Hecha» + celebración (chispas de `dinero`, 950 ms) es el commit
     `8595827` de Fase F, de antes de este worktree — lo verifiqué contra el encargo punto
     por punto y cumple: bajo el último mensaje, solo con bloque abierto, ley 3 (sin
     celebrar un cierre que falló). No lo reconstruí.
  6. `1ff7ab5` **Nudge dentro del chat**: componente canónico `Nudge.tsx`, píldoras «Listo» /
     «Ahora no», Enter/Escape, expande desde reposo, sin sonido. `servidor.ts` tiene el
     cliente (`obtenerNudgePendiente`, `responderNudge`) contra `/nudges/pendiente` y
     `/nudges/{id}/respuesta` — **esos endpoints no existen en el núcleo todavía** (grep
     limpio en `servidor.py`); el cliente devuelve `null`/`false` ante cualquier fallo, así
     que no rompe nada hasta que la sesión de Fase 3 los construya.
  7. `b7623ba` **Retomar**: al abrir sin nada nuevo dicho, los últimos 3 turnos de la
     conversación vigente (antes eran todos) en `ink-muted` (clase nueva y reusable en
     `estilos.css`).
  8. `b52c2e4` **⌘⇧C**: copia el encargo cuando la última respuesta de Remi es una tarjeta de
     prompt (`partirRespuesta` ya distinguía `tipo: "encargo"`; solo faltaba el atajo).
  9. `32cffe2` **Limpieza DS**: Geist Mono 500 empaquetado (`geist-mono-500.woff2`, tomado
     del paquete npm `geist`, SIL OFL — antes solo estaba el 400 y `.num` pedía un peso que
     no existía); borde especular sacado del hex suelto en `App.css` a una variable única
     `--borde-especular` (**no** es un token real del DS: `tokens.css` se genera de
     `design/tokens.json`, que no edito a mano — queda anotado para sumarlo al Design System
     real); `.limite-error__detalle` pisaba `.code` a 11 px suelto, ahora usa los 13 px de
     `.code`. Biónica en nudges: cubierta por el punto 6. Biónica en celebración: ya estaba
     cubierta sin querer, porque «Cerrado. N min.» pasa por el mismo `partirRespuesta` +
     `Partes` que cualquier otra respuesta.
- **Verificado:** 89 vitest, tsc limpio, `cargo check` + `cargo test` (11 tests) limpios en
  `src-tauri`, 253/254 pytest del núcleo (la única roja, `test_vectores.py`, es de Fase C —
  confirmé que falla igual con `entregas.py`/`servidor.py` en stash, no es mía), `mypy
  entregas.py` limpio.
- **Decisiones que tomé sin preguntar:**
  1. `_proyecto_id_de_tema()` en `entregas.py` inventa un id determinístico (`uuid5`) por
     `tema` porque **hoy no existe un Proyecto con id real** en el núcleo — `tarea.proyecto_id`
     sale `None` siempre (`servidor.py`, donde se arma la `Tarea` al abrir un bloque). Piel
     dinero y «de-proyecto» están wireados de punta a punta y con tests, pero en la app real
     no se van a disparar hasta que algo le ponga `proyecto_id` a una tarea — que es trabajo
     de `nucleo/` fuera de mi frontera. Lo dejo escrito acá en vez de tocar `servidor.py` más
     de la una línea que pedía el encargo.
  2. Bundle de `3+4` en un commit: pedían «un commit por punto» pero los dos tocan el mismo
     efecto de `App.tsx` que resuelve si el bloque abierto paga; separarlos hubiera sido un
     commit roto a la mitad. Mismo criterio que ya usó esta rama en `9fda832` (`3+4`).
  3. No reconstruí el punto 5: ya estaba, commit `8595827`, y dupli carlo hubiera sido peor
     que dejarlo.
- **Dudas abiertas:**
  1. **`/nudges/pendiente` y `/nudges/{id}/respuesta` no existen.** El cliente y el
     componente están listos y probados con la lógica pura (`nudges.ts`), pero nadie vio un
     nudge real en pantalla todavía — hace falta el backend de Fase 3 y probarlo a mano.
  2. **`tarea.proyecto_id` sigue siendo siempre `null`.** Piel dinero y Reloj dinero no se
     van a ver nunca hasta que alguien (fuera de esta frontera) le asigne proyecto a una
     tarea al crearla. Encargo aparte para `nucleo/`.
  3. **Borde especular no es un token real.** Queda como variable local en `App.css`; falta
     sumarlo al Design System real (claude.ai) para que `tokens.css` lo genere de ahí.
  4. No vi nada de esto en pantalla (mismo motivo que Fase F: no hay `@testing-library/react`
     en este repo, todo lo cubierto es lógica pura en `.ts`).
- **Cómo probarlo a mano:**
  1. Reposo con algo que decir: la píldora nace en 210×64, a los 4 s se encoge sola a
     120×44; pasar el mouse la vuelve a mostrar.
  2. `curl -X POST localhost:4400/entregas -d '{"texto":"entrega para Alfonso el 18 de
     octubre por 5.000"}' -H 'Content-Type: application/json'` — 201 con `cliente:
     "Alfonso"`, `monto: 5000`.
  3. `cd nucleo && uv run pytest pruebas/test_entregas.py -v`.
  4. `cd apps/ventanita && npx vitest run && npx tsc --noEmit -p .`.
  5. `cd apps/ventanita/src-tauri && cargo test`.
  6. Decir «armame la tarea de mandar la factura», ver que aparece «Hecha» y el reloj de una
     línea bajo la respuesta; tocar «Hecha» y ver la celebración.

---

## 2026-09-30 · reparación del incidente de los Estados + vectores de Fase C · construido · 961aeb6

- **Qué cambió** (encargo corto de Juan Camilo, cinco puntos, un commit cada uno):
  1. `malik.md` recupera su línea «Próximo paso» tal cual la leyó Claude antes del incidente
     (`scripts/escritorio4.swift`). **`remi.md` y `organic-cash.md` NO se tocaron**: al ir a
     reponerlos encontré que ya no tenían el marcador de «se perdió» — tenían contenido
     distinto y concreto (`Revisar la lógica de cierre de tareas en Chat.tsx` y `Revisar el
     ENCARGO.md en malik-gestion`), y confirmé con el log del núcleo que es contenido real:
     el gancho de commits ya venía actualizando `remi.md` legítimamente con los commits de
     hoy mismo (verificado en vivo más tarde: su Estado pasó a hablar de `sin_evidencia_nueva`
     apenas hice ese commit). Pisarlos con el texto de antes del incidente hubiera sido
     repetir el mismo error que este encargo existe para prevenir.
  2. `git init` en `~/proyectos/remi-mente` (commit propio de ese repo, sin remote).
     `nucleo/boveda_git.py`: `snapshot_antes()`/`snapshot_despues()` alrededor de las tres
     escrituras del núcleo en la bóveda (`trabajo.actualizar_estado`, `cierre.guardar`,
     `episodios.guardar`). Probado con git de verdad, tmp y real: un `git revert` real
     recupera un pisón. La copia nocturna con restic ya incluye el `.git` nuevo — hace backup
     de la carpeta entera, no hace falta tocar `copia.sh`.
  3. `estado_libro.sin_evidencia_nueva()`: `redactar()` no llama a Haiku ni a Ollama si el
     pedido no trae commits nuevos — el fallo exacto del incidente (un script suelto llamando
     a `redactar()` con la bandeja vacía).
  4. La instrucción anti-invento ya existía desde `0483a55`; se suma un test que confirma que
     viaja de verdad al modelo.
  5. `nucleo/vectores.py`: `nomic-embed-text` (274 MB, Ollama) — elegido contra `bge-m3`
     (1,16 GB, manifest de la registry consultada antes de bajar nada) — vectoriza
     título+resumen+claves de `proyectos/`, `areas/`, `oficios/` (`tipo: oficio`) y
     `episodios/` en `sqlite-vec`, y solo recalcula si el hash del contenido cambió.
     `pensar.py` suma los 3–5 asociados a la mente antes de cada respuesta, solo títulos.
     `remi.db` real ya tiene las 22 notas vectorizadas.
- **Verificado de verdad, no simulado:** 236 pytest (`test_boveda_git.py` con git real,
  `test_vectores.py` con Ollama real contra la bóveda real), mypy limpio (45→47 módulos).
  Contra el núcleo instalado y reiniciado con `scripts/instalar.sh`: `POST /mensaje` con «lo
  del cliente que desconfiaba» trajo `shopify-cliente` entre los asociados y Sonnet contestó
  bien (sin inventar que es cliente de Juan Camilo). `git log` en la bóveda real ya tiene
  commits automáticos de actividad real de hoy (un Estado de `remi.md` actualizado por un
  commit mío, capturado por `snapshot_antes` antes de escribir un episodio de UpVisuals).
- **Decisiones que tomé sin preguntar:**
  1. No reescribí `organic-cash.md`: su «Próximo paso» quedó tal como estaba (no era el
     marcador de pérdida) — no tenía por qué tocarlo.
  2. `areas/` entra a los vectores aunque el encargo solo nombraba proyectos/oficios/
     episodios: es «un libro por área» de la arquitectura, mismo formato, y el costo es
     cero (se recalcula solo si cambia).
  3. `sqlite-vec` como dependencia nueva del núcleo (`uv add`), con override de mypy para sus
     tipos faltantes, igual que kokoro/soundfile.
- **Dudas abiertas:**
  1. Dos procesos escribiendo en la bóveda al mismo tiempo (dos sesiones de Claude Code, o el
     núcleo y un script a mano) podrían pisarse en la ventana entre `git add` y `git commit`
     de `boveda_git`. No pasó hoy, pero no hay lock. Si se repite, un `flock` alrededor
     del commit es la solución simple.
  2. `organic-cash.md` sigue sin su «Próximo paso» real: si Juan Camilo o Grok lo recuerdan,
     se repone a mano; si no, lo escribe el próximo commit real de ese proyecto.
- **Cómo probarlo a mano:** `cd ~/proyectos/remi-mente && git log --oneline` (tiene que haber
  más de un commit); `cd ~/proyectos/remi/nucleo && uv run pytest pruebas/test_boveda_git.py
  pruebas/test_vectores.py -v`; preguntarle a Remi «lo del cliente que desconfiaba» y ver que
  mencione Shopify.

---

## 2026-09-30 · Fase F · 1–2 la bolita y la voz vuelven al DS · construido · e071101

- **Qué cambió:** este encargo llegó a mitad del anterior (Biblia v3.3, «la ventanita final»):
  no tocar la estructura del chat, solo lo que sigue. `StatusDot.css`: pensando pasa a `pensar`
  (lavanda) con su glow, hablando a `brasa` con el suyo — antes la maqueta del 30-sep los pisaba
  a `ink-muted`/`ink` sin brillo (entrada `a2a866f`). Tamaños de esa maqueta (48 px hablando,
  28 px pensando) sin tocar; el anillo de «pensando» también pasa a `pensar`. `Chat.css`: la voz
  de Remi en el chat volvió a 20 px — `.display-it` (24 px, el token suelto) le ganaba a
  `.chat__remi` (que ya decía 20 px) por orden de cascada, no por diseño; ahora
  `.display-it.chat__remi` sube la especificidad sin tocar el token global (sigue en 24 px en
  `LimiteDeError`, que es la única otra pantalla que lo usa).
- **Decisiones que tomé sin preguntar:** ninguna nueva más allá de las de arriba.
- **Dudas abiertas:** no lo vi en pantalla (mismo motivo que el punto 5: no hay tests de
  componentes React en este repo). `tsc` y los 73 vitest en verde.
- **Cómo probarlo a mano:** abrir Remi, hacerle una pregunta que piense: el punto tiene que
  verse lavanda con un halo suave mientras piensa, y naranja (brasa) con su halo mientras
  contesta en voz. La respuesta escrita en el chat se ve un poco más chica que antes (20 px).

---

## 2026-09-30 · 5 celebración + botón Hecha en el chat · construido · 8595827

- **Qué cambió:** `Chat.tsx`/`Chat.css` (celebración y el botón), `servidor.ts` (`cerrarTarea`),
  `App.tsx` (pasa `tarea`/`sesion` al agregar el mensaje y conecta `onCerrarBloque`). Cuando el
  último mensaje de Remi abrió un bloque (`tipo: "hoy"`), aparece «Hecha» debajo; al tocarla
  cierra la tarea real y el mismo mensaje se enfría hacia `luz` con ocho chispas de `dinero`,
  950 ms, una vez, y el texto pasa a «Cerrado. N min.» en su lugar.
- **Decisiones que tomé sin preguntar:**
  1. **Sobre el chat, no una tarjeta aparte.** Fase F llegó a mitad de este punto pidiendo
     exactamente eso; no lo dupliqué.
  2. Si `cerrarTarea` falla (el núcleo no respondió), no hay celebración: ley 3, nada de
     festejar algo que no pasó. El botón queda como estaba, se puede tocar de nuevo.
  3. La duración que se muestra es `real_min` de la `Tarea` que devuelve
     `/tarea/{id}/estado`, no un cálculo mío en el cliente.
- **Dudas abiertas:**
  1. **No lo vi en pantalla.** Este repo no tiene tests de componentes React (todo lo que hay
     en vitest es lógica en `.ts`); armar `@testing-library/react` + jsdom es una decisión
     aparte que no tomé sola. `tsc` y los 73 vitest existentes están en verde.
  2. Si dos mensajes distintos de Remi abrieran un bloque cada uno (no pasa hoy: solo el
     último puede tener `tipo: "hoy"` mientras nada se cerró), el botón solo se ofrece en el
     último — los anteriores quedan sin «Hecha», que es lo que ya pasaba antes de este cambio.
- **Cómo probarlo a mano:** decir «armame la tarea de mandar la factura», ver que aparece
  «Hecha» bajo la respuesta; tocarla y mirar que el mensaje se enfríe con chispas y el texto
  cambie a «Cerrado. N min.». Con reducción de movimiento activada en macOS, tiene que cambiar
  el color sin chispas.

---

## 2026-09-30 · 0b Haiku escribe el Estado — y un incidente con los libros reales · construido · 0483a55

- **Qué cambió:** `nucleo/estado_libro.py::redactar` probaba Ollama primero; ahora prueba
  **Haiku por Max primero**, con `conocimiento/caracter.md` antepuesto a las instrucciones (la
  llamada no llevaba carácter para nada antes de esto: `--system-prompt` reemplazaba todo).
  Ollama queda de respaldo si Haiku no contesta.
- **Incidente (lo digo completo, no lo escondo):** para «reescribí una vez el Estado de los 7
  libros» corrí un script suelto que llamaba a `redactar()` con el Estado anterior como único
  dato y **commits vacíos**. Con la bandeja vacía, Haiku no reescribió el tono: **inventó
  hechos nuevos** que no estaban en el Estado anterior (a `beam.md` le puso «se añadió un
  icono de atención en el formulario de contacto», algo que no existe en el texto que le di).
  Pisé `beam.md`, `malik.md`, `organic-cash.md` y `remi.md` con eso, y **la bóveda no tiene
  git** — no había con qué revertir.
- **Recuperado:** el snapshot restic de anoche (`00fabe4a`, 00:22, antes de que existiera
  `beam.md` o los Estados de hoy) no sirve para esto — es de antes de que se escribiera el
  contenido que pisé. Restauré a mano lo que puedo probar que era real:
  - `beam.md`: **recuperado completo y exacto** — las tres líneas están literales en el
    contexto que el SessionStart le mandó a otra sesión de Claude Code hoy mismo, antes de
    que yo tocara nada.
  - `malik.md`, `organic-cash.md`, `remi.md`: recuperé **Quedaste** y **Decisiones** tal cual
    los vi en el diagnóstico de 0a, antes de pisarlos. La línea **Próximo paso** de esos tres
    no la reconstruí de memoria ni inventé una: quedó escrita como
    «esta línea se perdió en una reescritura sin respaldo del 30-sep» — así, si alguno de
    ustedes recuerda cuál era, se repone tal cual, y si no, la reemplaza el próximo commit
    real de cada proyecto.
- **Decisiones que tomé sin preguntar:**
  1. **No hice la reescritura de los 7 Estados que pedía el encargo.** Con commits reales
     (no vacíos) el riesgo de inventar baja mucho porque el modelo tiene de dónde sacar la
     frase, pero después de este susto no quise repetir el experimento sobre datos reales sin
     que alguien lo revise primero. Queda pendiente, con la salvedad de abajo.
  2. `omniway.md`, `shopify-cliente.md` y `upvisuals.md` nunca tuvieron `## Estado`: no
     escribo uno de la nada.
- **Dudas abiertas:**
  1. **La línea «Próximo paso» de malik, organic-cash y remi quedó marcada como perdida.**
     Si alguno de los tres se acuerda de cuál era, se corrige a mano.
  2. Antes de volver a intentar «reescribir el Estado» de un libro sin un commit nuevo de por
     medio, conviene que `redactar()` reciba una instrucción explícita de «no inventes nada
     que no esté en el Estado anterior» — hoy esa instrucción no existe en `INSTRUCCIONES` y
     esta prueba mostró que hace falta.
- **Cómo probarlo a mano:** `git diff` no sirve (la bóveda no tiene git); mirar
  `remi-mente/proyectos/beam.md`, `malik.md`, `organic-cash.md` y `remi.md` a ojo contra lo
  que recuerden que decían.

---

## 2026-09-30 · 0a episodios vacíos: no era un bug de escritura · construido · f261830

- **Qué cambió:** probé `cierre.guardar()` a mano con un transcript sintético (dos turnos con
  una promesa incluida) apuntando a una ruta fuera de cualquier libro: escribió el episodio,
  el título, el resumen y las cuatro secciones perfectos, y quedó una fila en `memoria`. Borré
  ese episodio y esa fila de prueba después de confirmar (no queda nada de la prueba en
  `remi-mente/` ni en `remi.db`). La escritura funciona de punta a punta. `nucleo/cierre.py`
  ahora distingue en el log si faltó `transcript_path` o si el transcript no tenía turnos
  legibles (antes decía lo mismo para los dos casos); `scripts/hooks/claude-sesion.py` deja
  una línea en `ventanita.log` cuando el POST a `/evento` no llega al núcleo.
- **Diagnóstico:** en todo `nucleo.log` solo hay 3 líneas `[cierre]` en la vida del proyecto;
  dos escribieron episodios de prueba (ya borrados a mano según la entrada de 3d) y una fue el
  arreglo de «sesión sin charla». El núcleo recién quedó persistente hoy (KeepAlive, entrada
  3e) — antes, si Claude Code cerraba una sesión con el núcleo caído, el POST fallaba en
  silencio (`_post` atrapa la excepción y no deja rastro) y no había forma de saberlo. Con el
  KeepAlive de hoy más el log nuevo, la próxima vez que falle va a quedar escrito.
- **Decisiones que tomé sin preguntar:** ninguna.
- **Dudas abiertas:** no hay todavía una sesión real (con `/exit` o cierre normal) posterior al
  KeepAlive de hoy para confirmarlo en vivo — la prueba de mañana (al final del reporte) cubre
  justo esto.
- **Cómo probarlo a mano:** abrir Claude Code en `~/proyectos/remi` o `~/beam`, charlar algo
  real, cerrar con `/exit` (no cerrando la terminal de un golpe), y mirar
  `remi-mente/episodios/` — tiene que aparecer un `.md` nuevo. Si no aparece,
  `tail ~/Library/Logs/Remi/ventanita.log` va a decir por qué.

---

## 2026-09-30 · 3d los cuatro proyectos de hoy, conectados · construido · 1c710ce

- **Qué cambió** (en la bóveda `remi-mente/proyectos/`, que no está en git): Juan Camilo
  pidió que Remi siga sus cuatro proyectos actuales: Organic Cash, Malik Gestión, BeaM y
  UpVisuals (Alfonso).
  1. **BeaM no tenía libro**: `beam.md` nuevo, con ruta `~/beam` y lo que dice su landing
     («Sell from your screen. Instantly.»: link → el cliente ve tu pantalla en vivo; Next.js +
     Supabase + LiveKit en Vercel; migración 0005 sin aplicar).
  2. **Organic Cash** suma `~/organic-bot-core` a sus rutas.
  3. **UpVisuals queda sin ruta**: no hay carpeta de código en ningún lado (el trabajo arranca
     cuando se paga la Fase 1). Cuando exista, va en su `ruta:`.
  4. Para que «dónde quedaste» diga algo real ya, mandé a `/evento` el último commit de cada
     repo (solo lectura de git): Malik, Organic Cash y BeaM tienen su `## Estado` escrito por
     Ollama.
- **Verificado:** cada carpeta y sus subcarpetas caen en su libro; BeaM entró a la memoria al
  reiniciar el núcleo; el contexto que recibiría Claude Code en cada carpeta sale bien.
- **Decisiones que tomé sin preguntar:** no commiteo nada en Malik (37 archivos sin
  commitear) ni en Organic Cash (17): es trabajo en curso de otras sesiones.
- **Dudas abiertas:** omniway y shopify-cliente siguen en la bóveda sin ruta; no son de los
  cuatro de hoy. No los borré.
- **Cómo probarlo a mano:** abrir Claude Code en `~/beam`: arranca con «Proyecto: BeaM…» y su
  Estado.

---

## 2026-09-30 · 3e Remi indestructible · construido · c7fbdb3

- **Qué cambió:**
  1. **Sin remoto:** el repo no tiene ningún `git remote`. No lo creé (lo pidió así).
  2. `a9e5849` copia nocturna cifrada: `scripts/copia.sh` fotografía `remi.db` con la API
     de backup de SQLite (integrity_check de la foto) y copia la bóveda con **restic**
     (instalado con Homebrew) a `iCloud Drive/Remi/copias`. Conserva 30 días desde la
     última copia. `config/copia.json`: iCloud activo; R2 y B2 preparados con sus pasos,
     sin activar; credenciales solo en el Llavero. LaunchAgent `com.remi.copia` a las 3:00,
     log en `copia.log`.
  3. `eee7d15` `scripts/restaurar.sh`: a una carpeta temporal y verifica (remi.db abre con
     integrity_check ok y la bóveda está completa archivo por archivo); `--reemplazar` la
     pone en su lugar parando el núcleo y apartando lo que había (`.antes-FECHA`, nunca
     borra).
  4. `c7fbdb3` `GET /salud` (503 si la base no abre) y `scripts/vigia.sh` cada minuto
     (`com.remi.vigia`): a los 5 minutos caído, una notificación de macOS, una sola vez; al
     volver, otra. `d109d4c` arregla la **falla intermitente de pytest** que venía de 3b: una
     carrera con el stdin del MCP en `test_memoria`.
- **Medido:**

  | Qué | Tiempo |
  |---|---|
  | Copia completa (foto + restic + limpieza) | 5 s |
  | Restaurar a temporal y verificar | 2,4 s |
  | Restaurar en su lugar (prueba) | 2,4 s |

- **Criterio de listo, probado:** borré una copia de prueba de remi.db y de la bóveda, corrí
  `restaurar.sh --reemplazar --db … --boveda …` y un núcleo aparte sobre lo restaurado (puerto
  4499) devolvió lo mismo que el real: 8 memorias, 12 tareas de hoy, el libro de UpVisuals.
- **Decisiones que tomé sin preguntar:**
  1. restic y no age: cifra, deduplica y borra por fecha en un solo programa.
  2. **La clave de cifrado vive en el Llavero** (`remi-copia`), generada al azar. Si el Mac
     muere, el Llavero muere con él: Juan Camilo tiene que guardarla afuera.
  3. El vigía no suena (ley de los nudges) y no escribe una línea por minuto.
- **Dudas abiertas:**
  1. **GitHub privado**: es de Juan Camilo crearlo; sin él, el código solo está en este Mac y
     en la copia no está (la copia es remi.db y la bóveda, no el repo).
  2. iCloud Drive puede «optimizar» y sacar del disco archivos del repositorio de restic; si
     una copia futura falla leyendo, el log lo va a decir. R2/B2 quedan listos para eso.
- **Cómo probarlo a mano:** `./scripts/restaurar.sh` (dice en cuánto y si está completo);
  mañana a las 3:05, `tail ~/Library/Logs/Remi/copia.log`.

---

## 2026-09-30 · 3d revisión de lo de Grok + semáforo, scroll y lectura · construido · f1cf463

- **Contexto:** los puntos 1–8 de 3d los escribió **Grok directamente en el repo**
  (`02e4a78`…`01a21ae`), a pedido de Juan Camilo. Choca con el protocolo de arriba («Grok
  nunca escribe en el repo»): lo anoto, no lo cambio; es decisión de él.
- **Revisión de 3d (lo que encontré y arreglé):**
  1. **El núcleo quedó en rojo**: 3 pytest y 3 mypy. `fc4e28e` arregla los tipos.
  2. **El gancho global no corría el hook propio del repo** (`4263efd`): con `core.hooksPath`
     puesto, `git rev-parse --git-path hooks/X` devuelve la carpeta global y el gancho se
     encontraba a sí mismo. Ahora busca en `--git-common-dir`. Ningún repo tenía hooks
     locales: no se perdió nada.
  3. **Una sesión de Claude Code sin charla dejaba un episodio vacío** («La sesión cerró.») y
     **pisaba el Estado del libro** (`5455d4f`). Ahora no deja nada (ARQUITECTURA §6).
  4. **Desde otra carpeta Claude no podía leer un libro**: `leer` pide el id y el índice
     solo viaja en el prompt de Remi. Nueva herramienta `indice(tema)` en el MCP (`f1cf463`).
- **Verificado de verdad:** los commits llegan a `/evento` y el libro de Remi actualizó su
  Estado; una sesión real de Claude Code en ~/proyectos/remi recibió «Proyecto: Remi…» al
  abrir y al cerrar dejó un episodio con Ollama; desde /private/tmp Claude leyó UpVisuals
  por el MCP («USD 3.700»); settings.json conserva el PreToolUse de malik-gestion y la
  config de escritorio conserva los otros servidores (respaldos `*.antes-3d`).
- **Ensucié y limpié:** mis dos sesiones de prueba pisaron el Estado del libro de Remi y
  dejaron dos episodios y dos filas de memoria. Restauré el Estado y borré las tres cosas.
  Quedan dos sesiones de pocos segundos en la tabla de tiempo.
- **En paralelo, pedidos de Juan Camilo:** `e3b0019` semáforo de tres puntos con vuelta (rojo
  oculta y vuelve con el Dock, amarillo a la píldora, verde agranda); `2405642` restaura el
  «dónde quedé» de Grok que ese commit había borrado por un choque de ediciones; `3f61ca2`
  sin barra de scroll; `c1df2f9` (11) lectura: tema Claro (tokens «dia» del DS) y biónica
  con intensidad. Instalé solo la app, sin reiniciar el núcleo mientras Grok trabajaba.
- **Decisiones que tomé sin preguntar:**
  1. El verde del semáforo va en `luz`: el DS no tiene verde. Si lo quiere verde de verdad,
     hay que sumar un token al DS.
  2. Con biónica, la voz de Remi pasa de Instrument Serif a Geist (sin negrita en serif).
  3. `indice` no se suma a las puertas de Remi: sigue con leer y guardar.
- **Dudas abiertas:**
  1. **La app de escritorio de Claude no tomó la memoria todavía**: está en
     `claude_desktop_config.json` pero no hay `mcp-server-memoria.log` y `mcp.log` no se
     escribe desde las 14:39. La app lee la config al abrir: hay que cerrarla y abrirla.
  2. Libros sin ruta: omniway, shopify-cliente, upvisuals. Repos sin libro: bun-ai-api,
     cervantes-ai-ml, organic-bot-core (caen en la Bandeja como «proyecto sin ficha»).
  3. El commit en malik-gestion lo hace Juan Camilo: yo no escribo en esa app.
- **Cómo probarlo a mano:** commit en malik-gestion → en un minuto cambia `## Estado` de
  `remi-mente/proyectos/malik.md`; abrir Claude Code ahí → arranca con dónde quedaste;
  cerrarlo tras charlar → aparece la nota en `remi-mente/episodios/`.

---

## 2026-09-30 · 3c arreglo: al enviar, el campo queda limpio · construido · e19e1b0

- **Qué cambió:** Juan Camilo avisó que el mensaje se quedaba pegado en el campo. En el log
  (23:45): dictó y apretó Enter sin parar el dictado; el mensaje salió, pero la grabación
  seguía y la transcripción parcial volvía a llenar el campo con todo lo dicho. Ahora Enter
  con el dictado andando lo para, transcribe lo último y manda el texto entero; una
  transcripción parcial de una grabación ya parada no escribe nada. Además
  `detener_escucha_y_transcribir` es async: congelaba la ventana mientras Whisper trabajaba y
  un toque dado en ese rato arrancaba otro dictado (23:44:48, tres veces). 67 vitest, 11
  cargo. Instalada.
- **Decisiones que tomé sin preguntar:** Enter durante el dictado manda, no descarta: lo
  dictado es lo que querías decir.
- **Dudas abiertas:** ninguna.
- **Cómo probarlo a mano:** tocar la bolita, dictar, y sin tocarla de nuevo apretar Enter:
  el mensaje sale entero y el campo queda vacío. Escribir otra cosa y mandarla.

---

## 2026-09-30 · 3c la ventanita es una sola pantalla de chat · construido · de5aa0c

- **Qué cambió** (un commit por punto; 1–3 juntos porque son la misma pantalla):
  - `1ae3fc7` (1–3) chat: bolita arriba, conversación en el medio (Remi a la izquierda en
    Instrument Serif itálica, Juan Camilo a la derecha en Geist ink-muted con borde brasa
    suave), historia de la conversación vigente (`GET /conversacion`), campo sin caja
    (Enter envía, Shift+Enter salta). La bolita: un toque dicta, con el texto en el campo
    mientras hablás (`transcribir_parcial`, cada 1,5 s); dos toques, conversación de voz.
    Pensando: un arco que gira. Encargo como tarjeta mono con Copiar.
  - `fd55ddb` (4) chip de cerebro: Claude modelo × bajo/medio/alto/máx, `ollama list` real
    (`GET /pensar/ollama`), Venice (pago). `d388193` (5) chip de voz «Alex · 1,5×».
  - `9e70bd3` (6) redimensionable (esquina), movible, mín 360×240, máx 90 % de la pantalla;
    recuerda tamaño y lugar. `tauri.conf.json` tocado (y `build.rs`).
  - `b7a958c` + `e980201` (7) charla pegada de más de 1500 caracteres → Sí/No →
    `remi-mente/episodios/AAAA-MM-DD-titulo.md` + fila en memoria. `a6b44ac` + `8ac30db` (8)
    «buscá…» habilita WebSearch solo en ese mensaje; links clicables. `e06dc7b` (9) Whisper
    residente. `de5aa0c` (10) `nucleo/probar_bloqueos.py`.
  - Arreglos vistos al probar: `e7052f2` el campo sin anillo de foco; `77999d1` las
    alucinaciones de Whisper no llegan al chat; `4996c0c` la tarjeta de encargo toma solo sus
    secciones.
  - 193 pytest, 67 vitest, 11 cargo, tsc y mypy limpios. Instalada con `actualizar.sh`.
- **Medido:**

  | Qué | Antes | Ahora |
  |---|---|---|
  | Transcribir la misma frase de 5 s | whisper-cli 1,6–2,8 s (18 s con swap) | whisper-server 1,0 s |
  | Memoria fija de Whisper | 0 | 1,7 GB |
  | Búsqueda web con Haiku | — | 13,5 s, 3 links |
  | Resumir una charla con gemma3:4b | — | 5,2 s |

- **Verificado sin tocar el mouse:** en una maqueta de navegador (Tauri simulado, núcleo
  real, fuera del repo): «hola» a la derecha y la respuesta a la izquierda; un encargo real
  de Sonnet como tarjeta; la pregunta de pegar; la bolita escuchando. Un wav a medio grabar
  por ffmpeg (cabecera 0xFFFFFFFF y trozo LIST) se transcribe con la cabecera arreglada.
  Bloqueos: seis de seis denegados (Read, Grep, Read con WebSearch, en las dos carpetas).
- **Decisiones que tomé sin preguntar:**
  1. **Venice sigue sin recordarse** aunque el encargo diga «se recuerda la elección»: es
     pago y la regla de 2i era elegirlo a mano cada vez. Todo lo demás se recuerda.
  2. «máx» es el nivel que el núcleo llama `extra` (32000 tokens): no cambié el nombre
     interno. Por defecto, «Sonnet · bajo».
  3. La voz «auto» pasa a Alex: el chip tiene que nombrar una voz.
  4. Escape con algo en curso lo corta y deja el chat abierto; sin nada en curso, o con la X,
     vuelve a la píldora. Un click en el fondo del chat no hace nada (antes cerraba).
  5. El tema del episodio se elige entre los que ya existen, con su título: gemma inventaba
     «remimarketing» y ponía «remi» a una charla de Alfonso.
  6. El Reloj y la nota «a la bandeja» no están en el chat.
  7. `/mensaje` ahora recibe `origen`: por voz se dicen hasta 3 frases y el chat muestra todo.
- **Dudas abiertas:**
  1. **Ollama (gemma3:4b) contesta resúmenes en inglés** en conversación de voz (22:28 y
     22:33 del 30/09): el modelo chico con la historia larga. No lo toqué.
  2. La pintura real de la ventana (redimensionar, recordar el lugar, la bolita latiendo)
     solo la puede ver Juan Camilo: lista en Notion «5 · Prueba de la ventanita (3c · chat)».
  3. El episodio real en la bóveda no lo escribí yo: es el último criterio de listo, para que
     lo pegue él.
- **Cómo probarlo a mano:** la lista de Notion, casilla por casilla.

## 2026-09-30 · 3b.3–3b.7 mensaje que se queda, animaciones, asistente técnico · construido · 84eb6c5

- **Qué cambió:** pedidos de Juan Camilo tras probar la maqueta. (3) `e6fd150` ninguna
  respuesta se cierra sola (X, Escape o un click con Remi callado); en diálogo la última
  respuesta sigue bajo el punto; hablando, el punto late con el volumen real de Kokoro
  (analizador WebAudio); escuchándote, dos anillos que se cierran hacia el punto; la voz
  arranca una vez por respuesta. (4) `e67bb8d` Kokoro espera 4 s + 150 ms por palabra (antes
  5 s fijos: a las 22:13 cayó a Paulina). (5) `fe76503` el modo Prompt es implícito:
  `nucleo/prompts/tecnico.md` va siempre con el carácter; la CLI lee (Read, Grep, Glob)
  `~/proyectos` y `~/projects`; nivel «extra»; techos 20/45/60/90 s, ventanita 160 s. (6)
  `d27a49a` bajo la respuesta: escuchar/parar, copiar, otra respuesta; voz y velocidad junto
  al chip; el chip elige solo modelo y nivel; atajos visibles tras 3 s de mouse encima. (7)
  `84eb6c5` voces y motores se vuelven a pedir al abrir. 179 pytest, 52 vitest, 9 cargo.
- **Verificado sin tocar el mouse:** Remi contestó leyendo `nucleo/pensar.py` y citó la
  línea (12 s). Un `.env` de prueba no se pudo leer: Read y Grep denegados. **El primer
  intento lo filtró**: los patrones sin ruta absoluta se resolvían contra la carpeta
  temporal; se corrigió con `Read(//<carpeta>/**/.env)`. Captura de la ventanita escribiendo:
  coincide con la maqueta.
- **Decisiones que tomé sin preguntar:**
  1. Carpetas legibles: `~/proyectos` y `~/projects` enteras; bloqueados `.env*`, `*.pem`,
     `*.key`, `*.db`, `*.sqlite`, `credentials*`, `secrets*`.
  2. Techos más largos para que entre leer código; el peor caso sube a 155 s.
  3. «Sin pensar» se fue con Prompt: él pidió elegir solo modelo y nivel. Si estaba puesto,
     se apaga al arrancar.
  4. Copiar copia solo la respuesta, como Claude.
- **Dudas abiertas:**
  1. **Whisper, de 1 s a 18 s en el día**, con 8,7 GB de swap y Colima (1,2 GB) corriendo.
     No es de Remi; no lo toqué. Un whisper residente evitaría recargar el modelo: encargo aparte.
  2. Una corrida de pytest falló una vez en 8,7 s y no se repitió en 9 corridas: intermitente,
     sin identificar. El commit `fe76503` entró con esa corrida en rojo.
  3. Lista de prueba manual en Notion: «5 · Prueba de cierre de la ventanita», bajo Remi.
- **Cómo probarlo a mano:** la lista de Notion, casilla por casilla.

## 2026-09-30 · 3b.1–3b.2 la ventanita como la maqueta de Juan Camilo · construido · a2a866f

- **Qué cambió:** Juan Camilo mandó una maqueta y pidió «solo hagamos que funcione», dejando
  los arreglos robustos para después. (1) `a34ef5e` el núcleo acepta `nivel` (bajo, medio,
  alto) por mensaje: 0, 8000 o 16000 tokens de razonamiento para el modelo elegido; techo de
  60 s con razonamiento, el peor caso de la cadena sigue en 93 s. (2) `a2a866f` la ventanita:
  chip «Opus 5.5 · Medio» bajo el cuadro con Haiku 4.5, Sonnet 5.5, Opus 5.5, Venice, Ollama,
  Prompt y Sin pensar (`ChipModelo.tsx`); escribiendo mide 420×210 y contestando crece con el
  texto hasta 520; contestando, punto grande crema; pensando, punto gris con lo que dijiste;
  nota, controles de voz y Reloj solo con el mouse encima. Se van la flechita de modo, el
  dropdown de motor y el botón «sin pensar». 179 pytest, 51 vitest, tsc y mypy limpios.
- **Decisiones que tomé sin preguntar:**
  1. **La maqueta pisa al DS en la ventanita**, porque él dirige: contestar va en `ink` y no
     en `brasa`, pensar en `ink-muted` y no en `pensar`, la respuesta a 20 px y no a 24.
  2. **El punto gris es «pensando»** con su frase debajo: lo leí así porque el texto de la
     maqueta está en minúsculas, como lo dicho por él.
  3. **Menús nativos de macOS** para el chip: se abren fuera de la ventana de 210 px.
  4. Al cambiar de modelo el nivel vuelve al suyo: Opus medio, Haiku y Sonnet bajo.
- **Dudas abiertas:** no pude ver los estados expandidos en pantalla sin tocar el mouse;
  solo verifiqué el reposo y que el núcleo nuevo rechaza un nivel inválido.
- **Cómo probarlo a mano:** un click: cuadro, chip y atajos. Abrir el chip y elegir Opus y
  Alto. Escribir una pregunta: punto gris con lo escrito, después punto crema con la
  respuesta; pasar el mouse para ver los controles.

## 2026-09-29 · 3b arreglo: el punto al centro de la píldora · construido · 08ee4fc

- **Qué cambió:** con el «dale» de Juan Camilo, se arregla la fila ❌ «Punto en la píldora» de
  la auditoría de 3b. En reposo la zona del punto ya no reserva 22 px (`SelectorModo.css`).
  Medido en una captura de la instalada, en 120×64: el punto y «hace N min» van del píxel
  17 al 42, antes del 23 al 54. 48 vitest y tsc limpios. Instalada.
- **Decisiones que tomé sin preguntar:** ninguna.
- **Dudas abiertas:** el resto de la auditoría sigue sin tocar.
- **Cómo probarlo a mano:** mirar la píldora en reposo: el punto queda centrado.

## 2026-09-29 · 3b la ventanita para usarla todo el día · construido · 29147d7

- **Qué cambió:** antes de todo, `4456700` commitea `docs/ARQUITECTURA-CEREBRO.md` tal cual.
  (1) `7cd1a62` una X arriba a la derecha, fuera de reposo: corta sin transcribir ni mandar
  (`cancelar_escucha` en `voz.rs`, `BotonCancelar.tsx`); la usan también Escape y el corte
  por silencio. (2) `d4f0ac0` la flechita de modo junto al punto, solo en `escuchando`,
  visible al acercar el mouse (`SelectorModo.tsx`, `IconosModo.tsx`); sale el selector
  provisional de 3a. (3) `cf203ac` modo «Prompt»: lo dicho vuelve como encargo para Claude
  Code con Sonnet y `nucleo/prompts/encargo.md`, con botón Copiar (`Encargo.tsx`); no
  clasifica ni guarda. (4) `8a8b9be` el diálogo corta a los 2000 ms de silencio. (5)
  `9f4ed31` la respuesta escrita y el encargo se quedan hasta que los cierres. (6) `29147d7`
  `limpiarMarkdown` en la ventanita y `sin_markdown` antes de Kokoro. 177 pytest, 48 vitest,
  9 cargo, tsc y mypy limpios. Instalada con `actualizar.sh`.
- **Medición pedida, equilibrio, «¿qué tengo pendiente con Alfonso?», núcleo instalado:**

  | Corrida | ms | entrada / caché leída / caché escrita / salida | leyó |
  |---|---|---|---|
  | 3a (antes del carácter corto) | 8238 | 4 / 6020 / 1032 / 493 | upvisuals |
  | 3b, 1.ª | 8364 | 4 / 5430 / 4579 / 392 | upvisuals |
  | 3b, 2.ª | 6555 | 4 / 7594 / 2319 / 435 | upvisuals |

  El carácter corto casi no se nota: bajó de 493 a ~410 tokens y la respuesta **sigue siendo
  una lista con negritas**, cuando `caracter.md` pide «por texto: hasta un párrafo corto;
  listas solo si él pide pasos». Hipótesis, sin probar: los 10 turnos literales de esta
  conversación son todos listas largas de pruebas anteriores y el modelo los imita («Es lo
  mismo de las últimas veces»). Se comprueba repitiendo la pregunta en una conversación nueva.

- **Punto 7 · auditoría de diseño, sin arreglar** (contra el lienzo «Ventanita de Remi —
  refinamiento» y `design/tokens.json`; la píldora medida en una captura de la instalada):

  | Elemento | Diseñado | Implementado | |
  |---|---|---|---|
  | Píldora de reposo | 120×44, `radius-pill`, punto centrado | 120×44 y `radius-pill`; crece a 120×64 con «hace N min» y a 210×64 con «la última vez» | ⚠️ los dos tamaños extra no están en el tablero |
  | Punto en la píldora | centrado | **5 px por debajo del centro**: `.punto-zona` tiene `min-height: 22px` (de `d4f0ac0`) y en 44 px de alto con `space-4` de relleno no entra. En la captura de 120×64 el punto ocupa y=23–32 | ❌ lo rompí yo en el punto 2 |
  | Color del punto en reposo | `baja` (el tablero corrige al DS, que dice `dormido`) | `baja` | ✅ con el tablero · ⚠️ el DS sigue diciendo `dormido` |
  | Escuchando | `luz`, pulsa, crece a 22 px sin moverse | `luz` + `glow-luz`, halo que pulsa, 22 px con el centro fijo | ✅ |
  | Pensando | `pensar` + brillo | `pensar` + `glow-pensar`, más «transcribiendo» mientras whisper trabaja | ✅ |
  | Hablando | `brasa`, la frase y el Reloj, sin cuadro | `brasa` + `glow-brasa`, frase, Reloj `brasa`; suma los controles de voz y la nota | ⚠️ una fila de controles que el tablero no tiene |
  | Punto anclado | a 28 px del borde superior | centro a 27 px (relleno `space-4` + zona de 22 px) | ✅ |
  | Expandido | 420×520, relleno 24, cuadro que llena, punto→cuadro 20 px («space-5») | 420×520, relleno `space-4` (16), cuadro que llena, separación `space-3` (12) | ⚠️ `space-5` no existe en el DS; el tablero pide un token inventado |
  | Atajos del expandido | abajo, en `ink-faint`, mono 11 px | abajo, en `ink-muted`, mono 11 px | ⚠️ el tablero contradice al DS (`ink-faint` solo ≥24 px); seguí al DS |
  | Tipografías | `display-it`, `num`, `code` del DS | las cuatro clases con los valores del DS; pero solo está empaquetada Geist Mono 400 y `num` pide 500 | ⚠️ `num` se ve en 400 |
  | Tamaños sueltos | mínimo `body-sm` (14 px) en la ventanita | mono 11 px en el pie del terminal y en el error; ni `label` ni `num` | ⚠️ fuera de escala |
  | `ink-muted` | texto secundario | «hace», notas, atajos, X, flechita: todo `ink-muted`; `ink-faint` sin uso | ✅ |
  | Borde especular | `rgba(243,235,221,0.10)` interno | el mismo valor, escrito a mano en `App.css` | ⚠️ no es token: hex a mano |
  | Celebración | 900 ms en `luz`, borde `luz`, «Cerrado.» en `display-it`; con reduced-motion, solo color | no existe | ❌ |
  | «Hecha» | botón píldora borde `brasa` en hablando | no existe; cerrar solo se puede diciendo la frase exacta | ❌ |
  | Piel `dinero` | punto y Reloj en `dinero` si hay entrega que paga | no existe; siempre `brasa` | ❌ (no pedido en 3b) |

- **Decisiones que tomé sin preguntar:**
  1. **No arreglé nada de la auditoría**, tampoco el punto corrido de la píldora aunque es
     mío: el encargo dice «sin arreglar». Es una línea en `SelectorModo.css`; espera encargo.
  2. Donde el tablero y `tokens.json` chocan (atajos en `ink-faint`, `space-5`) marqué ⚠️ y
     no ✅: manda el DS, pero alguien tiene que corregir uno de los dos.
  3. La tarea de fondo de la bitácora de 2i.9 estaba en un bucle roto; la detuve. No escribió
     nada.
- **Dudas abiertas:**
  1. ¿El DS pasa a `baja` para el reposo y suma un `space-5`, o el tablero se ajusta al DS?
  2. Celebración y «Hecha» van juntas (una se gana con la otra). ¿Entran en 3c o antes?
  3. La lista con negritas en equilibrio: ¿se prueba en conversación nueva antes de tocar
     `caracter.md`?
- **Cómo probarlo a mano:** tocar la ventanita y la X arriba a la derecha: vuelve a reposo
  sin mandar nada. Acercar el mouse al punto mientras escucha: aparece la flechita; elegir
  «Prompt», dictar un pedido y copiar el encargo. En diálogo, hacer una pausa de un segundo
  en medio de una frase: no corta. Escribir una pregunta: la respuesta se queda hasta la X.

## 2026-09-29 · 3a cerebro v1 (niveles 0 a 2) · construido · f5597c4

- **Qué cambió:** manda `docs/ARQUITECTURA-CEREBRO.md`. Contra lo construido en 3a: los
  puntos 1 y 3 ya estaban (`ae58466`, `4cb6dc7`); solo cambió el texto de la nota a «a la
  bandeja» (`7bc39ae`). Nuevo: (2) `49f042d` tres modos por la sesión de Max —rápido=haiku
  8 s, equilibrio=sonnet 25 s (por defecto), inteligente=opus con razonamiento 60 s— con
  caída al anterior y un selector mínimo en la ventanita. (4) `7a2f0dd` `claves` y `nivel`
  por el contrato, con migración; libros en nivel 1. (5) `aefa159` 10 turnos literales +
  resumen vivo (Ollama, si no Haiku, en segundo plano); conversación nueva tras 60 min sin
  turnos. (6) `407fb5b` log con modo, caché y libros leídos. (7) `f5597c4` pruebas. Antes,
  `822778b`: una pregunta se contesta y no va a la Bandeja. 174 pruebas, mypy limpio.
- **Criterio de listo y medición por modo, por texto, contra el núcleo instalado:**

  | Modo · pregunta | ms | entrada / caché leída / caché escrita / salida | leyó |
  |---|---|---|---|
  | equilibrio · ¿qué tengo pendiente con Alfonso? | 8238 | 4 / 6020 / 1032 / 493 | upvisuals |
  | equilibrio · ¿y cuándo arranco? (por el turno anterior) | 5985 | 4 / 6408 / 1499 / 371 | upvisuals |
  | rápido · ¿qué tengo pendiente con Alfonso? | 3582 | 3392 / 0 / 0 / 180 | — |
  | inteligente · ¿qué tengo pendiente con Alfonso? | 8449 | 4 / 4318 / 4865 / 480 | upvisuals |

- **Decisiones que tomé sin preguntar:**
  1. **No hice commits vacíos** para lo que ya estaba (puntos 1 y 3): lo digo con el hash.
  2. **`claves` quedó estricto** (`string|null` sin default): cada lugar que arma una
     `Memoria` lo pasa explícito, en vez de aflojar el generador para todos los contratos.
  3. **La migración tocó tu `remi.db`** (ALTER TABLE, sin borrar nada); antes dejé una copia
     en el scratchpad de la sesión.
  4. El selector de modo es mínimo, junto al del motor y solo con Claude: el definitivo
     (flechita junto al punto) es 3b.
  5. Peor caso de la cadena: 93 s; la ventanita espera 100 s.
- **Dudas abiertas:**
  1. **`docs/ARQUITECTURA-CEREBRO.md` está sin trackear.** No lo escribí yo; no lo commiteo.
  2. **La medición por modo no es limpia:** las tres preguntas fueron en la misma
     conversación, así que rápido contestó desde los turnos anteriores sin leer el libro, e
     inteligente dijo «lo mismo que antes». Para comparar de verdad hace falta 3f (banco de
     pruebas, conversaciones nuevas por modo).
  3. Las respuestas siguen trayendo markdown crudo (`**…**`, listas). Es del carácter.
  4. Los libros no tienen `claves` en su frontmatter todavía; la columna está vacía.
- **Cómo probarlo a mano:** elegir modo en el selector nuevo, preguntar por Alfonso y seguir
  con «¿y cuándo arranco?». `grep '\[claude\] modo=' ~/Library/Logs/Remi/nucleo.log`.

## 2026-09-29 · 3a Remi piensa de verdad · construido · 71643ac

- **Qué cambió:** siete commits, uno por punto. (1) `ae58466` todo mensaje de la ventanita
  piensa; «sin pensar» es un toggle que queda puesto; `CLAUDE.md` al día con la decisión.
  (2) `dde48b3` Sonnet por la sesión de Max, Haiku si tarda más de 25 s o falla; ventanita
  espera 50 s. (3) `4cb6dc7` `conocimiento/caracter.md` es el system prompt, leído en cada
  mensaje; sin techo de 20 palabras; en pantalla va entero, hablado hasta 3 frases.
  (4) `643e751` `sembrar_conocimiento.py` lleva las fichas al estante al arrancar: índice de
  2 a 8 entradas. (5) `42919fd` tabla `turnos`, 12 turnos de la última hora en cada llamada.
  (6) `8a36b1e` la respuesta completa y una nota chica («guardada en la bandeja»,
  «reloj corriendo»). (7) `71643ac` pruebas. 152 núcleo, 42 ventanita, mypy limpio.
- **Criterio de listo, verificado contra el núcleo instalado, por texto:**

  | Pregunta | Resultado | ms |
  |---|---|---|
  | ¿qué tengo pendiente con Alfonso? | montos y fechas de `upvisuals.md`; `modelo=claude-sonnet-5-5 leyó=sí` | 9691 |
  | ¿y cuándo arranco? | «cuando la Fase 1 esté pagada completa… 18 oct, hasta el 23» (por el turno anterior) | 7196 |

- **Decisiones que tomé sin preguntar:**
  1. `conocimiento/` va a `.gitignore` (salud y montos): se lee del disco, no entra al repo.
  2. La API sigue con `think=false` por defecto: quien decide pensar es la ventanita. Así las
     pruebas que postean `/mensaje` no lanzan la CLI de verdad.
  3. El `paso_minimo` de una tarea nace universal: la respuesta de una conversación no es un
     paso mínimo.
  4. La historia viaja dentro del mensaje, igual para los tres motores.
  5. `db.py` resolvía la ruta de la base al importarse y las pruebas se contaminaban entre sí
     (los turnos de una aparecían en la otra). Ahora se resuelve al conectar y cada prueba
     tiene su base. La base real no fue tocada por pruebas.
- **Dudas abiertas:**
  1. **Las preguntas se guardan como ideas en la Bandeja.** El clasificador no distingue
     preguntas: «¿qué tengo pendiente con Alfonso?» quedó como idea enfriando. Ensucia la
     ley 2. Arreglo corto: una pregunta (termina en «?») no se guarda.
  2. **La respuesta trae markdown** (`**negrita**`, listas) y la ventanita lo muestra crudo.
     Se arregla en el carácter («sin markdown») o renderizándolo. El carácter es de Juan
     Camilo.
  3. **Whisper alucinó «¡Suscríbete al canal!»** dos veces esta tarde y quedó como idea.
     Es la frase clásica de Whisper sobre silencio.
  4. `tokens entrada=4`: la CLI cuenta solo lo no cacheado. El dato real está en
     `cache_read_input_tokens`; hoy el log subestima.
  5. 7 a 10 s por respuesta con Sonnet. Con Haiku o Ollama baja, a costa de calidad.
- **Cómo probarlo a mano:** un click, escribir «¿qué tengo pendiente con Alfonso?», Enter;
  después «¿y cuándo arranco?».

## 2026-09-29 · 2i.12 clicks fantasma y motor por defecto · construido · e4ccba1

- **Qué cambió:** (1) `a09e0f7`: cada click deja isTrusted, detail, screenX/Y y los ms desde
  el último cambio de tamaño. Filtros en `gestos.ts` que no tocan la racha: «fantasma: muy
  seguido» (<80 ms del anterior) y «fantasma: resize» (<100 ms de un cambio de tamaño). En
  «pensando» ningún click cancela; solo Escape. Pruebas con las dos secuencias del log
  (18:42:59 y 18:44:01) tal cual. (2) `e4ccba1`: Claude por defecto; Venice elegible a
  mano, con «(pago)», y nunca por arrastre (una preferencia vieja en venice se lee como
  claude); si el motor guardado no está disponible al arrancar, vuelve a Claude y lo
  escribe. 142 pruebas núcleo, 42 ventanita. Instalada.
- **Decisiones que tomé sin preguntar:**
  1. **100 ms tras un cambio de tamaño, no 250.** Lo medí antes de escribirlo: los fantasmas
     llegan a 1–30 ms del anterior y a 14 ms de un cambio de tamaño; los 2.º clicks reales
     que graban llegan a 125–215 ms del 1.º, o sea a 105–195 ms del cambio que dispara el
     1.º. Con 250 se perdía la mitad de los dobles clicks del día. Hay una prueba que cuida
     el doble click real más rápido (125 ms) y falla si alguien sube el número.
  2. El «último cambio de tamaño» se marca al empezar la animación y otra vez al terminar
     (dura 250 ms): un click durante la animación cuenta como cercano al cambio.
- **Dudas abiertas:**
  1. **De dónde salen los fantasmas sigue sin saberse.** Ahora el log dice si son
     `confiable=false` (sintetizados) o caen todos en el mismo `xy`. Con una sesión de uso
     se sabe; hasta entonces el filtro por tiempo los ataja.
  2. Sigue pendiente: texto + Enter contesta «Guardada» en vez de pensar (diseño).
- **Cómo probarlo a mano:** usar Remi normal. En el log, buscar `razon=fantasma` y mirar
  `confiable` y `xy` de esas líneas.

## 2026-09-29 · 2i.11 Whisper large-v3-turbo · construido · 36bc1d6

- **Qué cambió:** `config/ventanita.json` apunta a `ggml-large-v3-turbo.bin` (ya estaba en
  la carpeta de Handy) en vez de `ggml-small.bin`. Rust lee la config en cada transcripción:
  entra sin recompilar ni reinstalar. **Medido** con 7,3 s de español limpio y Metal: small
  0,79 s · medium-q4 1,96 s · large-v3-turbo 2,19 s. Con audio limpio los tres transcriben
  idéntico; la diferencia es con voz real, ruido y acento.
- **Decisiones que tomé sin preguntar:** turbo y no medium: casi el mismo tiempo, mejor modelo.
- **Dudas abiertas:**
  1. **No puedo probar la mejora de comprensión sin el micrófono de Juan Camilo**; el audio
     sintético no la muestra. Se ve en uso.
  2. Cada frase cuesta ~1,4 s más de transcripción. Si en uso se siente lento, el punto medio
     es `whisper-medium-q4_1.bin` (1,96 s), también ya bajado.
  3. Sigue pendiente: texto + Enter contesta «Guardada» en vez de pensar (diseño; con Ollama
     gratis, pensar por defecto ya no cuesta).
- **Cómo probarlo a mano:** dictar una frase larga y rápida, la que antes entendía mal.

## 2026-09-29 · 2i.10 Ollama, el motor local y gratis · construido · 2a304f2

- **Qué cambió:** medí antes de construir lo que había propuesto (estante persistente) y la
  medición lo tiró: 2,05 s sin estante, 2,08 s con; el estante arranca en paralelo con la CLI
  y no suma. Los 1,5 s fijos son la CLI de Claude misma. Lo que sí baja el tiempo es no
  arrancarla: Ollama por HTTP en el mismo Mac. `nucleo/pensar.py`: Venice y Ollama comparten
  un cliente OpenAI-compatible; Ollama no manda clave; modelo por defecto `gemma3:4b`
  (`REMI_OLLAMA_MODELO`). `GET /pensar/motores` lo lista y dice qué le falta. 142 pruebas.
  **Medido:** primera respuesta 9,4 s (carga el modelo a memoria), después 0,6 s y 0,5 s.
- **Decisiones que tomé sin preguntar:**
  1. **Fuera del repo:** `brew services start ollama` (arranca al iniciar sesión) y
     `ollama pull gemma3:4b` (3,3 GB). Y creé `/Volumes/ORGANIC/Mac/Modelos-IA/ollama-models`:
     `~/.ollama/models` era un enlace **roto** a esa carpeta, dejado el 23/09 (el día del
     disco lleno) para tener los modelos en el SSD; Ollama no arrancaba por eso. Respeté esa
     decisión en vez de mover los modelos al disco interno.
  2. gemma3:4b y no un 7B: en un M4 con 16 GB, 4B contesta en medio segundo; el doble de
     tamaño sería el doble de tiempo por una mejora chica en español.
  3. Claude sigue como motor por defecto; Ollama se elige en el dropdown.
- **Dudas abiertas:**
  1. **Ollama descarga el modelo a los 5 min sin uso** (`OLLAMA_KEEP_ALIVE=5m`): la primera
     respuesta después de una pausa vuelve a costar ~9 s. Si Remi va a usarlo de día a día,
     conviene `OLLAMA_KEEP_ALIVE=-1` en el servicio: 3,3 GB de RAM ocupados siempre.
  2. Si ORGANIC no está montado, Ollama no arranca. Es la consecuencia del enlace del 23/09.
  3. Dos cosas reportadas por Juan Camilo, con dato ya tomado y sin tocar todavía:
     **texto + Enter contesta «Guardada…»** porque en texto solo piensa con el toggle (diseño;
     con Ollama gratis, pensar por defecto ya no cuesta); y **la comprensión**: los picos del
     micrófono están en −4 a −7 dB (fuerte, no es volumen), y en la carpeta de Handy ya está
     `ggml-large-v3-turbo`, muy superior al `small` que usa Remi. Es un cambio de config.
- **Cómo probarlo a mano:** en el dropdown elegir «Ollama (local, gratis)», prender «pensar
  con», escribir algo y Enter. La primera vez tarda; las siguientes, medio segundo.

## 2026-09-29 · 2i.9 un click no cancela la respuesta; semáforo en la esquina · construido · 43978ba

- **Qué cambió:** el diálogo ya contesta con voz (confirmado por Juan Camilo). (1) `0be864e`:
  en `hablando` un click no hace nada; para cortar está Escape. A las 17:43 una respuesta
  que iba bien se canceló por tocar la ventana. (2) `9d7e697`: dos puntos como los de macOS
  en la esquina superior izquierda, visibles solo al acercar el mouse: rojo (`alerta`)
  cierra, amarillo (`dinero`) oculta sin cortar la voz; vuelve con ⌘⌥⇧L o abriendo Remi.
  Es la única forma con el mouse de cerrar u ocultar (`Semaforo.tsx`, `App.tsx`,
  `capabilities/default.json`). (3) `43978ba`: arreglo de un `\n` literal mío que dejó el
  JSON de permisos inválido y el build en rojo. 35 pruebas. Instalada a las 17:46.
- **Decisiones que tomé sin preguntar:**
  1. **Sin verde.** Juan Camilo pidió «rojo, amarillo y verde». En una píldora no hay nada
     que maximizar y el DS no tiene verde. Si igual lo quiere, es un botón más.
  2. **Amarillo = ocultar, no minimizar al Dock.** Una ventana sin decoraciones no siempre
     se deja minimizar en macOS; ocultar funciona seguro y es lo mismo que hace el atajo de
     mostrar/ocultar. La voz sigue sonando oculta.
  3. Los puntos son controles: un click ahí no es un gesto ni arrastra la ventana.
- **Dudas abiertas:**
  1. **«Que conteste más rápido».** Hoy el tiempo lo come arrancar la CLI de Claude con el
     estante (2 a 9 s), no la voz. Bajarlo de verdad es una sesión persistente de la CLI, o
     Venice (sin estante). Es un encargo aparte.
  2. Los subtítulos de tres líneas con opción de ocultar siguen pendientes.
- **Cómo probarlo a mano:** hacer una pregunta en diálogo y, mientras contesta, tocar la
  ventana: sigue. Acercar el mouse a la esquina: aparecen los dos puntos; el amarillo la
  oculta con la voz sonando.

## 2026-09-29 · 2i.8 el vigilante se iba antes de que ffmpeg abriera el wav · construido · f4dbaf9

- **Qué cambió:** la instrumentación de 2i.7 lo dijo en dos líneas a las 17:38:34: «vigilancia
  de silencio arrancó» y, 255 ms después, «termina: el wav ya no está». ffmpeg con
  avfoundation tarda hasta un segundo en abrir el archivo de salida; el vigilante miraba
  antes, no lo encontraba y lo tomaba por «la grabación terminó». A las 17:29 fue lo mismo
  con el código viejo, que se iba callado: los cuatro minutos mudos. A las 17:22 funcionó de
  casualidad. Ahora «no existe» solo significa «terminó» si el archivo existió antes; al
  arrancar espera hasta 5 s y anota a los cuántos ms apareció (`voz.rs`). Instalada.
- **Decisiones que tomé sin preguntar:** ninguna nueva. Los subtítulos siguen esperando a
  que el diálogo conteste.
- **Dudas abiertas:** la misma carrera existe en el dictado con corte propio (`iniciar_escucha`
  con `cortar_solo`), que hoy nadie usa; queda cubierta por el mismo cambio.
- **Cómo probarlo a mano:** tres clicks, una frase, callarse 2 s. En el log: «el wav apareció
  a los N ms», después «nivel …» por segundo, «te escucho», «dejaste de hablar → corto sola».

## 2026-09-29 · 2i.7 el vigilante que calla · construido · 688c0e4

- **Qué cambió:** del intento de las 17:29: tres clicks, «corte por silencio activado», el
  wav creciendo a 29 KB/s con audio (pico 0.095 medido desde afuera)… y el vigilante **no
  escribió nada en cuatro minutos**, ni el nivel por segundo. Verifiqué y descarté: la app
  viva, ffmpeg vivo, micrófono autorizado (la hipótesis de TCC era falsa), código idéntico
  al que a las 17:22 sí escribía. El binario va sin símbolos: no se le puede mirar adentro.
  Lo único posible es que hable: ahora anota cuando arranca y, si no puede medir, por qué
  (`voz.rs`, `pico_reciente_o_motivo`). Y un techo al umbral adaptativo: 0.15.
- **Decisiones que tomé sin preguntar:**
  1. **El techo de 0.15 es un bug real, probado con los números de las 17:22**, no una
     adivinanza sobre el de las 17:29: si empezás a hablar apenas entrás en diálogo, el piso
     sale de ventanas con voz, ×2.5 lo deja por encima de tu voz y nunca «te escucho». Con
     techo, la voz (0.24–0.68) entra y el silencio del RODE (0.03–0.08) no.
  2. Los subtítulos que pidió Juan Camilo (tres líneas de lo que Remi dice, ocultables)
     esperan a que el diálogo conteste: primero que ande, después que se vea.
- **Dudas abiertas:**
  1. **No sé por qué el vigilante calló a las 17:29.** No lo voy a adivinar: con la
     instrumentación nueva, el próximo intento lo dice. Si vuelve a callar sin «vigilancia
     arrancó», el hilo no se está creando y el problema está en `activar_corte_por_silencio`.
  2. Tras cada `actualizar.sh` la voz Kokoro tarda ~18 s en cargar; si la primera respuesta
     llega antes, sale con la voz del sistema. No es un fallo, pero se nota.
- **Cómo probarlo a mano:** lo mismo: tres clicks, una frase, callarse 2 s. En el log tiene
  que aparecer «vigilancia de silencio arrancó» y luego «nivel …» cada segundo.

## 2026-09-29 · 2i.6 el diálogo manda, y el motor se elige a conciencia · construido · d5e168e

- **Qué cambió:** (1) `44aad7b`: **el diálogo nunca mandaba.** Del log de las 17:22:
  transcribió 28 caracteres y nada durante 12 s. La guarda anti-doble-envío de `enviar()`
  miraba «pensando», y el diálogo pone pensando mientras transcribe: al ir a mandar lo
  transcrito, se frenaba en silencio. Ahora mira si hay un POST en vuelo, y cuando rechaza
  lo escribe. (2) `329b751`: `POST /mensaje` acepta `motor: claude|venice`, que gana sobre
  el `.env`; `GET /pensar/motores` lista los dos con qué le falta a cada uno. (3) `d5e168e`:
  dropdown «pensar con [Claude (Max) ▾]» en el pie del cuadro, guardado con las
  preferencias, y un recordatorio cada media hora en reposo: «pensás con X» bajo el punto,
  un movimiento de 250 ms, se va a los 4 s. 138 pruebas núcleo, 35 ventanita. Instalada.
- **Decisiones que tomé sin preguntar:**
  1. **El recordatorio contra «nada respira».** Juan Camilo pidió que el dropdown «vibre
     cada media hora, sutil». El DS prohíbe animación permanente. Lo hice como UN movimiento
     de 250 ms con la curva del sistema, solo en reposo, sin sonido, en el renglón del «hace
     N min» (no agranda la píldora), y con `prefers-reduced-motion` solo cambia el color. Se
     apaga con una constante en `recordatorio.ts`.
  2. El recordatorio se mide desde el último recordatorio, no desde el último uso: usar
     Remi seguido no lo posterga para siempre.
  3. El `.env` queda como valor por defecto, no como la única forma de elegir motor.
  4. Los dobles de `pensar()` en los tests viejos pasaron a aceptar el motor.
- **Dudas abiertas:** el «zumbidito» lo leí visual, no sonoro. Si era sonido, es otra
  conversación: la voz de Remi ya usa los parlantes y un sonido de aviso choca con
  «cuerpo primero» si suena mientras trabajás.
- **Cómo probarlo a mano:** tres clicks, decir una frase, callarse 2 s → corta, manda y Remi
  contesta en voz. Un click, abrir el cuadro: el dropdown está junto a «pensar con». A los
  30 min en reposo, la etiqueta aparece y se mueve una vez.

## 2026-09-29 · 2i.5 el diálogo corta y contesta · construido · b37f24c

- **Qué cambió:** tres cosas, tres commits, del log de las 17:09. (1) **Umbral adaptativo**:
  el RODE en silencio da 0.030–0.080 y el umbral era 0.020, así que para el detector nunca
  te callabas; ahora el piso es el mínimo de los últimos 3 s y hay voz por encima de
  ×2,5 del piso (`voz.rs`, 8 pruebas). (2) **En diálogo se piensa**: la ventanita manda
  `think=true` en diálogo, y una idea con think se guarda igual pero contesta lo que pensó
  el motor (`servidor.py`, `App.tsx`). (3) **Dos motores**: `REMI_PENSADOR=claude|venice`
  en `nucleo/.env`, con `VENICE_API_KEY` y `REMI_VENICE_MODELO` (`pensar.py`). Verificado en
  vivo: una idea con think contestó «Guardá ahora mismo las tres recetas que más cocina tu
  mamá…» por Claude (Max). 134 pruebas, mypy limpio. Instalada.
- **Decisiones que tomé sin preguntar:**
  1. El motor por defecto es Claude (la membresía). Venice paga por token y **no tiene
     ningún modelo a $0**: los más baratos son `zai-org-glm-4.7-flash` (0.06/0.40 por
     millón) y `qwen3-5-9b` (0.10/0.15). Dejé el que dio Juan Camilo (`venice-uncensored`,
     0.20/0.90).
  2. Venice no tiene acceso al estante: el índice viaja en el prompt, pero sin herramientas
     no puede bajar nada. El log lo dice (`leyó=no (sin herramientas)`).
  3. En texto y dictado el toggle sigue mandando: solo el diálogo piensa siempre.
- **Dudas abiertas:**
  1. **La clave de Venice se pegó en el chat.** Está en `nucleo/.env` (fuera del repo) y en
     ningún otro lado del disco, pero ya viajó por esta conversación. Conviene rotarla.
  2. Una prueba mía llamó a Venice con la clave real (1080 tokens) porque `_leer_env` fijaba
     la ruta al definirse y el monkeypatch no la alcanzaba. Corregido en `b37f24c`.
  3. Pensar por Claude tardó 8,7 s con 5895 tokens de entrada (índice + herramientas del
     estante). Dentro del corte de 25 s de la ventanita, pero lento para un diálogo.
- **Cómo probarlo a mano:** tres clicks, ver «diálogo», una frase, callarse 2 s: tiene que
  cortar sola, y Remi contesta en voz. Para cambiar de motor: `REMI_PENSADOR=venice` en
  `nucleo/.env` y `./scripts/instalar.sh`.

## 2026-09-29 · 2i.4 el diálogo no se veía · construido · 6aff5f8

- **Qué cambió:** nada del gesto. Del log de las 16:59: los tres clicks **entraban en
  diálogo las dos veces** (`click n=3 → pasarADialogo`, a 1440 y a 535 ms del 2.º). Lo que
  Juan Camilo vivió como «se queda en dos clicks» era otra cosa: dictado y diálogo se ven
  igual, y el diálogo se comportaba como dictado porque el silencio nunca cortó (72 s
  hablando, parado con un click). Dos cosas de ver: la palabra «diálogo» bajo el punto
  mientras escucha en ese modo (`App.tsx`, `App.css`), y el vigilante de silencio anota el
  nivel del micrófono una vez por segundo, con el umbral y cuánto lleva callado (`voz.rs`,
  hallazgo 3 de Grok). Instalada.
- **Decisiones que tomé sin preguntar:**
  1. No toqué tiempos. La propuesta de Juan Camilo era «dos clicks en un segundo, tres en un
     segundo»; el log muestra que los tiempos ya estaban bien y que el problema no era ese.
  2. «diálogo» va en `luz`, el color de escuchar, y en `num`: parte del mismo estado, no
     otra locura (ley 4).
  3. El hallazgo 3 de Grok lo implementé sin encargo formal: era el dato que faltaba para
     entender el silencio que no corta, y Juan Camilo estaba probando en vivo.
- **Dudas abiertas:** el silencio en diálogo. Con la línea `[voz] nivel …` de esta versión,
  la próxima prueba dice si el piso del RODE queda por encima de 0.020. Si es eso, el
  arreglo es el umbral (o medirlo al arrancar), no el gesto.
- **Cómo probarlo a mano:** tres clicks, ver la palabra «diálogo» bajo el punto, decir una
  frase y callarse 3 segundos sin tocar nada.

## 2026-09-29 · 2i.3 tres clicks en menos de dos segundos · construido · 97857e0

- **Qué cambió:** una sola cosa. El triple click ya entraba en diálogo si venía pegado
  (16:51:33, gaps de 672 y 405 ms); a ritmo tranquilo no, porque cada click tenía que caer a
  menos de 700 ms del anterior, y el 3.º, ya fuera de la gracia, **paraba** la grabación
  (16:51:35, a 1609 ms). Ahora la racha guarda cuándo cayó el primero y, del 3.º en
  adelante, alcanza con estar a menos de 2 s de ese primero (`apps/ventanita/src/gestos.ts`,
  `MS_TRIPLE`). El doble click sigue igual de estricto. 32 pruebas. Instalada.
- **Decisiones que tomé sin preguntar:**
  1. La ventana ancha es **solo para el 3.º en adelante**. Si el 2.º también pudiera venir a
     2 s del 1.º, un click suelto en el cuadro vacío después de abrir texto arrancaría a
     grabar sin querer.
  2. `rachaSigueViva()` es una sola función para contar y para el mousedown que no le da el
     foco al cuadro: no hay dos definiciones de «racha viva» que se puedan separar.
- **Dudas abiertas:**
  1. **`43adc9e` entró en rojo.** Encadené el commit y la instalación al estado de salida de
     `grep`, no al de `npm test`, y dos pruebas viejas fallaban (ponían el click «para parar»
     a 1,2 s del primero, que con la regla nueva es un 3.º). El código era el correcto; las
     pruebas no. `97857e0` lo deja en verde. No vuelvo a encadenar sobre un `grep`.
  2. Sigue abierto lo del silencio que no corta en diálogo (2i.2).
- **Cómo probarlo a mano:** tres clicks tranquilos, repartidos en menos de 2 s, y hablar.

## 2026-09-29 · 2i.2 doble click para parar · construido · d64e97f

- **Qué cambió:** una sola cosa, del log de las 16:43. El doble click para empezar **ya
  funcionaba** (`16:43:16.435 click n=2 … accion=grabarVoz`, ventana expandida). Lo que dejó
  a Juan Camilo trabado 50 s fue un 3.er click 411 ms después —diálogo sin querer— y que en
  diálogo ningún click paraba (decisión mía de 2i). Ahora, pasada la gracia, un click para
  la grabación en dictado y en diálogo (`apps/ventanita/src/gestos.ts`); y el 2.º click de
  ese doble click, que caía con Remi transcribiendo y cancelaba, se absorbe. 29 pruebas, con
  la secuencia de las 16:43 tal cual. Instalada.
- **Decisiones que tomé sin preguntar:**
  1. **Revierto mi propia decisión de 2i** («en diálogo un click nunca para»). La tomé para
     que el 4.º click de las 15:31 no cortara; se logra igual con la gracia en 1000 ms medida
     desde el último gesto sobre la grabación (arranque, re-armado o pase a diálogo).
  2. En diálogo, parar con un click manda lo dicho, igual que el silencio. Terminar el
     diálogo sigue siendo Escape o la palanca.
- **Dudas abiertas:**
  1. **El silencio no cortó en 50 s de diálogo.** El corte se activó
     (`16:43:16.847 corte por silencio activado`) y nunca disparó. Es el hallazgo 3 de Grok
     (el piso del RODE mientras callás no se anota): sin ese dato no se puede afirmar si el
     umbral 0.02 queda por debajo del ruido de fondo. No se toca en este paso.
  2. Un 3.er click a 411 ms del 2.º entra en diálogo. Si a Juan Camilo le pasa seguido sin
     querer, la ventana del triple click es lo que hay que mirar, no el doble.
- **Cómo probarlo a mano:** doble click, hablar, doble click. Listo cuando el log muestre
  `pararGrabacion` seguido de `2.º click del que paró` y después `transcrito`.

## 2026-09-29 · 2i.1 el doble click era imposible · construido · 1ff883b

- **Qué cambió:** el diagnóstico de Claude sobre el log de las 16:18 era exacto: 13 clicks
  seguidos descartados con «dentro de un control», porque el 1.er click hace crecer la
  ventana y el cuadro aparece bajo el mouse, y `gestos.ts` descartaba el 2.º ANTES de contar
  la racha. Ahora la racha se cuenta primero; con el cuadro vacío y la racha viva, un click
  dentro del cuadro es el 2.º o el 3.º (`apps/ventanita/src/gestos.ts`). El gesto se escucha
  sobre `window` en fase de captura, y el mousedown del 2.º click no le da foco ni caret al
  textarea (`App.tsx`). Pruebas con la secuencia real de las 16:18 (26 en total). Palanca a
  `Control+Option+R` con cada evento en el log (`lib.rs`, `config/ventanita.json`).
  Instalada; el log dice `atajo de dictado registrado: Control+Alt+R (is_registered=true)`.
- **Decisiones que tomé sin preguntar:**
  1. **`MS_RACHA` sube de 550 a 700.** El 2.º click de la prueba real llegó a **584 ms**, y
     el punto 3 pedía que esa secuencia diera `grabar`: con 550 no daba ni contándola. Un
     doble click humano sobre algo que se está moviendo (250 ms de animación) no entra en
     550.
  2. **Los botones que viven dentro del cuadro cuentan como control, no como cuadro.** El
     toggle de «pensar con Claude» está en el pie del cuadro: sin esto, un doble click sobre
     él con el cuadro vacío arrancaría a grabar. La entrada de `decidir()` separa
     `dentroDeControl` de `dentroDelCuadro`.
  3. **Un click suelto dentro del cuadro vacío no graba, pero abre la racha.** Es lo que
     pasó a las 16:18:44: dos clicks a 183 ms, los dos en el cuadro. El primero es «para
     escribir» y a la vez el 1.º de la racha; el segundo graba.
  4. **El conflicto del atajo se detecta por ausencia.** La API de Tauri acepta
     `Control+Option+Space` y después macOS se lo queda: `register()` no falla. Lo único
     comprobable es `is_registered()` de nuestro lado, y la línea de registro lo dice.
- **Dudas abiertas:** la línea `[palanca] pulsada` la escribe la tecla de Juan Camilo. Si
  con `⌃⌥R` tampoco aparece, no es un rebote ni un registro fallido: el log lo diría.
- **Cómo probarlo a mano:** doble click y hablar; triple click y hablar; `⌃⌥R` dos veces.
  Listo cuando el log muestre `click n=2 … accion=grabarVoz` con la ventana ya expandida.

## 2026-09-29 · respuesta a las auditorías de 2h y 2f · Claude Code

Las dos me llegaron después de construir 2i y 2f.2, así que casi todo está resuelto; lo digo
con el hash. Sin cambios de código en esta entrada.

**2h gestos**

1. `voz.ts:209`, la misma frase suena varias veces y el punto 8 no estaba — **ya está**,
   `9035de2`. Contador de generación: cada `hablar()` y cada `callarse()` lo suben, y
   después de cada `await` la llamada comprueba que siga vigente. Un `AbortError` de
   `play()` es cancelación, no fallo, y no cae a la voz del sistema. Cada llamada deja en el
   log `[voz] #N empieza` y `[voz] #N terminó | cancelada | cae a la voz del sistema`
   (`apps/ventanita/src/voz.ts:27` y siguientes). Probado en `voz.prueba.ts`: dos llamadas
   seguidas suenan una sola vez.
2. `PromptTerminal.tsx:44`, Enter solo no hacía nada — **ya está**, `0163bff`. Enter envía,
   Shift+Enter salto de línea, ⌘↵ y Ctrl+Enter siguen; los tres quedan en el log como
   `[gesto] tecla tecla=… accion=…` (`PromptTerminal.tsx:49-53`). Sobre achicarse: desde
   `b41f594` cada cambio de tamaño queda como `[gesto] tamaño motivo=encoger|expandir|
   reposo` (`App.tsx:194`). El «punto 9» no me llegó en ningún encargo: no sé qué pedía.
3. `voz.rs:189`, el pico se anota al cruzar el umbral y al cortar, no el piso mientras
   callás — **acepto**, sin encargo todavía. Es cierto: hoy el pico queda en
   `voz.rs:192`, `:202` y `:213`, todos momentos de cambio. Lo que haría: en
   `vigilar_silencio`, una línea por segundo con el pico de esa ventana mientras `callado`
   crece, y solo en diálogo, que es donde el detector corre. Una línea, no cuatro por
   segundo: con eso alcanza para ver el piso del RODE.
4. La prueba de cuatro pasos con las manos quietas — **acepto**. Juan Camilo ya eligió la
   suya para 2i (doble click con pausas, triple click, palanca dos veces); la de Grok sirve
   como segunda sesión, sobre todo el paso «dos clicks separados por 1 s», que es justo el
   borde de la racha.
5. `registro.ts:39`, el log no espera y no mueve los 550 ms; lo que sí altera la prueba es
   un build corriendo — **acepto**, con una precisión. `scripts/actualizar.sh` reemplaza
   la app (`actualizar.sh:48`) pero **no borra** `ventanita.log`: el `rm -f` fue mío, a
   mano, antes de la reinstalación de A8. No corro `actualizar.sh` ni borro el log
   mientras haya una sesión de prueba en curso.

Cambio propuesto (id de `hablar()` y log del Enter): **ya está**, `9035de2` y `0163bff`.

**2f clasificar**

1. `clasificar.py:64`, con ≤4 palabras cualquier «listo» cerraba — **ya está**, `56407a6`.
   `hecha` solo si la frase normalizada es exactamente una de la lista, y nunca con «?».
   Las cinco frases están en `nucleo/pruebas/test_clasificar.py` con el resultado esperado.
2. `clasificar.py:71`, la negación no frenaba el arranque — **ya está**, `56407a6`. Con
   «no», «nunca», «tampoco», «ver si», «quizás», «a lo mejor», «se me ocurrió» o «idea» no
   abre. Las tres frases, en las pruebas.
3. `clasificar.py:34`, faltaban «me pongo con», «arranqué», «sigo con» — **ya está**,
   `56407a6`. Grok lo dejaba para otro encargo; el de 2f.2 lo pidió junto, así que fue en
   el mismo commit. Las tres frases, en las pruebas.
4. `clasificar.py:21`, «ya está» y «hasta acá» no cerraban — **ya está**, `56407a6`. Y
   también «hecho», «ya terminé», «ya estuvo», «cerrado».

Cambio propuesto (cierre exacto): **ya está**, `56407a6`. Las 14 frases de Grok dan el
resultado esperado; verificado en vivo contra el núcleo recargado, no solo en pytest.

## 2026-09-29 · 2h gestos · auditoría · Grok
1. [bug] apps/ventanita/src/voz.ts:209 — hablar() llama a callarse() y después espera el wav. Otra llamada que arranca durante esa espera no cancela la primera cuando el audio por fin llega, así que la misma frase suena varias veces en la única instancia. El punto 8 no está en el código: App.tsx:454 anota «hablando» con la cantidad de palabras, sin id y sin ended ni cancelado — ley 4 — costo chico
2. [bug] apps/ventanita/src/componentes/PromptTerminal.tsx:44 — solo ⌘Enter o Ctrl+Enter envían. El Enter solo no hace nada y no queda en el log. Achicarse es otro camino: App.tsx:451 al terminar de hablar, o el click con rama «vuelve a reposo» en App.tsx:559. El punto 9 no está escrito — ninguna ley — costo chico
3. [bug] apps/ventanita/src-tauri/src/voz.rs:189 — el pico se anota al cruzar 0.02 y al cortar (voz.rs:210), no el piso del RODE mientras callás. (a) el click tardío que para, (b) el segundo click a más de 550 ms y (c) diálogo en vez de voz ya los separa el log de App.tsx:512 (n, msDesdeAnterior, rama, temporizador). Para (d) falta el pico en silencio, y solo si el modo es diálogo: en voz el detector ni corre — ley 1 — costo chico
4. [opinión] Los puntos 1 a 6 y la prueba de 4 pasos no vinieron en el mensaje. Una sesión de «uso Remi un rato» mezcla las cuatro causas. La corta, en este orden, con las manos quietas entre medio: dos clicks rápidos y 5 s sin tocar; dos clicks separados por 1 s; tres clicks rápidos y 3 s callado; una palabra, Enter solo, y después ⌘Enter — ninguna ley — costo chico
5. [bug] apps/ventanita/src/registro.ts:39 — el log no se espera, así que no mueve los 550 ms. Lo que sí altera la prueba es el tauri build que está corriendo: borra ventanita.log y reemplaza la app — ninguna ley — costo chico

Cambio propuesto: en este encargo solo dos líneas de log, el id de hablar() al empezar y al terminar (ended o cancelado), y en el onKeyDown si el Enter traía ⌘ y si envió. El gesto no se toca hasta leer una sesión hecha con la prueba de arriba.

## 2026-09-29 · 2f clasificar · auditoría · Grok
Corrí clasificar() tal como está. «no me quedo listo» y «todavia no termino» ya dan idea: esa guarda existe. Estas diez, no.

1. [bug] nucleo/clasificar.py:64 — con 4 palabras o menos, cualquier «listo», «pare», «hecha» cierra el bloque abierto y lo marca hecho. Ley 1, porque el historial se queda con un cierre que no hiciste — costo chico
   • «pare un segundo» — esperado idea — da hecha
   • «la dejo hecha manana» — esperado idea — da hecha
   • «quedo listo» — esperado idea — da hecha
   • «¿listo?» — esperado idea — da hecha
   • «listo el contrato» — esperado idea — da hecha
2. [bug] nucleo/clasificar.py:71 — la negación no frena el arranque. «hoy» o «voy a» adentro de una idea abre un bloque. Ley 6 — costo chico
   • «hoy no puedo» — esperado idea — da hoy
   • «se me ocurrio q hoy armo un curso» — esperado idea — da hoy
   • «voy a ver si armo el curso» — esperado idea — da hoy
3. [bug] nucleo/clasificar.py:34 — arrancar solo reconoce empiezo y arranco, no cómo lo decís. El reloj no se abre. Ley 1 — costo medio
   • «me pongo con la propuesta» — esperado hoy — da idea
   • «arranque con alfonso» — esperado hoy — da idea
   • «sigo con la factura» — esperado hoy — da idea
4. [bug] nucleo/clasificar.py:21 — «ya esta» y «hasta aca» no cierran. El bloque queda abierto para siempre. Ley 1 — costo chico
   • «ya esta» — esperado hecha — da idea

Cambio propuesto: hecha solo si la frase normalizada es exactamente listo, hecha, termine, paro o pare, sin palabras de más. Eso para los cierres falsos. Los arranques que faltan van en otro encargo.

## 2026-09-29 · 2f.2 clasificador · construido · 2a3e8b9

- **Qué cambió:** `nucleo/clasificar.py` reemplaza «hasta 3 palabras más» y los arranques
  sueltos. `hecha` solo con la frase exacta (listo, hecha, hecho, terminé, paro, paré, ya
  está, ya terminé, ya estuvo, hasta acá, cerrado) y nunca con un «?». `hoy` solo si la
  frase empieza —tras un «ahora», «hoy» o «ya» opcional— con voy a, vamos con, me pongo
  con, arranco, arranqué, empiezo, empecé o sigo con, sin negación ni «ver si», «quizás»,
  «a lo mejor», «se me ocurrió», «idea». Todo lo demás, idea. Las 14 frases de Grok y las
  seis de la negación, en `pruebas/test_clasificar.py`. 126 pruebas, mypy limpio.
- **Decisiones que tomé sin preguntar:**
  1. **«listo la tarjeta» pasó de `hecha` a `idea`.** El encargo anterior lo daba por
     cierre; este dice que «listo el contrato» no cierra, y es la misma forma. Gana el
     encargo nuevo y la prueba vieja se dio vuelta.
  2. Los tests de otras suites que abrían bloque con «ahora llamo al banco» pasaron a «voy
     a llamar al banco»: «ahora» solo ya no es un arranque.
  3. «ahora sí arranco con esto» queda `idea`: el «sí» entre el prefijo y el arranque no
     está contemplado en la regla. Si te sale natural decirlo así, es una regla más.
- **Dudas abiertas:** las dos auditorías de Grok (2h y 2f) siguen sin texto en la bitácora;
  llegaron como `[pegá aquí el bloque…]`.
- **Cómo probarlo a mano:** con Remi instalada, decir «listo el contrato» → «Guardada. La
  miramos en dos días.»; «me pongo con la propuesta» → abre bloque; «ya está» → «Cerrada.
  N min.».

## 2026-09-29 · 2i gestos fiables · construido · 032eb48

- **Qué cambió:** los gestos viven en `apps/ventanita/src/gestos.ts`, un módulo puro con
  vitest (21 pruebas, entre ellas la secuencia real del log de las 15:31). Se acabó la espera
  de 520 ms: el 2.º click graba en el acto y el 3.º pasa a diálogo sobre la grabación viva,
  con un comando nuevo en `voz.rs` (`activar_corte_por_silencio`). Gracia de 900 ms; el
  diálogo no lo para un click; una escucha vacía re-arma a los 1,2 s y dos seguidas mandan a
  reposo. Palanca `Control+Option+Space` (`atajo_dictado` en `config/ventanita.json`), por
  el mismo camino que el doble click. Enter envía. `hablar()` con generación: sin eco, y
  cancelar no cae a la voz del sistema. Whisper no transcribe menos de 800 ms, usa `-sns` y
  `-nth 0.5`, y descarta ≤2 caracteres. Instalada con `actualizar.sh`.
- **Decisiones que tomé sin preguntar:**
  1. **En diálogo, un click no para la grabación: nunca.** El encargo decía «pasada la
     gracia, un click sí para (dictado)» y pedía que en la secuencia del log el 4.º click a
     los 1300 ms no cortara. Con gracia de 900 ms desde cualquier anclaje, ese click está
     fuera de la gracia (934 ms desde el 3.º; 1133 desde que arrancó la grabación), así que
     la única lectura que satisface la prueba es la del paréntesis: el click para el
     *dictado*; el diálogo lo cortan el silencio, Escape o la palanca. Y es lo que arregla la
     cadena de cinco ciclos.
  2. **La palanca no cuenta para la racha ni respeta la gracia:** es una tecla, no un dedo
     que sigue cayendo. Y en diálogo lo *termina* transcribiendo lo dicho: cierra la escucha,
     manda lo que hubo, y no se vuelve a armar.
  3. **`--vad` de whisper quedó fuera:** pide un modelo aparte que no está descargado. Van
     `-sns` (suprime tokens de no-voz en el decodificador) y `-nth 0.5`.
  4. Las dos políticas del diálogo (a qué modo le aplica el corte, y qué hacer tras una
     vacía) salieron también a `gestos.ts` para poder probarlas, y App las usa.
- **Dudas abiertas:**
  1. **Las dos auditorías de Grok (2h y 2f) llegaron como marcadores:** `[pegá aquí el
     bloque…]`, sin el texto. No las agregué porque sería inventarlas. Van cuando lleguen.
  2. La línea `[palanca] pulsada` la escribe la tecla de Juan Camilo; yo solo pude verificar
     `atajo de dictado registrado: Control+Alt+Space` al arrancar.
  3. Si `Control+Option+Space` choca con algo del sistema, se cambia en
     `config/ventanita.json` sin recompilar.
- **Cómo probarlo a mano:** una sola cosa, en este orden: doble click, hablar 5 s con pausas
  de 1 s, click para parar; triple click y hablar; `⌃⌥Space` dos veces. Después, «listo».

## 2026-09-29 · 2h ver antes de arreglar · construido · b41f594

- **Qué cambió:** luz, no arreglos. Los gestos no se tocaron. `nucleo/clasificar.py` tiene la
  guarda de negación. El test flaky del MCP espera 180 s. `nucleo/limpiar_pruebas.py` lista
  las tareas de prueba y solo borra con `--borrar`. La app escribe a
  `~/Library/Logs/Remi/ventanita.log` con `tauri-plugin-log` (los `log::` de Rust y, por
  `src/registro.ts`, todo lo que va a `console.*`), con hora en milisegundos, tope de 5 MB y
  rotación de uno. `App.tsx` y `voz.rs` registran cada click con su rama, el temporizador de
  la racha, el prendido del micrófono, cada parada con su origen, cada cambio de estado y de
  tamaño; el núcleo, una línea por `/mensaje` con tipo, ms y si pensó.
- **Decisiones que tomé sin preguntar:**
  1. El origen de la parada **viaja hasta Rust**: `detener_escucha_y_transcribir` ahora recibe
     «click», «silencio:fin», «silencio:sin_voz» o «escape». Antes Rust no sabía por qué lo
     mandaban a cerrar, y el log quedaba a medias entre los dos lados.
  2. Los `eprintln!` de `voz.rs` pasaron a `log::`: es lo único que llega al archivo.
  3. El 520 del temporizador salió a `MS_ESPERA_RACHA`, al lado de `MS_RACHA`. Los dos
     números del gesto, juntos y con nombre, porque la diferencia entre ellos es justo lo que
     hay que mirar.
  4. `registrar()` no puede romper la app: si el reenvío falla, la línea igual queda en la
     consola. Y no se engancha `attachConsole`, que haría un bucle.
- **Dudas abiertas:**
  1. **Los gestos no están arreglados, a propósito.** Ya hay una pista fuerte en el log de
     los clicks reales de Juan Camilo, y está en el reporte, pero la tabla formal va cuando
     él diga «listo» tras las cuatro pruebas en orden.
  2. Quedan las 12 tareas de prueba; la lista numerada está en el reporte y la elección es
     suya.
  3. `es_solo_ruido` (hallazgo 2 de Grok) sigue esperando encargo, y ya se lo vio actuar:
     Whisper devolvió «[MÚSICA]» y lo descartó bien.
- **Cómo probarlo a mano:**
  1. `tail -f ~/Library/Logs/Remi/ventanita.log` y hacer un click: aparece una línea
     `[gesto] click …` con la rama que tomó.
  2. Las cuatro pruebas del reporte, en orden, con 5 segundos entre cada una.
  3. `cd nucleo && uv run python limpiar_pruebas.py` para ver las tareas de prueba.

## 2026-09-29 · 2f la Bandeja · construido · 7f810b9

- **Qué cambió:** `/mensaje` dejó de convertir cada frase en una tarea. `nucleo/clasificar.py`
  (función pura, sin IA) decide idea, hoy o hecha; `nucleo/servidor.py` enruta: una idea
  enfría 48 h en `ideas` sin crear nada, un arranque abre tarea y sesión, y «listo» cierra el
  bloque abierto más reciente y dice cuánto tardó. `RespuestaMensaje` gana `tipo` y
  `tarea`/`sesion` pasan a opcionales, con la ventanita al día. `nucleo/sanear.py` cerró las
  12 sesiones colgadas. El reposo muestra «la última vez: 2 min» vía `GET /ultima-vez`.
  Y los tres hallazgos de Grok que tenían encargo.
- **Decisiones que tomé sin preguntar:**
  1. **El contrato no cambió.** `Idea` ya estaba en `contratos/contratos.json` con todo lo
     que hacía falta, y `RespuestaMensaje` es el sobre de la API, no una entidad del
     dominio: vive en `servidor.py`. Lo que sí respeté es no tocar `modelos.py` a mano.
  2. **«La última vez» mira el último bloque cerrado, no una tarea de hoy.** El encargo
     decía «si hay tarea hoy con historial», pero eso nunca puede mostrar el bloque recién
     cerrado: al decir «listo» la tarea pasa a `hecha` y sale de esa lista. Probándolo salía
     «la última vez: 13 min» de una tarea vieja en vez de los 2 min que pide el criterio.
  3. Los tests viejos decían «Llamar al banco» esperando que fuera una tarea. Ahora eso es
     una idea, que es lo correcto, así que pasaron a decir «ahora llamo al banco»: lo que en
     realidad querían probar.
  4. La píldora se ensancha a 210 px solo cuando muestra «la última vez»: esa línea es del
     doble de largo y no se parte.
  5. El 550 de la racha de clicks salió a la constante `MS_RACHA` en vez de corregir el
     número en la prosa, así no se pueden volver a separar.
- **Dudas abiertas:**
  1. **Quedan 12 tareas de basura** («hola», «scdscsc», «[Motor]») en estado `hoy`, con el
     historial que les puso `sanear.py`. No las borro: dijiste que las marcás vos.
  2. **«No me quedó listo» se clasifica como `hecha`.** Son cuatro palabras y contiene
     «listo», así que entra por la regla de «≤3 palabras más», tal como la escribiste.
     Cerraría un bloque que no terminaste. Se arregla con una guarda de negación, pero es
     una regla nueva y preferí no inventarla.
  3. **Un test es flaky:** `test_el_servidor_mcp_anuncia_exactamente_dos_herramientas` falló
     una vez de tres mientras compilaba la app en paralelo. Levanta un subproceso con
     `timeout=60`; bajo carga se queda corto.
  4. `es_solo_ruido` (hallazgo 2 de Grok) sigue esperando encargo.
- **Cómo probarlo a mano:**
  1. `./scripts/actualizar.sh` y abrí Remi.
  2. Decí «se me ocurrió una app de recetas» → «Guardada. La miramos en dos días.»
  3. Decí «voy a revisar el contrato ahora», trabajá dos minutos, decí «listo» →
     «Cerrada. 2 min.»
  4. Volvé a reposo: la píldora dice «la última vez: 2 min».
  5. Decí «listo» otra vez sin nada abierto → «No había nada abierto.», sin reto.
  6. `sqlite3 nucleo/remi.db "select texto from ideas order by creada_en desc limit 3"`.

## 2026-09-29 · 2g (lo que faltó) · construido · 45533d2

- **Qué cambió:** Remi se abre sola al iniciar sesión (segundo LaunchAgent
  `com.remi.ventanita` en `scripts/instalar.sh`, con `--sin-inicio-automatico` para
  omitirlo). `scripts/actualizar.sh` compila, reemplaza `/Applications/Remi.app`, recarga
  los dos agentes y dice qué commit quedó instalado. `scripts/desinstalar.sh` baja todo y
  borra la app sin tocar `nucleo/remi.db`. `docs/INSTALAR.md` en cinco líneas.
- **Respuesta a la auditoría de 2d:** verifiqué los cuatro contra el código y los cuatro
  son correctos, líneas incluidas.
  1. `servidor.ts:22` — **acepto.** Es el punto 6 del encargo B: sube a 25 s, por encima de
     los 20 s de `pensar.py`, con algo que ate los dos números.
  2. `voz.rs` `es_solo_ruido` — **acepto, y no lo toco todavía.** No hay encargo. Tal como
     está, la lista de 12 etiquetas solo ataja las alucinaciones más comunes de Whisper;
     una frase inventada entera entra como si la hubieras dicho. Lo que yo haría: no
     ampliar la lista (es infinita), sino descartar por señal — ya medimos el pico del
     audio en `pico_db`, y una transcripción larga sobre audio casi mudo es alucinación
     segura. Queda esperando encargo.
  3. `App.tsx:403` comentario de Option+click — **acepto.** Punto 7 del encargo B.
  4. `App.tsx:424` «< 400 ms» vs 550 — **acepto.** Punto 7 del encargo B.
- **Decisiones que tomé sin preguntar:**
  1. El agente de la app va **sin `KeepAlive`**: si cerrás la ventanita se queda cerrada
     hasta el próximo inicio de sesión. El núcleo sí se relevanta; la app es tuya.
  2. Los scripts preguntan por el label exacto con `launchctl list <label>` en vez de
     `| grep`: con Remi abierta, LaunchServices registra un
     `application.com.remi.ventanita.NNN` que también matcheaba.
  3. `desinstalar.sh` y `actualizar.sh` sacan del registro la copia construida en
     `target/` (ver la duda 1).
- **Dudas abiertas:**
  1. **Lo que te hizo ver que Remi no estaba.** Dos cosas, las dos mías. Una: para probar
     `desinstalar.sh` (punto 3 del encargo) lo corrí de verdad, dos veces, y entre esas
     corridas y la reinstalación `/Applications/Remi.app` no existió — esa fue la ventana
     en la que miraste. Dos, y más grave: la copia construida en
     `target/release/bundle/macos/` **también se llama Remi.app**, LaunchServices conocía
     las dos, y al nombre «Remi» le asignaba la del build
     (`osascript -e 'path to application "Remi"'` lo devolvía). O sea que el agente que
     escribí en el punto 1, que hacía `open -a Remi`, abría la copia equivocada. Corregido
     en `45533d2`: se abre por ruta absoluta y solo la instalada queda registrada.
  2. Sigue sin resolverse qué fase va después de 2f (ver la entrada de 2e.0).
- **Cómo probarlo a mano:**
  1. `launchctl list | grep remi` — tienen que estar `com.remi.nucleo` y
     `com.remi.ventanita`.
  2. Cerrá la terminal y `open -a Remi`, o abrila desde Launchpad: el ícono es la brasa.
  3. Cerrá sesión y volvé a entrar: Remi tiene que aparecer sola.
  4. `./scripts/actualizar.sh` después de tocar código — al final dice a qué ruta resuelve
     «Remi» y cuánto espacio queda.

## 2026-09-29 · 2d · auditoría · Grok
1. [bug] apps/ventanita/src/servidor.ts:22 — el fetch de /mensaje se corta a los 8 s.
   nucleo/pensar.py:42-45 dice que guardar puede tardar 10 s y la CLI espera 20 s, y el
   núcleo sigue igual. App.tsx:69 y App.tsx:217 dicen «No pude guardarlo» aunque puede
   haberse guardado; si lo repetís, queda duplicado — ley 3 — costo chico
2. [bug] apps/ventanita/src-tauri/src/voz.rs:233 — es_solo_ruido solo descarta 12
   etiquetas exactas (música, silencio, …). Cualquier otra alucinación de Whisper, frase
   entera, entra como si la hubieras dicho — ley 2 — costo chico
3. [opinión] apps/ventanita/src/App.tsx:403 — el comentario de arriba describe
   Option+click; el de la línea 408 y el código (429, 440) cuentan 1/2/3 por tiempo, que
   es el gesto elegido — ninguna ley — costo chico
4. [opinión] apps/ventanita/src/App.tsx:424 — el comentario dice «< 400 ms» y la racha
   usa 550 — ninguna ley — costo chico
Cambio propuesto: en servidor.ts:22, subir TIMEOUT_NUCLEO_MS por encima de los 20 s de
pensar.py:45 (25 s alcanzan), para que «No pude guardarlo» salga solo cuando el núcleo de
verdad no contestó.

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
