"""Pruebas que ejecutan los planes de planificadores reales y esperan ``"VÁLIDO"``.

Hay dos grupos de planes. Los de ``planes_reales/``, junto a este fichero, son
de problemas escritos para estas pruebas, resueltos con ff, LAMA, LPG-td y
OPTIC-CLP, y están en el repositorio: se ejecutan siempre. Cada script define
``mundo``.

Los de ``tests/tests_private/real_tests/`` son de problemas que no se pueden
publicar, así que ese directorio no está en el repositorio, y sin él su prueba se
omite. Al cargarse, cada script define ``acciones``, ``ubicaciones``, ``drones``,
``cajas``, ``personas``, ``contenidos``, ``objetivos`` y, si hay transportadores,
``transportadores``. Su bloque ``if __name__ == "__main__"``, que abre la ventana
de pygame, no se ejecuta porque los scripts se cargan con otro ``run_name``.
"""

from __future__ import annotations

import contextlib
import io
import logging
import runpy
import unittest
from pathlib import Path
from typing import TYPE_CHECKING, Any

from simulador_pddl import Mundo
from simulador_pddl.simulacion import InformeVerificacion

if TYPE_CHECKING:
    from collections.abc import Callable

# Los planes de problemas propios, que están en el repositorio.
PLANES_PUBLICOS = Path(__file__).resolve().parent / "planes_reales"

# Los planes de problemas que no se pueden publicar: el directorio no está en el
# repositorio.
PRUEBAS_REALES = Path(__file__).resolve().parent.parent / "tests_private" / "real_tests"


class TestPlanesPlanificadoresReales(unittest.TestCase):
    """Todos los planes traducidos de los planificadores son válidos."""

    def setUp(self) -> None:
        """Silencia la narración de los drones."""
        # La narración de los drones (logging) ocuparía miles de líneas: aquí solo
        # importa el veredicto.
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def comprobar_planes(
        self, directorio: Path, crear_mundo: Callable[[dict[str, Any]], Mundo]
    ) -> None:
        """Comprueba que cada script de ``directorio`` da el veredicto ``"VÁLIDO"``.

        Args:
            directorio: El directorio con los scripts, que se buscan también en sus
                subdirectorios.
            crear_mundo: Devuelve el mundo de un script a partir de las variables
                que define.
        """
        scripts = sorted(
            script
            for script in directorio.rglob("*.py")
            if script.name != "__init__.py"
        )

        # Si el directorio estuviera vacío, el bucle no comprobaría nada y la prueba
        # pasaría sin haber ejecutado ningún plan.
        self.assertTrue(scripts, f"no se han encontrado scripts en {directorio}")

        for script in scripts:
            with self.subTest(script=str(script.relative_to(directorio))):
                # run_path vuelve a ejecutar el script, así que cada plan se simula
                # sobre objetos recién creados.
                mundo = crear_mundo(runpy.run_path(str(script), run_name="real_test"))

                with contextlib.redirect_stdout(io.StringIO()):
                    informe = mundo.simulacion_texto()

                self.assertEqual(
                    informe.veredicto, InformeVerificacion.VALIDO, informe.resumen()
                )

    def test_los_planes_reales_publicos_son_validos(self) -> None:
        """Comprueba que cada script de ``planes_reales/`` da ``"VÁLIDO"``."""
        self.comprobar_planes(PLANES_PUBLICOS, lambda plan: plan["mundo"])

    def test_todos_los_planes_reales_son_validos(self) -> None:
        """Comprueba que cada script de ``real_tests/`` da el veredicto ``"VÁLIDO"``."""
        if not PRUEBAS_REALES.is_dir():
            self.skipTest(f"el directorio {PRUEBAS_REALES} no existe")

        def crear_mundo(plan: dict[str, Any]) -> Mundo:
            return Mundo(
                plan["acciones"],
                localizaciones=plan["ubicaciones"],
                drones=plan["drones"],
                cajas=plan["cajas"],
                personas=plan["personas"],
                contenidos=plan["contenidos"],
                # Solo los problemas con transportadores definen esta lista.
                transportadores=plan.get("transportadores"),
                objetivos=plan["objetivos"],
            )

        self.comprobar_planes(PRUEBAS_REALES, crear_mundo)


if __name__ == "__main__":
    unittest.main()
