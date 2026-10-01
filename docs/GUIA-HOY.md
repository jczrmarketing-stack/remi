# Remi · guía de uso (1 de octubre)

Para los primeros días reales con un cliente. Verificado contra `main` c10d480. Lo que no está, se dice al final.

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

## 5 · Entregas y cobros (todavía a mano)
```bash
curl -s -X POST 127.0.0.1:4400/entregas -H 'content-type: application/json' \
  -d '{"texto":"entrega para Alfonso el 18 de octubre por 5.000","tema":"upvisuals"}'
```
Con eso la bolita pasa a dinero y Metas muestra la entrega. Cobrada: `POST /entregas/<id>/estado`.

## 6 · Teléfono
Telegram: @lucho777_bot, charla corta, silencio 23:00–7:00, reporte de la noche por la mañana. Panel en el teléfono: solo cuando el túnel tenga Access delante (ver INSTALAR.md).

## 7 · Llaves
Panel → Ajustes → Conexiones: guardar y «Probar». Nunca en un chat. Rotar las cuatro que pasaron por chats.

## 8 · Cierre del día
No hay comando. A las 3:00 copia cifrada, 4:00 consolidación con commit de la bóveda, 7:30 doctor + reporte. Si un Estado dice algo que no pasó: `git -C ~/proyectos/remi-mente log -3` y me lo pegás.

## Lo que hoy NO está
- Entregas hablando (§5), «cobré X» por voz.
- Panel: hora y fecha límite de tareas, «mañana asoma», tema de ideas, metas con nombre, pantalla Proyecto con fases y SOP (J1–J5, en curso en la app).
- Access + túnel al teléfono (Access primero).
- Banco de pruebas (3f), vuelta de Notion, calendario.

## Reglas que no cambian
Remi es solo tuyo. Llaves nunca en git ni en chats. Bóveda fuera del repo. Claude Code no borra tus notas ni tus filas. Si algo contradice la Biblia, gana la Biblia.
