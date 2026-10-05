"""PR: del encargo a producción (Biblia Parte VIII). El `revisor` es un
doble — nunca una llamada real de pago en pytest."""
import produccion
from produccion import HallazgoDiff, HallazgoSeguridad, ListaDeLaVerdad, RevisionDiff


def test_paquete_base_trae_claude_md_y_contratos():
    paquete = produccion.generar_paquete_base("UpVisuals", "Landing de ventas", "Next.js + Supabase")
    assert "CLAUDE.md" in paquete
    assert "contratos/contratos.json" in paquete
    assert "UpVisuals" in paquete["CLAUDE.md"]
    assert "Next.js + Supabase" in paquete["CLAUDE.md"]


def test_un_hallazgo_serio_bloquea_la_entrega():
    hallazgos = [HallazgoSeguridad(archivo="api/pagos.ts", severidad="serio", resumen="llave en texto plano")]
    assert produccion.puede_entregar(hallazgos) is False


def test_sin_hallazgos_serios_la_entrega_pasa():
    hallazgos = [HallazgoSeguridad(archivo="x.ts", severidad="medio", resumen="validación floja")]
    assert produccion.puede_entregar(hallazgos) is True


def test_sin_ningun_hallazgo_la_entrega_pasa():
    assert produccion.puede_entregar([]) is True


def test_revisar_sesion_ordena_por_gravedad():
    def revisor_doble(diff: str) -> RevisionDiff:
        return RevisionDiff(
            hallazgos=[
                HallazgoDiff(archivo="a.ts", gravedad="menor", resumen="nombre confuso", encargo_de_arreglo="renombrar"),
                HallazgoDiff(archivo="b.ts", gravedad="grave", resumen="SQL sin parametrizar", encargo_de_arreglo="usar placeholders"),
                HallazgoDiff(archivo="c.ts", gravedad="medio", resumen="falta un test", encargo_de_arreglo="agregar test"),
            ],
            explicacion=["se agregó el endpoint de pagos", "porque Beam lo pidió", "podría romper el webhook si cambia el monto"],
        )

    revision = produccion.revisar_sesion("diff falso", revisor_doble)
    assert [h.gravedad for h in revision.hallazgos] == ["grave", "medio", "menor"]
    assert len(revision.explicacion) == 3


def test_nada_grave_pendiente_falso_si_hay_un_grave():
    revision = RevisionDiff(
        hallazgos=[HallazgoDiff(archivo="x.ts", gravedad="grave", resumen="x", encargo_de_arreglo="x")],
        explicacion=["a", "b", "c"],
    )
    assert produccion.nada_grave_pendiente(revision) is False


def test_lista_de_la_verdad_completa_puede_cerrar():
    lista = ListaDeLaVerdad(
        se_uso_de_verdad=True, revision_sin_pendientes_graves=True, entiende_que_cambio=True, hay_copia_monitoreo_y_reversa=True,
    )
    assert lista.fase_puede_cerrar() is True
    assert lista.primera_pendiente() is None


def test_lista_de_la_verdad_encoge_al_primer_pendiente_sin_listar_todo():
    lista = ListaDeLaVerdad(
        se_uso_de_verdad=False, revision_sin_pendientes_graves=False, entiende_que_cambio=True, hay_copia_monitoreo_y_reversa=True,
    )
    assert lista.fase_puede_cerrar() is False
    assert lista.primera_pendiente() == "usarlo de verdad, no solo pasar las pruebas"
