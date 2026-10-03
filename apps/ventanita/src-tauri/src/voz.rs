//! Micrófono real, reemplaza a Handy: graba con ffmpeg (avfoundation) y
//! transcribe con whisper.cpp (Homebrew), reusando un modelo que Handy
//! ya tenía descargado. Nada de esto sale del Mac.
use std::fs;
use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStderr, Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter};

// Si ffmpeg muere antes de esto, fue un fallo real (permiso de
// micrófono negado, dispositivo inválido, etc.) — no lo tomamos como
// "ya está grabando".
const ESPERA_CONFIRMAR_ARRANQUE: Duration = Duration::from_millis(400);

// El wav que graba ffmpeg: 16 kHz, mono, 16 bits.
const BYTES_POR_SEGUNDO: u64 = 16_000 * 2;
// Cabecera estándar de un wav PCM: los datos empiezan después.
const LARGO_CABECERA_WAV: u64 = 44;
// Cada cuánto miramos cómo viene el audio.
const PASO_VIGILANCIA: Duration = Duration::from_millis(250);
// Ventana que miramos en cada paso.
const VENTANA_SEGUNDOS: f64 = 0.4;
// Por debajo de esto nunca hay voz (sobre 1.0 = máximo del micrófono). Es
// un piso, no el umbral: el umbral real se adapta al ruido de fondo.
const UMBRAL_VOZ: f32 = 0.02;
// Hay voz cuando el pico supera el piso del micrófono por este factor. Del
// log del 29/09 17:09: el RODE en silencio da 0.030–0.080 y hablando
// 0.24–0.68. Con el umbral fijo en 0.020 «callado» nunca subía y el
// diálogo no cortaba jamás. Con ×2.5 sobre un piso de 0.05 el umbral queda
// en 0.125: por encima del ruido, por debajo de la voz.
const FACTOR_SOBRE_PISO: f32 = 2.5;
// Y un techo: si empezás a hablar apenas entrás en diálogo, las primeras
// ventanas son todas voz, el «piso» sale alto y ×2.5 lo deja por encima de
// tu propia voz — nunca «te escucho» y a los 10 s se rinde. Con el RODE la
// voz pica 0.24–0.68: por encima de 0.15 es voz en cualquier micrófono.
const UMBRAL_MAXIMO: f32 = 0.15;
// Cuántas ventanas recientes se miran para estimar el piso (12 × 0.4 s ≈ 3 s
// con pasos de 250 ms). Entre palabra y palabra hay huecos: el mínimo de
// tres segundos es el fondo aunque estés hablando.
const VENTANAS_PARA_EL_PISO: usize = 12;

/// El piso: lo más bajo que se oyó en las últimas ventanas. None sin datos.
fn piso_de(recientes: &[f32]) -> Option<f32> {
    recientes.iter().copied().reduce(f32::min)
}

/// Umbral de voz para un piso dado: entre UMBRAL_VOZ y UMBRAL_MAXIMO.
fn umbral_para(piso: f32) -> f32 {
    (piso * FACTOR_SOBRE_PISO).clamp(UMBRAL_VOZ, UMBRAL_MAXIMO)
}
// Cuánto silencio seguido, después de hablar, cuenta como "ya terminaste".
// 2 s y no 1,2: con 1,2 el diálogo cortaba a mitad de frase cada vez que
// Juan Camilo se paraba a pensar la palabra siguiente (3b). Solo lo usa el
// diálogo: el dictado nunca corta por silencio.
const SILENCIO_PARA_CORTAR: Duration = Duration::from_millis(1400);
// Si en todo este tiempo no dijiste nada, Remi deja de esperar (en diálogo
// no hay cuadro para escribir: sin esto quedaba grabando para siempre).
const SIN_VOZ_MAXIMO: Duration = Duration::from_secs(10);
// ffmpeg con avfoundation tarda hasta un segundo en abrir el wav de salida.
// El vigilante arranca antes: si en su primera mirada el archivo no está,
// no es que la grabación terminó, es que todavía no empezó a escribirse.
// El 29/09 a las 17:29 y 17:38 se iba a los 250 ms creyendo eso — cuatro
// minutos mudos. Hasta aquí espera a que aparezca.
const ESPERA_WAV_MAXIMA: Duration = Duration::from_secs(5);

// La ventanita escucha este evento para cortar sola la grabación.
pub const EVENTO_SILENCIO: &str = "voz://silencio";

// Por qué se cortó: "fin" = hablaste y te callaste; "sin_voz" = no dijiste
// nada en SIN_VOZ_MAXIMO. La ventanita decide distinto en cada caso.
#[derive(Serialize, Clone)]
pub struct AvisoSilencio {
    pub motivo: &'static str,
}

#[derive(Deserialize, Clone)]
struct ConfigVoz {
    ffmpeg_bin: String,
    whisper_cli_bin: String,
    // Whisper residente (agente com.remi.whisper). Si falta o no contesta,
    // se usa whisper-cli como antes.
    #[serde(default)]
    whisper_server_url: Option<String>,
    modelo: String,
    idioma: String,
    dispositivo_audio: String,
}

#[derive(Deserialize)]
struct ConfigVentanitaConVoz {
    voz: ConfigVoz,
}

pub struct Grabacion {
    hijo: Child,
    ruta_wav: PathBuf,
    // Si ya hay un hilo vigilando el silencio. El 3.er click pasa a diálogo
    // sobre la grabación viva, y no puede armar dos vigilantes.
    vigilando: bool,
    // El hilo que vigila el silencio mira esto en cada paso: al detener la
    // grabación se prende y el hilo muere sin emitir nada. Antes seguía
    // vivo sobre el archivo ya cerrado y podía avisar un silencio viejo
    // encima de la grabación siguiente.
    cancelar_vigilancia: Arc<AtomicBool>,
    // V1 (2/10/2026): hasta dónde (bytes de muestras, después de la
    // cabecera) lo grabado ya es texto definitivo, y ese texto. Cada
    // transcripción parcial confirma un trozo cuando hay una pausa, y al
    // parar solo se transcribe lo que queda: 55 s de dictado tardaban 5,9 s
    // al parar porque Whisper volvía a pasar por todo.
    bytes_confirmados: usize,
    texto_confirmado: String,
}

impl Grabacion {
    fn detener(mut self) -> PathBuf {
        self.cancelar_vigilancia.store(true, Ordering::Relaxed);
        // ffmpeg cierra el archivo prolijo si le mandamos 'q' por stdin,
        // en vez de matarlo (eso deja el wav a medio escribir).
        if let Some(mut entrada) = self.hijo.stdin.take() {
            let _ = entrada.write_all(b"q");
        }
        let _ = self.hijo.wait();
        self.ruta_wav
    }
}

#[derive(Default)]
pub struct EstadoGrabacion(Mutex<Option<Grabacion>>);

impl EstadoGrabacion {
    // Si la app se cierra (o se reinicia en dev) con una grabación activa,
    // ffmpeg queda huérfano grabando para siempre y ocupa el micrófono —
    // ya pasó una vez. Se llama al salir.
    pub fn matar_si_hay_grabacion(&self) {
        if let Ok(mut guarda) = self.0.lock() {
            if let Some(mut grabacion) = guarda.take() {
                log::warn!("[voz] la app cierra con una grabación activa: matando ffmpeg");
                grabacion.cancelar_vigilancia.store(true, Ordering::Relaxed);
                let _ = grabacion.hijo.kill();
                let _ = grabacion.hijo.wait();
                let _ = fs::remove_file(&grabacion.ruta_wav);
            }
        }
    }
}

fn ruta_config() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("..")
        .join("config")
        .join("ventanita.json")
}

fn leer_config_voz() -> Result<ConfigVoz, String> {
    let ruta = ruta_config();
    let contenido = fs::read_to_string(&ruta)
        .map_err(|_| format!("no encontré {}", ruta.display()))?;
    let config: ConfigVentanitaConVoz = serde_json::from_str(&contenido)
        .map_err(|_| "config/ventanita.json inválido (falta la sección voz)".to_string())?;
    Ok(config.voz)
}

// Nombre único por grabación: si un hilo viejo (que vigila un silencio que
// ya no importa) llega a mirar este archivo después de que se borró, no
// puede confundirlo con una grabación nueva que reusa el mismo nombre.
static CONTADOR_GRABACION: AtomicU64 = AtomicU64::new(0);

fn ruta_temporal(sufijo: &str) -> PathBuf {
    let n = CONTADOR_GRABACION.fetch_add(1, Ordering::Relaxed);
    std::env::temp_dir().join(format!("remi-voz-{}-{n}{sufijo}", std::process::id()))
}

// ffmpeg escribe MUCHO por stderr: si nadie lo lee, se llena el pipe y se
// traba. Este hilo solo lo drena.
fn drenar_stderr(stderr: ChildStderr) {
    thread::spawn(move || {
        for _ in BufReader::new(stderr).lines().map_while(Result::ok) {}
    });
}

// Pico de la última ventana del wav, entre 0.0 y 1.0. El filtro
// silencedetect de ffmpeg no imprime nada en esta versión, así que
// medimos el audio nosotros leyendo el archivo mientras crece.
fn pico_reciente(ruta_wav: &Path) -> Option<f32> {
    pico_reciente_o_motivo(ruta_wav).ok()
}

// La versión que explica. El 29/09 a las 17:29 el vigilante no escribió
// nada en 4 minutos con el wav creciendo: la rama «no pude leer» callaba y
// no había forma de saber en qué se trababa.
fn pico_reciente_o_motivo(ruta_wav: &Path) -> Result<f32, String> {
    let mut archivo = fs::File::open(ruta_wav).map_err(|e| format!("no abre: {e}"))?;
    let largo = archivo
        .metadata()
        .map_err(|e| format!("sin metadata: {e}"))?
        .len();
    let ventana = (BYTES_POR_SEGUNDO as f64 * VENTANA_SEGUNDOS) as u64;
    if largo < ventana + LARGO_CABECERA_WAV {
        return Err(format!("todavía no hay una ventana entera ({largo} bytes)"));
    }

    use std::io::{Seek, SeekFrom};
    archivo
        .seek(SeekFrom::Start(largo - ventana))
        .map_err(|e| format!("no pude posicionarme: {e}"))?;
    let mut crudo = vec![0u8; ventana as usize];
    archivo
        .read_exact(&mut crudo)
        .map_err(|e| format!("no pude leer la ventana: {e}"))?;

    let pico = crudo
        .chunks_exact(2)
        .map(|par| i16::from_le_bytes([par[0], par[1]]).unsigned_abs())
        .max()
        .unwrap_or(0);
    Ok(pico as f32 / i16::MAX as f32)
}

// Avisa a la ventanita cuando dejaste de hablar, para cortar sola — o
// cuando pasó SIN_VOZ_MAXIMO sin que dijeras nada.
fn vigilar_silencio(ruta_wav: PathBuf, app: AppHandle, cancelado: Arc<AtomicBool>) {
    thread::spawn(move || {
        log::info!("[voz] vigilancia de silencio arrancó sobre {}", ruta_wav.display());
        let mut hubo_voz = false;
        let mut callado = Duration::ZERO;
        let mut transcurrido = Duration::ZERO;
        // «No existe» solo quiere decir «terminó» si alguna vez existió.
        let mut wav_visto = false;

        // Hallazgo 3 de Grok: el pico solo quedaba al cruzar el umbral y al
        // cortar, nunca el piso mientras callás. Sin ese dato no se puede
        // saber si el ruido del RODE queda por encima de UMBRAL_VOZ, que es
        // exactamente lo que explicaría un diálogo que nunca corta. Una
        // línea por segundo, no cuatro.
        let mut pasos_desde_el_ultimo_aviso = 0u32;
        const PASOS_POR_AVISO: u32 = 4; // 4 × 250 ms = 1 s
        let mut recientes: std::collections::VecDeque<f32> =
            std::collections::VecDeque::with_capacity(VENTANAS_PARA_EL_PISO);

        loop {
            thread::sleep(PASO_VIGILANCIA);
            if cancelado.load(Ordering::Relaxed) {
                return;
            }
            transcurrido += PASO_VIGILANCIA;

            if !wav_visto && ruta_wav.exists() {
                wav_visto = true;
                log::info!("[voz] el wav apareció a los {} ms", transcurrido.as_millis());
            }

            let pico = match pico_reciente_o_motivo(&ruta_wav) {
                Ok(pico) => pico,
                Err(motivo) => {
                    if !ruta_wav.exists() {
                        if wav_visto {
                            log::info!("[voz] vigilancia termina: el wav ya no está");
                            return;
                        }
                        if transcurrido >= ESPERA_WAV_MAXIMA {
                            log::warn!(
                                "[voz] vigilancia termina: el wav no apareció en {} s",
                                ESPERA_WAV_MAXIMA.as_secs()
                            );
                            return;
                        }
                        continue;
                    }
                    // Una vez por segundo, no cuatro: pero nunca en silencio.
                    pasos_desde_el_ultimo_aviso += 1;
                    if pasos_desde_el_ultimo_aviso >= PASOS_POR_AVISO {
                        pasos_desde_el_ultimo_aviso = 0;
                        log::warn!("[voz] sin nivel: {motivo}");
                    }
                    continue;
                }
            };

            if recientes.len() == VENTANAS_PARA_EL_PISO {
                recientes.pop_front();
            }
            recientes.push_back(pico);
            let piso = piso_de(recientes.make_contiguous()).unwrap_or(pico);
            let umbral = umbral_para(piso);

            pasos_desde_el_ultimo_aviso += 1;
            if pasos_desde_el_ultimo_aviso >= PASOS_POR_AVISO {
                pasos_desde_el_ultimo_aviso = 0;
                log::info!(
                    "[voz] nivel {pico:.3} · piso {piso:.3} · umbral {umbral:.3} · voz={} · callado={} ms",
                    if hubo_voz { "sí" } else { "no" },
                    callado.as_millis()
                );
            }

            if pico >= umbral {
                if !hubo_voz {
                    log::info!("[voz] te escucho (pico {pico:.3})");
                }
                hubo_voz = true;
                callado = Duration::ZERO;
                continue;
            }

            if !hubo_voz {
                if transcurrido >= SIN_VOZ_MAXIMO {
                    log::info!(
                        "[voz] {}s sin voz (pico {pico:.3}) → dejo de esperar",
                        SIN_VOZ_MAXIMO.as_secs()
                    );
                    let _ = app.emit(EVENTO_SILENCIO, AvisoSilencio { motivo: "sin_voz" });
                    return;
                }
                continue;
            }

            callado += PASO_VIGILANCIA;
            if callado >= SILENCIO_PARA_CORTAR {
                log::info!(
                    "[voz] dejaste de hablar: callado {} ms (umbral {} ms, pico {pico:.3}) → corto sola",
                    callado.as_millis(),
                    SILENCIO_PARA_CORTAR.as_millis()
                );
                let _ = app.emit(EVENTO_SILENCIO, AvisoSilencio { motivo: "fin" });
                return;
            }
        }
    });
}

// Whisper alucina etiquetas cuando el audio es silencio o ruido: si eso
// es TODO lo que devolvió, no escuchó nada.
fn es_solo_ruido(texto: &str) -> bool {
    let limpio = texto
        .trim()
        .trim_matches(|c: char| c == '"' || c == '.' || c == ',')
        .trim()
        .to_lowercase();
    if limpio.is_empty() {
        return true;
    }
    let sin_marcas = limpio
        .trim_start_matches(['[', '(', '*'])
        .trim_end_matches([']', ')', '*'])
        .trim();
    matches!(
        sin_marcas,
        "música"
            | "musica"
            | "music"
            | "silencio"
            | "silence"
            | "blank_audio"
            | "sonido"
            | "aplausos"
            | "risas"
            | "ruido"
            | "suspiro"
    ) || es_alucinacion(&limpio)
}

// Lo que Whisper «oye» en el silencio: cierres de video de YouTube con los
// que se entrenó. El 30/09 entraron al chat como si Juan Camilo los hubiera
// dicho («Gracias por ver el video.», «¡Suscríbete al canal!»). Solo si es
// la transcripción entera: una frase real que los nombre pasa igual.
const ALUCINACIONES: &[&str] = &[
    "suscribete al canal",
    "suscribete",
    "gracias por ver el video",
    "gracias por ver",
    "gracias por ver el video suscribete al canal",
    "no olvides suscribirte",
    "subtitulos realizados por la comunidad de amaraorg",
    "subtitulos por la comunidad de amaraorg",
    "thanks for watching",
    "thank you for watching",
];

fn es_alucinacion(texto: &str) -> bool {
    let normal: String = texto
        .to_lowercase()
        .chars()
        .map(|c| match c {
            'á' => 'a',
            'é' => 'e',
            'í' => 'i',
            'ó' => 'o',
            'ú' | 'ü' => 'u',
            otro => otro,
        })
        .filter(|c| c.is_alphanumeric() || c.is_whitespace())
        .collect();
    let normal = normal.split_whitespace().collect::<Vec<_>>().join(" ");
    ALUCINACIONES.contains(&normal.as_str())
}

// ffmpeg imprime un banner enorme antes del error real; nos quedamos con
// la última línea no vacía, que es la que importa.
fn ultima_linea_util(salida: &str) -> String {
    salida
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty())
        .next_back()
        .unwrap_or("(sin detalle)")
        .to_string()
}

#[tauri::command]
pub fn iniciar_escucha(
    app: AppHandle,
    estado: tauri::State<EstadoGrabacion>,
    cortar_solo: bool,
) -> Result<(), String> {
    let config = leer_config_voz()?;
    let mut guarda = estado.0.lock().map_err(|e| e.to_string())?;
    if guarda.is_some() {
        return Err("ya había una grabación activa".to_string());
    }

    let ruta_wav = ruta_temporal(".wav");
    log::info!(
        "[voz] grabando: {} -f avfoundation -i :{} → {} (corte solo: {cortar_solo})",
        config.ffmpeg_bin,
        config.dispositivo_audio,
        ruta_wav.display()
    );
    let mut comando = Command::new(&config.ffmpeg_bin);
    comando
        .args([
            "-y",
            "-f",
            "avfoundation",
            "-i",
            &format!(":{}", config.dispositivo_audio),
            "-ar",
            "16000",
            "-ac",
            "1",
            // Sin esto ffmpeg guarda ~32 KB (≈1 s de audio) antes de
            // escribir al disco: el vigilante veía el audio con un segundo
            // de atraso y el corte por silencio llegaba tarde o no llegaba.
            "-flush_packets",
            "1",
        ])
        .stdin(Stdio::piped())
        .stdout(Stdio::null())
        .stderr(Stdio::piped());

    comando.arg(&ruta_wav);

    let mut hijo = comando
        .spawn()
        .map_err(|e| format!("no pude arrancar ffmpeg: {e}"))?;

    // ffmpeg tarda un toque en fallar (permiso de mic negado, dispositivo
    // que no existe): si ya murió en este rato corto, no mentimos que
    // está grabando.
    thread::sleep(ESPERA_CONFIRMAR_ARRANQUE);
    if let Ok(Some(estado_salida)) = hijo.try_wait() {
        let mut error = String::new();
        if let Some(mut stderr) = hijo.stderr.take() {
            let _ = stderr.read_to_string(&mut error);
        }
        let detalle = format!(
            "ffmpeg terminó enseguida ({estado_salida}): {}",
            ultima_linea_util(&error)
        );
        log::error!("[voz] {detalle}");
        log::error!("[voz] stderr completo:\n{error}");
        return Err(detalle);
    }

    if let Some(stderr) = hijo.stderr.take() {
        drenar_stderr(stderr);
    }
    let cancelar_vigilancia = Arc::new(AtomicBool::new(false));
    if cortar_solo {
        vigilar_silencio(ruta_wav.clone(), app.clone(), cancelar_vigilancia.clone());
    }

    *guarda = Some(Grabacion {
        hijo,
        ruta_wav,
        vigilando: cortar_solo,
        cancelar_vigilancia,
        bytes_confirmados: 0,
        texto_confirmado: String::new(),
    });
    Ok(())
}

/// El 3.er click: la grabación sigue tal cual y se le prende el corte por
/// silencio. Reiniciarla perdería lo que ya dijiste mientras hacías el
/// gesto. Llamarlo dos veces no arma dos vigilantes.
#[tauri::command]
pub fn activar_corte_por_silencio(
    app: AppHandle,
    estado: tauri::State<EstadoGrabacion>,
) -> Result<(), String> {
    let mut guarda = estado.0.lock().map_err(|e| e.to_string())?;
    let Some(grabacion) = guarda.as_mut() else {
        log::warn!("[voz] pidieron corte por silencio sin grabación activa");
        return Err("no había ninguna grabación activa".to_string());
    };
    if grabacion.vigilando {
        log::info!("[voz] el corte por silencio ya estaba activo");
        return Ok(());
    }
    grabacion.vigilando = true;
    vigilar_silencio(
        grabacion.ruta_wav.clone(),
        app,
        grabacion.cancelar_vigilancia.clone(),
    );
    log::info!("[voz] corte por silencio activado sobre la grabación viva");
    Ok(())
}

/// Cancelar: cierra la grabación y borra el audio SIN transcribir. Es lo
/// que hacen la X y Escape; antes cortaban con detener_escucha_y_transcribir
/// y Whisper trabajaba igual para un texto que nadie iba a usar.
#[tauri::command]
pub fn cancelar_escucha(estado: tauri::State<EstadoGrabacion>, origen: String) -> Result<(), String> {
    let grabacion = estado.0.lock().map_err(|e| e.to_string())?.take();
    let Some(grabacion) = grabacion else {
        log::info!("[voz] cancelar ({origen}) sin grabación activa: nada que hacer");
        return Ok(());
    };
    let ruta_wav = grabacion.detener();
    let _ = fs::remove_file(&ruta_wav);
    log::info!("[voz] cancelada ({origen}): sin transcribir, audio borrado");
    Ok(())
}

/// `origen` dice QUIÉN cortó: "click", "silencio:fin", "silencio:sin_voz",
/// "escape" o "timeout". Lo sabe la ventanita, no acá, y sin eso el log no
/// alcanza para entender un gesto que salió mal.
// Async: corre fuera del hilo de la ventana. Síncrono, la congelaba mientras
// Whisper transcribía, y un toque dado en ese rato llegaba después y
// arrancaba otro dictado (30/09, 23:44:48, tres veces seguidas).
#[tauri::command(async)]
pub fn detener_escucha_y_transcribir(
    estado: tauri::State<'_, EstadoGrabacion>,
    origen: String,
) -> Result<String, String> {
    let grabacion = estado
        .0
        .lock()
        .map_err(|e| e.to_string())?
        .take()
        .ok_or_else(|| {
            log::warn!("[voz] parada ({origen}) sin grabación activa");
            "no había ninguna grabación activa".to_string()
        })?;

    log::info!("[voz] parada ({origen}): cierro ffmpeg y transcribo");
    let bytes_confirmados = grabacion.bytes_confirmados;
    let texto_confirmado = grabacion.texto_confirmado.clone();
    let ruta_wav = grabacion.detener();
    let resultado = transcribir(&ruta_wav, bytes_confirmados, &texto_confirmado);
    let _ = fs::remove_file(&ruta_wav);
    match &resultado {
        Ok(texto) => log::info!("[voz] transcrito ({origen}): {} caracteres", texto.len()),
        Err(error) => log::warn!("[voz] sin transcripción ({origen}): {error}"),
    }
    resultado
}

// Una voz normal pica bien por encima de esto; si no llega, el micrófono
// no escuchó nada (silenciado, volumen de entrada bajo, o mal dispositivo).
const PICO_MINIMO_DB: f32 = -42.0;
// Por debajo de esto no hay una frase: es un click que cortó enseguida.
// Whisper, con menos de un segundo, se inventa algo. No se le da la chance.
const DURACION_MINIMA: Duration = Duration::from_millis(800);
// Una transcripción de una o dos letras es ruido con forma de letra.
const LARGO_MINIMO_TRANSCRIPCION: usize = 3;

fn duracion_del_wav(ruta_wav: &Path) -> Option<Duration> {
    let largo = fs::metadata(ruta_wav).ok()?.len();
    let muestras = largo.saturating_sub(LARGO_CABECERA_WAV);
    Some(Duration::from_secs_f64(muestras as f64 / BYTES_POR_SEGUNDO as f64))
}

fn pico_db(ffmpeg_bin: &str, ruta_wav: &Path) -> Option<f32> {
    let salida = Command::new(ffmpeg_bin)
        .arg("-i")
        .arg(ruta_wav)
        .args(["-af", "volumedetect", "-f", "null", "-"])
        .output()
        .ok()?;
    let texto = String::from_utf8_lossy(&salida.stderr);
    let linea = texto.lines().find(|l| l.contains("max_volume:"))?;
    linea
        .split("max_volume:")
        .nth(1)?
        .trim()
        .trim_end_matches("dB")
        .trim()
        .parse()
        .ok()
}

/// Transcribe lo grabado. `bytes_confirmados` y `texto_confirmado` son lo
/// que las parciales ya dejaron definitivo: solo se pasa por Whisper lo que
/// sigue, y el texto final es lo confirmado más eso.
fn transcribir(ruta_wav: &Path, bytes_confirmados: usize, texto_confirmado: &str) -> Result<String, String> {
    let config = leer_config_voz()?;

    if let Some(duracion) = duracion_del_wav(ruta_wav) {
        if duracion < DURACION_MINIMA {
            log::info!(
                "[voz] grabación de {} ms: muy corta para ser una frase, no la transcribo",
                duracion.as_millis()
            );
            return Err("no era una frase (muy corta)".to_string());
        }
        log::info!("[voz] grabación de {} ms", duracion.as_millis());
    }

    if let Some(pico) = pico_db(&config.ffmpeg_bin, ruta_wav) {
        log::info!("[voz] pico del audio: {pico} dB");
        if pico < PICO_MINIMO_DB {
            return Err(format!(
                "no se escuchó nada (pico {pico:.1} dB): revisá el micrófono o el volumen de entrada"
            ));
        }
    }

    // Sin voz sostenida en lo que falta, no se le pasa a Whisper (alucina
    // «Gracias.» con ruido): queda lo confirmado, o «no se entendió».
    {
        let mut bytes = fs::read(ruta_wav).map_err(|e| format!("no pude leer lo grabado: {e}"))?;
        if let Some(inicio_datos) = cabecera_completa(&mut bytes) {
            let datos = &bytes[inicio_datos..];
            let desde = bytes_confirmados.min(datos.len());
            if !hay_voz_sostenida(&niveles_por_ventana(&datos[desde..]), umbral_de(datos)) {
                log::info!("[voz] lo que falta transcribir no tiene voz sostenida: no va a Whisper");
                let texto = texto_confirmado.trim().to_string();
                if texto.chars().count() >= LARGO_MINIMO_TRANSCRIPCION {
                    return Ok(texto);
                }
                return Err("no se entendió nada de lo grabado".to_string());
            }
        }
    }

    // Lo que queda por transcribir: desde lo confirmado (o el archivo entero
    // si no había nada confirmado), y de eso solo el tramo con voz: el
    // silencio de los bordes no va a Whisper (3-oct, palabras inventadas al
    // final). Si el wav no tiene cabecera legible, el archivo entero.
    let mut bytes = fs::read(ruta_wav).map_err(|e| format!("no pude leer lo grabado: {e}"))?;
    let (ruta_a_transcribir, trozo_temporal) = match cabecera_completa(&mut bytes) {
        Some(inicio_datos) => {
            let datos = &bytes[inicio_datos..];
            let desde = bytes_confirmados.min(datos.len());
            let voz = solo_la_voz(&datos[desde..], umbral_de(datos));
            let trozo = escribir_trozo(&bytes[..inicio_datos], voz)?;
            if bytes_confirmados > 0 {
                log::info!(
                    "[voz] confirmados {} s antes de parar: transcribo solo los últimos {} s",
                    bytes_confirmados as u64 / BYTES_POR_SEGUNDO,
                    (datos.len() - desde) as u64 / BYTES_POR_SEGUNDO
                );
            }
            log::info!(
                "[voz] a Whisper van {} ms de voz (de {} ms grabados)",
                voz.len() as u64 * 1000 / BYTES_POR_SEGUNDO,
                (datos.len() - desde) as u64 * 1000 / BYTES_POR_SEGUNDO
            );
            (trozo.clone(), Some(trozo))
        }
        None => (ruta_wav.to_path_buf(), None),
    };

    let arranque = Instant::now();
    let texto = match config.whisper_server_url.as_deref().map(|url| transcribir_con_servidor(url, &ruta_a_transcribir)) {
        Some(Ok(texto)) => {
            log::info!("[voz] whisper residente: {} ms", arranque.elapsed().as_millis());
            Ok(texto)
        }
        otro => {
            if let Some(Err(error)) = otro {
                log::warn!("[voz] whisper residente no contestó ({error}): uso whisper-cli");
            }
            transcribir_con_cli(&config, &ruta_a_transcribir).map(|texto| {
                log::info!("[voz] whisper-cli: {} ms", arranque.elapsed().as_millis());
                texto
            })
        }
    };
    if let Some(trozo) = trozo_temporal {
        let _ = fs::remove_file(trozo);
    }
    let nuevo = texto?;
    let nuevo = nuevo.trim();
    let texto = unir(texto_confirmado, if es_solo_ruido(nuevo) { "" } else { nuevo });
    // Whisper cierra el silencio con «gracias». Si eso es todo el texto, no
    // se manda. Si solo cierra una frase y el audio calló al final, se quita
    // esa palabra. «gracias por el dato» no termina en gracias y se queda.
    let texto = match limpiar_gracias(&texto, silencio_al_final(ruta_wav)) {
        Some(limpio) => limpio,
        None => {
            log::info!("[voz] «gracias» de whisper, sin más frase: no lo mando");
            return Err("no se entendió nada de lo grabado".to_string());
        }
    };
    if texto.is_empty() {
        log::warn!("[voz] whisper solo devolvió ruido: {nuevo:?}");
        return Err("no se entendió nada de lo grabado".to_string());
    }
    if texto.chars().count() < LARGO_MINIMO_TRANSCRIPCION {
        log::warn!("[voz] transcripción de {} caracteres, la descarto: {texto:?}", texto.chars().count());
        return Err("no se entendió nada de lo grabado".to_string());
    }
    Ok(texto)
}

fn nucleo_de_palabra(palabra: &str) -> String {
    palabra
        .trim_matches(|c: char| {
            matches!(
                c,
                '.' | '!' | '¡' | '?' | '¿' | ',' | ';' | ':' | '…' | '"' | '\''
            )
        })
        .to_lowercase()
}

fn es_solo_gracias(texto: &str) -> bool {
    let mut palabras = texto.split_whitespace();
    match (palabras.next(), palabras.next()) {
        (Some(unica), None) => nucleo_de_palabra(unica) == "gracias",
        _ => false,
    }
}

fn termina_en_gracias(texto: &str) -> bool {
    texto
        .split_whitespace()
        .next_back()
        .is_some_and(|palabra| nucleo_de_palabra(palabra) == "gracias")
}

fn quitar_gracias_final(texto: &str) -> String {
    let recortado = texto.trim_end();
    match recortado.rfind(char::is_whitespace) {
        Some(corte) => recortado[..corte].trim_end().to_string(),
        None => String::new(),
    }
}

/// None: no se manda. Some: el texto que sí se manda.
fn limpiar_gracias(texto: &str, silencio_al_final: bool) -> Option<String> {
    if es_solo_gracias(texto) {
        return None;
    }
    if termina_en_gracias(texto) && silencio_al_final {
        let limpio = quitar_gracias_final(texto);
        if limpio.is_empty() {
            return None;
        }
        return Some(limpio);
    }
    Some(texto.to_string())
}

fn silencio_al_final(ruta_wav: &Path) -> bool {
    pico_reciente(ruta_wav).is_some_and(|pico| pico < UMBRAL_VOZ)
}

/// Lo confirmado y lo nuevo, con un espacio entre medio si hace falta.
fn unir(confirmado: &str, nuevo: &str) -> String {
    match (confirmado.trim(), nuevo.trim()) {
        ("", n) => n.to_string(),
        (c, "") => c.to_string(),
        (c, n) => format!("{c} {n}"),
    }
}

/// Un wav aparte con la cabecera dada y solo estas muestras, con los
/// tamaños RIFF/data arreglados. Quien lo pide lo borra.
fn escribir_trozo(cabecera: &[u8], datos: &[u8]) -> Result<PathBuf, String> {
    let mut bytes = Vec::with_capacity(cabecera.len() + datos.len());
    bytes.extend_from_slice(cabecera);
    bytes.extend_from_slice(datos);
    cabecera_completa(&mut bytes).ok_or("la cabecera del trozo no sirve")?;
    let ruta = ruta_temporal("-trozo.wav");
    fs::write(&ruta, &bytes).map_err(|e| e.to_string())?;
    Ok(ruta)
}

// — V1: el dictado no espera por lo ya dicho —
//
// Cada parcial mira lo que todavía no es definitivo (desde
// `bytes_confirmados`). Si ahí hay una pausa (nivel bajo el umbral durante
// PAUSA_PARA_CONFIRMAR) después de haber hablado, lo de antes de la pausa
// se transcribe una sola vez y queda confirmado; se corta EN LA MITAD de la
// pausa, nunca a mitad de palabra: así cada lado queda con ≥ 200 ms de
// silencio de margen — el trozo que termina no pierde su última «s» y el
// que empieza no arranca con la cola de un sonido ni pierde la primera
// sílaba. (Un solape de 300 ms, probado el 2/10, repetía la cola de la
// palabra anterior: «acces os».) Sin pausa, a los PENDIENTE_MAXIMO se corta
// en la mitad del hueco más largo que haya.
const VENTANA_CORTE: Duration = Duration::from_millis(100);
const PAUSA_PARA_CONFIRMAR: Duration = Duration::from_millis(400);
// Un trozo confirmado tiene al menos esto: a Whisper no se le dan pedacitos.
const TROZO_MINIMO: Duration = Duration::from_secs(1);
const PENDIENTE_MAXIMO: Duration = Duration::from_secs(12);

fn bytes_de(duracion: Duration) -> usize {
    (duracion.as_secs_f64() * BYTES_POR_SEGUNDO as f64) as usize
}

fn ventanas_de(duracion: Duration) -> usize {
    (duracion.as_millis() / VENTANA_CORTE.as_millis()) as usize
}

/// Pico (0.0–1.0) de cada ventana entera de VENTANA_CORTE.
fn niveles_por_ventana(datos: &[u8]) -> Vec<f32> {
    datos
        .chunks_exact(bytes_de(VENTANA_CORTE))
        .map(|ventana| {
            let pico = ventana
                .chunks_exact(2)
                .map(|par| i16::from_le_bytes([par[0], par[1]]).unsigned_abs())
                .max()
                .unwrap_or(0);
            pico as f32 / i16::MAX as f32
        })
        .collect()
}

// 3-oct: «gracias, gracias, gracias». Whisper alucina frases cortas
// («Gracias.», «¡Vamos!», «¿Qué?») con ruido o silencio, y desde V1 cada
// trozo de dictado se transcribe aparte: cada trozo de puro ruido (teclas,
// respiración) daba otra alucinación, y en la conversación entraba como un
// turno. Un trozo va a Whisper solo si tiene voz sostenida: al menos
// MIN_VENTANAS_DE_VOZ ventanas sobre el umbral, contadas solo en tramos de
// dos o más seguidas (una sílaba dura 0,2–0,3 s; un click de tecla, una).
const MIN_VENTANAS_DE_VOZ: usize = 3;

/// Cuántas ventanas de voz hay en tramos de al menos dos seguidas.
fn ventanas_de_voz(niveles: &[f32], umbral: f32) -> usize {
    let mut total = 0;
    let mut tramo = 0;
    for &nivel in niveles.iter().chain(std::iter::once(&0.0)) {
        if nivel >= umbral {
            tramo += 1;
        } else {
            if tramo >= 2 {
                total += tramo;
            }
            tramo = 0;
        }
    }
    total
}

fn hay_voz_sostenida(niveles: &[f32], umbral: f32) -> bool {
    ventanas_de_voz(niveles, umbral) >= MIN_VENTANAS_DE_VOZ
}

/// El tramo con voz de `datos`: desde MARGEN_DE_VOZ antes de la primera
/// ventana de voz sostenida hasta MARGEN_DE_VOZ después de la última. El
/// silencio de los bordes no va a Whisper: sobre la cola callada (los 1,4 s
/// que espera la conversación para cortar) inventaba palabras al final
/// («Gracias.»), que Juan Camilo no había dicho (3-oct).
const MARGEN_DE_VOZ: Duration = Duration::from_millis(300);

fn solo_la_voz(datos: &[u8], umbral: f32) -> &[u8] {
    let niveles = niveles_por_ventana(datos);
    let mut con_voz = vec![false; niveles.len()];
    let mut i = 0;
    while i < niveles.len() {
        if niveles[i] >= umbral {
            let inicio = i;
            while i < niveles.len() && niveles[i] >= umbral {
                i += 1;
            }
            if i - inicio >= 2 {
                con_voz[inicio..i].iter_mut().for_each(|v| *v = true);
            }
        } else {
            i += 1;
        }
    }
    let (Some(primera), Some(ultima)) = (con_voz.iter().position(|&v| v), con_voz.iter().rposition(|&v| v)) else {
        return datos;
    };
    let margen = ventanas_de(MARGEN_DE_VOZ);
    let ventana = bytes_de(VENTANA_CORTE);
    let desde = primera.saturating_sub(margen) * ventana;
    let hasta = ((ultima + 1 + margen) * ventana).min(datos.len());
    &datos[desde..hasta]
}

/// El umbral de toda la grabación (su piso), para medir un pedazo de ella.
fn umbral_de(datos: &[u8]) -> f32 {
    umbral_para(piso_de(&niveles_por_ventana(datos)).unwrap_or(0.0))
}

#[derive(Debug, PartialEq, Eq)]
struct Corte {
    // Cuántas ventanas del pendiente quedan confirmadas (el corte es al final
    // de la última; el trozo siguiente arranca justo ahí).
    ventanas: usize,
    // Si en ese trozo hubo voz. Sin voz no hay nada que transcribir: solo se
    // avanza.
    con_voz: bool,
}

/// Dónde cortar lo pendiente, o None si todavía no toca.
fn decidir_corte(niveles: &[f32]) -> Option<Corte> {
    let minimo = ventanas_de(TROZO_MINIMO);
    let pausa = ventanas_de(PAUSA_PARA_CONFIRMAR);
    let maximo = ventanas_de(PENDIENTE_MAXIMO);
    if niveles.len() < minimo + pausa {
        return None;
    }
    let piso = piso_de(niveles)?;
    let umbral = umbral_para(piso);
    let con_voz_hasta = |n: usize| hay_voz_sostenida(&niveles[..n], umbral);

    // Las rachas bajo el umbral: (inicio, largo), en orden.
    let mut rachas: Vec<(usize, usize)> = Vec::new();
    for (i, &nivel) in niveles.iter().enumerate() {
        if nivel >= umbral {
            continue;
        }
        match rachas.last_mut() {
            Some((inicio, largo)) if *inicio + *largo == i => *largo += 1,
            _ => rachas.push((i, 1)),
        }
    }
    // El corte es la mitad de la racha, y tiene que dejar TROZO_MINIMO antes.
    let mitad = |(inicio, largo): (usize, usize)| inicio + largo / 2;

    // La última pausa después de haber hablado.
    if let Some(racha) = rachas
        .iter()
        .copied()
        .filter(|&(inicio, largo)| largo >= pausa && mitad((inicio, largo)) >= minimo && con_voz_hasta(inicio))
        .next_back()
    {
        return Some(Corte { ventanas: mitad(racha), con_voz: true });
    }
    if niveles.len() < maximo {
        return None;
    }
    if !con_voz_hasta(niveles.len()) {
        // Doce segundos sin decir nada: no hay texto ahí, solo se avanza.
        return Some(Corte { ventanas: niveles.len(), con_voz: false });
    }
    // Sin pausa en doce segundos: la mitad del hueco más largo bajo el umbral
    // (aunque no llegue a pausa) es donde menos probable es partir una palabra.
    if let Some(racha) = rachas
        .iter()
        .copied()
        .filter(|&racha| mitad(racha) >= minimo)
        .max_by_key(|&(_, largo)| largo)
    {
        return Some(Corte { ventanas: mitad(racha), con_voz: true });
    }
    // Ni un hueco: la ventana más callada.
    let (mas_callada, _) = niveles
        .iter()
        .enumerate()
        .skip(minimo)
        .min_by(|a, b| a.1.total_cmp(b.1))?;
    Some(Corte { ventanas: mas_callada + 1, con_voz: true })
}

/// Lo que devuelve una parcial, y lo que queda confirmado después de ella.
struct Parcial {
    texto: String,
    bytes_confirmados: usize,
    texto_confirmado: String,
}

/// Una vuelta del dictado sobre `datos` (las muestras, sin cabecera): si hay
/// un trozo que confirmar, lo transcribe y lo deja definitivo; después
/// transcribe lo pendiente. Devuelve confirmado + pendiente.
fn avanzar_parcial(
    url: &str,
    cabecera: &[u8],
    datos: &[u8],
    bytes_confirmados: usize,
    texto_confirmado: &str,
) -> Result<Parcial, String> {
    let mut confirmados = bytes_confirmados.min(datos.len());
    let mut texto_confirmado = texto_confirmado.to_string();

    if let Some(corte) = decidir_corte(&niveles_por_ventana(&datos[confirmados..])) {
        let fin = confirmados + corte.ventanas * bytes_de(VENTANA_CORTE);
        if corte.con_voz {
            let arranque = Instant::now();
            let trozo = escribir_trozo(cabecera, solo_la_voz(&datos[confirmados..fin], umbral_de(datos)))?;
            let texto = transcribir_con_servidor(url, &trozo);
            let _ = fs::remove_file(&trozo);
            let texto = texto?;
            log::info!(
                "[voz] confirmado: trozo de {} ms transcrito en {} ms (total confirmado {} s)",
                ((fin - confirmados) as u64 * 1000) / BYTES_POR_SEGUNDO,
                arranque.elapsed().as_millis(),
                fin as u64 / BYTES_POR_SEGUNDO
            );
            if !es_solo_ruido(&texto) {
                texto_confirmado = unir(&texto_confirmado, &texto);
            }
        } else {
            log::info!("[voz] {} s sin voz: avanzo sin transcribir", (fin - confirmados) as u64 / BYTES_POR_SEGUNDO);
        }
        confirmados = fin;
    }

    let pendiente = &datos[confirmados..];
    let nuevo = if pendiente.len() < PARCIAL_MINIMO_BYTES
        || !hay_voz_sostenida(&niveles_por_ventana(pendiente), umbral_de(datos))
    {
        String::new()
    } else {
        let trozo = escribir_trozo(cabecera, solo_la_voz(pendiente, umbral_de(datos)))?;
        let texto = transcribir_con_servidor(url, &trozo);
        let _ = fs::remove_file(&trozo);
        let texto = texto?;
        if es_solo_ruido(&texto) { String::new() } else { texto }
    };
    Ok(Parcial {
        texto: unir(&texto_confirmado, &nuevo),
        bytes_confirmados: confirmados,
        texto_confirmado,
    })
}

// — Lo que vas diciendo, mientras lo decís (3c · 2) —
// Copia lo grabado hasta ahora, arregla la cabecera (ffmpeg la completa
// recién al cerrar) y lo manda al Whisper residente. Solo con el servidor:
// recargar el modelo cada 1,5 s con whisper-cli sería peor que no mostrar
// nada. Async: corre fuera del hilo de la ventana.
const PARCIAL_MINIMO_BYTES: usize = 16_000 * 2; // 1 s de audio a 16 kHz mono

#[tauri::command(async)]
pub fn transcribir_parcial(estado: tauri::State<'_, EstadoGrabacion>) -> Result<String, String> {
    let (ruta, bytes_confirmados, texto_confirmado) = {
        let guarda = estado.0.lock().map_err(|e| e.to_string())?;
        match guarda.as_ref() {
            Some(grabacion) => (
                grabacion.ruta_wav.clone(),
                grabacion.bytes_confirmados,
                grabacion.texto_confirmado.clone(),
            ),
            None => return Err("no hay grabación".to_string()),
        }
    };
    let config = leer_config_voz()?;
    let Some(url) = config.whisper_server_url.as_deref() else {
        return Err("sin whisper residente".to_string());
    };
    let mut bytes = fs::read(&ruta).map_err(|e| format!("no pude leer lo grabado: {e}"))?;
    let Some(inicio_datos) = cabecera_completa(&mut bytes) else {
        return Err("el wav todavía no tiene datos".to_string());
    };
    if bytes.len() - inicio_datos < PARCIAL_MINIMO_BYTES {
        return Err("muy poco audio todavía".to_string());
    }
    let (cabecera, datos) = bytes.split_at(inicio_datos);
    let parcial = avanzar_parcial(url, cabecera, datos, bytes_confirmados, &texto_confirmado)?;
    if parcial.bytes_confirmados != bytes_confirmados {
        // Solo si la grabación sigue siendo esta y nadie confirmó entre
        // medio (las parciales van de a una desde la ventanita).
        let mut guarda = estado.0.lock().map_err(|e| e.to_string())?;
        if let Some(grabacion) = guarda.as_mut() {
            if grabacion.ruta_wav == ruta && grabacion.bytes_confirmados == bytes_confirmados {
                grabacion.bytes_confirmados = parcial.bytes_confirmados;
                grabacion.texto_confirmado = parcial.texto_confirmado;
            }
        }
    }
    Ok(parcial.texto)
}

/// Arregla los tamaños RIFF y data de un wav a medio escribir. Devuelve dónde
/// empiezan las muestras, o None si todavía no está el trozo «data».
fn cabecera_completa(bytes: &mut [u8]) -> Option<usize> {
    if bytes.len() < 12 || &bytes[0..4] != b"RIFF" {
        return None;
    }
    let pos = bytes.windows(4).position(|v| v == b"data")?;
    let inicio = pos + 8;
    if bytes.len() < inicio {
        return None;
    }
    let riff = (bytes.len() - 8) as u32;
    let datos = (bytes.len() - inicio) as u32;
    bytes[4..8].copy_from_slice(&riff.to_le_bytes());
    bytes[pos + 4..pos + 8].copy_from_slice(&datos.to_le_bytes());
    Some(inicio)
}

// El modelo ya cargado en el agente com.remi.whisper: ~1 s por frase en vez
// de recargar 1,6 GB cada vez. Por curl, sin sumar un cliente HTTP a Rust.
fn transcribir_con_servidor(url: &str, ruta_wav: &Path) -> Result<String, String> {
    let salida = Command::new("/usr/bin/curl")
        .args(["-s", "-f", "--max-time", "60", "-F"])
        .arg(format!("file=@{}", ruta_wav.display()))
        .args(["-F", "response_format=text", "-F", "temperature=0.0"])
        .arg(format!("{}/inference", url.trim_end_matches('/')))
        .output()
        .map_err(|e| format!("no pude correr curl: {e}"))?;
    if !salida.status.success() {
        return Err(format!("curl salió con {}", salida.status));
    }
    // El servidor parte el texto en renglones por segmento: se unen.
    let texto = String::from_utf8_lossy(&salida.stdout)
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ");
    Ok(texto)
}

fn transcribir_con_cli(config: &ConfigVoz, ruta_wav: &Path) -> Result<String, String> {
    let base_salida = ruta_temporal("");

    let salida = Command::new(&config.whisper_cli_bin)
        .args([
            "-m",
            &config.modelo,
            "-l",
            &config.idioma,
            "-nt",
            "-np",
            // Los umbrales de no-voz de esta versión de whisper-cli:
            // -sns suprime los tokens que no son habla ([MÚSICA], [SILENCIO]…)
            // en el decodificador, en vez de dejarlos salir y filtrarlos
            // después; -nth baja de 0.6 a 0.5 el umbral a partir del cual un
            // segmento se toma por sin-voz. --vad queda fuera: pide un
            // modelo aparte que no está descargado.
            "-sns",
            "-nth",
            "0.5",
            "-otxt",
            "-of",
        ])
        .arg(&base_salida)
        .arg(ruta_wav)
        .output()
        .map_err(|e| format!("no pude correr whisper-cli: {e}"))?;

    if !salida.status.success() {
        return Err(format!(
            "whisper-cli falló: {}",
            String::from_utf8_lossy(&salida.stderr)
        ));
    }

    let ruta_txt = base_salida.with_extension("txt");
    let texto = fs::read_to_string(&ruta_txt).unwrap_or_default();
    let _ = fs::remove_file(&ruta_txt);
    Ok(texto)
}

#[cfg(test)]
mod pruebas {
    use super::*;

    // Un wav mínimo: cabecera de 44 bytes (el contenido de la cabecera no
    // importa para pico_reciente, que solo lee la cola) + muestras i16 LE.
    fn escribir_wav(nombre: &str, muestras: &[i16]) -> PathBuf {
        let ruta = std::env::temp_dir().join(format!("remi-prueba-{}-{nombre}.wav", std::process::id()));
        let mut bytes = vec![0u8; LARGO_CABECERA_WAV as usize];
        for m in muestras {
            bytes.extend_from_slice(&m.to_le_bytes());
        }
        fs::write(&ruta, bytes).unwrap();
        ruta
    }

    fn muestras_por_ventana() -> usize {
        (16_000.0 * VENTANA_SEGUNDOS) as usize
    }

    #[test]
    fn las_alucinaciones_de_whisper_son_ruido() {
        assert!(es_solo_ruido("¡Suscríbete al canal!"));
        assert!(es_solo_ruido(" Gracias por ver el video."));
        assert!(es_solo_ruido("Subtítulos realizados por la comunidad de Amara.org"));
        assert!(!es_solo_ruido("Gracias por ver el video de Alfonso, mandale el alcance"));
        assert!(!es_solo_ruido("dos cosas que"));
    }

    #[test]
    fn la_cabecera_de_un_wav_a_medio_escribir_se_arregla() {
        let mut bytes = b"RIFF\xff\xff\xff\xffWAVEfmt ".to_vec();
        bytes.extend_from_slice(&[0u8; 20]);
        bytes.extend_from_slice(b"LIST\x04\0\0\0abcd");
        bytes.extend_from_slice(b"data\xff\xff\xff\xff");
        bytes.extend_from_slice(&[1u8; 10]);
        let inicio = cabecera_completa(&mut bytes).unwrap();
        assert_eq!(bytes.len() - inicio, 10);
        assert_eq!(u32::from_le_bytes(bytes[4..8].try_into().unwrap()) as usize, bytes.len() - 8);
        let pos = inicio - 8;
        assert_eq!(u32::from_le_bytes(bytes[pos + 4..pos + 8].try_into().unwrap()), 10);
        assert_eq!(cabecera_completa(&mut b"RIFF".to_vec()), None);
    }

    #[test]
    fn sin_una_ventana_entera_no_hay_pico() {
        let ruta = escribir_wav("corto", &vec![0i16; muestras_por_ventana() / 2]);
        assert_eq!(pico_reciente(&ruta), None);
        let _ = fs::remove_file(ruta);
    }

    #[test]
    fn silencio_queda_bajo_el_umbral() {
        let ruta = escribir_wav("silencio", &vec![0i16; muestras_por_ventana() * 2]);
        let pico = pico_reciente(&ruta).unwrap();
        assert!(pico < UMBRAL_VOZ, "pico {pico}");
        let _ = fs::remove_file(ruta);
    }

    #[test]
    fn voz_al_final_pasa_el_umbral_aunque_antes_hubiera_silencio() {
        let n = muestras_por_ventana();
        let mut muestras = vec![0i16; n * 3];
        // Última ventana: una onda a ~10 % del máximo (una voz normal pica más).
        for (i, m) in muestras[n * 2..].iter_mut().enumerate() {
            *m = if i % 2 == 0 { 3300 } else { -3300 };
        }
        let ruta = escribir_wav("voz", &muestras);
        let pico = pico_reciente(&ruta).unwrap();
        assert!(pico >= UMBRAL_VOZ, "pico {pico}");
        let _ = fs::remove_file(ruta);
    }

    #[test]
    fn silencio_al_final_tras_voz_queda_bajo_el_umbral() {
        let n = muestras_por_ventana();
        let mut muestras = vec![3300i16; n * 2];
        for m in muestras[n..].iter_mut() {
            *m = 0;
        }
        let ruta = escribir_wav("voz-luego-silencio", &muestras);
        let pico = pico_reciente(&ruta).unwrap();
        assert!(pico < UMBRAL_VOZ, "pico {pico}");
        let _ = fs::remove_file(ruta);
    }

    #[test]
    fn la_duracion_sale_del_tamano_del_wav() {
        let n = muestras_por_ventana(); // 0.4 s
        let ruta = escribir_wav("duracion", &vec![0i16; n * 2]); // 0.8 s
        let duracion = duracion_del_wav(&ruta).unwrap();
        assert!((duracion.as_millis() as i64 - 800).abs() <= 1, "{duracion:?}");
        assert!(duracion >= DURACION_MINIMA);
        let _ = fs::remove_file(ruta);
    }

    #[test]
    fn el_umbral_se_adapta_al_piso_del_microfono() {
        // El RODE del 29/09: en silencio 0.03–0.08, hablando 0.24–0.68.
        let silencio = [0.045, 0.061, 0.038, 0.052, 0.080, 0.033, 0.049];
        let piso = piso_de(&silencio).unwrap();
        let umbral = umbral_para(piso);
        assert!((piso - 0.033).abs() < 1e-6);
        // Todo lo que fue silencio queda por debajo del umbral…
        assert!(silencio.iter().all(|&p| p < umbral), "umbral {umbral}");
        // …y la voz por encima.
        assert!(0.24 >= umbral && 0.68 >= umbral, "umbral {umbral}");
    }

    #[test]
    fn en_una_habitacion_callada_el_umbral_no_baja_del_piso_fijo() {
        assert_eq!(umbral_para(0.004), UMBRAL_VOZ);
        assert_eq!(piso_de(&[]), None);
    }

    #[test]
    fn si_empezas_hablando_el_umbral_no_sube_por_encima_de_tu_voz() {
        // Las primeras ventanas son todas voz (17:29): el piso «es» 0.20.
        let piso = piso_de(&[0.31, 0.24, 0.20, 0.45]).unwrap();
        let umbral = umbral_para(piso);
        assert_eq!(umbral, UMBRAL_MAXIMO);
        // Tu voz sigue siendo voz…
        assert!(0.24 >= umbral);
        // …y el silencio del RODE sigue siendo silencio.
        assert!(0.08 < umbral);
    }

    // — V1: dónde se corta el dictado —

    fn niveles(trozos: &[(usize, f32)]) -> Vec<f32> {
        trozos.iter().flat_map(|&(n, nivel)| std::iter::repeat_n(nivel, n)).collect()
    }

    #[test]
    fn con_una_pausa_despues_de_hablar_se_corta_en_la_mitad_de_la_pausa() {
        // 2 s de voz, 0,6 s de pausa, 1 s de voz, y sigue hablando.
        let n = niveles(&[(20, 0.4), (6, 0.03), (10, 0.5)]);
        let corte = decidir_corte(&n).unwrap();
        assert_eq!(corte, Corte { ventanas: 23, con_voz: true });
        // Dentro de la pausa, nunca en voz: a los dos lados del corte hay
        // silencio.
        let umbral = umbral_para(piso_de(&n).unwrap());
        assert!(n[corte.ventanas - 1] < umbral && n[corte.ventanas] < umbral);
    }

    #[test]
    fn se_corta_en_la_ultima_pausa_para_confirmar_lo_mas_posible() {
        let n = niveles(&[(20, 0.4), (5, 0.03), (20, 0.5), (4, 0.03), (3, 0.5)]);
        assert_eq!(decidir_corte(&n), Some(Corte { ventanas: 47, con_voz: true }));
    }

    #[test]
    fn una_pausa_corta_entre_palabras_no_corta() {
        // 3 s de voz con huecos de 200–300 ms: ninguno llega a 400 ms.
        let n = niveles(&[(10, 0.4), (3, 0.03), (10, 0.5), (2, 0.03), (10, 0.4)]);
        assert_eq!(decidir_corte(&n), None);
    }

    #[test]
    fn sin_pausa_a_los_doce_segundos_se_corta_en_la_mitad_del_hueco_mas_largo() {
        // Huecos de 200 y 300 ms (ninguno es pausa): se corta en la mitad
        // del de 300, nunca en voz.
        let n = niveles(&[(30, 0.4), (2, 0.03), (40, 0.4), (3, 0.03), (45, 0.4)]);
        assert_eq!(decidir_corte(&n), Some(Corte { ventanas: 73, con_voz: true }));
        let n = niveles(&[(30, 0.4), (2, 0.03), (90, 0.4)]);
        assert_eq!(decidir_corte(&n), Some(Corte { ventanas: 31, con_voz: true }));
        // Sin ningún hueco: la ventana más callada.
        let mut n = niveles(&[(120, 0.4)]);
        n[80] = 0.2;
        assert_eq!(decidir_corte(&n), Some(Corte { ventanas: 81, con_voz: true }));
        // Antes de los doce segundos, sin pausa, no toca.
        assert_eq!(decidir_corte(&niveles(&[(110, 0.4)])), None);
    }

    #[test]
    fn el_silencio_del_principio_no_se_confirma_y_doce_segundos_callado_solo_avanza() {
        // Todavía no hablaste: nada que transcribir.
        assert_eq!(decidir_corte(&niveles(&[(30, 0.03)])), None);
        assert_eq!(decidir_corte(&niveles(&[(120, 0.03)])), Some(Corte { ventanas: 120, con_voz: false }));
        // Silencio y después voz sin pausa: tampoco.
        assert_eq!(decidir_corte(&niveles(&[(20, 0.03), (20, 0.4)])), None);
    }

    #[test]
    fn con_menos_de_un_segundo_y_medio_no_se_decide_nada() {
        assert_eq!(decidir_corte(&niveles(&[(13, 0.4)])), None);
        assert_eq!(decidir_corte(&[]), None);
    }

    #[test]
    fn los_niveles_salen_por_ventana_de_cien_ms() {
        let por_ventana = bytes_de(VENTANA_CORTE);
        assert_eq!(por_ventana, 3200);
        let mut datos = vec![0u8; por_ventana * 2 + 10];
        datos[por_ventana + 4..por_ventana + 6].copy_from_slice(&3300i16.to_le_bytes());
        let n = niveles_por_ventana(&datos);
        assert_eq!(n.len(), 2);
        assert!(n[0] < 0.001 && (n[1] - 0.1).abs() < 0.01, "{n:?}");
    }

    #[test]
    fn un_trozo_es_un_wav_valido_con_sus_tamanos() {
        let mut cabecera = b"RIFF\0\0\0\0WAVEfmt ".to_vec();
        cabecera.extend_from_slice(&[0u8; 20]);
        cabecera.extend_from_slice(b"data\0\0\0\0");
        let ruta = escribir_trozo(&cabecera, &[7u8; 100]).unwrap();
        let bytes = fs::read(&ruta).unwrap();
        let _ = fs::remove_file(&ruta);
        assert_eq!(bytes.len(), cabecera.len() + 100);
        assert_eq!(u32::from_le_bytes(bytes[4..8].try_into().unwrap()) as usize, bytes.len() - 8);
        let pos = cabecera.len() - 8;
        assert_eq!(u32::from_le_bytes(bytes[pos + 4..pos + 8].try_into().unwrap()), 100);
        assert_eq!(unir("", "hola"), "hola");
        assert_eq!(unir("hola", ""), "hola");
        assert_eq!(unir("hola", " qué tal "), "hola qué tal");
    }

    /// Medición del «listo cuando» de V1 sobre un clip real, contra el
    /// Whisper residente (no corre sola: pide el servidor y un wav de 16 kHz
    /// mono). Simula el dictado creciendo de a 1,5 s, como hace la ventanita,
    /// y al final transcribe solo lo que quedó, como la parada. Imprime los
    /// tiempos y las dos transcripciones (entera vs por trozos) para
    /// compararlas a ojo.
    ///
    ///   REMI_CLIP_WAV=/ruta/clip.wav REMI_WHISPER_URL=http://127.0.0.1:4401 \
    ///   cargo test --quiet medir_dictado_largo -- --ignored --nocapture
    #[test]
    #[ignore]
    fn medir_dictado_largo() {
        let ruta = PathBuf::from(std::env::var("REMI_CLIP_WAV").expect("REMI_CLIP_WAV"));
        let url = std::env::var("REMI_WHISPER_URL").unwrap_or_else(|_| "http://127.0.0.1:4401".to_string());
        let mut bytes = fs::read(&ruta).unwrap();
        let inicio_datos = cabecera_completa(&mut bytes).unwrap();
        let (cabecera, datos) = bytes.split_at(inicio_datos);
        let segundos = datos.len() as f64 / BYTES_POR_SEGUNDO as f64;
        println!("clip de {segundos:.1} s");

        // Hoy: todo el archivo de una vez al parar.
        let arranque = Instant::now();
        let entera = transcribir_con_servidor(&url, &ruta).unwrap();
        println!("entera al parar: {} ms", arranque.elapsed().as_millis());

        // V1: parciales cada 1,5 s de audio, y al parar solo el resto.
        let paso = bytes_de(Duration::from_millis(1500));
        let mut confirmados = 0usize;
        let mut texto_confirmado = String::new();
        let mut hasta = paso;
        let mut parciales_ms = Vec::new();
        while hasta < datos.len() {
            let arranque = Instant::now();
            let parcial = avanzar_parcial(&url, cabecera, &datos[..hasta], confirmados, &texto_confirmado).unwrap();
            parciales_ms.push(arranque.elapsed().as_millis());
            confirmados = parcial.bytes_confirmados;
            texto_confirmado = parcial.texto_confirmado;
            hasta += paso;
        }
        let trozo = escribir_trozo(cabecera, &datos[confirmados..]).unwrap();
        let arranque = Instant::now();
        let ultimo = transcribir_con_servidor(&url, &trozo).unwrap();
        let ultimo_ms = arranque.elapsed().as_millis();
        let _ = fs::remove_file(&trozo);
        let por_trozos = unir(&texto_confirmado, if es_solo_ruido(&ultimo) { "" } else { &ultimo });
        println!(
            "por trozos: confirmados {:.1} s antes de parar; último trozo de {:.1} s en {} ms; parciales máx {} ms, mediana {} ms",
            confirmados as f64 / BYTES_POR_SEGUNDO as f64,
            (datos.len() - confirmados) as f64 / BYTES_POR_SEGUNDO as f64,
            ultimo_ms,
            parciales_ms.iter().max().unwrap_or(&0),
            { let mut v = parciales_ms.clone(); v.sort(); v.get(v.len() / 2).copied().unwrap_or(0) }
        );
        println!("\n— entera —\n{entera}\n\n— por trozos —\n{por_trozos}\n");
        assert!(ultimo_ms < 1500, "el último trozo tardó {ultimo_ms} ms");
    }

    #[test]
    fn gracias_de_whisper_se_quita_si_el_audio_callo_y_no_se_manda_si_es_todo() {
        assert_eq!(
            limpiar_gracias("seguimos con eso gracias.", true).as_deref(),
            Some("seguimos con eso")
        );
        assert_eq!(limpiar_gracias("¡Gracias!", false), None);
        assert_eq!(limpiar_gracias("Gracias.", true), None);
        assert_eq!(
            limpiar_gracias("gracias por el dato", true).as_deref(),
            Some("gracias por el dato")
        );
        assert_eq!(limpiar_gracias("hola gracias", false).as_deref(), Some("hola gracias"));
        assert_eq!(limpiar_gracias("hola. ¡Gracias!", true).as_deref(), Some("hola."));
    }

    #[test]
    fn el_silencio_del_final_se_lee_del_wav() {
        let callado = escribir_wav("gracias-callado", &vec![0i16; muestras_por_ventana() * 2]);
        assert!(silencio_al_final(&callado));
        let _ = fs::remove_file(callado);

        let n = muestras_por_ventana();
        let mut muestras = vec![0i16; n * 2];
        for (i, muestra) in muestras[n..].iter_mut().enumerate() {
            *muestra = if i % 2 == 0 { 3300 } else { -3300 };
        }
        let hablando = escribir_wav("gracias-hablando", &muestras);
        assert!(!silencio_al_final(&hablando));
        let _ = fs::remove_file(hablando);
    }

    // — 3-oct: «gracias, gracias, gracias» —
    // Whisper alucina frases cortas («Gracias.», «¡Vamos!») con ruido o
    // silencio. Un trozo va a Whisper solo si tiene voz sostenida.

    #[test]
    fn clicks_de_teclado_sueltos_no_son_voz() {
        // Una ventana alta cada tanto (teclas): nunca dos seguidas.
        let mut n = niveles(&[(40, 0.03)]);
        for i in (2..40).step_by(4) {
            n[i] = 0.6;
        }
        assert_eq!(ventanas_de_voz(&n, 0.1), 0);
        assert!(!hay_voz_sostenida(&n, 0.1));
    }

    #[test]
    fn una_palabra_corta_si_es_voz() {
        // «Gracias» dicha de verdad: ~0,4 s seguidos.
        let n = niveles(&[(10, 0.03), (4, 0.4), (10, 0.03)]);
        assert_eq!(ventanas_de_voz(&n, 0.1), 4);
        assert!(hay_voz_sostenida(&n, 0.1));
    }

    #[test]
    fn un_respiro_de_dos_ventanas_no_alcanza() {
        let n = niveles(&[(10, 0.03), (2, 0.2), (10, 0.03)]);
        assert!(!hay_voz_sostenida(&n, 0.1));
    }

    #[test]
    fn un_trozo_sin_voz_sostenida_no_se_confirma_como_voz() {
        // Doce segundos de teclas: se avanza sin transcribir.
        let mut n = niveles(&[(120, 0.03)]);
        for i in (1..120).step_by(5) {
            n[i] = 0.5;
        }
        assert_eq!(decidir_corte(&n), Some(Corte { ventanas: 120, con_voz: false }));
    }

    #[test]
    fn a_whisper_va_la_voz_sin_los_bordes_callados() {
        // 1 s callado, 1 s de voz, 1,5 s callado (la espera de la conversación).
        let ventana = bytes_de(VENTANA_CORTE);
        let mut datos = Vec::new();
        for (n, nivel) in [(10usize, 300i16), (10, 12000), (15, 300)] {
            for _ in 0..n * ventana / 2 {
                datos.extend_from_slice(&nivel.to_le_bytes());
            }
        }
        let voz = solo_la_voz(&datos, umbral_de(&datos));
        // La voz más 0,3 s de cada lado: 1,6 s, no 3,5.
        assert_eq!(voz.len(), 16 * ventana);
        // Sin voz sostenida, se deja todo (lo decide hay_voz_sostenida).
        let callado = vec![0u8; 20 * ventana];
        assert_eq!(solo_la_voz(&callado, 0.1).len(), callado.len());
    }

    #[test]
    fn whisper_solo_ruido_se_detecta() {
        assert!(es_solo_ruido("[Música]"));
        assert!(es_solo_ruido(" (silencio). "));
        assert!(es_solo_ruido(""));
        assert!(!es_solo_ruido("Llamar al banco"));
    }
}
