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

**Access antes del túnel — nunca al revés.** `scripts/tunel.sh` (LaunchAgent
`com.remi.tunel`) publica el panel en `remi.inv3rza.com` sin pedir nada por su cuenta: si
no hay Access delante, cualquiera que encuentre el dominio ve el panel entero (tareas,
Bandeja, plata, llaves parciales). Por eso el orden es:

1. En el dashboard de Cloudflare (Zero Trust → Access → Applications), armar una
   aplicación para `remi.inv3rza.com` con la regla de acceso (solo tu email, o lo que
   decidas) **antes** de correr `tunel.sh` por primera vez. Esto lo hace Juan Camilo a
   mano — no es un paso de instalación automática.
2. Recién ahí, `./scripts/tunel.sh` (o confirmar que el LaunchAgent ya está arriba:
   `launchctl list | grep com.remi.tunel`).
3. `./scripts/doctor.sh` tiene que decir `OK panel`. Si dice que el panel está público, Access
   no quedó bien puesto — no uses el link hasta que `doctor.sh` esté en verde.
4. Desde Safari en el iPhone, abrí `https://remi.inv3rza.com` (pide el login de Access la
   primera vez).
5. Tocá **Compartir** → **Agregar a pantalla de inicio**.
6. Abrí el ícono nuevo y confirmá que el panel carga (si pide login de más o tarda, revisá
   `~/Library/Logs/Remi/tunel.log` en el Mac).
