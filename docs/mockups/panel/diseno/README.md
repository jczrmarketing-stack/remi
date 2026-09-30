# Panel de Remi — diseño aprobado (Claude Design, 30-sep)

Exportado del lienzo «Panel de Remi». Cada archivo es HTML estático con estilos inline y los tokens reales de `design/tokens.json` (Noche; `Hoy-dia` con Día). Abrí cualquiera en el navegador. Claude Code construye `apps/panel` desde estos archivos: misma estructura, mismos tamaños, mismos textos; los datos salen del núcleo.

| Archivo | Qué es |
|---|---|
| `Ajustes-lectura.html` | Ajustes de lectura: tema, biónica, intensidad 55–85 %, aire, piel del Reloj, presupuesto de silencio completo. |
| `Apagado.html` | Núcleo apagado: sin rojo, reintento cada 30 s, referencia a scripts/doctor.sh. |
| `Bandeja.html` | Bandeja: lavanda mientras enfría (48 h), ámbar cuando está lista; solo la lista tiene botones Soltar / Mantener 48 h más / Hacer tarea. Sin contadores. |
| `Hoy-bionica.html` | Hoy · lectura biónica activada: nudge de Remi y párrafos con anclas (1–3→1, 4→2, 5+→mitad; ancla 700, resto 400, interlineado 1,7). Solo en lo que escribe Remi. |
| `Hoy-cerrado.html` | Hoy · hito cerrado: celebración 900 ms (tarjeta en luz, chispas), «Cerrado. Siguiente: …», lista de cierre (commit ✓ hook, Estado ✓, avisar cliente → Remi redacta, nunca envía). |
| `Hoy-dia.html` | Hoy · tema Día: mismos componentes con los tokens Día de tokens.json. |
| `Hoy-foco.html` | Hoy · modo foco (maqueta C): entra a los 20 min de bloque, solo cifras mono, «Después: …». Sale al cerrar. |
| `Hoy-vacio.html` | Hoy · nada abierto: Remi propone por orden del líder (entregas con dinero primero). |
| `Main.html` | Hoy · pantalla permanente (maqueta B): número de la semana, FocusCard con Reloj instrumento, Además hoy (máx. 3), Vence, ideas frías, orden del líder. |
| `Metas.html` | Metas · la plata: meta → $/mes → brecha → acción; ingreso por línea; segunda meta apagada hasta que la primera pase de 50 %. |
| `Movil-Bandeja.html` | Teléfono · Bandeja. |
| `Movil-Foco.html` | Teléfono · foco. |
| `Movil-Hoy-bionica.html` | Teléfono · Hoy con lectura biónica. |
| `Movil-Hoy.html` | Teléfono · Hoy (390×844): plata, FocusCard con Reloj brasa, 3 filas, ideas frías, barra inferior de 4 pestañas ≥ 44 px. |
| `Movil-Proyectos.html` | Teléfono · caminos como lista (sin constelación), el de plata arriba. |
| `Proyectos.html` | Proyectos: constelación (tamaño = prioridad, arco = recorrido) + camino lineal del seleccionado. En 375 px la constelación se vuelve lista. |
| `Semana.html` | Revisión semanal (lunes, 20 min): plata del mes, lo cerrado, lo aplazado, ideas frías, la locura de la semana. Temporizador. |

Reglas que el código debe respetar: una locura por pantalla · el rojo solo habla de tiempo · sin contadores de fallo ni rachas · celebración una sola vez, 900 ms · biónica nunca en botones, campos ni código · Remi redacta, nunca envía.
