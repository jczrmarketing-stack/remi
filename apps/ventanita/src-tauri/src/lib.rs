use std::fs;
use std::path::PathBuf;

use serde::Deserialize;
use tauri::Manager;
use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, ShortcutState};

mod voz;
use voz::EstadoGrabacion;

// Cmd+Shift+R colisiona con "recargar ignorando caché" del navegador y,
// siendo un atajo GLOBAL, lo captura en todo el sistema. Este es el
// respaldo si config/ventanita.json falta o no se puede leer.
const ATAJO_POR_DEFECTO: &str = "CmdOrCtrl+Alt+Shift+L";

// El log vive donde macOS espera los logs, al lado del del núcleo, para
// poder leer los dos juntos cuando algo no se entiende.
const CARPETA_LOGS: &str = "Library/Logs/Remi";
const ARCHIVO_LOG: &str = "ventanita";
// Un log que llena el disco es peor que no tener log. Al pasarse, guarda
// uno viejo y empieza de nuevo.
const MAX_BYTES_LOG: u128 = 5 * 1024 * 1024;

fn carpeta_de_logs() -> PathBuf {
    let casa = std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string());
    PathBuf::from(casa).join(CARPETA_LOGS)
}

#[derive(Deserialize)]
struct ConfigVentanita {
    atajo_mostrar_ocultar: String,
}

// config/ventanita.json vive en la raíz del repo, fuera de src-tauri, para
// poder cambiar el atajo sin recompilar (solo hace falta relanzar la app).
fn ruta_config() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("..")
        .join("config")
        .join("ventanita.json")
}

fn leer_atajo() -> String {
    let ruta = ruta_config();
    match fs::read_to_string(&ruta) {
        Ok(contenido) => match serde_json::from_str::<ConfigVentanita>(&contenido) {
            Ok(config) => config.atajo_mostrar_ocultar,
            Err(_) => {
                log::warn!("config/ventanita.json inválido, uso el atajo por defecto");
                ATAJO_POR_DEFECTO.to_string()
            }
        },
        Err(_) => {
            log::warn!("no encontré {}, uso el atajo por defecto", ruta.display());
            ATAJO_POR_DEFECTO.to_string()
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let atajo_configurado = leer_atajo();

    tauri::Builder::default()
        // Una sola Remi. Abrirla estando ya abierta no crea otra ventana:
        // trae la que hay y le da el foco. Antes había que adivinar si
        // estaba corriendo, y dos instancias se peleaban el micrófono.
        .plugin(tauri_plugin_single_instance::init(|app, _argumentos, _carpeta| {
            let Some(ventana) = app.get_webview_window("main") else {
                return;
            };
            let _ = ventana.show();
            let _ = ventana.unminimize();
            let _ = ventana.set_focus();
        }))
        .manage(EstadoGrabacion::default())
        .invoke_handler(tauri::generate_handler![
            voz::iniciar_escucha,
            voz::activar_corte_por_silencio,
            voz::detener_escucha_y_transcribir
        ])
        // Todo a un archivo: los `log::info!` de Rust y, desde el otro
        // lado, la consola del webview (ver src/registro.ts). Sin esto, lo
        // que pasa con la app instalada no se ve en ninguna parte: no hay
        // terminal donde mirar.
        .plugin(
            tauri_plugin_log::Builder::new()
                .clear_targets()
                .target(tauri_plugin_log::Target::new(
                    tauri_plugin_log::TargetKind::Folder {
                        path: carpeta_de_logs(),
                        file_name: Some(ARCHIVO_LOG.to_string()),
                    },
                ))
                // Hora con milisegundos: para entender un gesto hace falta
                // ver el orden y la distancia entre dos eventos, no el
                // segundo en que cayeron.
                .format(|salida, mensaje, registro| {
                    salida.finish(format_args!(
                        "{} [{}] {}",
                        chrono::Local::now().format("%H:%M:%S%.3f"),
                        registro.level(),
                        mensaje
                    ))
                })
                .max_file_size(MAX_BYTES_LOG)
                .rotation_strategy(tauri_plugin_log::RotationStrategy::KeepOne)
                .level(log::LevelFilter::Info)
                .build(),
        )
        .plugin(tauri_plugin_opener::init())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(|app, _shortcut, event| {
                    if event.state() != ShortcutState::Pressed {
                        return;
                    }
                    let Some(ventana) = app.get_webview_window("main") else {
                        return;
                    };
                    let visible = ventana.is_visible().unwrap_or(true);
                    if visible {
                        let _ = ventana.hide();
                    } else {
                        let _ = ventana.show();
                        let _ = ventana.set_focus();
                    }
                })
                .build(),
        )
        .setup(move |app| {
            let atajo: Shortcut = atajo_configurado
                .parse()
                .unwrap_or_else(|_| ATAJO_POR_DEFECTO.parse().expect("atajo por defecto inválido"));
            app.global_shortcut().register(atajo)?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, evento| {
            // Si la app cierra con el micrófono grabando, no dejar a ffmpeg
            // huérfano: ya pasó, se quedó grabando 50+ minutos y le ganaba
            // el dispositivo a la siguiente grabación.
            if matches!(
                evento,
                tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit
            ) {
                app_handle.state::<EstadoGrabacion>().matar_si_hay_grabacion();
            }
        });
}
