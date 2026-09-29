//! Micrófono real, reemplaza a Handy: graba con ffmpeg (avfoundation) y
//! transcribe con whisper.cpp (Homebrew), reusando un modelo que Handy
//! ya tenía descargado. Nada de esto sale del Mac.
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

use serde::Deserialize;

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

fn ruta_temporal(sufijo: &str) -> PathBuf {
    std::env::temp_dir().join(format!("remi-voz-{}{}", std::process::id(), sufijo))
}

#[tauri::command]
pub fn iniciar_escucha(estado: tauri::State<EstadoGrabacion>) -> Result<(), String> {
    let config = leer_config_voz()?;
    let mut guarda = estado.0.lock().map_err(|e| e.to_string())?;
    if guarda.is_some() {
        return Err("ya había una grabación activa".to_string());
    }

    let ruta_wav = ruta_temporal(".wav");
    let hijo = Command::new(&config.ffmpeg_bin)
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
        .arg(&ruta_wav)
        .stdin(Stdio::piped())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("no pude arrancar ffmpeg: {e}"))?;

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

fn transcribir(ruta_wav: &Path) -> Result<String, String> {
    let config = leer_config_voz()?;
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
    Ok(texto.trim().to_string())
}
