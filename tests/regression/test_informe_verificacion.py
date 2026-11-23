"""Pruebas del veredicto y los objetivos de un ``InformeVerificacion``.

Comprueban tres cosas. Un informe refleja la simulación en el momento en que se
obtiene: no cambia cuando su simulación se reinicia o se vuelve a ejecutar. El
veredicto es el correcto en cada situación: una ejecución sin terminar es
``"INCOMPLETO"``, un plan terminado sin objetivos es ``"EJECUTABLE"``, y un error es
``"NO EJECUTABLE"``. Y los instantes en que un objetivo se logró y se rompió describen
el último periodo en el que se cumplió.
"""

from __future__ import annotations

import contextlib
import io
import logging
import unittest
from typing import TYPE_CHECKING

from simulador_pddl import (
    Brazo,
    Caja,
    CogerCaja,
    Contenido,
    Dron,
    DronEnLocalizacion,
    EntregarCaja,
    Localizacion,
    Mover,
    Mundo,
    Persona,
    PersonaTieneContenido,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from simulador_pddl import Accion, Objetivo
    from simulador_pddl.simulacion import InformeVerificacion


# Los contenidos de los problemas de este módulo. Un contenido no cambia al
# ejecutar un plan, así que todas las pruebas pueden compartirlos.
COMIDA = Contenido("comida")
CONTENIDOS = (COMIDA,)


class TestInformeNoSigueALaSimulacion(unittest.TestCase):
    """Un informe no cambia cuando cambia su simulación."""

    def setUp(self) -> None:
        """Silencia el registro y crea un plan que entrega una caja."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        deposito = Localizacion("deposito")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        caja = Caja("caja1", deposito, COMIDA)
        persona = Persona("persona1", deposito, COMIDA)
        self.mundo = Mundo(
            [
                CogerCaja(dron, brazo, caja, 0, 1),
                EntregarCaja(dron, brazo, caja, persona, 1, 1),
            ],
            localizaciones=[deposito],
            drones=[dron],
            cajas=[caja],
            personas=[persona],
            contenidos=CONTENIDOS,
            objetivos=[PersonaTieneContenido(persona, COMIDA)],
        )

    def ejecutar_plan(self) -> InformeVerificacion:
        """Ejecuta el plan en modo texto, sin imprimir, y devuelve su informe."""
        with contextlib.redirect_stdout(io.StringIO()):
            return self.mundo.simulacion_texto()

    def test_informe_no_cambia_tras_reiniciar(self) -> None:
        """Comprueba que ``reiniciar()`` no cambia un informe ya devuelto."""
        informe = self.ejecutar_plan()
        self.assertEqual(informe.veredicto, informe.VALIDO)
        logrado_en = informe.estados_objetivos[0].logrado_en

        self.mundo.reiniciar()

        self.assertEqual(informe.veredicto, informe.VALIDO)
        self.assertTrue(informe.estados_objetivos[0].cumplido)
        self.assertEqual(informe.estados_objetivos[0].logrado_en, logrado_en)

    def test_informe_tomado_antes_de_ejecutar_no_sigue_la_ejecucion(self) -> None:
        """Comprueba que un informe previo a la ejecución sigue ``"INCOMPLETO"``."""
        informe_antes = self.mundo.verificar()
        self.assertEqual(informe_antes.veredicto, informe_antes.INCOMPLETO)

        self.ejecutar_plan()

        self.assertEqual(informe_antes.veredicto, informe_antes.INCOMPLETO)
        self.assertIsNone(informe_antes.estados_objetivos[0].logrado_en)

    def test_nueva_ejecucion_tras_reiniciar_da_un_nuevo_informe_correcto(self) -> None:
        """Comprueba que una segunda ejecución da otro informe, también ``"VÁLIDO"``."""
        primero = self.ejecutar_plan()
        self.mundo.reiniciar()
        segundo = self.ejecutar_plan()

        self.assertEqual(primero.veredicto, primero.VALIDO)
        self.assertEqual(segundo.veredicto, segundo.VALIDO)
        self.assertIsNot(primero.estados_objetivos[0], segundo.estados_objetivos[0])


class TestExplicacionFalloNoSigueALaSimulacion(unittest.TestCase):
    """La explicación de un objetivo fallido es la del momento del informe."""

    def setUp(self) -> None:
        """Silencia el registro y crea un plan que deja al dron fuera de su objetivo."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.deposito = Localizacion("deposito")
        self.meta = Localizacion("meta")
        self.otro_sitio = Localizacion("otro_sitio")
        self.dron = Dron("dron1", self.deposito, [Brazo("brazo")])
        self.mundo = Mundo(
            [Mover(self.dron, self.deposito, self.otro_sitio, 0, 1)],
            localizaciones=[self.deposito, self.meta, self.otro_sitio],
            drones=[self.dron],
            cajas=[],
            personas=[],
            contenidos=[],
            objetivos=[DronEnLocalizacion(self.dron, self.meta)],
        )

    def test_explicacion_no_cambia_tras_reiniciar(self) -> None:
        """Comprueba que la explicación de un fallo sobrevive a ``reiniciar()``."""
        with contextlib.redirect_stdout(io.StringIO()):
            informe = self.mundo.simulacion_texto()
        esperado = (
            "el dron dron1 está en la localización otro_sitio, "
            "no en la localización meta"
        )
        self.assertEqual(informe.estados_objetivos[0].explicacion_fallo, esperado)

        self.mundo.reiniciar()

        self.assertEqual(informe.estados_objetivos[0].explicacion_fallo, esperado)
        self.assertIn(esperado, informe.resumen())


class TestEjecucionSinTerminar(unittest.TestCase):
    """Una ejecución detenida antes del final del plan es ``"INCOMPLETO"``."""

    def setUp(self) -> None:
        """Silencia el registro y crea un plan que sigue tras cumplir su objetivo."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        deposito = Localizacion("deposito")
        localizacion1 = Localizacion("localizacion1")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        caja = Caja("caja1", deposito, COMIDA)
        persona = Persona("persona1", localizacion1, COMIDA)
        # La caja se entrega en t=3, cuando termina EntregarCaja, y siguen dos
        # movimientos más.
        self.mundo = Mundo(
            [
                CogerCaja(dron, brazo, caja, 0, 1),
                Mover(dron, deposito, localizacion1, 1, 1),
                EntregarCaja(dron, brazo, caja, persona, 2, 1),
                Mover(dron, localizacion1, deposito, 3, 1),
                Mover(dron, deposito, localizacion1, 4, 1),
            ],
            localizaciones=[deposito, localizacion1],
            drones=[dron],
            cajas=[caja],
            personas=[persona],
            contenidos=CONTENIDOS,
            objetivos=[PersonaTieneContenido(persona, COMIDA)],
        )
        self.simulacion = self.mundo._simulacion

    def avanzar_hasta(self, instante: float) -> None:
        """Reproduce el plan hasta ``instante`` o hasta que termine."""
        self.simulacion._reproducir()
        while (
            self.simulacion._tiempo_simulacion < instante
            and not self.simulacion._terminada
        ):
            self.simulacion._actualizar(0.5)

    def test_objetivos_cumplidos_sin_terminar_el_plan_es_incompleto(self) -> None:
        """Comprueba que parar tras cumplir los objetivos da ``"INCOMPLETO"``."""
        self.avanzar_hasta(3.5)
        informe = self.simulacion._crear_informe()

        self.assertTrue(informe.todos_cumplidos)
        self.assertFalse(informe.completado)
        self.assertEqual(informe.veredicto, informe.INCOMPLETO)
        self.assertFalse(informe.es_valido)
        self.assertIn("INCOMPLETO", informe.resumen())

    def test_la_misma_ejecucion_terminada_es_valida(self) -> None:
        """Comprueba que la misma ejecución es ``"VÁLIDO"`` una vez termina el plan."""
        self.avanzar_hasta(3.5)
        self.avanzar_hasta(10)
        informe = self.simulacion._crear_informe()

        self.assertTrue(informe.completado)
        self.assertEqual(informe.veredicto, informe.VALIDO)
        self.assertTrue(informe.es_valido)

    def test_un_error_gana_a_incompleto(self) -> None:
        """Comprueba que un error gana a ``"INCOMPLETO"``.

        Una ejecución sin terminar en la que hay un error es ``"NO EJECUTABLE"``.
        """
        self.avanzar_hasta(1.5)
        self.simulacion._poner_error("fallo simulado")
        informe = self.simulacion._crear_informe()

        self.assertFalse(informe.completado)
        self.assertEqual(informe.veredicto, informe.NO_EJECUTABLE)


class TestPlanSinObjetivos(unittest.TestCase):
    """Un plan terminado sin objetivos es ``"EJECUTABLE"``.

    Si tiene objetivos y los cumple, es ``"VÁLIDO"``.
    """

    def setUp(self) -> None:
        """Silencia el registro."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def ejecutar_plan(
        self, objetivos_para: Callable[[Dron, Localizacion], list[Objetivo]]
    ) -> InformeVerificacion:
        """Ejecuta un plan de un solo ``Mover`` y devuelve su informe.

        ``objetivos_para`` recibe el dron y su destino y devuelve los objetivos.
        """
        deposito = Localizacion("deposito")
        localizacion1 = Localizacion("localizacion1")
        dron = Dron("dron1", deposito, [Brazo("brazo")])
        mundo = Mundo(
            [Mover(dron, deposito, localizacion1, 0, 1)],
            localizaciones=[deposito, localizacion1],
            drones=[dron],
            cajas=[],
            personas=[],
            contenidos=[],
            objetivos=objetivos_para(dron, localizacion1),
        )
        with contextlib.redirect_stdout(io.StringIO()):
            return mundo.simulacion_texto()

    def test_plan_terminado_sin_objetivos_es_ejecutable_no_valido(self) -> None:
        """Comprueba que un plan sin objetivos es ``"EJECUTABLE"``.

        También lo dice el resumen.
        """
        informe = self.ejecutar_plan(lambda _dron, _localizacion: [])

        self.assertEqual(informe.veredicto, informe.EJECUTABLE)
        self.assertFalse(informe.es_valido)
        self.assertIn("Veredicto: EJECUTABLE", informe.resumen())
        self.assertIn("Objetivos: no se han definido", informe.resumen())

    def test_el_mismo_plan_con_un_objetivo_que_cumple_es_valido(self) -> None:
        """Comprueba que el mismo plan con un objetivo que logra es ``"VÁLIDO"``."""
        informe = self.ejecutar_plan(
            lambda dron, localizacion: [DronEnLocalizacion(dron, localizacion)]
        )

        self.assertEqual(informe.veredicto, informe.VALIDO)
        self.assertTrue(informe.es_valido)

    def test_plan_vacio_sin_objetivos_es_ejecutable(self) -> None:
        """Comprueba que un plan vacío sin objetivos es ``"EJECUTABLE"``."""
        deposito = Localizacion("deposito")
        mundo = Mundo(
            [],
            localizaciones=[deposito],
            drones=[Dron("dron1", deposito, [Brazo("brazo")])],
            cajas=[],
            personas=[],
            contenidos=[],
        )
        with contextlib.redirect_stdout(io.StringIO()):
            informe = mundo.simulacion_texto()

        self.assertEqual(informe.veredicto, informe.EJECUTABLE)


class TestPeriodosDeObjetivos(unittest.TestCase):
    """``logrado_en`` y ``roto_en`` describen el último periodo en que se cumple."""

    def setUp(self) -> None:
        """Silencia el registro y crea un dron y dos localizaciones."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.deposito = Localizacion("deposito")
        self.localizacion1 = Localizacion("localizacion1")
        self.dron = Dron("dron1", self.deposito, [Brazo("brazo")])

    def ejecutar_plan(self, movimientos: list[Accion]) -> InformeVerificacion:
        """Ejecuta los movimientos. El objetivo es que el dron esté en el depósito."""
        mundo = Mundo(
            movimientos,
            localizaciones=[self.deposito, self.localizacion1],
            drones=[self.dron],
            cajas=[],
            personas=[],
            contenidos=[],
            objetivos=[DronEnLocalizacion(self.dron, self.deposito)],
        )
        with contextlib.redirect_stdout(io.StringIO()):
            return mundo.simulacion_texto()

    def test_objetivo_que_se_cumple_se_rompe_y_se_vuelve_a_cumplir(self) -> None:
        """Comprueba que ``logrado_en`` es el inicio del último periodo.

        Se cumple desde t=0, se rompe en t=1 y se vuelve a cumplir desde t=2.
        """
        informe = self.ejecutar_plan(
            [
                Mover(self.dron, self.deposito, self.localizacion1, 0, 1),
                Mover(self.dron, self.localizacion1, self.deposito, 1, 1),
            ]
        )
        estado = informe.estados_objetivos[0]

        self.assertTrue(estado.cumplido)
        self.assertEqual(estado.logrado_en, 2)
        self.assertIsNone(estado.roto_en)
        self.assertEqual(estado._texto_tiempos(), "cumplido desde t=2.00s")

    def test_objetivo_roto_definitivamente_tras_cumplirse_dos_veces(self) -> None:
        """Comprueba que ``logrado_en`` y ``roto_en`` son los del último periodo.

        Se cumple de t=0 a t=1 y de t=2 a t=3; después queda roto.
        """
        informe = self.ejecutar_plan(
            [
                Mover(self.dron, self.deposito, self.localizacion1, 0, 1),
                Mover(self.dron, self.localizacion1, self.deposito, 1, 1),
                Mover(self.dron, self.deposito, self.localizacion1, 2, 1),
            ]
        )
        estado = informe.estados_objetivos[0]

        self.assertFalse(estado.cumplido)
        self.assertEqual((estado.logrado_en, estado.roto_en), (2, 3))
        self.assertEqual(
            estado._texto_tiempos(), "se cumplió en t=2.00s y se rompió en t=3.00s"
        )


class TestInstanteObjetivoDeEntrega(unittest.TestCase):
    """Un objetivo de entrega se logra al terminar ``EntregarCaja``, no al empezar."""

    def setUp(self) -> None:
        """Silencia el registro y crea un plan cuyo ``EntregarCaja`` dura de 2 a 5."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        deposito = Localizacion("deposito")
        self.brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [self.brazo])
        self.caja = Caja("caja1", deposito, COMIDA)
        self.persona = Persona("persona1", deposito, COMIDA)
        self.mundo = Mundo(
            [
                CogerCaja(dron, self.brazo, self.caja, 0, 1),
                EntregarCaja(dron, self.brazo, self.caja, self.persona, 2, 3),
            ],
            localizaciones=[deposito],
            drones=[dron],
            cajas=[self.caja],
            personas=[self.persona],
            contenidos=CONTENIDOS,
            objetivos=[PersonaTieneContenido(self.persona, COMIDA)],
        )

    def test_objetivo_de_entrega_se_logra_al_terminar_la_entrega(self) -> None:
        """Comprueba que el objetivo se anota en t=5, el final de ``EntregarCaja``.

        Dar la caja a la persona es el efecto ``at end`` de ``EntregarCaja``.
        """
        with contextlib.redirect_stdout(io.StringIO()):
            informe = self.mundo.simulacion_texto()

        self.assertEqual(informe.veredicto, informe.VALIDO)
        self.assertEqual(informe.estados_objetivos[0].logrado_en, 5)

    def test_la_caja_sigue_en_el_brazo_mientras_dura_la_entrega(self) -> None:
        """Comprueba el estado en mitad de ``EntregarCaja``, y al final.

        En t=2.5 el dron todavía sujeta la caja, la persona todavía necesita su
        contenido y el objetivo no se cumple. Pedir un informe en ese momento no
        debe cambiar el instante que se anota después.
        """
        simulacion = self.mundo._simulacion
        simulacion._reproducir()
        simulacion._actualizar(2.5)

        self.assertIs(self.brazo.contenido, self.caja)
        self.assertNotIn(self.caja, self.persona.posee)
        self.assertEqual(self.persona.necesidades, [COMIDA])
        estado = self.mundo.verificar().estados_objetivos[0]
        self.assertFalse(estado.cumplido)
        self.assertIsNone(estado.logrado_en)

        simulacion._actualizar(10)

        self.assertIsNone(self.brazo.contenido)
        self.assertIn(self.caja, self.persona.posee)
        self.assertEqual(self.mundo.verificar().estados_objetivos[0].logrado_en, 5)


if __name__ == "__main__":
    unittest.main()
