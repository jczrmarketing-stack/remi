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
