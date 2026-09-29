//! Micrófono real, reemplaza a Handy: graba con ffmpeg (avfoundation) y
//! transcribe con whisper.cpp (Homebrew), reusando un modelo que Handy
//! ya tenía descargado. Nada de esto sale del Mac.
use std::fs;
use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStderr, Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use serde::Deserialize;
use tauri::{AppHandle, Emitter};

// Si ffmpeg muere antes de esto, fue un fallo real (permiso de
// micrófono negado, dispositivo inválido, etc.) — no lo tomamos como
// "ya está grabando".
const ESPERA_CONFIRMAR_ARRANQUE: Duration = Duration::from_millis(400);

// El wav que graba ffmpeg: 16 kHz, mono, 16 bits.
const BYTES_POR_SEGUNDO: u64 = 16_000 * 2;
// Cada cuánto miramos cómo viene el audio.
const PASO_VIGILANCIA: Duration = Duration::from_millis(250);
// Ventana que miramos en cada paso.
const VENTANA_SEGUNDOS: f64 = 0.4;
// Por encima de esto hay voz (sobre 1.0 = máximo del micrófono).
const UMBRAL_VOZ: f32 = 0.02;
// Cuánto silencio seguido, después de hablar, cuenta como "ya terminaste".
const SILENCIO_PARA_CORTAR: Duration = Duration::from_millis(1200);

// La ventanita escucha este evento para cortar sola la grabación.
pub const EVENTO_SILENCIO: &str = "voz://silencio";

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

#[derive(Default)]
pub struct EstadoGrabacion(Mutex<Option<(Child, PathBuf)>>);

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
    let mut archivo = fs::File::open(ruta_wav).ok()?;
    let largo = archivo.metadata().ok()?.len();
    let ventana = (BYTES_POR_SEGUNDO as f64 * VENTANA_SEGUNDOS) as u64;
    if largo < ventana + 44 {
        return None;
    }

    use std::io::{Seek, SeekFrom};
    archivo.seek(SeekFrom::Start(largo - ventana)).ok()?;
    let mut crudo = vec![0u8; ventana as usize];
    archivo.read_exact(&mut crudo).ok()?;

    let pico = crudo
        .chunks_exact(2)
        .map(|par| i16::from_le_bytes([par[0], par[1]]).unsigned_abs())
        .max()
        .unwrap_or(0);
    Some(pico as f32 / i16::MAX as f32)
}

// Avisa a la ventanita cuando dejaste de hablar, para cortar sola.
fn vigilar_silencio(ruta_wav: PathBuf, app: AppHandle) {
    thread::spawn(move || {
        let mut hubo_voz = false;
        let mut callado = Duration::ZERO;

        loop {
            thread::sleep(PASO_VIGILANCIA);
            let Some(pico) = pico_reciente(&ruta_wav) else {
                // El archivo dejó de crecer: la grabación ya terminó.
                if !ruta_wav.exists() {
                    return;
                }
                continue;
            };

            if pico >= UMBRAL_VOZ {
                hubo_voz = true;
                callado = Duration::ZERO;
                continue;
            }

            if !hubo_voz {
                continue;
            }

            callado += PASO_VIGILANCIA;
            if callado >= SILENCIO_PARA_CORTAR {
                eprintln!("[voz] dejaste de hablar (pico {pico:.3}) → corto sola");
                let _ = app.emit(EVENTO_SILENCIO, ());
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
    eprintln!(
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
        eprintln!("[voz] {detalle}");
        eprintln!("[voz] stderr completo:\n{error}");
        return Err(detalle);
    }

    if let Some(stderr) = hijo.stderr.take() {
        drenar_stderr(stderr);
    }
    if cortar_solo {
        vigilar_silencio(ruta_wav.clone(), app.clone());
    }

    *guarda = Some((hijo, ruta_wav));
    Ok(())
}

#[tauri::command]
pub fn detener_escucha_y_transcribir(estado: tauri::State<EstadoGrabacion>) -> Result<String, String> {
    let (mut hijo, ruta_wav) = estado
        .0
        .lock()
        .map_err(|e| e.to_string())?
        .take()
        .ok_or_else(|| "no había ninguna grabación activa".to_string())?;

    // ffmpeg cierra el archivo prolijo si le mandamos 'q' por stdin,
    // en vez de matarlo (eso deja el wav a medio escribir).
    if let Some(mut entrada) = hijo.stdin.take() {
        let _ = entrada.write_all(b"q");
    }
    let _ = hijo.wait();

    let resultado = transcribir(&ruta_wav);
    let _ = fs::remove_file(&ruta_wav);
    resultado
}

// Una voz normal pica bien por encima de esto; si no llega, el micrófono
// no escuchó nada (silenciado, volumen de entrada bajo, o mal dispositivo).
const PICO_MINIMO_DB: f32 = -42.0;

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

    if let Some(pico) = pico_db(&config.ffmpeg_bin, ruta_wav) {
        eprintln!("[voz] pico del audio: {pico} dB");
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
        eprintln!("[voz] whisper solo devolvió ruido: {texto:?}");
        return Err("no se entendió nada de lo grabado".to_string());
    }
    Ok(texto)
}
