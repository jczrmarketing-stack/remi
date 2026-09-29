"""El estante: lo que no puede romperse.

La memoria funciona como la de una persona: en la mente están los títulos y
con qué se quedó de cada cosa; el cuerpo vive en el estante y se baja solo
cuando hace falta. Estas pruebas cuidan justo esa frontera.
"""
import importlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient


def _arrancar(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    for nombre in ("servidor", "db", "modelos", "pensar", "memoria_mcp"):
        sys.modules.pop(nombre, None)
    import db
    import servidor

    importlib.reload(db)
    importlib.reload(servidor)
    return servidor


def _memoria(titulo="Una cosa", resumen="Con esto me quedé", tema="prueba", cuerpo="Lo largo."):
    from modelos import Memoria

    return Memoria(
        id=uuid4(),
        titulo=titulo,
        resumen=resumen,
        tema=tema,
        fecha=datetime.now(timezone.utc),
        cuerpo=cuerpo,
        fuente="manual",
    )


# — El índice nunca trae el cuerpo —


def test_el_indice_no_trae_el_cuerpo_ni_por_asomo(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    import db

    conexion = db.conectar()
    db.guardar_memoria(conexion, _memoria(cuerpo="ESTO NO PUEDE APARECER EN EL INDICE"))
    indice = db.indice_memoria(conexion)
    conexion.close()

    assert len(indice) == 1
    entrada = indice[0]
    assert not hasattr(entrada, "cuerpo")
    assert "ESTO NO PUEDE APARECER" not in repr(entrada)

    # Y por HTTP tampoco.
    cliente = TestClient(servidor.app)
    crudo = cliente.get("/memoria").text
    assert "ESTO NO PUEDE APARECER" not in crudo
    assert sorted(json.loads(crudo)[0]) == ["fecha", "id", "resumen", "tema", "titulo"]


def test_el_indice_viene_de_lo_mas_nuevo_a_lo_mas_viejo(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    import db
    from modelos import Memoria

    conexion = db.conectar()
    for anio, titulo in ((2024, "vieja"), (2026, "nueva"), (2025, "media")):
        db.guardar_memoria(
            conexion,
            Memoria(
                id=uuid4(),
                titulo=titulo,
                resumen="r",
                tema="t",
                fecha=datetime(anio, 1, 1, tzinfo=timezone.utc),
                cuerpo="c",
                fuente="manual",
            ),
        )
    titulos = [e.titulo for e in db.indice_memoria(conexion)]
    conexion.close()
    assert titulos == ["nueva", "media", "vieja"]


# — El estante: leer y guardar, en voz de Remi —


def test_leer_un_id_que_no_existe_no_regana(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    import memoria_mcp

    respuesta = memoria_mcp.leer("no-existe")
    # Ley 3: dice qué pasó y qué hacer. Sin «deberías», sin contar el fallo.
    assert "no-existe" in respuesta
    for palabra in ("error", "inválido", "deberías", "otra vez", "fallo"):
        assert palabra not in respuesta.lower()
    assert "índice" in respuesta.lower()


def test_leer_acepta_el_id_corto_que_muestra_el_indice(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    import db
    import memoria_mcp

    memoria = _memoria(cuerpo="El cuerpo entero.")
    conexion = db.conectar()
    db.guardar_memoria(conexion, memoria)
    conexion.close()

    respuesta = memoria_mcp.leer(str(memoria.id)[:8])
    assert "El cuerpo entero." in respuesta
    assert memoria.titulo in respuesta


def test_guardar_rechaza_titulo_vacio_y_resumen_largo(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    import db
    import memoria_mcp

    assert "no me entra" in memoria_mcp.guardar("", "resumen", "cuerpo", "tema").lower()
    assert "no me entra" in memoria_mcp.guardar("t", "x" * 241, "cuerpo", "tema").lower()
    assert "no me entra" in memoria_mcp.guardar("x" * 81, "resumen", "cuerpo", "tema").lower()

    conexion = db.conectar()
    assert db.indice_memoria(conexion) == []
    conexion.close()


def test_guardar_lo_que_si_entra_queda_en_el_estante(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    import db
    import memoria_mcp

    assert "Guardado" in memoria_mcp.guardar("Un título", "Un resumen", "El cuerpo", "tema")
    conexion = db.conectar()
    indice = db.indice_memoria(conexion)
    conexion.close()
    assert [e.titulo for e in indice] == ["Un título"]


# — La mente: el índice en el system prompt —


def test_el_system_prompt_lleva_la_linea_del_indice_cuando_hay_entradas(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    import db
    import pensar

    memoria = _memoria(titulo="Lo de Shopify", resumen="Latinoamérica compra por WhatsApp", tema="shopify")
    conexion = db.conectar()
    db.guardar_memoria(conexion, memoria)
    indice = db.indice_memoria(conexion)
    conexion.close()

    instrucciones = pensar.instrucciones_con_indice(indice)
    corto = str(memoria.id)[:8]
    assert f"[{corto}]" in instrucciones
    assert "shopify · Lo de Shopify — Latinoamérica compra por WhatsApp" in instrucciones
    assert memoria.fecha.date().isoformat() in instrucciones
    # El cuerpo jamás: para eso está el estante.
    assert memoria.cuerpo not in instrucciones


def test_sin_entradas_no_se_anexa_nada(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    import pensar

    # Un encabezado sin líneas debajo invitaría a inventar recuerdos.
    assert pensar.instrucciones_con_indice([]) == pensar.INSTRUCCIONES


# — El encierro de la CLI —


def test_el_comando_abre_el_estante_y_solo_el_estante(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    import pensar

    config = pensar._config_mcp(tmp_path)
    comando = pensar._comando("haiku", "instrucciones", config)

    assert comando[comando.index("--mcp-config") + 1] == str(config)
    herramientas = comando[comando.index("--allowedTools") + 1].split(",")
    assert herramientas == ["mcp__memoria__leer", "mcp__memoria__guardar"]

    # El encierro sigue puesto.
    assert comando[comando.index("--tools") + 1] == ""
    assert "--restricted" in comando
    assert "--strict-mcp-config" in comando
    assert comando[comando.index("--setting-sources") + 1] == ""
    # Una vuelta no alcanza para pedir la lectura, recibirla y contestar.
    assert comando[comando.index("--max-turns") + 1] == "3"


def test_la_config_mcp_declara_un_solo_servidor(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    import pensar

    config = json.loads(pensar._config_mcp(tmp_path).read_text())
    assert list(config["mcpServers"]) == ["memoria"]
    servidor_memoria = config["mcpServers"]["memoria"]
    assert servidor_memoria["args"] == [str(pensar.SERVIDOR_MEMORIA)]
    # El estante corre en otro proceso: tiene que ver la misma base.
    assert servidor_memoria["env"]["REMI_DB_PATH"] == str(tmp_path / "remi.db")


def test_el_estante_deja_marca_al_ser_leido(tmp_path, monkeypatch):
    """El JSON final de la CLI no dice qué herramientas usó, así que la
    marca la deja el propio estante."""
    _arrancar(tmp_path, monkeypatch)
    import db
    import memoria_mcp

    memoria = _memoria()
    conexion = db.conectar()
    db.guardar_memoria(conexion, memoria)
    conexion.close()

    marca = tmp_path / "leyo"
    monkeypatch.setenv("REMI_MARCA_LECTURA", str(marca))
    assert not marca.exists()
    memoria_mcp.leer(str(memoria.id))
    assert marca.exists()


def test_guardar_no_deja_marca_de_lectura(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    import memoria_mcp

    marca = tmp_path / "leyo"
    monkeypatch.setenv("REMI_MARCA_LECTURA", str(marca))
    memoria_mcp.guardar("Un título", "Un resumen", "El cuerpo", "tema")
    assert not marca.exists()


# — El servidor MCP habla MCP de verdad —


def test_el_servidor_mcp_anuncia_exactamente_dos_herramientas(tmp_path, monkeypatch):
    monkeypatch.setenv("REMI_DB_PATH", str(tmp_path / "remi.db"))
    import pensar

    peticiones = "\n".join(
        json.dumps(p)
        for p in (
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "prueba", "version": "1"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        )
    )
    terminado = subprocess.run(
        [sys.executable, str(pensar.SERVIDOR_MEMORIA)],
        input=peticiones + "\n",
        capture_output=True,
        text=True,
        # 60 s se quedaba corto cuando esto corría mientras compilaba la
        # app: el subproceso levanta el SDK de MCP y tarda.
        timeout=180,
    )
    nombres = []
    for linea in terminado.stdout.splitlines():
        respuesta = json.loads(linea)
        if respuesta.get("id") == 2:
            nombres = sorted(h["name"] for h in respuesta["result"]["tools"])
    assert nombres == ["guardar", "leer"]


# — La semilla —


def test_la_semilla_no_duplica_si_se_corre_dos_veces(tmp_path, monkeypatch):
    _arrancar(tmp_path, monkeypatch)
    sys.modules.pop("sembrar_memoria", None)
    import db
    import sembrar_memoria

    assert sembrar_memoria.sembrar() == 1
    assert sembrar_memoria.sembrar() == 0

    conexion = db.conectar()
    indice = db.indice_memoria(conexion)
    conexion.close()
    assert len(indice) == 1
    assert indice[0].titulo.startswith("Construimos para la gente que usa Shopify")


# — Los endpoints —


def test_endpoints_del_estante(tmp_path, monkeypatch):
    servidor = _arrancar(tmp_path, monkeypatch)
    cliente = TestClient(servidor.app)

    creada = cliente.post(
        "/memoria", json={"titulo": "T", "resumen": "R", "cuerpo": "C", "tema": "tema"}
    )
    assert creada.status_code == 201
    memoria_id = creada.json()["id"]

    assert cliente.get(f"/memoria/{memoria_id}").json()["cuerpo"] == "C"
    assert cliente.patch(f"/memoria/{memoria_id}", json={"cuerpo": "Otro"}).json()["cuerpo"] == "Otro"
    # Lo que no entra en el contrato es 422, no un 500.
    assert cliente.patch(f"/memoria/{memoria_id}", json={"titulo": "x" * 81}).status_code == 422
    assert cliente.post(
        "/memoria", json={"titulo": "", "resumen": "R", "cuerpo": "C", "tema": "t"}
    ).status_code == 422

    assert cliente.delete(f"/memoria/{memoria_id}").status_code == 204
    assert cliente.delete(f"/memoria/{memoria_id}").status_code == 404
    assert cliente.get(f"/memoria/{memoria_id}").status_code == 404
