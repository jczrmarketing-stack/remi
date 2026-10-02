"""T10.2: armar la mente con un presupuesto fijo — nunca se borra ni se
mueve una nota de remi.db, solo se recorta lo que se MUESTRA esta vez."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pensar
from db import EntradaIndice


def _entrada(titulo, tema="malik", nivel=None, hace_dias=0, resumen="r"):
    return EntradaIndice(
        id=uuid4(),
        titulo=titulo,
        resumen=resumen,
        tema=tema,
        fecha=datetime.now(timezone.utc) - timedelta(days=hace_dias),
        claves=None,
        nivel=nivel,
    )


def test_todo_entra_si_el_presupuesto_alcanza():
    indice = [_entrada(f"Nota {i}", hace_dias=i) for i in range(5)]

    incluidas, recortadas = pensar._indice_con_presupuesto(indice, presupuesto_tokens=8000)

    assert len(incluidas) == 5
    assert recortadas == {}


def test_nivel_0_y_1_nunca_se_recortan_aunque_el_presupuesto_sea_minimo():
    protegidas = [_entrada(f"Protegida {i}", tema="malik", nivel=0, hace_dias=i) for i in range(20)]

    incluidas, recortadas = pensar._indice_con_presupuesto(protegidas, presupuesto_tokens=1)

    assert len(incluidas) == 20
    assert recortadas == {}


def test_lo_que_no_entra_se_cuenta_por_tema_no_se_pierde():
    indice = [_entrada(f"Nota {i}", tema="malik", hace_dias=i) for i in range(50)]

    incluidas, recortadas = pensar._indice_con_presupuesto(indice, presupuesto_tokens=1)

    assert len(incluidas) < 50
    assert recortadas.get("malik", 0) == 50 - len(incluidas)


def test_lo_mas_fresco_entra_antes_cuando_el_presupuesto_corta():
    viejo = _entrada("La vieja", tema="malik", hace_dias=100)
    nueva = _entrada("La nueva", tema="malik", hace_dias=0)
    # Presupuesto justo para una sola línea.
    presupuesto = (len(pensar._linea_indice(nueva)) + 1) * 1 // 4 + 1

    incluidas, recortadas = pensar._indice_con_presupuesto([viejo, nueva], presupuesto_tokens=presupuesto)

    assert [e.titulo for e in incluidas] == ["La nueva"]
    assert recortadas == {"malik": 1}


def test_instrucciones_con_indice_avisa_lo_que_quedo_afuera():
    indice = [_entrada(f"Nota {i}", tema="upvisuals", hace_dias=i) for i in range(30)]

    texto = pensar.instrucciones_con_indice(indice, base="CARÁCTER", presupuesto_tokens=1)

    assert "no entró acá por espacio" in texto
    assert "buscar_memoria" in texto
    assert "upvisuals:" in texto


def test_instrucciones_con_indice_sin_recorte_no_menciona_el_presupuesto():
    indice = [_entrada("Única", hace_dias=0)]

    texto = pensar.instrucciones_con_indice(indice, base="CARÁCTER", presupuesto_tokens=8000)

    assert "no entró acá por espacio" not in texto
