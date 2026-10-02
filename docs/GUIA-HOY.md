# Remi · guía de uso (1 de octubre)

Para los primeros días reales con un cliente. Verificado contra `main` tras T0–T5
(docs/PLAN-100.md). Lo que no está, se dice al final.

## 0 · Antes de empezar (1 min)
- `scripts/doctor.sh` → debe dar 0 FALLA. Si falla algo, dice cuál y qué hacer.
- Panel: `http://127.0.0.1:4402` (corre solo, es un servicio). Ventanita: la bolita.

## 1 · Cómo se le habla
- **1 clic** en la bolita: dictar. **⌃⌥R**: alterna dictado. **2 clics**: parar/leer. **3 clics**: cerrar.
- Corto. Remi contesta en ≤60 palabras, sin markdown. Párrafo largo = bug: pegámelo.
- Chips: **Claude** (default) · **Groq (gratis)** · **OpenRouter (centavos)** · Ollama sin red · Venice (pago, no).
- «voy a X ahora» abre un bloque (Hoy lo muestra con el Reloj). Una idea suelta va a la Bandeja 48 h. «listo» / «ya quedó» / «hecha» cierra el bloque y dice el tiempo.

## 2 · El cliente escribe
> me escribió: «…» · el cliente dice: «…» · me dijo: «…»

Remi devuelve lectura, riesgos, respuesta en tu voz y límites. Vos enviás; Remi nunca envía. Si no suena a vos: «no suena a mí, yo diría …».

## 3 · Propuesta, contrato, proyecto
> arma la propuesta para <cliente>: <una frase> · ahora el contrato de la Fase 1

Proyecto nuevo: `~/proyectos/kit-inicial/crear-proyecto.sh <nombre>`. Libro en la bóveda con `tipo: cliente|propio`, `ruta:` y `## Camino` (lo siembra `scripts/sembrar_camino.py` desde el SOP). Hitos: desde el panel (Proyectos) o `POST /libros/<tema>/camino/<n>`.

## 4 · Encargos a Claude Code
Chip **Prompt** → `<proyecto>: <una tarea>` → ⌘⇧C copia la tarjeta. Al cerrar la sesión, el episodio y el Estado se escriben solos. Retomar: `/donde-quede`.

## 5 · Entregas y cobros, hablando
- «entrega para Alfonso el 18 de octubre por 5.000» → crea la entrega en el libro de
  Alfonso. La bolita pasa a dinero y Metas la muestra.
- «Alfonso pagó 1.500» / «me pagaron 1.500 de UpVisuals» → la anota como cobro de esa
  fase: «Anotado: 1.500 de Alfonso. Van 2.500 de 5.000.» Si no reconoce de quién, no
  adivina — queda para que lo pregunte Remi (§9).
- «mañana llamo al banco», «a las 3 reunión», «el viernes entrego el reporte», «vence el
  15 de octubre el dominio» → anota la tarea con esa fecha u hora, sin abrir bloque.
- A mano, si hace falta: `POST /cobros {"tema": "...", "monto": 1500}` (pagado ya) o
  `POST /entregas` (texto libre, como antes).

## 6 · Teléfono
Telegram: @lucho777_bot, charla corta, silencio 23:00–7:00, reporte de la noche por la mañana. Panel en el teléfono: solo cuando el túnel tenga Access delante (ver INSTALAR.md).

## 7 · Llaves
Panel → Ajustes → Conexiones: guardar y «Probar». Nunca en un chat. Rotar las cuatro que pasaron por chats.

## 8 · Cierre del día
No hay comando. A las 3:00 copia cifrada (incluye `nucleo/.env`, cifrado igual que
`remi.db`), 4:00 consolidación con commit de la bóveda y rotación de logs, 7:30 doctor +
reporte. Si un Estado dice algo que no pasó: `git -C ~/proyectos/remi-mente log -3` y me lo
pegás.

## 9 · Remi pregunta lo que le falta
Un libro sin `tipo:`, sin cliente, sin «listo cuando» en una fase, o con una línea
«(Completar: …)» — Remi lo pregunta sola, nunca más de tres a la vista. Te la hace al
abrir un bloque de ese proyecto, o por Telegram (una vez al día como mucho). Contestar
normal la resuelve; «después» la saca hasta mañana, sin contarlo en contra.

## Para la sesión de Claude en la app (dev)
`scripts/recargar.sh --vigilar` en una terminal del Mac deja un ayudante corriendo: la
sesión de la app le puede pedir recargar el panel o correr pytest/Playwright/vitest sin
tocar los LaunchAgents a mano. Un solo ayudante a la vez (`pkill -f "recargar.sh --vigilar"`
antes de arrancar otro).

## Lo que hoy NO está
- Panel: pantalla Proyecto con fases y SOP viendo la forma real del núcleo (J3 ya está
  construida contra el núcleo falso; falta verla contra T2–T4).
- Access + túnel al teléfono: Access lo pone Juan Camilo a mano en Cloudflare, antes de
  usar el link (ver docs/INSTALAR.md § Panel en el teléfono).
- «Remi pregunta» en el lienzo del panel (C2): diseñado, esperando el visto bueno.
- Banco de pruebas (3f), vuelta de Notion, calendario, ritual de la mañana.

## Reglas que no cambian
Remi es solo tuyo. Llaves nunca en git ni en chats. Bóveda fuera del repo. Claude Code no borra tus notas ni tus filas. Si algo contradice la Biblia, gana la Biblia.
