"""La Biblia en la bóveda (encargo del 2-oct, tarea 1): `referencia/` entra a
la mente en nivel 1, sin pisar el libro `proyectos/remi.md` aunque los dos
tengan `tema: remi`. Bóveda y base temporales."""
import db
import sembrar_conocimiento
import vectores

LIBRO = "---\ntitulo: Remi — el asistente\ntema: remi\nresumen: El libro del proyecto.\n---\n\nCuerpo del libro.\n"
BIBLIA = (
    "---\ntitulo: La Biblia de Remi (copia de lectura)\ntema: remi\n"
    "resumen: Copia de la Biblia v3.9.\nclaves: [biblia, leyes]\ntipo: referencia\n---\n\n"
    "## Las seis leyes del cerebro\n\n03 · Sin cadena de culpa.\n"
)


def _boveda(tmp_path, monkeypatch):
    (tmp_path / "proyectos").mkdir()
    (tmp_path / "referencia").mkdir()
    (tmp_path / "proyectos" / "remi.md").write_text(LIBRO)
    (tmp_path / "referencia" / "biblia.md").write_text(BIBLIA)
    monkeypatch.setenv("REMI_CONOCIMIENTO", str(tmp_path / "proyectos"))
    monkeypatch.setenv("REMI_BOVEDA", str(tmp_path))
    return tmp_path


def _memorias_remi():
    conexion = db.conectar()
    try:
        return {m.titulo: m for m in db.memorias_por_tema(conexion, "remi")}
    finally:
        conexion.close()


def test_la_biblia_entra_en_nivel_1_sin_pisar_el_libro_de_remi(tmp_path, monkeypatch):
    _boveda(tmp_path, monkeypatch)
    sembrar_conocimiento.sembrar()
    cuenta = sembrar_conocimiento.sembrar_referencias()

    assert cuenta["creadas"] == 1
    memorias = _memorias_remi()
    assert set(memorias) == {"Remi — el asistente", "La Biblia de Remi (copia de lectura)"}
    biblia = memorias["La Biblia de Remi (copia de lectura)"]
    assert biblia.nivel == 1 and "Sin cadena de culpa" in biblia.cuerpo
    assert memorias["Remi — el asistente"].cuerpo == "Cuerpo del libro."


def test_volver_a_sembrar_actualiza_solo_la_biblia(tmp_path, monkeypatch):
    boveda = _boveda(tmp_path, monkeypatch)
    sembrar_conocimiento.sembrar()
    sembrar_conocimiento.sembrar_referencias()
    assert sembrar_conocimiento.sembrar_referencias()["iguales"] == 1

    (boveda / "referencia" / "biblia.md").write_text(BIBLIA + "\nUna línea nueva.\n")
    assert sembrar_conocimiento.sembrar_referencias()["actualizadas"] == 1
    sembrar_conocimiento.sembrar()  # el libro, al sembrarse, no toca la Biblia
    memorias = _memorias_remi()
    assert "Una línea nueva." in memorias["La Biblia de Remi (copia de lectura)"].cuerpo
    assert memorias["Remi — el asistente"].cuerpo == "Cuerpo del libro."


def test_la_biblia_tambien_se_asocia_por_vectores(tmp_path, monkeypatch):
    _boveda(tmp_path, monkeypatch)
    assert [n.tipo for n in vectores.notas() if "Biblia" in n.titulo] == ["referencia"]


# — Si la frase nombra la Biblia, la sección que toca entra al contexto —
# (sin esto, ni Haiku ni Sonnet la bajaban con `leer`: el carácter ya trae
# su resumen de las seis leyes y contestaban con ese, diciendo que la leyeron)

BIBLIA_LARGA = (
    "---\ntitulo: La Biblia de Remi (copia de lectura)\ntema: remi\nresumen: r\nclaves: [biblia]\ntipo: referencia\n---\n\n"
    "## Las seis leyes del cerebro\n\nIntro.\n\n"
    "LEY 01 · CEGUERA TEMPORAL\n\n#### El reloj recuerda por ti\n\n**Regla:** Remi mide sola la duración.\n\n"
    "LEY 03 · SIN CADENA DE CULPA\n\n#### Remi nunca lleva la cuenta\n\n**Regla:** cero contadores. Un recordatorio incumplido **se encoge** a un paso mínimo.\n\n"
    "LEY 04 · PRESIÓN INVERTIDA\n\n#### Lo importante, más chico\n\n**Regla:** nada urgente.\n"
)


def test_la_frase_que_nombra_la_biblia_trae_la_seccion_literal(tmp_path, monkeypatch):
    import precarga

    boveda = _boveda(tmp_path, monkeypatch)
    (boveda / "referencia" / "biblia.md").write_text(BIBLIA_LARGA)

    texto = precarga.de_referencia("¿qué dice tu Biblia de la ley 3?")

    assert texto is not None
    assert "LEY 03 · SIN CADENA DE CULPA" in texto and "se encoge" in texto
    assert "LEY 01" not in texto and "LEY 04" not in texto
    assert "referencia/biblia.md" in texto


def test_sin_nombrar_la_biblia_no_trae_nada(tmp_path, monkeypatch):
    import precarga

    _boveda(tmp_path, monkeypatch)
    assert precarga.de_referencia("¿qué dice la ley 3?") is None


def test_la_biblia_sin_seccion_clara_igual_dice_donde_esta(tmp_path, monkeypatch):
    import precarga

    boveda = _boveda(tmp_path, monkeypatch)
    (boveda / "referencia" / "biblia.md").write_text(BIBLIA_LARGA)
    texto = precarga.de_referencia("¿está completo cada paso de la biblia?")
    assert texto is not None and "referencia/biblia.md" in texto and "`leer`" in texto


def test_nombrar_remi_o_las_fases_no_trae_la_biblia(tmp_path, monkeypatch):
    import precarga

    boveda = _boveda(tmp_path, monkeypatch)
    (boveda / "referencia" / "biblia.md").write_text(BIBLIA_LARGA.replace("claves: [biblia]", "claves: [biblia, leyes, fases, remi]"))
    assert precarga.de_referencia("¿cómo van las fases de remi?") is None
    assert precarga.de_referencia("¿qué dice la biblia de la ley 3?") is not None
