from uuid import uuid4

import pytest
from pydantic import ValidationError

from modelos import Tarea


def test_tarea_rechaza_campo_fuera_de_contrato():
    with pytest.raises(ValidationError):
        Tarea(
            id=uuid4(),
            titulo="ahora llamo al banco",
            proyecto_id=None,
            estado="hoy",
            paso_minimo="ahora llamo al banco",
            estimado_min=None,
            real_min=None,
            compartible=False,
            urgente=True,  # campo inventado: no está en contratos.json
        )
