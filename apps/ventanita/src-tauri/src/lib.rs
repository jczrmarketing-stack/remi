use std::fs;
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::{Duration, Instant};

use serde::Deserialize;
use tauri::{Emitter, Manager};
use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, ShortcutState};

mod voz;
use voz::EstadoGrabacion;

// Cmd+Shift+R colisiona con "recargar ignorando caché" del navegador y,
// siendo un atajo GLOBAL, lo captura en todo el sistema. Este es el
// respaldo si config/ventanita.json falta o no se puede leer.
const ATAJO_POR_DEFECTO: &str = "CmdOrCtrl+Alt+Shift+L";
// La palanca de dictado. Control+Option+Space parecía libre, pero macOS lo
// captura antes que nadie para «Seleccionar la siguiente fuente de
// entrada»: registrar() no falla y la pulsación nunca llega. R no tiene
// conflicto conocido. Se puede cambiar en config/ventanita.json.
const ATAJO_DICTADO_POR_DEFECTO: &str = "Control+Alt+R";
// Una tecla mantenida repite: dos pulsos en menos de esto son uno.
const ANTIRREBOTE_PALANCA: Duration = Duration::from_millis(300);
// Lo que la ventanita escucha cuando cae la palanca.
const EVENTO_PALANCA: &str = "gesto://palanca";

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
    #[serde(default)]
    atajo_dictado: Option<String>,
}

struct Atajos {
    mostrar_ocultar: String,
    dictado: String,
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

fn leer_atajos() -> Atajos {
    let por_defecto = Atajos {
        mostrar_ocultar: ATAJO_POR_DEFECTO.to_string(),
        dictado: ATAJO_DICTADO_POR_DEFECTO.to_string(),
    };
    let ruta = ruta_config();
    match fs::read_to_string(&ruta) {
        Ok(contenido) => match serde_json::from_str::<ConfigVentanita>(&contenido) {
            Ok(config) => Atajos {
                mostrar_ocultar: config.atajo_mostrar_ocultar,
                dictado: config
                    .atajo_dictado
                    .unwrap_or_else(|| ATAJO_DICTADO_POR_DEFECTO.to_string()),
            },
            Err(_) => {
                log::warn!("config/ventanita.json inválido, uso los atajos por defecto");
                por_defecto
            }
        },
        Err(_) => {
            log::warn!("no encontré {}, uso los atajos por defecto", ruta.display());
            por_defecto
        }
    }
}

// Último pulso de la palanca, para el antirrebote.
struct UltimaPalanca(Mutex<Option<Instant>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let atajos = leer_atajos();
    let atajo_dictado: Shortcut = atajos.dictado.parse().unwrap_or_else(|_| {
        log::warn!("atajo_dictado inválido ({}), uso {ATAJO_DICTADO_POR_DEFECTO}", atajos.dictado);
        ATAJO_DICTADO_POR_DEFECTO
            .parse()
            .expect("atajo de dictado por defecto inválido")
    });
    let atajo_mostrar: Shortcut = atajos.mostrar_ocultar.parse().unwrap_or_else(|_| {
        log::warn!("atajo_mostrar_ocultar inválido ({}), uso {ATAJO_POR_DEFECTO}", atajos.mostrar_ocultar);
        ATAJO_POR_DEFECTO.parse().expect("atajo por defecto inválido")
    });
    let palanca_para_handler = atajo_dictado;

    tauri::Builder::default()
        .manage(UltimaPalanca(Mutex::new(None)))
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
            voz::cancelar_escucha,
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
                .with_handler(move |app, atajo, event| {
                    let es_palanca = *atajo == palanca_para_handler;
                    // Cada evento de la palanca queda escrito, también el
                    // soltar: si no aparece NINGUNO, la combinación no está
                    // llegando a la app (macOS o alguien la captura antes).
                    if es_palanca && event.state() == ShortcutState::Released {
                        log::info!("[palanca] soltada");
                        return;
                    }
                    if event.state() != ShortcutState::Pressed {
                        return;
                    }
                    let Some(ventana) = app.get_webview_window("main") else {
                        log::warn!("[palanca] pulsada, pero no encuentro la ventana");
                        return;
                    };

                    // — La palanca de dictado —
                    if es_palanca {
                        let ahora = Instant::now();
                        let ultima = app.state::<UltimaPalanca>();
                        if let Ok(mut guarda) = ultima.0.lock() {
                            if let Some(anterior) = *guarda {
                                let hace = ahora.duration_since(anterior);
                                if hace < ANTIRREBOTE_PALANCA {
                                    log::info!(
                                        "[palanca] pulsada a los {} ms de la anterior: rebote, ignorada",
                                        hace.as_millis()
                                    );
                                    return;
                                }
                            }
                            *guarda = Some(ahora);
                        }
                        // Si estaba oculta, que se vea — sin robarle el foco
                        // a la app en la que estás: la palanca es para
                        // dictar sin dejar de trabajar.
                        if !ventana.is_visible().unwrap_or(true) {
                            let _ = ventana.show();
                            log::info!("[palanca] la ventana estaba oculta: la muestro");
                        }
                        log::info!("[palanca] pulsada");
                        let _ = app.emit(EVENTO_PALANCA, ());
                        return;
                    }

                    // — Mostrar / ocultar —
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
            app.global_shortcut().register(atajo_mostrar)?;
            // Registrar la palanca no puede tirar la app: sin ella Remi
            // sigue andando con los clicks. Pero tiene que quedar escrito.
            match app.global_shortcut().register(atajo_dictado) {
                Ok(()) => {
                    // La API no sabe si macOS se queda con la combinación
                    // (register() acepta Control+Option+Space y después la
                    // pulsación nunca llega): lo único comprobable es que
                    // quedó registrada de nuestro lado. El conflicto se ve
                    // por ausencia: cero líneas «pulsada» tras apretarla.
                    let confirmado = app
                        .global_shortcut()
                        .is_registered(atajo_dictado);
                    log::info!(
                        "[palanca] atajo de dictado registrado: {} (is_registered={confirmado}; \
                         si al apretarlo no aparece «pulsada», lo captura el sistema)",
                        atajos.dictado
                    );
                }
                Err(error) => {
                    log::error!(
                        "[palanca] NO pude registrar {}: {error}. Remi anda solo con clicks",
                        atajos.dictado
                    );
                }
            }
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
