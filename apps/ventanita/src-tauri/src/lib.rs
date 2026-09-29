use tauri::Manager;
use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, ShortcutState};

// Atajo global para ocultar/mostrar la ventanita: sin barra de título ni
// ícono en el Dock (skipTaskbar), esta es la única forma de recuperarla.
const ATAJO_MOSTRAR_OCULTAR: &str = "CmdOrCtrl+Shift+R";

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
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
        .setup(|app| {
            let atajo: Shortcut = ATAJO_MOSTRAR_OCULTAR.parse()?;
            app.global_shortcut().register(atajo)?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
