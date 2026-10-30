# Mapa del repo Remi · 2026-10-30

Una línea por archivo: ruta · líneas · qué expone. Léelo antes de buscar con grep; abre solo el archivo que necesites. Se regenera con `python3 scripts/mapa.py`.


## apps/panel

- `apps/panel/next-env.d.ts` · 7 l.
- `apps/panel/playwright.config.ts` · 58 l.
- `apps/panel/src/bionica.ts` · 49 l. · largoAncla, TrozoBionico, partirBionica, perillasBionica
- `apps/panel/src/config.ts` · 6 l. · URL_NUCLEO, PUERTO_PANEL
- `apps/panel/src/contratos.ts` · 174 l. · UUID, ISODateString, Tarea, Idea, Sesion, Nudge …
- `apps/panel/src/app/layout.tsx` · 36 l. · metadata, viewport, RootLayout
- `apps/panel/src/app/page.tsx` · 583 l. · PaginaHoy
- `apps/panel/src/app/ajustes/page.tsx` · 119 l. · PaginaAjustes
- `apps/panel/src/app/bandeja/page.tsx` · 169 l. · PaginaBandeja
- `apps/panel/src/app/coding/page.tsx` · 274 l. · PaginaCoding
- `apps/panel/src/app/metas/page.tsx` · 248 l. · PaginaMetas
- `apps/panel/src/app/proyectos/page.tsx` · 225 l. · PaginaProyectos
- `apps/panel/src/app/proyectos/[tema]/page.tsx` · 570 l. · PaginaProyecto
- `apps/panel/src/app/rumbo/page.tsx` · 434 l. · PaginaRumbo
- `apps/panel/src/app/rumbo/caminos/[id]/page.tsx` · 156 l. · PaginaCamino
- `apps/panel/src/app/rumbo/motor/page.tsx` · 81 l. · PaginaMotor
- `apps/panel/src/app/rumbo/partida/page.tsx` · 113 l. · PaginaPartida
- `apps/panel/src/app/semana/page.tsx` · 247 l. · PaginaSemana
- `apps/panel/src/components/Apagado.tsx` · 40 l. · Apagado
- `apps/panel/src/components/Bionica.tsx` · 31 l. · Bionica
- `apps/panel/src/components/Chip.tsx` · 11 l. · Chip
- `apps/panel/src/components/Conexiones.tsx` · 245 l. · Conexiones
- `apps/panel/src/components/Constelacion.tsx` · 120 l. · CUPO_CONSTELACION, Constelacion
- `apps/panel/src/components/Header.tsx` · 60 l. · Header
- `apps/panel/src/components/MoneyRow.tsx` · 27 l. · MoneyRow
- `apps/panel/src/components/NudgeCard.tsx` · 33 l. · NudgeCard
- `apps/panel/src/components/PreguntaDeRemi.tsx` · 155 l. · PreguntaDeRemi
- `apps/panel/src/components/ProgressBar.tsx` · 16 l. · ProgressBar
- `apps/panel/src/components/ProjectPath.tsx` · 45 l. · ProjectPath
- `apps/panel/src/components/Reloj.tsx` · 105 l. · Reloj
- `apps/panel/src/components/StatusDot.tsx` · 19 l. · StatusDot
- `apps/panel/src/components/TabBar.tsx` · 32 l. · TabBar
- `apps/panel/src/components/Tramo.tsx` · 33 l. · Tramo
- `apps/panel/src/hooks/PreferenciasContext.tsx` · 77 l. · PielReloj, Preferencias, POR_DEFECTO, PreferenciasProvider, usePreferencias
- `apps/panel/src/hooks/useCargaNucleo.ts` · 38 l. · useCargaNucleo
- `apps/panel/src/lib/formato.ts` · 114 l. · formatoHora, horaDeISO, fechaCorta, venceTexto, diaDelInstante, enFrase …
- `apps/panel/src/lib/hoy.ts` · 139 l. · BloqueAbierto, Propuesta, DatosHoy, proponer, cargarHoy, minutosDesde …
- `apps/panel/src/lib/lider.ts` · 61 l. · Escalon, liderDe, escalonDe, ordenDelLider, hitoDe, recorridoDe …
- `apps/panel/src/lib/nucleo.ts` · 406 l. · NucleoApagado, TareaConHistorial, Salud, IdeaBandeja, CerradoPor, Hito …
- `apps/panel/src/lib/proyecto.ts` · 68 l. · enlaceObsidian, datosDe, ultimaCobradaDe, PartesDelEstado, partesDelEstado, tonoDeFase
- `apps/panel/tests/ajustes.spec.ts` · 32 l.
- `apps/panel/tests/bandeja.spec.ts` · 79 l.
- `apps/panel/tests/hoy.spec.ts` · 158 l.
- `apps/panel/tests/metas.spec.ts` · 71 l.
- `apps/panel/tests/nucleo-rewrite.spec.ts` · 12 l.
- `apps/panel/tests/partida.spec.ts` · 41 l.
- `apps/panel/tests/pregunta.spec.ts` · 113 l.
- `apps/panel/tests/proyecto.spec.ts` · 194 l.
- `apps/panel/tests/proyectos.spec.ts` · 125 l.
- `apps/panel/tests/rumbo-camino.spec.ts` · 53 l.
- `apps/panel/tests/rumbo-cuenta.spec.ts` · 46 l.
- `apps/panel/tests/rumbo-motor.spec.ts` · 58 l.
- `apps/panel/tests/rumbo.spec.ts` · 54 l.
- `apps/panel/tests/semana.spec.ts` · 81 l.

## apps/ventanita

- `apps/ventanita/vite.config.ts` · 33 l.
- `apps/ventanita/vitest.config.ts` · 11 l.
- `apps/ventanita/src/App.tsx` · 1874 l. · App
- `apps/ventanita/src/avisoNotion.prueba.ts` · 38 l.
- `apps/ventanita/src/avisoNotion.ts` · 84 l. · MS_ENTRE_CONSULTAS_AVISO_NOTION, TAMANO_AVISO_NOTION, AvisoDeNotion, RespuestaAvisoNotion, avisoEnPantalla, BloqueAviso …
- `apps/ventanita/src/bionica.prueba.ts` · 30 l.
- `apps/ventanita/src/bionica.ts` · 49 l. · largoAncla, TrozoBionico, partirBionica, perillasBionica
- `apps/ventanita/src/bloqueAbierto.prueba.ts` · 31 l.
- `apps/ventanita/src/bloqueAbierto.ts` · 12 l. · debeMostrarReloj
- `apps/ventanita/src/config.ts` · 5 l. · URL_NUCLEO
- `apps/ventanita/src/contratos.ts` · 174 l. · UUID, ISODateString, Tarea, Idea, Sesion, Nudge …
- `apps/ventanita/src/envivo.prueba.ts` · 38 l.
- `apps/ventanita/src/envivo.ts` · 46 l. · FraseEnVivo, LineaEnVivo, partirLineas, leerLinea
- `apps/ventanita/src/frases.prueba.ts` · 34 l.
- `apps/ventanita/src/gestos.prueba.ts` · 468 l.
- `apps/ventanita/src/gestos.ts` · 317 l. · MS_RACHA, MS_TRIPLE, MS_FANTASMA_SEGUIDO, MS_FANTASMA_RESIZE, MS_GRACIA, Racha …
- `apps/ventanita/src/grabacion.prueba.ts` · 14 l.
- `apps/ventanita/src/grabacion.ts` · 11 l. · quedoUnaGrabacionColgada
- `apps/ventanita/src/guardarCharla.prueba.ts` · 26 l.
- `apps/ventanita/src/guardarCharla.ts` · 13 l. · PREGUNTA_GUARDAR, yaPreguntoSiGuarda
- `apps/ventanita/src/historial.prueba.ts` · 37 l.
- `apps/ventanita/src/historial.ts` · 39 l. · etiquetaDeFecha, TurnoParaVolver, chatAlVolver
- `apps/ventanita/src/lectura.prueba.ts` · 26 l.
- `apps/ventanita/src/lectura.ts` · 61 l. · Tema, Lectura, LECTURA_POR_DEFECTO, obtenerLectura, fijarLectura, aplicarTema …
- `apps/ventanita/src/main.tsx` · 13 l.
- `apps/ventanita/src/markdown.prueba.ts` · 90 l.
- `apps/ventanita/src/markdown.ts` · 118 l. · limpiarMarkdown, Parte, Bloque, partesConEnlaces, partirRespuesta
- `apps/ventanita/src/microfono.ts` · 65 l. · EVENTO_SILENCIO, iniciarEscucha, OrigenParada, cancelarEscucha, activarCortePorSilencio, transcribirParcial …
- `apps/ventanita/src/movimiento.ts` · 63 l. · animarTamano
- `apps/ventanita/src/nudges.prueba.ts` · 28 l.
- `apps/ventanita/src/nudges.ts` · 20 l. · MS_ENTRE_CONSULTAS_NUDGE, RespuestaNudge, respuestaDeTecla
- `apps/ventanita/src/portapapeles.ts` · 30 l. · copiarAlPortapapeles
- `apps/ventanita/src/preferencias.prueba.ts` · 87 l.
- `apps/ventanita/src/preferencias.ts` · 236 l. · VELOCIDADES, Velocidad, PreferenciaVoz, VOZ_AUTOMATICA, estaSilenciado, alternarSilencio …
- `apps/ventanita/src/recordatorio.prueba.ts` · 21 l.
- `apps/ventanita/src/recordatorio.ts` · 16 l. · MS_ENTRE_RECORDATORIOS, MS_RECORDATORIO_VISIBLE, tocaRecordar
- `apps/ventanita/src/registro.ts` · 77 l. · enchufarConsola, registrar
- `apps/ventanita/src/reposo.prueba.ts` · 46 l.
- `apps/ventanita/src/reposo.ts` · 25 l. · TAMANO_ISLA_MINIMA, TAMANO_ISLA_CON_TEXTO, TAMANO_ISLA_NUDGE, MS_NUDGE_VISIBLE, MS_ISLA_VISIBLE, MS_ISLA_ENCOGER …
- `apps/ventanita/src/servidor.ts` · 349 l. · TokensClaude, TipoMensaje, RespuestaMensaje, MotorDePensar, obtenerMotores, OpcionesMensaje …
- `apps/ventanita/src/tiempo.prueba.ts` · 18 l.
- `apps/ventanita/src/tiempo.ts` · 51 l. · registrarInteraccion, ultimaInteraccion, formatearDuracion, formatearReloj, formatearHace
- `apps/ventanita/src/tipos.ts` · 11 l. · Estado, OrigenMensaje, Modo
- `apps/ventanita/src/useAvisoNotion.ts` · 150 l. · useAvisoNotion
- `apps/ventanita/src/ventana.prueba.ts` · 39 l.
- `apps/ventanita/src/ventana.ts` · 85 l. · Tamano, Posicion, Pantalla, TAMANO_MINIMO, TAMANO_CHAT_POR_DEFECTO, FRACCION_MAXIMA …
- `apps/ventanita/src/vite-env.d.ts` · 2 l.
- `apps/ventanita/src/voz.prueba.ts` · 154 l.
- `apps/ventanita/src/voz.ts` · 588 l. · VozDisponible, limiteDeVoz, dividirEnFrases, haySoporteDeVoz, obtenerVoces, repartirVelocidad …
- `apps/ventanita/src/componentes/AccionesRespuesta.tsx` · 69 l. · AccionesRespuesta
- `apps/ventanita/src/componentes/AvisoNotion.tsx` · 44 l. · AvisoNotion
- `apps/ventanita/src/componentes/Campo.tsx` · 69 l. · CampoRef, LARGO_PARA_EPISODIO, Campo
- `apps/ventanita/src/componentes/Chat.tsx` · 249 l. · Mensaje, Chat
- `apps/ventanita/src/componentes/ChipCerebro.tsx` · 92 l. · ChipCerebro
- `apps/ventanita/src/componentes/ChipLectura.tsx` · 107 l. · ChipLectura
- `apps/ventanita/src/componentes/ChipVoz.tsx` · 63 l. · nombreLegible, ChipVoz
- `apps/ventanita/src/componentes/Encargo.tsx` · 39 l. · Encargo
- `apps/ventanita/src/componentes/Historial.tsx` · 57 l. · Historial
- `apps/ventanita/src/componentes/LimiteDeError.tsx` · 40 l. · LimiteDeError
- `apps/ventanita/src/componentes/Nudge.tsx` · 67 l. · Nudge
- `apps/ventanita/src/componentes/Reloj.tsx` · 30 l. · Reloj
- `apps/ventanita/src/componentes/Semaforo.tsx` · 63 l. · Semaforo
- `apps/ventanita/src/componentes/StatusDot.tsx` · 68 l. · StatusDot
- `apps/ventanita/src-tauri/build.rs` · 4 l.
- `apps/ventanita/src-tauri/src/lib.rs` · 284 l. · run
- `apps/ventanita/src-tauri/src/main.rs` · 7 l.
- `apps/ventanita/src-tauri/src/voz.rs` · 1542 l. · AvisoSilencio, Grabacion, EstadoGrabacion, matar_si_hay_grabacion, iniciar_escucha, activar_corte_por_silencio …

## nucleo

- `nucleo/accesibilidad.py` · 60 l. · B10.2 (PLAN-FINAL.md): accesibilidad de macOS — la app activa y el · VentanaActiva, leer_ventana_activa_macos
- `nucleo/agenda.py` · 110 l. · Agenda por voz (T2.5): «mañana…», «a las 3…», «el viernes…», «vence el · AgendaParseada, parsear
- `nucleo/aldia.py` · 343 l. · B2: «Al día» — Remi sabe en qué vas, sin que lo marques (PLAN-FINAL.md, · Evidencia, Evento, EstamosEn, LoUltimo, Sigue, MientrasNoEstabas …
- `nucleo/analisis_camino.py` · 184 l. · R3 (forma Q, PLAN-FINAL.md): el análisis de un camino. El código nunca · FuenteCruda, ResultadoInvestigacion, Investigador, verificar_fuentes, ejecutar_investigacion, CuerpoAnalisis …
- `nucleo/avisos.py` · 324 l. · B5 (docs/PLAN-FINAL.md): avisos que jalan la atención — los únicos tres · ConfigAvisos, leer_apps_trabajo, leer_config, Aviso, registrar, responder …
- `nucleo/bandeja.py` · 169 l. · La Bandeja (Ley 6): lo suelto enfría 48 h antes de una revisión en frío. · IdeaNoEncontrada, IdeaNoFria, RevisionHecha, leer_idea, esta_fria, listar_abiertas …
- `nucleo/boveda_git.py` · 73 l. · Cada escritura de Remi en la bóveda queda con revert real. · raiz, snapshot_antes, snapshot_despues
- `nucleo/calendario.py` · 119 l. · B10.1 (PLAN-FINAL.md): Google Calendar. Las citas entran como `Tarea` · EventoInvalido, evento_a_tarea, tarea_a_evento, sincronizar_citas, CuerpoImportar, importar_citas …
- `nucleo/calibracion.py` · 180 l. · R4.5 (forma P, PLAN-FINAL.md): pronósticos y calibración. · Recalibrador, entrenar_recalibrador, CuerpoPronostico, crear_pronostico, CuerpoResolver, resolver_pronostico …
- `nucleo/caminos.py` · 370 l. · La sección «## Camino» de un libro de proyecto: hitos «- [ ] …» / «- [x] …». · Hito, plantilla_de, bloque_camino_de, paso_remi_de, detalle_de, cierra_con_de …
- `nucleo/cierre.py` · 476 l. · Al cerrar Claude Code, un episodio y el Estado del libro. · hay_problema_resuelto, hay_evidencia_de_arreglo, redactar_error, secciones_error_de, escribir_episodio_error, guardar …
- `nucleo/clasificar.py` · 211 l. · Una frase no siempre es una tarea. Sin IA: idea, hoy o hecha. · normalizar, pide_busqueda, es_texto_de_cliente, contenido_anotar_leccion, es_cortesia_o_muy_corta, contenido_anota_esto …
- `nucleo/claves.py` · 170 l. · Claves (3–6 palabras) en el frontmatter de libros, oficios y episodios. · filtrar_inventadas, extraer, tiene_claves, agregar, generar_faltantes
- `nucleo/cobros.py` · 43 l. · Un cobro que llega hablado (T2.4): «Alfonso pagó 1.000», «me pagaron · CobroParseado, parsear
- `nucleo/coding.py` · 505 l. · Coding con la bóveda delante (Biblia Parte VII + VIII). Una tarea de · lecciones_para, ultimas_de_coding, resumen_de, bloque_de_experiencia, Mano, LimiteDeMax …
- `nucleo/concreto.py` · 80 l. · Si piden un prompt, el prompt sale primero. · pide_prompt, entrega_primero, concreto_primero
- `nucleo/conexiones.py` · 224 l. · Conexiones (Panel → Ajustes): llaves y tokens, nunca su valor completo. · NombreInvalido, Prueba, Conexion, estado, guardar, probar …
- `nucleo/correcciones.py` · 162 l. · Aprender de las correcciones (Biblia Parte VI): Remi propone, nunca guarda solo. · es_correccion, es_confirmacion, oficio_destino, proponer_regla, proponer, revisar_confirmacion …
- `nucleo/db.py` · 1598 l. · SQLite: fuente de verdad de Remi. remi.db nunca va al repo (ver .gitignore). · ruta_db, inicializar_esquema, conectar, crear_tarea, actualizar_paso_minimo, actualizar_estado_tarea …
- `nucleo/entregas.py` · 281 l. · Entregas (3f · 2): CRUD del contrato Entrega, aparte de servidor.py — un · EntregaParseada, parsear_entrega, crear_entrega, listar_entregas, leer_entrega, entrega_del_proyecto …
- `nucleo/episodios.py` · 171 l. · Una charla pegada se guarda como episodio (3c · 7). · Episodio, carpeta_episodios, slug, guardar
- `nucleo/estado_crm.py` · 104 l. · Trae lo abierto de «Remi · CRM de vida» (Notion) a mente/negocio/crm.md. · filtro, render, refrescar
- `nucleo/estado_libro.py` · 259 l. · La sección «Estado» de un libro de proyecto. · es_paso_interno, leer_estado, escribir_estado, sin_evidencia_nueva, entidades_sospechosas, redactar …
- `nucleo/estimacion.py` · 71 l. · R4.1-R4.3 (PLAN-FINAL.md): números honestos. El código nunca decide · combinar_a_ciegas, pesos_mezcla, mezclar, estimar_a_ciegas, Critica, necesita_segunda_ronda
- `nucleo/etiquetar.py` · 162 l. · Etiquetar notas de la bóveda desde el teléfono, un toque por nota. · notas, siguiente, medicion, manejar_comando, manejar_boton
- `nucleo/experiencia.py` · 628 l. · T8 (Biblia v3.9, Parte VII «La experiencia es memoria»): lecciones con · carpeta, Leccion, secciones_de, validar, slug, LeccionGuardada …
- `nucleo/ficha.py` · 199 l. · B6: los números derivados de la ficha de cliente — gastado (agrupado), · GastoAgrupado, gastos_comunes_mes, gastado_de, por_hora, Ficha, ficha_de …
- `nucleo/gasto.py` · 165 l. · Tope de gasto en los motores pagados (B1, docs/PLAN-FINAL.md). Venice y · ConfigGasto, leer_config, escribir_config, calcular_usd, registrar, gasto_dia_usd …
- `nucleo/gastos.py` · 104 l. · B6.1: un gasto que llega hablado — «gasté 40 en el servidor de · GastoParseado, parsear
- `nucleo/generar_modelos.py` · 114 l. · Genera nucleo/modelos.py desde contratos/contratos.json. · tipo_python, linea_campo, generar
- `nucleo/hilos.py` · 31 l. · B7: hilos por tema (de la revisión R6). Al saltar de proyecto en medio · rastrear, voz_del_hilo
- `nucleo/indexar.py` · 316 l. · El índice único de la mente: `mente/indice.db`, FTS5 + sqlite-vec, por hash. · Hallazgo, ruta_indice, conectar, actualizar, buscar, leer …
- `nucleo/iniciativa.py` · 290 l. · El motor de iniciativa (Biblia Parte III «el que sabe cuándo», ley 6). · silenciar, Candidato, evaluar, registrar, pendiente_o_nuevo, responder
- `nucleo/juego.py` · 100 l. · R3 (PLAN-FINAL.md): «Ábreme el juego» — 20 jugadas con muestreo · JugadaCruda, filtrar_jugadas, generar_jugadas, jugadas_a_ideas
- `nucleo/libros.py` · 302 l. · Un proyecto es una carpeta. El libro lo dice en `ruta:` del frontmatter. · Fase, Libro, carpeta, fecha_corta, fecha_del_nombre, fuera_del_estante …
- `nucleo/limpiar_pruebas.py` · 216 l. · Lo que quedó de probar Remi en la base real — dos patrones, nada más: · candidatos_dia_cero, archivar_dia_cero, deshacer_dia_cero, main
- `nucleo/memoria_mcp.py` · 232 l. · El estante de Remi, como servidor MCP (stdio). · indice, leer, guardar, anotar_leccion, buscar_lecciones, buscar_memoria
- `nucleo/mensaje_cliente.py` · 40 l. · B3.1: «ya le mandé el avance a Alfonso» cierra el hito de ese cliente · libro_nombrado
- `nucleo/modelos.py` · 213 l. · Generado desde contratos/contratos.json por generar_modelos.py. · Tarea, Idea, Sesion, Nudge, Memoria, Pregunta …
- `nucleo/noche.py` · 360 l. · Consolidación nocturna (ARQUITECTURA-CEREBRO §6): LaunchAgent com.remi.noche · actualizar_estados_del_dia, fusionar_episodios_del_dia, recalcular_vectores, reordenar_mente, diff_de_la_noche, enviar_reporte_de_la_noche …
- `nucleo/notion.py` · 246 l. · Cliente delgado de la API de Notion, y la puerta HTTP del sync (Fase 4). · token, pagina_id, vuelta_habilitada, Notion, prop_titulo, prop_texto …
- `nucleo/notion_avisos.py` · 372 l. · Puente Notion → Ventanita: los avisos de «Remi · CRM de vida». · fuente_id, sondear, Salida, pendiente, responder, arrancar_hilo …
- `nucleo/notion_sync.py` · 437 l. · Fase 4 · espejo de Notion: proyectos y entregas. · ResumenSync, sincronizar
- `nucleo/orden_rumbo.py` · 55 l. · R5.1 (PLAN-FINAL.md): Hoy ordenado por el Rumbo. Orden: (1) fecha · PropuestaHoy, PropuestaElegida, elegir
- `nucleo/pensar.py` · 1982 l. · Pensar con Claude, opt-in por mensaje (think=true). Por defecto Remi no · SinLlave, LimiteDeClaude, reglas_de_no_leer, Modo, caracter, rol_tecnico …
- `nucleo/plata.py` · 321 l. · La plata del mes (Panel · Metas): sin regaños, solo números. · Semana, EntregaCobrada, Mes, EntregaProxima, Meta, RevisionFria …
- `nucleo/precarga.py` · 385 l. · Precarga del proyecto activo (ARQUITECTURA-CEREBRO §4). · proyecto_activo, resumen_nivel2, bloque, de_referencia, tema_dudoso, linea_de_duda …
- `nucleo/preguntas.py` · 619 l. · T3 (fase Q, Biblia v3.8): Remi pregunta lo que le falta — nunca un · marcar_en_el_aire, en_el_aire, borrar_en_el_aire, es_arranque_cierre_o_pregunta, preguntar_en_voz, avisar_por_telegram_si_toca …
- `nucleo/probar_bloqueos.py` · 68 l. · ¿Remi puede leer una clave? Prueba de verdad, con la CLI (3c · 10). · probar
- `nucleo/produccion.py` · 137 l. · PR (PLAN-FINAL.md, Biblia Parte VIII): del encargo a producción. Los · generar_paquete_base, HallazgoSeguridad, puede_entregar, HallazgoDiff, RevisionDiff, revisar_sesion …
- `nucleo/recoger.py` · 244 l. · Recoger links por Telegram para la bóveda. · extraer_urls, resumen_corto, cerrar_auto, reanudar, manejar
- `nucleo/refresco_claude_code.py` · 173 l. · Refresco semanal del oficio Claude Code (Biblia Parte VI, Fase S punto 5). · traer_changelog, refrescar
- `nucleo/reloj.py` · 167 l. · R2 (forma S, PLAN-FINAL.md): el Reloj — estimación basada en evidencia · EstimacionReloj, estimar, excede_90_min, Latido, calcular_latido, piezas_caladas …
- `nucleo/remi_mcp.py` · 78 l. · El cerebro vivo de Remi, como servidor MCP global (stdio). · estado_vivo, preguntar, leer, anotar, supuestos
- `nucleo/rumbo.py` · 613 l. · R1 (forma N, PLAN-FINAL.md): Rumbo — visión, meta, escalera y punto de · PropuestaVision, parsear_vision, calcular_partida_medida, ItemPartida, PropuestaVisionVista, CuerpoVision …
- `nucleo/sanear.py` · 57 l. · Cierra las sesiones que quedaron abiertas y nadie cerró. · sanear
- `nucleo/semana.py` · 105 l. · GET /semana (Forma D, T4.2): las cinco preguntas del panel «Semana» · Cerrado, Aplazado, IdeaDestacada, Semana, calcular, ver_semana
- `nucleo/sembrar_conocimiento.py` · 204 l. · Mete las fichas de conocimiento/proyectos/*.md en el estante. · Ficha, carpeta, carpeta_oficios, leer_ficha, nivel_de, sembrar …
- `nucleo/sembrar_memoria.py` · 79 l. · Pone en el estante lo que Remi tiene que saber desde el primer día. · sembrar
- `nucleo/servidor.py` · 2478 l. · FastAPI local. El bind en 127.0.0.1 no protege del origen: por acá no pueden · problema_de_aislamiento, ciclo_de_vida, recortar_voz, sin_markdown, para_hablar, frase_remi …
- `nucleo/simulacion.py` · 69 l. · R4.4 (PLAN-FINAL.md): simulación de seis meses, sembrada con `numpy` · Bandas, Frecuencia, ResultadoSimulacion, simular, kelly_tope
- `nucleo/telegram.py` · 473 l. · Telegram (Biblia Parte IV): el teléfono — avisos y charla corta. · es_privado, para_el_telefono, token, chat_id_configurado, Transporte, ClienteBotAPI …
- `nucleo/temas.py` · 81 l. · A qué libro pertenece una idea (Biblia v3.7: `Idea.tema`). · tema_de_texto
- `nucleo/trabajo.py` · 712 l. · Las herramientas avisan solas. Remi no espera una palabra clave. · es_ruta_de_pruebas, es_carpeta_de_proyecto, es_cuanto, cuanto_le_meti, minutos_esta_semana, minutos_totales …
- `nucleo/tts.py` · 140 l. · Voz de Remi, local y sin clave: Kokoro-82M en CPU. · Voz, lang_code, elegir_voz, resolver_voz, precalentar, sintetizar
- `nucleo/vectores.py` · 215 l. · Vectores locales de la bóveda (ARQUITECTURA-CEREBRO §3 / Biblia Parte IV·B). · Nota, preparar, notas, embed, actualizar_todos, asociar
- `nucleo/vida.py` · 196 l. · La mente de Juan Camilo como archivos: quién es, su negocio, supuestos, bandeja y búsqueda · construir_estado, buscar, agregar
- `nucleo/voseo.py` · 167 l. · De vos a tú, sin modelo. · voseo_a_tu

## scripts

- `scripts/archivar_ruido_de_sesiones.py` · 72 l. · T11.2: las ideas de ruido que T8.0 dejó de crear, pero que ya habían · es_ruido, candidatas, main
- `scripts/banco.py` · 130 l. · El banco de la revisión (docs/PLAN-REVISION.md, R0): un núcleo de prueba · parar, arrancar, frases
- `scripts/hook_prompt_boveda.py` · 96 l. · Hook UserPromptSubmit de Claude Code: antes de que Claude piense, la bóveda · consulta_de, fichas_de_repos, contexto, main
- `scripts/hook_sesion_inicio.py` · 19 l. · Hook SessionStart de Claude Code: mete el estado vivo de Juan Camilo en el
- `scripts/instalar_hook_claude.py` · 75 l. · Pone el hook de inicio de sesión de Remi en ~/.claude/settings.json. · transformar, main
- `scripts/mapa.py` · 143 l. · Mapa del repo y de la mente, para que Claude no explore con grep lo que ya se sabe. · mapa_repo, mapa_mente, main
- `scripts/oficios_a_skills.py` · 80 l. · T9.4: exporta cada oficio de la bóveda como skill de usuario de Claude · main
- `scripts/sembrar_camino.py` · 89 l. · Siembra «## Camino» en los libros que todavía no lo tienen, con los · main
- `scripts/skill_a_oficio.py` · 95 l. · T9.4: trae un SKILL.md de solo conocimiento (sin scripts que ejecuten · main

## scripts/hooks

- `scripts/hooks/avisar-commit.py` · 92 l. · Avisa al núcleo que hubo un commit. Si no está, se calla. · main
- `scripts/hooks/claude-sesion.py` · 139 l. · SessionStart y SessionEnd de Claude Code, hacia el núcleo de Remi. · hito_del_primer_turno, main
- `scripts/hooks/instalar-claude.py` · 70 l. · Suma SessionStart y SessionEnd al settings.json de Claude Code. · instalar, main
- `scripts/hooks/instalar-mcp.py` · 64 l. · Registra el MCP de memoria en Claude Code (scope user) y en la app de escritorio. · entrada, configurar_escritorio, registrar_claude_code, main

## vendor/kokoro

- `vendor/kokoro/tts_kokoro.py` · 67 l. · Prueba de humo del TTS de Remi: genera un wav por cada una de las cuatro · main

203 archivos de código; 137 archivos de pruebas en `nucleo/pruebas/` (correr: `cd nucleo && .venv/bin/python -m pytest -q`).
