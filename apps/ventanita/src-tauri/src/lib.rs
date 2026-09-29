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
                eprintln!("config/ventanita.json inválido, uso el atajo por defecto");
                ATAJO_POR_DEFECTO.to_string()
            }
        },
        Err(_) => {
            eprintln!("no encontré {}, uso el atajo por defecto", ruta.display());
            ATAJO_POR_DEFECTO.to_string()
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let atajo_configurado = leer_atajo();

    tauri::Builder::default()
        .manage(EstadoGrabacion::default())
        .invoke_handler(tauri::generate_handler![
            voz::iniciar_escucha,
            voz::detener_escucha_y_transcribir
        ])
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
