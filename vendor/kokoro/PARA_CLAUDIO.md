# PARA CLAUDIO — TTS Kokoro en Remi

Leé esto entero antes de tocar código. No inventes voces, no metas ElevenLabs, no pidas API key, no uses razonamiento de Haiku para hablar.

Camillo (el usuario) ya eligió motor y voces. Tu trabajo es enchufarlas en Remi.

En este chat, Claude = **Claudio**. No lo corrijas.

---

## Qué se decidió (no reabrir)

- Motor: **Kokoro-82M** (`hexgrad/Kokoro-82M`), Apache-2.0, local, CPU, gratis.
- No Chatterbox en esta entrega (pide GPU ~4 GB). Queda fuera de 2d.
- No Edge TTS como principal. Fallback futuro, no ahora.
- Voces **exactas**, estas cuatro, ni una más:

| id            | idioma | género | rol en UI          | default |
|---------------|--------|--------|--------------------|---------|
| `af_bella`    | en-US  | mujer  | Inglés            | default EN |
| `ef_dora`     | es     | mujer  | Español mujer     |         |
| `em_alex`     | es     | hombre | Español hombre    | default ES |
| `em_santa`    | es     | hombre | Español grave     |         |

- Velocidad **no** la pide el modelo. Generá a 1.0 y el player de la ventanita hace `1× / 1.5× / 2×` (time-stretch). Igual que ahora.
- Claude/Haiku **no** genera audio. Solo texto. Cero tokens extra de voz.
- Sigue valiendo: Haiku **sin razonamiento**, clave **borrada del entorno del subproceso**, error de CLI = fallo silencioso (nunca leer “API Error: 400” con la voz de Remi).
- 2d es la ventanita. Esto es TTS. No cierra 2d. No abras MCP. MCP es 2e.0.

---

## Archivos que ya están bajados (no los vuelvas a descargar si están)

Carpeta de este paquete:

```
kokoro-para-claudio/
  kokoro-v1_0.pth          ~327 MB   pesos
  config.json
  VOICES.md
  SHA256SUMS
  PARA_CLAUDIO.md          ← este archivo
  tts_kokoro.py            ← prueba mínima
  requirements-kokoro.txt
  voices/
    af_bella.pt            ~511 KB
    ef_dora.pt
    em_alex.pt
    em_santa.pt
  samples/                 mp3 de referencia (así suenan)
    af_bella.mp3
    ef_dora.mp3
    em_alex.mp3
    em_santa.mp3
```

Copiá esa carpeta adentro del repo de Remi, por ejemplo:

```
<repo>/vendor/kokoro/
```

Verificá checksums:

```bash
cd vendor/kokoro && sha256sum -c SHA256SUMS
```

Fuente canónica si algo falta:
https://huggingface.co/hexgrad/Kokoro-82M

---

## Cómo corre (contrato de runtime)

Un **solo** modelo en memoria. Las 4 voces son embeddings. Cambiar voz ≠ recargar el pth.

Idioma lo marca el **prefijo de la voz**, no un segundo modelo:

- `a…` → inglés US (`lang_code='a'`)
- `e…` → español (`lang_code='e'`)

Si el texto está en español y la voz es `af_bella`, suena spanglish. **Nunca mezcles.**

Regla:

```
si voice empieza con 'a' → lang_code = 'a'
si voice empieza con 'e' → lang_code = 'e'
```

Detección de idioma del texto de Remi (simple, suficiente):

- Si el usuario eligió voz a mano → usá esa voz (y su lang).
- Si está en “auto”:
  - texto mayormente ES → `em_alex`
  - texto mayormente EN → `af_bella`

No uses un modelo extra de lid. Heurística + `langdetect` liviano está bien. Si hay duda, voz default del locale de la UI.

---

## Dependencias

```txt
kokoro>=0.9
soundfile
torch          # CPU wheel en Mac
misaki[en]     # G2P; el extra espeak cubre ES
```

En Mac:

```bash
uv add kokoro soundfile
# espeak-ng para español (G2P)
brew install espeak-ng
```

Sin `espeak-ng`, el inglés de Bella anda; el español de Dora/Alex/Santa se rompe.

---

## API que tenés que exponer en el núcleo (`servidor.py`)

No inventes otra forma. Un endpoint, sync o cola corta, audio completo (Kokoro no es streaming de verdad útil acá).

`POST /tts`

```json
{
  "text": "Hola, soy Remi.",
  "voice": "em_alex",
  "speed": 1.0
}
```

Respuesta: `audio/wav` 24 kHz mono.

Errores:

- voz desconocida → 400, JSON, **sin hablarlo**
- texto vacío → 204
- fallo de motor → log + silencio. Remi no dice “API Error”.

`GET /tts/voices` → lista fija de las 4, con `id`, `lang`, `label`.

El cliente (Rust / ventanita) ya tiene 1× 1.5× 2×. `speed` en el POST queda en 1.0 salvo que el player no pueda stretch. Preferí stretch en el cliente.

---

## Código de referencia (oficial)

```python
from kokoro import KPipeline
import soundfile as sf

# Un pipeline por idioma. Cachealos. No crees uno por request.
pipe_en = KPipeline(lang_code="a")
pipe_es = KPipeline(lang_code="e")

def synth(text: str, voice: str, out_wav: str):
    pipe = pipe_en if voice.startswith("a") else pipe_es
    chunks = []
    for _, _, audio in pipe(text, voice=voice, speed=1.0):
        chunks.append(audio)
    import numpy as np
    wav = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
    sf.write(out_wav, wav, 24000)
```

Las voces se resuelven por **nombre** (`af_bella`, …). Si el paquete `kokoro` las baja de HF, bien. Si está offline, apuntá a `vendor/kokoro/voices/*.pt`. No pidas red en caliente en cada frase.

`tts_kokoro.py` en esta carpeta es la prueba de humo. Tiene que generar 4 wavs con la frase:

```
ES: "Hola, soy Remi. Te escucho."
EN: "Hi, I'm Remi. I'm listening."
```

Si eso no suena como los mp3 de `samples/`, paramos.

---

## UI de la ventanita (mínimo)

Selector de 4 voces + Auto.

Etiquetas (español de Camillo, no las cambies):

- Bella (EN)
- Dora (ES)
- Alex (ES)   ← default
- Santa (ES)

No pongas “Neural”, “Kokoro-82M”, “hexgrad” en la UI.

---

## Lo que NO hagas

- No cargues las 54 voces.
- No clones voz.
- No uses GPU como requisito. CPU first. Metal si viene gratis.
- No pases el texto por Haiku otra vez “para que suene natural”.
- No exportes `ANTHROPIC_API_KEY` al subproceso de TTS (no hace falta; no la toques).
- No documentes esto como cierre de 2d.
- No abras MCP.

---

## Criterio de listo

1. `uv run python vendor/kokoro/tts_kokoro.py` tira 4 wavs.
2. `/tts` con `em_alex` y texto ES devuelve wav.
3. `/tts` con `af_bella` y texto EN devuelve wav.
4. Voz inventada no habla el error.
5. Player 1 / 1.5 / 2 sigue igual.
6. Disco extra vs antes: ~327 MB + 2 MB. RAM extra ~400 MB mientras habla. Aceptado.

Cuando eso pase, anotá en el doc: “TTS Kokoro 4 voces, local, sin clave”. Listo.

---

## NOTA DE JUAN CAMILO (manda sobre lo de arriba si contradice)

- Los pesos y las voces **no** están en esta carpeta. `uv add kokoro soundfile` y el paquete los baja solo de `hexgrad/Kokoro-82M` la primera vez (~330 MB). Antes: `brew install espeak-ng`.
- No hay `SHA256SUMS`, `samples/` ni `tts_kokoro.py` acá: escribí vos `tts_kokoro.py` como prueba de humo (4 wavs con las frases de arriba).
- La ventanita hoy habla con `speechSynthesis` (`utterance.rate` + `onend`). Con Kokoro el audio es un WAV por HTTP:
  · reproducí con `HTMLAudioElement`; velocidad = `audio.playbackRate` (1 / 1.5 / 2);
  · `hablar()` resuelve en el evento `ended` del audio (App.tsx depende de eso para salir de "hablando");
  · `callarse()` pausa el audio además de `speechSynthesis.cancel()`;
  · si `POST /tts` falla o el núcleo no responde → `speechSynthesis` como hoy, en silencio.
- Selector de voz (Auto / Bella / Dora / Alex / Santa) guardado en `preferencias.ts` como la velocidad. Tokens y fuentes del design system. Nada de "Kokoro" en la UI.
- Un commit al terminar. No cierra 2d. No abras MCP.
