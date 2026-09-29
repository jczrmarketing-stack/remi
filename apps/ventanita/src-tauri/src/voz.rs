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
use std::time::Duration;

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
const SILENCIO_PARA_CORTAR: Duration = Duration::from_millis(1200);
// Si en todo este tiempo no dijiste nada, Remi deja de esperar (en diálogo
// no hay cuadro para escribir: sin esto quedaba grabando para siempre).
const SIN_VOZ_MAXIMO: Duration = Duration::from_secs(10);

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

            let pico = match pico_reciente_o_motivo(&ruta_wav) {
                Ok(pico) => pico,
                Err(motivo) => {
                    if !ruta_wav.exists() {
                        log::info!("[voz] vigilancia termina: el wav ya no está");
                        return;
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
                log::info!("[voz] dejaste de hablar (pico {pico:.3}) → corto sola");
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
    )
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

/// `origen` dice QUIÉN cortó: "click", "silencio:fin", "silencio:sin_voz",
/// "escape" o "timeout". Lo sabe la ventanita, no acá, y sin eso el log no
/// alcanza para entender un gesto que salió mal.
#[tauri::command]
pub fn detener_escucha_y_transcribir(
    estado: tauri::State<EstadoGrabacion>,
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
    let ruta_wav = grabacion.detener();
    let resultado = transcribir(&ruta_wav);
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

fn transcribir(ruta_wav: &Path) -> Result<String, String> {
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

    let texto = texto.trim().to_string();
    if es_solo_ruido(&texto) {
        log::warn!("[voz] whisper solo devolvió ruido: {texto:?}");
        return Err("no se entendió nada de lo grabado".to_string());
    }
    if texto.chars().count() < LARGO_MINIMO_TRANSCRIPCION {
        log::warn!("[voz] transcripción de {} caracteres, la descarto: {texto:?}", texto.chars().count());
        return Err("no se entendió nada de lo grabado".to_string());
    }
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

    #[test]
    fn whisper_solo_ruido_se_detecta() {
        assert!(es_solo_ruido("[Música]"));
        assert!(es_solo_ruido(" (silencio). "));
        assert!(es_solo_ruido(""));
        assert!(!es_solo_ruido("Llamar al banco"));
    }
}
