"""Pruebas que ejecutan los planes de planificadores reales y esperan ``"VÁLIDO"``.

Los planes son los scripts del directorio ``tests/tests_private/real_tests/``, que
no está en el repositorio: sin él, la prueba se omite. Al cargarse, cada script
define ``acciones``, ``ubicaciones``, ``drones``, ``cajas``, ``personas``,
``objetivos`` y, si hay transportadores, ``transportadores``. Su bloque
``if __name__ == "__main__"``, que abre la ventana de pygame, no se ejecuta
porque los scripts se cargan con otro ``run_name``.
"""

import contextlib
import io
import logging
import runpy
import unittest
from pathlib import Path

from simulador_pddl import Mundo
from simulador_pddl.simulacion import InformeVerificacion

# Los planes de los planificadores son material privado: el directorio no está en el
# repositorio.
PRUEBAS_REALES = Path(__file__).resolve().parent.parent / "tests_private" / "real_tests"


class TestPlanesPlanificadoresReales(unittest.TestCase):
    """Todos los planes traducidos de los planificadores son válidos."""

    def setUp(self) -> None:
        """Silencia la narración de los drones."""
        # La narración de los drones (logging) serían miles de líneas: aquí solo
        # importa el veredicto.
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_todos_los_planes_reales_son_validos(self) -> None:
        """Comprueba que cada script de ``real_tests/`` da el veredicto ``"VÁLIDO"``."""
        if not PRUEBAS_REALES.is_dir():
            self.skipTest(f"el directorio {PRUEBAS_REALES} no existe")

        scripts = sorted(PRUEBAS_REALES.rglob("*.py"))

        # Si el directorio estuviera vacío, el bucle no comprobaría nada y la prueba
        # pasaría sin haber ejecutado ningún plan.
        self.assertTrue(scripts, f"no se han encontrado scripts en {PRUEBAS_REALES}")

        for script in scripts:
            with self.subTest(script=str(script.relative_to(PRUEBAS_REALES))):
                # run_path vuelve a ejecutar el script, así que cada plan se simula
                # sobre objetos recién creados.
                plan = runpy.run_path(str(script), run_name="real_test")
                mundo = Mundo(
                    plan["acciones"],
                    localizaciones=plan["ubicaciones"],
                    drones=plan["drones"],
                    cajas=plan["cajas"],
                    personas=plan["personas"],
                    # Solo los problemas con transportadores definen esta lista.
                    transportadores=plan.get("transportadores"),
                    objetivos=plan["objetivos"],
                )

                with contextlib.redirect_stdout(io.StringIO()):
                    informe = mundo.simulacion_texto()

                self.assertEqual(
                    informe.veredicto, InformeVerificacion.VALIDO, informe.resumen()
                )


if __name__ == "__main__":
    unittest.main()
