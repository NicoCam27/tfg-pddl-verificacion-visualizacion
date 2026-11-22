"""Pruebas de que un plan clásico se simula como una secuencia de pasos.

Un planificador clásico devuelve una secuencia de pasos sin tiempos. Se escribe
numerando los pasos desde 0: la acción del paso ``i`` empieza en ``i`` y dura 1.
Como las acciones no se solapan, entre el inicio y el final de una acción no
ocurre nada más, así que aplicar sus efectos en dos fases produce el mismo
estado que aplicarlos a la vez, como en PDDL clásico.

Por tanto, un plan clásico correcto es ``"VÁLIDO"``, un paso imposible hace que el plan
sea ``"NO EJECUTABLE"`` justo en ese paso, y el veredicto no depende de la duración
elegida para los pasos.
"""

from __future__ import annotations

import contextlib
import io
import unittest
from typing import TYPE_CHECKING

from simulador_pddl.acciones import CogerCaja, EntregarCaja, Mover
from simulador_pddl.mundo import Mundo
from simulador_pddl.objetivos import PersonaTieneContenido
from simulador_pddl.objetos import Brazo, Caja, Dron, Localizacion, Persona
from simulador_pddl.simulacion import InformeVerificacion

if TYPE_CHECKING:
    from collections.abc import Callable

    from simulador_pddl.acciones import Accion

# Duraciones de paso con las que se repite cada plan: la convención (1) y otras.
DURACIONES_PASO = (1, 5, 0.5)


def ejecutar_plan(mundo: Mundo) -> InformeVerificacion:
    """Ejecuta el plan en modo texto, sin imprimir, y devuelve su informe."""
    with contextlib.redirect_stdout(io.StringIO()):
        return mundo.simulacion_texto()


def construir_mundo(duracion_paso: float, *, omitir_regreso: bool = False) -> Mundo:
    """Construye el mundo de un plan clásico de dos entregas.

    El dron entrega ``comida`` a ``persona1`` en ``loc1``, vuelve al depósito y
    entrega ``medicina`` a ``persona2`` en ``loc2``: siete pasos. El paso ``i``
    empieza en ``i * duracion_paso`` y dura ``duracion_paso``.

    Args:
        duracion_paso: La duración de cada paso del plan.
        omitir_regreso: Si es ``True``, se quita el paso 3 (el regreso al
            depósito), así que en el nuevo paso 3 el dron intenta coger una caja
            que está en otra localización.
    """
    deposito = Localizacion("deposito")
    loc1 = Localizacion("loc1")
    loc2 = Localizacion("loc2")
    brazo = Brazo("brazo")
    dron = Dron("dron1", deposito, [brazo])
    caja1 = Caja("caja1", deposito, "comida")
    caja2 = Caja("caja2", deposito, "medicina")
    persona1 = Persona("persona1", loc1, "comida")
    persona2 = Persona("persona2", loc2, "medicina")

    # Los pasos del plan clásico, en orden y sin tiempos: cada uno construye su
    # acción a partir del inicio y la duración que le corresponden.
    pasos: list[Callable[[float, float], Accion]] = [
        lambda i, d: CogerCaja(dron, brazo, caja1, i, d),
        lambda i, d: Mover(dron, deposito, loc1, i, d),
        lambda i, d: EntregarCaja(dron, brazo, caja1, persona1, i, d),
        lambda i, d: Mover(dron, loc1, deposito, i, d),
        lambda i, d: CogerCaja(dron, brazo, caja2, i, d),
        lambda i, d: Mover(dron, deposito, loc2, i, d),
        lambda i, d: EntregarCaja(dron, brazo, caja2, persona2, i, d),
    ]
    if omitir_regreso:
        del pasos[3]

    acciones = [
        paso(numero * duracion_paso, duracion_paso) for numero, paso in enumerate(pasos)
    ]
    return Mundo(
        acciones,
        localizaciones=[deposito, loc1, loc2],
        drones=[dron],
        cajas=[caja1, caja2],
        personas=[persona1, persona2],
        objetivos=[
            PersonaTieneContenido(persona1, "comida"),
            PersonaTieneContenido(persona2, "medicina"),
        ],
    )


class TestPlanesClasicos(unittest.TestCase):
    """Un plan clásico, escrito con un paso por unidad de tiempo."""

    def test_plan_clasico_correcto_es_valido(self) -> None:
        """Comprueba que un plan clásico correcto es ``"VÁLIDO"``."""
        informe = ejecutar_plan(construir_mundo(1))

        self.assertEqual(informe.veredicto, InformeVerificacion.VALIDO)
        self.assertEqual(informe.acciones_terminadas, 7)

    def test_duracion_por_defecto_basta_para_un_plan_clasico(self) -> None:
        """Comprueba que basta con dar el inicio: la duración vale 1 por defecto.

        Es la forma más corta de escribir un plan clásico:
        ``CogerCaja(dron, brazo, caja, 0)``.
        """
        deposito = Localizacion("deposito")
        loc1 = Localizacion("loc1")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        caja = Caja("caja1", deposito, "comida")
        persona = Persona("persona1", loc1, "comida")
        mundo = Mundo(
            [
                CogerCaja(dron, brazo, caja, 0),
                Mover(dron, deposito, loc1, 1),
                EntregarCaja(dron, brazo, caja, persona, 2),
            ],
            localizaciones=[deposito, loc1],
            drones=[dron],
            cajas=[caja],
            personas=[persona],
            objetivos=[PersonaTieneContenido(persona, "comida")],
        )

        informe = ejecutar_plan(mundo)

        self.assertEqual(informe.veredicto, InformeVerificacion.VALIDO)
        self.assertEqual(informe.estados_objetivos[0].logrado_en, 3)

    def test_paso_imposible_falla_en_ese_paso(self) -> None:
        """Comprueba que un paso imposible da ``"NO EJECUTABLE"`` en ese paso.

        Sin el regreso al depósito, el paso 3 intenta coger ``caja2`` desde
        ``loc1``: terminan los pasos 0, 1 y 2, y la ejecución se detiene ahí.
        """
        informe = ejecutar_plan(construir_mundo(1, omitir_regreso=True))

        self.assertEqual(informe.veredicto, InformeVerificacion.NO_EJECUTABLE)
        self.assertEqual(informe.acciones_terminadas, 3)
        self.assertIsNotNone(informe.error)
        self.assertIn("caja2", informe.error or "")


class TestDuracionDelPaso(unittest.TestCase):
    """El veredicto de un plan clásico no depende de la duración de los pasos."""

    def test_plan_correcto_es_valido_con_cualquier_duracion(self) -> None:
        """Comprueba que el plan es ``"VÁLIDO"`` con cada duración de paso.

        Cada objetivo se logra al final de la misma entrega, así que su instante
        es el número de pasos transcurridos multiplicado por la duración.
        """
        for duracion in DURACIONES_PASO:
            with self.subTest(duracion_paso=duracion):
                informe = ejecutar_plan(construir_mundo(duracion))

                self.assertEqual(informe.veredicto, InformeVerificacion.VALIDO)
                logrados = [e.logrado_en for e in informe.estados_objetivos]
                self.assertEqual(logrados, [3 * duracion, 7 * duracion])

    def test_paso_imposible_falla_en_el_mismo_paso_con_cualquier_duracion(
        self,
    ) -> None:
        """Comprueba que el error se produce en el mismo paso con cualquier duración."""
        errores = []
        for duracion in DURACIONES_PASO:
            with self.subTest(duracion_paso=duracion):
                informe = ejecutar_plan(construir_mundo(duracion, omitir_regreso=True))

                self.assertEqual(informe.veredicto, InformeVerificacion.NO_EJECUTABLE)
                self.assertEqual(informe.acciones_terminadas, 3)
                errores.append(informe.error)

        # El mensaje no incluye tiempos, así que es el mismo en todos los casos.
        self.assertEqual(len(set(errores)), 1)


if __name__ == "__main__":
    unittest.main()
