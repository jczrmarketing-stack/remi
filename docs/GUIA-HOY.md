# Remi · guía de uso de hoy

Para el primer día real con un cliente. Todo lo de aquí está en el repo hoy (verificado contra `main` 7610eb1 + `f-ventanita` d52ec1b). Lo que no está, se dice al final.

## 0 · Antes de abrir la ventanita (2 min)
- `git -C ~/proyectos/remi log --oneline -1` → debe mostrar el merge de `f-ventanita` (T1). Si aún dice `7610eb1`, la isla, la piel dinero y el Nudge no están en la app instalada.
- Menú de la bolita → «actualizar» (o `scripts/actualizar.sh` desde main). Solo main corre el actualizador.
- `tail -3 ~/Library/Logs/Remi/nucleo.log` → sin `Traceback`. `curl -s 127.0.0.1:4400/salud` → responde.

## 1 · Cómo se le habla
- **1 clic** en la bolita: dictar. **⌃⌥R**: alterna dictado. **2 clics**: parar/leer. **3 clics**: cerrar.
- Escribe corto. Remi contesta en ≤60 palabras, sin markdown. Si suelta un párrafo largo, es un bug: pégamelo.
- Chip cerebro: **Claude** (Haiku rutina, Sonnet pensar, Opus contratos). Ollama solo sin red. Venice está «(pago)»: hoy no.
- Todo lo que digas queda en `turnos` y se resume; nunca se corta. Una idea va sola a la Bandeja; «listo», «ya quedó», «hecha» (frase exacta, sin «?») cierra la tarea abierta.

## 2 · El cliente escribe («me escribió un cliente»)
Pega el mensaje con una de estas frases delante — el clasificador las reconoce por regla, no por IA:

> me escribió: «…» · el cliente dice: «…» · me dijo: «…»

Remi carga los oficios `clientes` + `proyectos-sop` + `mi-voz` y devuelve: **lectura** (qué pide, qué necesita, qué teme), **riesgos**, **respuesta en tu voz**, **límites** (piso de precio, sin fecha firme antes del alcance, pago antes). Tú envías. Remi nunca envía.

Si la respuesta no suena a ti: «no suena a mí, yo diría …». Eso es una corrección y alimenta `mi-voz`.

## 3 · Propuesta y contrato
> arma la propuesta para <cliente>: <lo que pidió en una frase>

SOP §B: máximo 5 preguntas de descubrimiento, fases con alcance + monto + «listo cuando», Fase 1 pequeña y cobrable. Luego: «ahora el contrato de la Fase 1» (chip Opus). Léelo como lo leería la IA del cliente.

## 4 · Arrancar el proyecto
```bash
~/proyectos/kit-inicial/crear-proyecto.sh <nombre-cliente>
```
Nunca un repo vacío. El libro del proyecto lo creas tú en la bóveda (copia `proyectos/beam.md`, cambia `titulo/tema/claves/ruta`, deja `## Estado` con Quedaste / Decisiones / Próximo paso). Remi lo encuentra por `ruta:` y desde ahí los commits de esa carpeta caen en ese libro.

## 5 · Encargos a Claude Code (por la puerta de Remi)
Chip **Prompt** en la ventanita, luego:
> <proyecto>: <una tarea>

Sale una tarjeta con el encargo (una tarea = un commit, «listo cuando», con los oficios `prompting` y `claude-code` adentro). **⌘⇧C** lo copia. Pégalo en una terminal. Al cerrar la sesión de Claude Code, el hook `SessionEnd` y el `post-commit` global avisan al núcleo (`POST /evento`): el episodio y el Estado se escriben solos. Para retomar: `/donde-quede` en Claude Code, o «¿dónde quedé en <proyecto>?» en la ventanita.

## 6 · Entregas y cobros (hoy, a mano)
La ventanita todavía no crea entregas desde el chat (solo las lee). Hasta que se conecte:
```bash
curl -s -X POST 127.0.0.1:4400/entregas -H 'content-type: application/json' \
  -d '{"texto":"entrega para Alfonso el 18 de octubre por 5.000","tema":"upvisuals"}'
```
La forma es fija: `entrega para <cliente> el <día> de <mes> por <monto>`. Con eso la bolita pasa a **dinero** y aparece el Reloj de una línea bajo el bloque abierto. Cobrada: `POST /entregas/<id>/estado`.

## 7 · Cierre del día
No hay comando. Cada sesión de Claude Code que cierras deja su episodio; una charla larga en la ventanita ofrece guardarse. A las 4:00 la consolidación corre sola (LaunchAgent) con commit de la bóveda antes y después. Si por la mañana un Estado dice algo que no pasó: `git -C ~/proyectos/remi-mente log -3` y me lo pegas.

## Lo que hoy NO está (no lo intentes)
- Panel Hoy web (maquetas listas, sin construir) y túnel remi.inv3rza.com.
- Crear entregas hablando (§6), «cobré X» por voz, celebración de Hecha con dinero.
- Notion ida y vuelta (T3) y Telegram (T4): hasta el merge, nada vuelve de Notion.
- Banco de pruebas (3f) y app en primer plano (NSWorkspace).
- Precios piso en `oficios/clientes.md`: están en blanco. Escribe ahí «Fase 1 mínimo USD X» hoy mismo — una línea.

## Reglas que no cambian
Remi es solo tuyo. Llaves nunca en git. Bóveda fuera del repo. Claude Code no borra tus notas. Si algo contradice la Biblia, gana la Biblia.
