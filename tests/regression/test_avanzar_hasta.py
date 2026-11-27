"""Pruebas de ``Mundo.avanzar_hasta()``.

El método ejecuta el plan hasta un instante, sin imprimir nada, y devuelve el
informe de ese punto. Las pruebas comprueban dónde se detiene (a mitad de una
acción, en el instante en que empieza una, al terminar el plan o al fallar una
acción), que ejecutar por partes da lo mismo que ejecutar de una vez, que se
puede seguir después con ``simulacion_texto()`` y qué argumentos rechaza.
"""

from __future__ import annotations

import contextlib
import io
import logging
import math
import unittest

from simulador_pddl import (
    Brazo,
    Caja,
    CogerCaja,
    Contenido,
    Dron,
    EntregarCaja,
    InformeVerificacion,
    Localizacion,
    Mover,
    Mundo,
    Persona,
    PersonaTieneContenido,
)

# Los contenidos de los problemas de este módulo. Un contenido no cambia al
# ejecutar un plan, así que todas las pruebas pueden compartirlos.
COMIDA = Contenido("comida")
CONTENIDOS = (COMIDA,)


class TestAvanzarHasta(unittest.TestCase):
    """``avanzar_hasta()`` ejecuta el plan hasta el instante pedido."""

    def setUp(self) -> None:
        """Silencia el registro y crea un plan que lleva una caja a una persona.

        El dron coge la caja de t=0 a t=1, va del depósito a loc1 de t=1 a t=3 y
        entrega la caja de t=3 a t=4.
        """
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.mundo = self._crear_mundo()

    def _crear_mundo(self) -> Mundo:
        """Crea el problema y el plan, y guarda los objetos en la prueba."""
        self.deposito = Localizacion("deposito")
        self.loc1 = Localizacion("loc1")
        self.brazo = Brazo("brazo")
        self.dron = Dron("dron1", self.deposito, [self.brazo])
        self.caja = Caja("caja1", self.deposito, COMIDA)
        self.persona = Persona("persona1", self.loc1, COMIDA)
        self.coger = CogerCaja(self.dron, self.brazo, self.caja, inicio_sim=0)
        self.mover = Mover(
            self.dron, self.deposito, self.loc1, inicio_sim=1, duracion_sim=2
        )
        self.entregar = EntregarCaja(
            self.dron, self.brazo, self.caja, self.persona, inicio_sim=3
        )
        return Mundo(
            [self.coger, self.mover, self.entregar],
            localizaciones=[self.deposito, self.loc1],
            drones=[self.dron],
            cajas=[self.caja],
            personas=[self.persona],
            contenidos=CONTENIDOS,
            objetivos=[PersonaTieneContenido(self.persona, COMIDA)],
        )

    def _resumir(
        self, informe: InformeVerificacion
    ) -> tuple[Localizacion, bool, int, str]:
        """Devuelve el estado del dron y el del informe, para compararlos."""
        return (
            self.dron.localizacion,
            self.brazo.caja is self.caja,
            informe.acciones_terminadas,
            informe.veredicto,
        )

    def test_a_mitad_del_plan_el_informe_es_incompleto(self) -> None:
        """Comprueba que a mitad de una acción el plan queda sin terminar."""
        informe = self.mundo.avanzar_hasta(1.5)

        self.assertEqual(informe.veredicto, InformeVerificacion.INCOMPLETO)
        self.assertEqual(self.dron.localizacion, self.deposito)
        self.assertIs(self.brazo.caja, self.caja)

    def test_una_accion_que_empieza_en_el_instante_queda_recien_empezada(
        self,
    ) -> None:
        """Comprueba que se aplican todos los sucesos del instante pedido.

        En t=1 termina ``CogerCaja`` y empieza ``Mover``: los finales se aplican
        antes que los inicios, y los dos se aplican.
        """
        self.mundo.avanzar_hasta(1)

        self.assertTrue(self.coger.terminada)
        self.assertTrue(self.mover.iniciada)
        self.assertFalse(self.mover.terminada)

    def test_por_partes_da_lo_mismo_que_de_una_vez(self) -> None:
        """Comprueba que el resultado no depende de cuántas veces se avance.

        Avanzar dos veces hasta el mismo instante tampoco cambia nada.
        """
        for instante in (0.3, 1, 1, 2.7, 3.5):
            informe = self.mundo.avanzar_hasta(instante)
        por_partes = self._resumir(informe)

        de_una_vez = self._resumir(self._crear_mundo().avanzar_hasta(3.5))

        self.assertEqual(por_partes, de_una_vez)

    def test_mas_alla_del_final_el_plan_termina(self) -> None:
        """Comprueba que un instante posterior al plan lo lleva hasta el final.

        El reloj se queda en el último suceso del plan, t=4, no en el instante
        pedido.
        """
        for instante in (100, math.inf):
            with self.subTest(instante=instante):
                mundo = self._crear_mundo()
                informe = mundo.avanzar_hasta(instante)

                self.assertEqual(informe.veredicto, InformeVerificacion.VALIDO)
                self.assertEqual(mundo._simulacion._tiempo_simulacion, 4)

    def test_no_imprime_nada(self) -> None:
        """Comprueba que no escribe nada en la salida estándar."""
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            self.mundo.avanzar_hasta(2)
            self.mundo.avanzar_hasta(math.inf)

        self.assertEqual(salida.getvalue(), "")

    def test_se_puede_seguir_con_la_simulacion_en_texto(self) -> None:
        """Comprueba que ``simulacion_texto()`` sigue desde donde se dejó el plan."""
        self.mundo.avanzar_hasta(2)
        with contextlib.redirect_stdout(io.StringIO()):
            informe = self.mundo.simulacion_texto()

        self.assertEqual(informe.veredicto, InformeVerificacion.VALIDO)

    def test_un_plan_que_falla_se_detiene_en_el_error(self) -> None:
        """Comprueba que una acción que falla detiene la ejecución en ese instante.

        El primer movimiento deja al dron en loc1 en t=1. El segundo empieza en ese
        instante y sale del depósito, donde el dron ya no está, así que falla. La
        ejecución se detiene en t=1 sin lanzar una excepción, aunque se pida avanzar
        hasta ``math.inf``.
        """
        deposito, loc1 = Localizacion("deposito"), Localizacion("loc1")
        dron = Dron("dron1", deposito, [])
        mundo = Mundo(
            [
                Mover(dron, deposito, loc1, inicio_sim=0),
                Mover(dron, deposito, loc1, inicio_sim=1),
            ],
            localizaciones=[deposito, loc1],
            drones=[dron],
            cajas=[],
            personas=[],
            contenidos=CONTENIDOS,
        )

        informe = mundo.avanzar_hasta(math.inf)

        self.assertEqual(informe.veredicto, InformeVerificacion.NO_EJECUTABLE)
        self.assertIsNotNone(informe.error)
        self.assertEqual(mundo._simulacion._tiempo_simulacion, 1)

    def test_un_instante_que_no_es_un_numero_lanza_type_error(self) -> None:
        """Comprueba que el instante tiene que ser un int o un float."""
        for instante in ("1", True):
            with self.subTest(instante=instante), self.assertRaises(TypeError):
                self.mundo.avanzar_hasta(instante)  # type: ignore[arg-type]

    def test_un_instante_negativo_nan_o_pasado_lanza_value_error(self) -> None:
        """Comprueba que el instante no puede ser negativo, NaN ni ya pasado.

        Para volver atrás hay que reiniciar, y el mensaje lo dice.
        """
        for instante in (-1, math.nan):
            with self.subTest(instante=instante), self.assertRaises(ValueError):
                self.mundo.avanzar_hasta(instante)

        self.mundo.avanzar_hasta(2)
        with self.assertRaises(ValueError) as contexto:
            self.mundo.avanzar_hasta(1)
        self.assertIn("reiniciar()", str(contexto.exception))


if __name__ == "__main__":
    unittest.main()
