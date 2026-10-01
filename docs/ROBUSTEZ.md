# Remi · Plan de robustez

*30 de septiembre de 2026. Decidido con Juan Camilo. Si algo lo contradice, gana este plan junto con la Biblia.*

**Meta**: Remi contesta rápido, inventa poco, falla poco, y no pide mantenimiento. Claude al frente; todo lo demás es respaldo o trastienda.

## 1 · Diagnóstico (lo que hay en `main`, 30-sep)

Funciona y está en `main`: memoria que no se corta (turnos + resumen vivo + estante + vectores locales), carácter, oficios por tema, puerta de prompts, «me escribió un cliente», entregas, hooks de git y Claude Code, `/donde-quede`, bóveda con git y commit automático, copia cifrada nocturna, vigía.

Tres riesgos reales, ninguno es «falta código»:

1. **La trastienda inventa.** Haiku pisó libros tres veces; el 30-sep apareció otro invento en un episodio. Los frenos existen (verificación mecánica de entidades, git en la bóveda) pero la causa sigue: un modelo flojo escribiendo verdades sin supervisión.
2. **Demasiadas piezas.** Tauri, FastAPI, whisper-cli, Kokoro, Ollama, 4 LaunchAgents, MCP, hooks, `claude -p`, y ahora Notion, Telegram, OpenRouter, Groq. Cada una puede romperse sin que nadie la toque. La más peligrosa: `claude -p`, porque Claude Code se actualiza solo.
3. **Notion de ida y vuelta.** Un sync bidireccional es la pieza de más mantenimiento del plan.

## 2 · Las reglas

### Robustez: plan B en todo lo que sale del Mac
- Todo proveedor externo: timeout, un reintento, respaldo, una línea de log. Nada rompe el turno.
- **Cerebro con respaldo**: si Claude (Max) devuelve límite o `claude -p` falla, el turno se reintenta con OpenRouter · DeepSeek V4-Pro y la respuesta lleva `motor_usado`; la ventanita muestra el chip real. Cuando Claude vuelve, vuelve.
- Motores por nombre de proveedor: Claude (default, Haiku/Sonnet/Opus por nivel), Groq (gratis, rutina), OpenRouter (DeepSeek Flash / V4-Pro, openai/gpt-oss-120b, Qwen3-Coder por nivel; `models` con caída automática y `provider.sort=price`), Venice (manual, pago), Ollama (sin red). Modelos en `config/motores.json`, nunca en código.
- **Trastienda** (resumen vivo, claves, títulos de episodios, consolidación nocturna): Groq · openai/gpt-oss-120b → OpenRouter · DeepSeek Flash → Ollama. Max queda para la voz de Remi.
- Vectores: siempre locales (Ollama).

### Mantenimiento casi nulo: menos piezas, una prueba diaria
- **`scripts/doctor.sh`**: un comando que revisa núcleo, whisper, kokoro, ollama, LaunchAgents, bóveda git limpia, llaves presentes en `.env`, última copia cifrada, último episodio, disco. El vigía lo corre cada mañana y avisa por Telegram solo si algo falla.
- **Notion solo de ida** (Remi → Notion, vitrina). La vuelta de campos se activa cuando Remi lleve un mes en uso y Juan Camilo sepa si abre Notion siquiera.
- **Siete días sin funciones nuevas** después de cerrar las terminales de hoy. Solo bugs de uso real. Remi solo sirve si se le habla todos los días.
- Versiones fijas: whisper-cli y Kokoro por ruta; `claude` con versión anotada en la bitácora; si `claude -p` cambia de forma, el respaldo cubre y `doctor.sh` avisa.

### Alucinación baja: la IA propone, las reglas y Juan Camilo deciden
- Los Estados de la bóveda se escriben solo desde evidencia literal (mensajes de commit, frases del transcript). Sin cita, no hay línea. Es la regla única, no una de varias.
- Trastienda con openai/gpt-oss-120b en vez de gemma3:4b: el modelo que más inventaba era el más flojo.
- **Reporte de la noche por Telegram**: «anoche cambié esto en N libros», con diff corto de la bóveda. Cualquier invento se revierte con `git revert` en `remi-mente`.
- La verificación mecánica de entidades corre también como test en la suite.

### Velocidad: medir y recortar
- Primero el número: el núcleo loguea `ms=` por mensaje; el banco de pruebas (3f) lo convierte en tabla.
- Metas: texto < 4 s, voz < 8 s de punta a punta.
- Palancas, por orden: nivel rápido con Haiku; no abrir el MCP en cada turno cuando la precarga ya trae la memoria; respuesta en streaming para que Kokoro hable desde la primera frase; Kokoro caliente en memoria.

## 3 · Orden

1. **Hoy**: cerrar T1 (motores + plan B + trastienda), T2 (Fase 3), T3 (Notion de ida), T4 (Telegram + reporte nocturno).
2. **Mañana**: `doctor.sh` + banco de pruebas (3f). Con datos se eligen motores y se recorta latencia.
3. **Siete días de uso real** con un cliente. Lo que falla se dice en la ventanita («esto falló») y alimenta el libro de errores.
4. **Después, solo si se extrañaron**: panel Hoy, vuelta de Notion, calendario.

## 4 · Lo que no cambia
Remi es solo de Juan Camilo. Claude al frente. Llaves en `nucleo/.env`, nunca en git. Bóveda fuera del repo, con git. Claude Code no borra notas. Si algo contradice la Biblia, gana la Biblia.
