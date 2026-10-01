# Instalar Remi

```bash
./scripts/instalar.sh      # el núcleo como servicio + Remi abre sola al iniciar sesión
./scripts/actualizar.sh    # compila, reemplaza /Applications/Remi.app y recarga todo
tail -f ~/Library/Logs/Remi/nucleo.log   # qué pensó, qué guardó, si la voz quedó lista
./scripts/desinstalar.sh   # baja los agentes y borra la app (nunca toca nucleo/remi.db)
```

**Si tocás código y no cambia nada: corré `./scripts/actualizar.sh`.** Ya no es `tauri dev`
— la Remi que se abre es la de `/Applications`, y esa solo cambia cuando la recompilás.

## Mapa de puertos

| Puerto | Qué es |
|---|---|
| 4400 | núcleo (FastAPI) |
| 4401 | whisper-server (voz, residente) |
| 4402 | panel |
| 3000–3009 | reservados |

## Panel en el teléfono

El túnel (`scripts/tunel.sh`, LaunchAgent `com.remi.tunel`) publica el panel en
`remi.inv3rza.com`. Una vez que esté arriba (`launchctl list | grep com.remi.tunel`):

1. Desde Safari en el iPhone, abrí `https://remi.inv3rza.com`.
2. Tocá **Compartir** → **Agregar a pantalla de inicio**.
3. Abrí el ícono nuevo y confirmá que el panel carga (si pide login o tarda, revisá
   `~/Library/Logs/Remi/tunel.log` en el Mac).
