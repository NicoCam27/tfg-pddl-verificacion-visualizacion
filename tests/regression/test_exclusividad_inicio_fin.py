"""Pruebas de la semántica ``at start`` / ``at end`` de las acciones durativas.

Una acción reclama su caja o su transportador cuando empieza y aplica sus
efectos finales cuando termina. Estas pruebas comprueban lo que se sigue de
ello: dos drones no pueden manejar la misma caja o el mismo transportador en
ventanas de tiempo solapadas, una acción puede empezar en el instante en que
termina la anterior, y ``reiniciar()`` deshace una acción que ha empezado y no
ha terminado.

También comprueban la regla de solapamiento, que se aplica al ejecutar, cuando
empieza cada acción: un movimiento ocupa el dron entero, y cualquier otra acción
solo el brazo que usa. Una acción que la incumple deja el plan como
``"NO EJECUTABLE"``.
"""

from __future__ import annotations

import contextlib
import io
import unittest
from typing import TYPE_CHECKING, Any

from simulador_pddl.acciones import (
    CogerCaja,
    CogerTransportador,
    Mover,
    MoverTransportador,
    Soltar,
)
from simulador_pddl.mundo import Mundo
from simulador_pddl.objetos import (
    Brazo,
    Caja,
    Contenido,
    Dron,
    Localizacion,
    Transportador,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from simulador_pddl.acciones import Accion
    from simulador_pddl.simulacion import InformeVerificacion


# Los contenidos de los problemas de este módulo. Un contenido no cambia al
# ejecutar un plan, así que todas las pruebas pueden compartirlos.
COMIDA = Contenido("comida")
CONTENIDOS = (COMIDA,)


def ejecutar_plan(mundo: Mundo, paso_tiempo: float) -> InformeVerificacion:
    """Ejecuta el plan en modo texto, sin imprimir, y devuelve su informe."""
    with contextlib.redirect_stdout(io.StringIO()):
        return mundo.simulacion_texto(paso_tiempo)


class TestExclusividadDeCajaEntreDrones(unittest.TestCase):
    """Una caja solo la puede manejar un dron a la vez."""

    def setUp(self) -> None:
        """Crea dos drones y una caja en la misma localización."""
        self.deposito = Localizacion("deposito")
        self.brazo1 = Brazo("brazo1")
        self.brazo2 = Brazo("brazo2")
        self.dron1 = Dron("dron1", self.deposito, [self.brazo1])
        self.dron2 = Dron("dron2", self.deposito, [self.brazo2])
        self.caja6 = Caja("caja6", self.deposito, COMIDA)

    def _objetos(self) -> dict[str, list[Any]]:
        """Devuelve los objetos del problema, sin lista de transportadores."""
        return {
            "localizaciones": [self.deposito],
            "drones": [self.dron1, self.dron2],
            "cajas": [self.caja6],
            "personas": [],
            "contenidos": list(CONTENIDOS),
        }

    def test_coger_solapado_la_misma_caja_se_rechaza(self) -> None:
        """Comprueba que una caja no se puede coger mientras otro dron aún la tiene.

        ``dron2`` empieza a coger ``caja6`` en t=2.1, mientras ``dron1`` todavía la
        tiene (la coge de t=2 a t=2.5, y no la suelta hasta t=2.7).
        """
        acciones = [
            CogerCaja(
                dron=self.dron1,
                brazo=self.brazo1,
                caja=self.caja6,
                inicio_sim=2,
                duracion_sim=0.5,
            ),
            Soltar(
                dron=self.dron1,
                brazo=self.brazo1,
                caja=self.caja6,
                inicio_sim=2.5,
                duracion_sim=0.2,
            ),
            CogerCaja(
                dron=self.dron2,
                brazo=self.brazo2,
                caja=self.caja6,
                inicio_sim=2.1,
                duracion_sim=0.9,
            ),
        ]
        mundo = Mundo(acciones, **self._objetos())
        informe = ejecutar_plan(mundo, paso_tiempo=0.05)

        self.assertFalse(informe.ejecutable)
        self.assertIsNotNone(informe.error)
        self.assertIn("caja6", informe.error or "")

    def test_coger_soltar_coger_sin_solapar_sigue_funcionando(self) -> None:
        """Comprueba que la caja se puede coger una vez que el otro dron la ha soltado.

        El mismo plan, pero ``dron2`` empieza a coger ``caja6`` en t=2.7, el
        ``tiempo_fin`` exacto de ``Soltar``.
        """
        acciones = [
            CogerCaja(
                dron=self.dron1,
                brazo=self.brazo1,
                caja=self.caja6,
                inicio_sim=2,
                duracion_sim=0.5,
            ),
            Soltar(
                dron=self.dron1,
                brazo=self.brazo1,
                caja=self.caja6,
                inicio_sim=2.5,
                duracion_sim=0.2,
            ),
            CogerCaja(
                dron=self.dron2,
                brazo=self.brazo2,
                caja=self.caja6,
                inicio_sim=2.7,
                duracion_sim=0.9,
            ),
        ]
        mundo = Mundo(acciones, **self._objetos())
        informe = ejecutar_plan(mundo, paso_tiempo=0.05)

        self.assertTrue(informe.ejecutable, informe.error)

    def test_acciones_encadenadas_en_el_mismo_instante_funcionan(self) -> None:
        """Comprueba que una acción puede empezar cuando acaba la anterior.

        ``Soltar`` empieza justo cuando termina ``CogerCaja`` (t=2.5). Es el caso más
        común en los planes de un planificador real, y depende de que los finales
        de un instante se apliquen antes que sus inicios (ver
        ``Simulacion._aplicar_suceso()``).
        """
        acciones = [
            CogerCaja(
                dron=self.dron1,
                brazo=self.brazo1,
                caja=self.caja6,
                inicio_sim=2,
                duracion_sim=0.5,
            ),
            Soltar(
                dron=self.dron1,
                brazo=self.brazo1,
                caja=self.caja6,
                inicio_sim=2.5,
                duracion_sim=0.2,
            ),
        ]
        mundo = Mundo(acciones, **self._objetos())
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertEqual(self.caja6.localizacion, self.deposito)
        self.assertIsNone(self.brazo1.caja)


class TestExclusividadDeTransportadorEntreDrones(unittest.TestCase):
    """Un transportador solo lo puede sujetar un dron a la vez."""

    def setUp(self) -> None:
        """Crea dos drones y un transportador en la misma localización."""
        self.deposito = Localizacion("deposito")
        self.localizacion1 = Localizacion("localizacion1")
        self.brazo1 = Brazo("brazo1")
        self.brazo2 = Brazo("brazo2")
        self.dron1 = Dron("dron1", self.deposito, [self.brazo1])
        self.dron2 = Dron("dron2", self.deposito, [self.brazo2])
        self.transportador = Transportador("transportador1", self.deposito, 4)

    def _objetos(self) -> dict[str, list[Any]]:
        """Devuelve los objetos del problema, con su transportador."""
        return {
            "localizaciones": [self.deposito, self.localizacion1],
            "drones": [self.dron1, self.dron2],
            "cajas": [],
            "personas": [],
            "contenidos": [],
            "transportadores": [self.transportador],
        }

    def test_dos_drones_compitiendo_por_el_mismo_transportador_se_rechaza(self) -> None:
        """Comprueba que un transportador no se puede coger mientras otro dron lo mueve.

        Las acciones de dos drones distintos no se comparan al construir el plan,
        así que el conflicto aparece mientras se ejecuta: ``dron1`` reclama el
        transportador al inicio de su ``MoverTransportador``, y se rechaza el
        coger de ``dron2``.
        """
        acciones = [
            MoverTransportador(
                dron=self.dron1,
                transportador=self.transportador,
                brazo=self.brazo1,
                origen=self.deposito,
                destino=self.localizacion1,
                inicio_sim=0,
                duracion_sim=2,
            ),
            CogerTransportador(
                dron=self.dron2,
                transportador=self.transportador,
                brazo=self.brazo2,
                inicio_sim=0.5,
                duracion_sim=0.5,
            ),
        ]
        mundo = Mundo(acciones, **self._objetos())
        informe = ejecutar_plan(mundo, paso_tiempo=0.05)

        self.assertFalse(informe.ejecutable)
        self.assertIn("transportador1", informe.error or "")


class TestSolapamientoDentroDeUnDron(unittest.TestCase):
    """Un movimiento ocupa el dron entero, cualquier otra acción solo ocupa su brazo."""

    def setUp(self) -> None:
        """Crea un dron con dos brazos, dos cajas y un transportador."""
        self.deposito = Localizacion("deposito")
        self.localizacion1 = Localizacion("localizacion1")
        self.izquierda = Brazo("izquierda")
        self.derecha = Brazo("derecha")
        self.dron = Dron("dron1", self.deposito, [self.izquierda, self.derecha])
        self.caja_a = Caja("cajaA", self.deposito, COMIDA)
        self.caja_b = Caja("cajaB", self.deposito, COMIDA)
        self.transportador = Transportador("transportador1", self.deposito, 2)

    def _objetos(self) -> dict[str, list[Any]]:
        """Devuelve los objetos del problema, con su transportador."""
        return {
            "localizaciones": [self.deposito, self.localizacion1],
            "drones": [self.dron],
            "cajas": [self.caja_a, self.caja_b],
            "personas": [],
            "contenidos": list(CONTENIDOS),
            "transportadores": [self.transportador],
        }

    def _comprobar_rechazo(self, acciones: Sequence[Accion], mensaje: str) -> None:
        """Comprueba que la segunda acción no empieza porque choca con la primera.

        El plan se ejecuta y se detiene al empezar la segunda acción, con
        ``mensaje`` como error.
        """
        mundo = Mundo(acciones, **self._objetos())
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertEqual(informe.veredicto, informe.NO_EJECUTABLE)
        self.assertEqual(informe.error, mensaje)
        self.assertFalse(acciones[1].iniciada)

    def test_coger_durante_un_mover_del_mismo_dron_se_rechaza(self) -> None:
        """Comprueba que un dron no puede coger una caja mientras se mueve.

        La carga usa un brazo que el movimiento no nombra, así que solo la regla
        de que un movimiento ocupa el dron entero puede rechazarla.
        """
        acciones = [
            Mover(
                self.dron,
                self.deposito,
                self.localizacion1,
                inicio_sim=0,
                duracion_sim=2,
            ),
            CogerCaja(
                self.dron, self.izquierda, self.caja_a, inicio_sim=1, duracion_sim=1
            ),
        ]

        self._comprobar_rechazo(
            acciones,
            f"el dron dron1 no puede empezar {acciones[1].desc!r} en t=1 antes de "
            f"terminar {acciones[0].desc!r} en t=2",
        )

    def test_mover_durante_un_coger_del_mismo_dron_se_rechaza(self) -> None:
        """Comprueba que un dron no puede empezar a moverse mientras coge una caja."""
        acciones = [
            CogerCaja(
                self.dron, self.izquierda, self.caja_a, inicio_sim=0, duracion_sim=2
            ),
            Mover(
                self.dron,
                self.deposito,
                self.localizacion1,
                inicio_sim=1,
                duracion_sim=1,
            ),
        ]

        self._comprobar_rechazo(
            acciones,
            f"el dron dron1 no puede empezar {acciones[1].desc!r} en t=1 antes de "
            f"terminar {acciones[0].desc!r} en t=2",
        )

    def test_coger_durante_un_mover_transportador_del_mismo_dron_se_rechaza(
        self,
    ) -> None:
        """Comprueba que ``MoverTransportador`` ocupa el dron entero, como ``Mover``.

        La carga usa el brazo que no lleva el transportador.
        """
        acciones = [
            MoverTransportador(
                self.dron,
                self.transportador,
                self.izquierda,
                self.deposito,
                self.localizacion1,
                inicio_sim=0,
                duracion_sim=2,
            ),
            CogerCaja(
                self.dron, self.derecha, self.caja_a, inicio_sim=1, duracion_sim=1
            ),
        ]

        self._comprobar_rechazo(
            acciones,
            f"el dron dron1 no puede empezar {acciones[1].desc!r} en t=1 antes de "
            f"terminar {acciones[0].desc!r} en t=2",
        )

    def test_dos_brazos_de_un_dron_pueden_coger_a_la_vez(self) -> None:
        """Comprueba que dos cargas solapadas se aceptan en brazos distintos."""
        acciones = [
            CogerCaja(
                self.dron, self.izquierda, self.caja_a, inicio_sim=0, duracion_sim=1
            ),
            CogerCaja(
                self.dron, self.derecha, self.caja_b, inicio_sim=0, duracion_sim=1
            ),
        ]
        mundo = Mundo(acciones, **self._objetos())
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertIs(self.izquierda.caja, self.caja_a)
        self.assertIs(self.derecha.caja, self.caja_b)

    def test_un_brazo_no_puede_coger_dos_cajas_a_la_vez(self) -> None:
        """Comprueba que dos cargas solapadas se rechazan en el mismo brazo."""
        acciones = [
            CogerCaja(
                self.dron, self.izquierda, self.caja_a, inicio_sim=0, duracion_sim=2
            ),
            CogerCaja(
                self.dron, self.izquierda, self.caja_b, inicio_sim=1, duracion_sim=1
            ),
        ]

        self._comprobar_rechazo(
            acciones,
            f"el brazo izquierda del dron dron1 no puede empezar {acciones[1].desc!r} "
            f"en t=1 antes de terminar {acciones[0].desc!r} en t=2",
        )


class TestReiniciarRestauraEstadoAMitadDeAccion(unittest.TestCase):
    """``reiniciar()`` deshace los efectos de una acción que solo ha empezado."""

    def test_reiniciar_deshace_una_accion_que_empezo_y_no_termino(self) -> None:
        """Comprueba que ``reiniciar()`` restaura una caja de una carga sin terminar.

        ``_iniciar_coger_caja()`` ya cambia el estado de la caja (de ``DISPONIBLE`` a
        ``TRANSPORTADA``) antes de que termine la acción. ``reiniciar()`` tiene que
        devolverlo todo al estado inicial, no solo borrar los indicadores
        ``iniciada`` / ``terminada`` de la acción.
        """
        deposito = Localizacion("deposito")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        caja = Caja("caja1", deposito, COMIDA)

        acciones = [
            CogerCaja(dron=dron, brazo=brazo, caja=caja, inicio_sim=0, duracion_sim=1),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito],
            drones=[dron],
            cajas=[caja],
            personas=[],
            contenidos=CONTENIDOS,
        )

        mundo._simulacion._reproducir()
        # A mitad de CogerCaja: _iniciar_coger_caja() está aplicado,
        # _terminar_coger_caja() no.
        mundo._simulacion._actualizar(0.5)

        self.assertEqual(caja.estado, Caja.TRANSPORTADA)

        mundo.reiniciar()

        self.assertEqual(caja.estado, Caja.DISPONIBLE)
        self.assertIsNone(brazo.caja)
        self.assertEqual(caja.localizacion, deposito)

    def test_reiniciar_libera_un_brazo_reservado_por_un_transportador(self) -> None:
        """Comprueba que ``reiniciar()`` libera el brazo de un movimiento a medias.

        El transportador se coge cuando empieza la acción, así que el brazo queda
        reservado antes de que termine la acción, sin ninguna caja. ``reiniciar()``
        tiene que liberar el brazo y el transportador: si el brazo siguiera
        reservado, ninguna acción posterior podría usarlo, y el mismo plan no se
        podría volver a ejecutar.
        """
        deposito = Localizacion("deposito")
        localizacion1 = Localizacion("localizacion1")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        transportador = Transportador("transportador1", deposito, 2)

        acciones = [
            MoverTransportador(
                dron,
                transportador,
                brazo,
                deposito,
                localizacion1,
                inicio_sim=0,
                duracion_sim=2,
            ),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito, localizacion1],
            drones=[dron],
            cajas=[],
            personas=[],
            contenidos=[],
            transportadores=[transportador],
        )

        mundo._simulacion._reproducir()
        # A mitad de la acción: el transportador está cogido y no soltado.
        mundo._simulacion._actualizar(1.0)

        self.assertIs(brazo.transportador, transportador)
        self.assertIs(transportador.propietario_actual, dron)

        mundo.reiniciar()

        self.assertIsNone(brazo.transportador)
        self.assertIsNone(brazo.caja)
        self.assertIsNone(transportador.propietario_actual)
        self.assertIsNone(transportador.brazo_actual)

        # El mismo plan se vuelve a ejecutar desde el principio.
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertEqual(transportador.localizacion, localizacion1)


if __name__ == "__main__":
    unittest.main()
