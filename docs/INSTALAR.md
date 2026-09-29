# Instalar Remi

```bash
./scripts/instalar.sh      # el núcleo como servicio + Remi abre sola al iniciar sesión
./scripts/actualizar.sh    # compila, reemplaza /Applications/Remi.app y recarga todo
tail -f ~/Library/Logs/Remi/nucleo.log   # qué pensó, qué guardó, si la voz quedó lista
./scripts/desinstalar.sh   # baja los agentes y borra la app (nunca toca nucleo/remi.db)
```

**Si tocás código y no cambia nada: corré `./scripts/actualizar.sh`.** Ya no es `tauri dev`
— la Remi que se abre es la de `/Applications`, y esa solo cambia cuando la recompilás.
