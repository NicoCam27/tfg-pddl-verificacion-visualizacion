"""Pruebas de que el código que se enseña al usuario funciona con la API actual.

Ejecutan los scripts ``tests/ejemplo_*.py`` y comprueban el veredicto de cada
uno. Los ejemplos completos del README son esos mismos scripts: cada uno lleva
antes una marca, ``<!-- ejemplo: tests/ejemplo_basico.py -->``, que en GitHub no se
ve, y una prueba comprueba que el bloque es igual que su script. Así, probar los
scripts prueba también el README. Los bloques del README que no son programas
completos, como los que continúan otro ejemplo o los esquemas con ``...``, no
llevan marca, así que ninguna prueba los comprueba. Si la API cambia y nadie
actualiza un ejemplo, el ejemplo queda roto sin que lo note ninguna otra prueba:
estas fallan.

No abren ninguna ventana: ``Mundo.simulacion_visual()`` se sustituye por una
ejecución sin pantalla hasta el final del plan, que devuelve el mismo informe. La
ventana ya la prueba ``test_simulacion_visual.py``. Aquí importa que el ejemplo
construye un plan válido y que llama a la biblioteca como permite su API. La
sustitución conserva la firma del método, así que una llamada con argumentos que
ya no existen sigue fallando.
"""

from __future__ import annotations

import contextlib
import io
import logging
import math
import re
import runpy
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from simulador_pddl import InformeVerificacion, Mundo

# La raíz del repositorio: este fichero está en tests/regression/.
RAIZ = Path(__file__).resolve().parents[2]
README = RAIZ / "README.md"


def ejecutar_sin_ventana(ruta: Path) -> tuple[dict[str, Any], str]:
    """Ejecuta el script ``ruta`` sin abrir ventanas y sin escribir en la terminal.

    Returns:
        Las variables globales del script al terminar y lo que imprimió.
    """

    def hasta_el_final(mundo: Mundo, *_args: object, **_kwargs: object) -> Any:
        return mundo.avanzar_hasta(math.inf)

    salida = io.StringIO()
    with (
        mock.patch.object(
            Mundo, "simulacion_visual", autospec=True, side_effect=hasta_el_final
        ),
        contextlib.redirect_stdout(salida),
    ):
        variables = runpy.run_path(str(ruta), run_name="ejemplo")
    return variables, salida.getvalue()


def leer_readme() -> str:
    """Devuelve el texto del README, sin los retornos de carro de Windows."""
    return README.read_text(encoding="utf-8").replace("\r\n", "\n")


class TestEjemplosDelReadme(unittest.TestCase):
    """Los ejemplos completos del README son los scripts de ejemplo."""

    def setUp(self) -> None:
        """Silencia el registro."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_cada_ejemplo_marcado_es_su_script(self) -> None:
        """Comprueba que cada ejemplo marcado del README es igual que su script.

        Cada marca tiene que ir justo antes de un bloque de código Python, y su
        script tiene que existir: una marca mal escrita o separada de su bloque
        dejaría el ejemplo sin comprobar. Esta prueba solo compara textos: que los
        scripts funcionen lo comprueba ``TestScriptsDeEjemplo``.
        """
        readme = leer_readme()
        marcas = re.findall(r"<!-- ejemplo: (.*?) -->", readme)
        ejemplos = re.findall(
            r"<!-- ejemplo: (.*?) -->\n```python\n(.*?)```", readme, re.DOTALL
        )
        self.assertNotEqual(marcas, [])
        self.assertEqual([ruta for ruta, _ in ejemplos], marcas)

        for ruta, codigo in ejemplos:
            with self.subTest(script=ruta):
                script = RAIZ / ruta
                self.assertTrue(script.is_file(), f"no existe {ruta}")
                self.assertEqual(
                    codigo, script.read_text(encoding="utf-8").replace("\r\n", "\n")
                )

    def test_la_salida_que_muestra_el_readme_es_la_del_ejemplo_basico(self) -> None:
        """Comprueba que el resumen que enseña el README es el que da el ejemplo.

        El README muestra el resumen del informe del ejemplo básico, que es
        ``tests/ejemplo_basico.py``. Si cambia el texto del resumen, el README
        tiene que cambiar con él.
        """
        variables, _ = ejecutar_sin_ventana(RAIZ / "tests" / "ejemplo_basico.py")

        self.assertIn(variables["informe"].resumen(), leer_readme())


class TestScriptsDeEjemplo(unittest.TestCase):
    """Los scripts ``tests/ejemplo_*.py`` se ejecutan y dan su veredicto."""

    def setUp(self) -> None:
        """Silencia el registro."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_cada_script_da_el_veredicto_que_dice_su_documentacion(self) -> None:
        """Comprueba el veredicto final de cada script con un solo plan.

        ``ejemplo_dos_drones_paralelos.py`` suelta una caja en lugar de entregarla
        a propósito, así que su veredicto es ``"NO RESUELVE"``.
        """
        veredictos = {
            "ejemplo_basico.py": InformeVerificacion.VALIDO,
            "ejemplo_transportador.py": InformeVerificacion.VALIDO,
            "ejemplo_dos_drones_paralelos.py": InformeVerificacion.NO_RESUELVE,
        }
        for nombre, veredicto in veredictos.items():
            with self.subTest(script=nombre):
                variables, _ = ejecutar_sin_ventana(RAIZ / "tests" / nombre)
                self.assertEqual(variables["informe"].veredicto, veredicto)

    def test_los_dos_planes_de_varios_planificadores_son_validos(self) -> None:
        """Comprueba que el script imprime ``"VÁLIDO"`` para cada uno de sus planes.

        Para cada uno de sus dos planes, el script imprime una línea con el
        nombre del plan y su veredicto, p. ej. ``plan_planificador_a - VÁLIDO``.
        Se comprueban esas dos líneas.
        """
        _, salida = ejecutar_sin_ventana(
            RAIZ / "tests" / "ejemplo_varios_planificadores.py"
        )

        for plan in ("plan_planificador_a", "plan_planificador_b"):
            with self.subTest(plan=plan):
                self.assertIn(f"{plan} - {InformeVerificacion.VALIDO}\n", salida)


if __name__ == "__main__":
    unittest.main()
