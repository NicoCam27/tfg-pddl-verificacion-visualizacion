"""Pruebas del veredicto y los objetivos de un ``InformeVerificacion``.

Comprueban cuatro cosas. Un informe refleja la simulación en el momento en que se
obtiene: no cambia cuando su simulación se reinicia o se vuelve a ejecutar. El
veredicto es el que corresponde a cada situación: un plan que termina sin errores
y logra todos sus objetivos es ``"VÁLIDO"``, una ejecución sin terminar es
``"INCOMPLETO"``, un plan terminado sin objetivos es ``"EJECUTABLE"``, uno que no
logra todos sus objetivos es ``"NO RESUELVE"`` y un error es ``"NO EJECUTABLE"``.
Los instantes en que un objetivo se logró y se rompió describen el último periodo
en el que se cumplió. Y si falla una acción, el informe la devuelve, y
``simulacion_texto()`` la imprime.
"""

from __future__ import annotations

import contextlib
import io
import logging
import math
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


def crear_mundo_que_falla(*, al_terminar: bool) -> Mundo:
    """Crea un mundo cuyo plan falla al empezar o al terminar una acción.

    Al empezar: el dron va del depósito a loc1 de t=0 a t=1, y en t=1 intenta
    volver a salir del depósito. Al terminar: dos entregas de comida a la misma
    persona empiezan en t=1, y la que acaba en t=3 falla porque la persona ya
    recibió la comida en t=2.
    """
    deposito = Localizacion("deposito")
    loc1 = Localizacion("loc1")
    izquierdo = Brazo("izquierdo")
    derecho = Brazo("derecho")
    dron = Dron("dron1", deposito, [izquierdo, derecho])
    caja1 = Caja("caja1", deposito, COMIDA)
    caja2 = Caja("caja2", deposito, COMIDA)
    persona = Persona("persona1", deposito, COMIDA)

    if al_terminar:
        acciones: list[Accion] = [
            CogerCaja(dron, izquierdo, caja1, 0, 1),
            CogerCaja(dron, derecho, caja2, 0, 1),
            EntregarCaja(dron, izquierdo, caja1, persona, 1, 2),
            EntregarCaja(dron, derecho, caja2, persona, 1, 1),
        ]
    else:
        acciones = [
            Mover(dron, deposito, loc1, 0, 1),
            Mover(dron, deposito, loc1, 1, 1),
        ]
    return Mundo(
        acciones,
        localizaciones=[deposito, loc1],
        drones=[dron],
        cajas=[caja1, caja2],
        personas=[persona],
        contenidos=CONTENIDOS,
    )


class TestAccionFallida(unittest.TestCase):
    """El informe devuelve la acción que falló, y la salida de texto la nombra."""

    def setUp(self) -> None:
        """Silencia el registro."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_el_informe_devuelve_la_accion_que_fallo_y_cuando(self) -> None:
        """Comprueba la acción fallida y su instante, con y sin fallos.

        Es la misma acción del plan, no una copia. Si la acción falla al empezar,
        ``fallo_en`` es su ``inicio_sim``, y si falla al terminar, su
        ``tiempo_fin``. Un informe sin fallos no tiene acción fallida ni instante.
        """
        casos = {False: (1, 1), True: (2, 3)}
        for al_terminar, (indice, instante) in casos.items():
            with self.subTest(al_terminar=al_terminar):
                mundo = crear_mundo_que_falla(al_terminar=al_terminar)
                informe = mundo.avanzar_hasta(math.inf)
                self.assertIs(
                    informe.accion_fallida, mundo._simulacion._acciones[indice]
                )
                self.assertEqual(informe.fallo_en, instante)

        mundo = crear_mundo_que_falla(al_terminar=True)
        informe = mundo.avanzar_hasta(0.5)
        self.assertIsNone(informe.accion_fallida)
        self.assertIsNone(informe.fallo_en)

    def test_un_informe_conserva_su_accion_fallida_al_reiniciar(self) -> None:
        """Comprueba que ``reiniciar()`` no cambia la acción fallida de un informe.

        Tampoco cambia su instante, aunque la acción ya no conste como empezada.
        """
        mundo = crear_mundo_que_falla(al_terminar=True)
        informe = mundo.avanzar_hasta(math.inf)
        fallida = informe.accion_fallida

        mundo.reiniciar()

        self.assertIsNotNone(fallida)
        self.assertIs(informe.accion_fallida, fallida)
        self.assertEqual(informe.fallo_en, 3)
        nuevo = mundo.verificar()
        self.assertIsNone(nuevo.accion_fallida)
        self.assertIsNone(nuevo.fallo_en)

    def test_la_salida_de_texto_nombra_la_accion_que_fallo(self) -> None:
        """Comprueba la línea ``NO INICIA`` o ``NO TERMINA``, justo antes del error.

        Va en el instante en que falla la acción: su inicio o su final.
        """
        casos = {
            False: (
                "[t=  1.00s] NO INICIA Mover(dron=dron1, origen=deposito, "
                "destino=loc1, inicio_sim=1, duracion_sim=1)"
            ),
            True: (
                "[t=  3.00s] NO TERMINA EntregarCaja(dron=dron1, brazo=izquierdo, "
                "caja=caja1, persona=persona1, inicio_sim=1, duracion_sim=2)"
            ),
        }
        for al_terminar, linea in casos.items():
            with self.subTest(al_terminar=al_terminar):
                mundo = crear_mundo_que_falla(al_terminar=al_terminar)
                salida = io.StringIO()
                with contextlib.redirect_stdout(salida):
                    informe = mundo.simulacion_texto()

                lineas = salida.getvalue().splitlines()
                error = f"Error en la simulación: {informe.error}"
                # Entre la línea y el error hay una línea en blanco.
                self.assertEqual(lineas[lineas.index(error) - 2], linea)


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

    def test_nueva_ejecucion_tras_reiniciar_da_un_nuevo_informe_valido(self) -> None:
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
        """Comprueba que ``reiniciar()`` no cambia la explicación de un fallo."""
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

    def test_objetivos_cumplidos_sin_terminar_el_plan_es_incompleto(self) -> None:
        """Comprueba que parar tras cumplir los objetivos da ``"INCOMPLETO"``."""
        informe = self.mundo.avanzar_hasta(3.5)

        self.assertTrue(informe.todos_cumplidos)
        self.assertFalse(informe.completado)
        self.assertEqual(informe.veredicto, informe.INCOMPLETO)
        self.assertFalse(informe.es_valido)
        self.assertIn("INCOMPLETO", informe.resumen())

    def test_la_misma_ejecucion_terminada_es_valida(self) -> None:
        """Comprueba que la misma ejecución es ``"VÁLIDO"`` una vez termina el plan."""
        self.mundo.avanzar_hasta(3.5)
        informe = self.mundo.avanzar_hasta(10)

        self.assertTrue(informe.completado)
        self.assertEqual(informe.veredicto, informe.VALIDO)
        self.assertTrue(informe.es_valido)

    def test_un_error_prevalece_sobre_incompleto(self) -> None:
        """Comprueba que un error prevalece sobre ``"INCOMPLETO"``.

        Una ejecución sin terminar en la que hay un error es ``"NO EJECUTABLE"``.
        """
        self.mundo.avanzar_hasta(1.5)
        self.simulacion._poner_error(
            "fallo simulado", self.simulacion._acciones_activas[0]
        )
        informe = self.simulacion._crear_informe()

        self.assertFalse(informe.completado)
        self.assertEqual(informe.veredicto, informe.NO_EJECUTABLE)


class TestPlanSinObjetivos(unittest.TestCase):
    """Un plan terminado sin objetivos es ``"EJECUTABLE"``.

    Si tiene objetivos y los cumple, es ``"VÁLIDO"``, y si no, ``"NO RESUELVE"``.
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

    def test_plan_terminado_sin_objetivos_es_ejecutable_no_es_valido(self) -> None:
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

    def test_el_mismo_plan_con_un_objetivo_que_no_cumple_no_resuelve(self) -> None:
        """Comprueba que el plan con un objetivo que no logra es ``"NO RESUELVE"``.

        El objetivo es que el dron esté en el depósito: se cumple al empezar y se
        rompe cuando el dron llega a su destino. El plan se ejecuta entero sin
        errores, pero no lo resuelve.
        """
        informe = self.ejecutar_plan(
            lambda dron, _localizacion: [DronEnLocalizacion(dron, dron.localizacion)]
        )

        self.assertEqual(informe.veredicto, informe.NO_RESUELVE)
        self.assertTrue(informe.ejecutable)
        self.assertTrue(informe.completado)
        self.assertFalse(informe.es_valido)
        self.assertIn("Veredicto: NO RESUELVE", informe.resumen())

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

        Se cumple de t=0 a t=1 y de t=2 a t=3. Después queda roto.
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

        Entregar la caja a la persona es el efecto ``at end`` de ``EntregarCaja``.
        """
        with contextlib.redirect_stdout(io.StringIO()):
            informe = self.mundo.simulacion_texto()

        self.assertEqual(informe.veredicto, informe.VALIDO)
        self.assertEqual(informe.estados_objetivos[0].logrado_en, 5)

    def test_la_caja_sigue_en_el_brazo_mientras_dura_la_entrega(self) -> None:
        """Comprueba el estado a mitad de ``EntregarCaja`` y al final.

        En t=2.5 el dron todavía sujeta la caja, la persona todavía necesita su
        contenido y el objetivo no se cumple. Pedir un informe en ese momento no
        debe cambiar el instante que se anota después.
        """
        simulacion = self.mundo._simulacion
        simulacion._reproducir()
        simulacion._actualizar(2.5)

        self.assertIs(self.brazo.caja, self.caja)
        self.assertNotIn(self.caja, self.persona.posee)
        self.assertEqual(self.persona.necesidades, [COMIDA])
        estado = self.mundo.verificar().estados_objetivos[0]
        self.assertFalse(estado.cumplido)
        self.assertIsNone(estado.logrado_en)

        simulacion._actualizar(10)

        self.assertIsNone(self.brazo.caja)
        self.assertIn(self.caja, self.persona.posee)
        self.assertEqual(self.mundo.verificar().estados_objetivos[0].logrado_en, 5)


if __name__ == "__main__":
    unittest.main()
