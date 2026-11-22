"""Pruebas de principio a fin de cada tipo de acción.

Cada prueba ejecuta un plan corto y comprueba el estado que dejan
las fases ``at start`` y ``at end``, incluido un movimiento cuyo origen no es
donde está el dron, que falla cuando empieza.
"""

from __future__ import annotations

import contextlib
import io
import unittest
from typing import TYPE_CHECKING, Any

from simulador_pddl.acciones import (
    CogerCaja,
    CogerTransportador,
    EntregarCaja,
    Mover,
    MoverTransportador,
    PonerCajaEnTransportador,
    SacarCajaDeTransportador,
    Soltar,
    SoltarTransportador,
)
from simulador_pddl.mundo import Mundo
from simulador_pddl.objetivos import PersonaTieneContenido
from simulador_pddl.objetos import (
    Brazo,
    Caja,
    Dron,
    Localizacion,
    Persona,
    Transportador,
)

if TYPE_CHECKING:
    from simulador_pddl.simulacion import InformeVerificacion


def ejecutar_plan(mundo: Mundo, paso_tiempo: float) -> InformeVerificacion:
    """Ejecuta el plan en modo texto, sin imprimir, y devuelve su informe."""
    with contextlib.redirect_stdout(io.StringIO()):
        return mundo.simulacion_texto(paso_tiempo)


class TestEntregarCajaAPersona(unittest.TestCase):
    """``CogerCaja`` y ``EntregarCaja``: una caja se entrega a una persona."""

    def test_coger_y_entregar_entrega_la_caja(self) -> None:
        """Comprueba que coger y entregar una caja la entrega y libera el brazo."""
        deposito = Localizacion("deposito")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        caja = Caja("caja1", deposito, "comida")
        persona = Persona("persona1", deposito, necesidades="comida")

        objetivos = [PersonaTieneContenido(persona, "comida")]

        acciones = [
            CogerCaja(dron=dron, brazo=brazo, caja=caja, inicio_sim=0, duracion_sim=1),
            EntregarCaja(
                dron=dron,
                brazo=brazo,
                caja=caja,
                persona=persona,
                inicio_sim=1,
                duracion_sim=1,
            ),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito],
            drones=[dron],
            cajas=[caja],
            personas=[persona],
            objetivos=objetivos,
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertEqual(informe.veredicto, informe.VALIDO)
        self.assertIsNone(brazo.contenido)

    def test_segunda_entrega_solapada_de_un_contenido_se_rechaza(self) -> None:
        """Comprueba que una persona no recibe dos veces el mismo contenido a la vez.

        Las dos acciones ``EntregarCaja`` empiezan mientras la persona todavía
        necesita la comida, ya que la necesidad solo se quita cuando termina una
        entrega. La primera en terminar entrega su caja y la segunda falla entonces.
        Su caja se queda en el brazo de su dron.
        """
        deposito = Localizacion("deposito")
        brazo1 = Brazo("brazo1")
        brazo2 = Brazo("brazo2")
        dron1 = Dron("dron1", deposito, [brazo1])
        dron2 = Dron("dron2", deposito, [brazo2])
        caja1 = Caja("caja1", deposito, "comida")
        caja2 = Caja("caja2", deposito, "comida")
        persona = Persona("persona1", deposito, necesidades="comida")

        acciones = [
            CogerCaja(dron1, brazo1, caja1, inicio_sim=0, duracion_sim=1),
            CogerCaja(dron2, brazo2, caja2, inicio_sim=0, duracion_sim=1),
            EntregarCaja(dron1, brazo1, caja1, persona, inicio_sim=1, duracion_sim=2),
            EntregarCaja(dron2, brazo2, caja2, persona, inicio_sim=2, duracion_sim=2),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito],
            drones=[dron1, dron2],
            cajas=[caja1, caja2],
            personas=[persona],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertFalse(informe.ejecutable)
        self.assertEqual(
            informe.error,
            "la caja caja2 no se puede entregar a la persona persona1: tiene "
            "'comida', y la persona no necesita nada",
        )
        self.assertIn(caja1, persona.posee)
        self.assertNotIn(caja2, persona.posee)
        self.assertIs(brazo2.contenido, caja2)
        self.assertIs(caja2.propietario_actual, dron2)

    def test_entregar_un_contenido_que_la_persona_no_necesita_falla_al_empezar(
        self,
    ) -> None:
        """Comprueba que el error dice qué tiene la caja y qué necesita la persona."""
        deposito = Localizacion("deposito")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        caja = Caja("caja1", deposito, "medicina")
        persona = Persona("persona1", deposito, necesidades=["comida", "agua"])

        acciones = [
            CogerCaja(dron, brazo, caja, inicio_sim=0, duracion_sim=1),
            EntregarCaja(dron, brazo, caja, persona, inicio_sim=1, duracion_sim=1),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito],
            drones=[dron],
            cajas=[caja],
            personas=[persona],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertEqual(
            informe.error,
            "la caja caja1 no se puede entregar a la persona persona1: tiene "
            "'medicina', y la persona necesita 'comida' y 'agua'",
        )
        self.assertFalse(acciones[1].iniciada)
        self.assertIs(brazo.contenido, caja)
        self.assertEqual(persona.necesidades, ["comida", "agua"])

    def test_entregar_una_caja_que_el_brazo_no_sujeta_falla_al_empezar(
        self,
    ) -> None:
        """Comprueba que el error culpa al brazo por no sujetar la caja al entregar."""
        localizacion1 = Localizacion("localizacion1")
        localizacion2 = Localizacion("localizacion2")
        brazo = Brazo("brazo")
        dron = Dron("dron1", localizacion1, [brazo])
        caja = Caja("caja1", localizacion2, "comida")
        persona = Persona("persona1", localizacion1, necesidades="comida")

        acciones = [
            EntregarCaja(dron, brazo, caja, persona, inicio_sim=0, duracion_sim=1),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[localizacion1, localizacion2],
            drones=[dron],
            cajas=[caja],
            personas=[persona],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertEqual(
            informe.error, "el brazo brazo no sujeta la caja caja1, está vacío"
        )
        self.assertFalse(acciones[0].iniciada)

    # TODO(NicoCam27): cuando se implemente el objeto Contenido, no existirán
    # necesidades repetidas y este caso se quitará.
    # NOMULTIPLECONTENT-1
    def test_caja_ya_entregada_no_se_puede_volver_a_entregar(self) -> None:
        """Comprueba que entregar una caja que la persona ya tiene falla al empezar.

        La persona necesita el contenido dos veces, así que el segundo
        ``EntregarCaja`` pasa la comprobación de necesidades. Nombra la caja que
        entregó el primero, que ya no está en el brazo: el error tiene que decir
        que la persona ya la tiene, no solo que el brazo está vacío. Nada cambia
        después del error.
        """
        deposito = Localizacion("deposito")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        caja = Caja("caja1", deposito, "comida")
        persona = Persona("persona1", deposito, necesidades=["comida", "comida"])

        acciones = [
            CogerCaja(dron, brazo, caja, inicio_sim=0, duracion_sim=1),
            EntregarCaja(dron, brazo, caja, persona, inicio_sim=1, duracion_sim=1),
            EntregarCaja(dron, brazo, caja, persona, inicio_sim=2, duracion_sim=1),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito],
            drones=[dron],
            cajas=[caja],
            personas=[persona],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertEqual(informe.veredicto, informe.NO_EJECUTABLE)
        self.assertEqual(
            informe.error,
            "la caja caja1 no se puede entregar a la persona persona1, ya la posee",
        )
        self.assertEqual(persona.posee, [caja])
        self.assertEqual(persona.necesidades, ["comida"])
        self.assertIs(caja.propietario_actual, persona)
        self.assertIsNone(brazo.contenido)


class TestSoltar(unittest.TestCase):
    """``Soltar``: una caja se deja en la localización del dron."""

    def test_coger_mover_soltar_deja_la_caja_en_la_nueva_localizacion(self) -> None:
        """Comprueba que una caja soltada queda disponible en la nueva localización."""
        deposito = Localizacion("deposito")
        localizacion1 = Localizacion("localizacion1")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        caja = Caja("caja1", deposito, "comida")

        acciones = [
            CogerCaja(dron=dron, brazo=brazo, caja=caja, inicio_sim=0, duracion_sim=1),
            Mover(
                dron=dron,
                origen=deposito,
                destino=localizacion1,
                inicio_sim=1,
                duracion_sim=1,
            ),
            Soltar(dron=dron, brazo=brazo, caja=caja, inicio_sim=2, duracion_sim=1),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito, localizacion1],
            drones=[dron],
            cajas=[caja],
            personas=[],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertEqual(caja.localizacion, localizacion1)
        self.assertEqual(caja.estado, Caja.DISPONIBLE)
        self.assertIsNone(caja.propietario_actual)
        self.assertIsNone(brazo.contenido)

    def test_coger_por_otro_dron_durante_soltar_se_rechaza(self) -> None:
        """Comprueba que una caja no se puede coger mientras se está soltando.

        El dron conserva la caja hasta el final de ``Soltar``. Si otro dron
        intenta cogerla entre medias, el plan no es ejecutable.
        """
        deposito = Localizacion("deposito")
        brazo1 = Brazo("brazo1")
        brazo2 = Brazo("brazo2")
        dron1 = Dron("dron1", deposito, [brazo1])
        dron2 = Dron("dron2", deposito, [brazo2])
        caja = Caja("caja1", deposito, "comida")

        acciones = [
            CogerCaja(
                dron=dron1, brazo=brazo1, caja=caja, inicio_sim=0, duracion_sim=1
            ),
            Soltar(dron=dron1, brazo=brazo1, caja=caja, inicio_sim=1, duracion_sim=1),
            CogerCaja(
                dron=dron2, brazo=brazo2, caja=caja, inicio_sim=1.5, duracion_sim=1
            ),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito],
            drones=[dron1, dron2],
            cajas=[caja],
            personas=[],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertFalse(informe.ejecutable)
        self.assertIn("caja1", informe.error or "")

    def test_la_caja_sigue_en_el_brazo_hasta_que_termina_soltar(self) -> None:
        """Comprueba que ``Soltar`` suelta la caja cuando termina, no cuando empieza."""
        deposito = Localizacion("deposito")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        caja = Caja("caja1", deposito, "comida")

        acciones = [
            CogerCaja(dron=dron, brazo=brazo, caja=caja, inicio_sim=0, duracion_sim=1),
            Soltar(dron=dron, brazo=brazo, caja=caja, inicio_sim=1, duracion_sim=2),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito],
            drones=[dron],
            cajas=[caja],
            personas=[],
        )

        mundo._simulacion._reproducir()
        # A mitad de Soltar.
        mundo._simulacion._actualizar(2.0)

        self.assertIs(brazo.contenido, caja)
        self.assertEqual(caja.estado, Caja.TRANSPORTADA)
        self.assertIs(caja.propietario_actual, dron)

        mundo._simulacion._actualizar(10)

        self.assertIsNone(brazo.contenido)
        self.assertEqual(caja.estado, Caja.DISPONIBLE)
        self.assertIsNone(caja.propietario_actual)


class TestCogerCajaQueYaEsDelDron(unittest.TestCase):
    """``CogerCaja`` de una caja que ya es del mismo dron, con otro brazo."""

    def setUp(self) -> None:
        """Crea un dron con dos brazos, una caja y un transportador en el depósito."""
        self.deposito = Localizacion("deposito")
        self.izquierdo = Brazo("izquierdo")
        self.derecho = Brazo("derecho")
        self.dron = Dron("dron1", self.deposito, [self.izquierdo, self.derecho])
        self.caja = Caja("caja1", self.deposito, "comida")
        self.transportador = Transportador("transportador1", self.deposito, 4)

    def ejecutar(self, acciones: list[Any]) -> InformeVerificacion:
        """Ejecuta las acciones como un plan y devuelve su informe."""
        mundo = Mundo(
            acciones,
            localizaciones=[self.deposito],
            drones=[self.dron],
            cajas=[self.caja],
            personas=[],
            transportadores=[self.transportador],
        )
        return ejecutar_plan(mundo, paso_tiempo=0.1)

    def test_cogerla_mientras_la_coge_con_otro_brazo_falla_al_empezar(self) -> None:
        """Comprueba el error de coger una caja que el dron ya está cogiendo."""
        acciones = [
            CogerCaja(
                self.dron, self.izquierdo, self.caja, inicio_sim=0, duracion_sim=2
            ),
            CogerCaja(
                self.dron, self.derecho, self.caja, inicio_sim=0.5, duracion_sim=1
            ),
        ]
        informe = self.ejecutar(acciones)

        self.assertFalse(informe.ejecutable)
        self.assertIn(
            "el dron dron1 no puede coger la caja caja1, ya la está cogiendo o "
            "sacando de un transportador con otro brazo",
            informe.error or "",
        )
        self.assertFalse(acciones[1].iniciada)

    def test_cogerla_cuando_ya_la_sujeta_con_otro_brazo_falla_al_empezar(
        self,
    ) -> None:
        """Comprueba que el error nombra el brazo que ya sujeta la caja."""
        acciones = [
            CogerCaja(
                self.dron, self.izquierdo, self.caja, inicio_sim=0, duracion_sim=1
            ),
            CogerCaja(self.dron, self.derecho, self.caja, inicio_sim=1, duracion_sim=1),
        ]
        informe = self.ejecutar(acciones)

        self.assertFalse(informe.ejecutable)
        self.assertIn(
            "el dron dron1 no puede coger la caja caja1, "
            "ya la sujeta con el brazo izquierdo",
            informe.error or "",
        )
        self.assertIs(self.izquierdo.contenido, self.caja)
        self.assertIsNone(self.derecho.contenido)

    def test_cogerla_mientras_la_saca_de_un_transportador_falla_al_empezar(
        self,
    ) -> None:
        """Comprueba el error de coger una caja que el dron ya está sacando."""
        acciones = [
            CogerCaja(
                self.dron, self.izquierdo, self.caja, inicio_sim=0, duracion_sim=1
            ),
            PonerCajaEnTransportador(
                self.dron,
                self.izquierdo,
                self.caja,
                self.transportador,
                inicio_sim=1,
                duracion_sim=1,
            ),
            SacarCajaDeTransportador(
                self.dron,
                self.izquierdo,
                self.caja,
                self.transportador,
                inicio_sim=2,
                duracion_sim=2,
            ),
            CogerCaja(self.dron, self.derecho, self.caja, inicio_sim=3, duracion_sim=1),
        ]
        informe = self.ejecutar(acciones)

        self.assertFalse(informe.ejecutable)
        self.assertIn(
            "el dron dron1 no puede coger la caja caja1, ya la está cogiendo o "
            "sacando de un transportador con otro brazo",
            informe.error or "",
        )
        self.assertFalse(acciones[3].iniciada)


class TestIdaYVueltaTransportador(unittest.TestCase):
    """Poner y sacar una caja de un transportador: la caja entra y sale."""

    def test_la_caja_va_del_dron_al_transportador_y_vuelve(self) -> None:
        """Comprueba que una caja que entra y sale acaba en el brazo."""
        deposito = Localizacion("deposito")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        caja = Caja("caja1", deposito, "comida")
        transportador = Transportador("transportador1", deposito, 4)

        acciones = [
            CogerCaja(dron=dron, brazo=brazo, caja=caja, inicio_sim=0, duracion_sim=1),
            PonerCajaEnTransportador(
                dron=dron,
                brazo=brazo,
                caja=caja,
                transportador=transportador,
                inicio_sim=1,
                duracion_sim=1,
            ),
            SacarCajaDeTransportador(
                dron=dron,
                brazo=brazo,
                caja=caja,
                transportador=transportador,
                inicio_sim=2,
                duracion_sim=1,
            ),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito],
            drones=[dron],
            cajas=[caja],
            personas=[],
            transportadores=[transportador],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertIs(brazo.contenido, caja)
        self.assertNotIn(caja, transportador.cajas_dentro)

    def test_capacidad_del_transportador_respetada_entre_acciones_distintas(
        self,
    ) -> None:
        """Comprueba que un transportador con un solo hueco rechaza una segunda caja."""
        deposito = Localizacion("deposito")
        brazo_izquierdo = Brazo("izquierda")
        brazo_derecho = Brazo("derecha")
        dron = Dron("dron1", deposito, [brazo_izquierdo, brazo_derecho])
        caja_a = Caja("cajaA", deposito, "comida")
        caja_b = Caja("cajaB", deposito, "medicina")
        # Solo hay sitio para una caja.
        transportador = Transportador("transportador1", deposito, 1)

        acciones = [
            CogerCaja(
                dron=dron,
                brazo=brazo_izquierdo,
                caja=caja_a,
                inicio_sim=0,
                duracion_sim=1,
            ),
            CogerCaja(
                dron=dron,
                brazo=brazo_derecho,
                caja=caja_b,
                inicio_sim=0,
                duracion_sim=1,
            ),
            PonerCajaEnTransportador(
                dron=dron,
                brazo=brazo_izquierdo,
                caja=caja_a,
                transportador=transportador,
                inicio_sim=1,
                duracion_sim=1,
            ),
            PonerCajaEnTransportador(
                dron=dron,
                brazo=brazo_derecho,
                caja=caja_b,
                transportador=transportador,
                inicio_sim=2.5,
                duracion_sim=1,
            ),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito],
            drones=[dron],
            cajas=[caja_a, caja_b],
            personas=[],
            transportadores=[transportador],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertFalse(informe.ejecutable)
        self.assertIn("capacidad", informe.error or "")


class TestCajaQueNoEstaEnElBrazoNiEnElTransportador(unittest.TestCase):
    """Meter una caja que el brazo no sujeta y sacar una que no está dentro.

    El error tiene que nombrar esa causa: el brazo vacío o la caja que no está
    en el transportador.
    """

    def setUp(self) -> None:
        """Crea el dron y el transportador en una localización y la caja en otra."""
        self.localizacion1 = Localizacion("localizacion1")
        self.localizacion2 = Localizacion("localizacion2")
        self.brazo = Brazo("brazo")
        self.dron = Dron("dron1", self.localizacion1, [self.brazo])
        self.caja = Caja("caja1", self.localizacion2, "comida")
        self.transportador = Transportador("transportador1", self.localizacion1, 4)

    def ejecutar(self, acciones: list[Any]) -> InformeVerificacion:
        """Ejecuta las acciones como un plan y devuelve su informe."""
        mundo = Mundo(
            acciones,
            localizaciones=[self.localizacion1, self.localizacion2],
            drones=[self.dron],
            cajas=[self.caja],
            personas=[],
            transportadores=[self.transportador],
        )
        return ejecutar_plan(mundo, paso_tiempo=0.1)

    def test_meterla_falla_porque_el_brazo_no_la_sujeta(self) -> None:
        """Comprueba que ``PonerCajaEnTransportador`` culpa al brazo vacío."""
        acciones = [
            PonerCajaEnTransportador(
                self.dron,
                self.brazo,
                self.caja,
                self.transportador,
                inicio_sim=0,
                duracion_sim=1,
            ),
        ]
        informe = self.ejecutar(acciones)

        self.assertEqual(
            informe.error, "el brazo brazo no sujeta la caja caja1, está vacío"
        )
        self.assertFalse(acciones[0].iniciada)

    def test_sacarla_falla_porque_no_esta_en_el_transportador(self) -> None:
        """Comprueba que ``SacarCajaDeTransportador`` dice que la caja no está."""
        acciones = [
            SacarCajaDeTransportador(
                self.dron,
                self.brazo,
                self.caja,
                self.transportador,
                inicio_sim=0,
                duracion_sim=1,
            ),
        ]
        informe = self.ejecutar(acciones)

        self.assertEqual(
            informe.error,
            "la caja caja1 no está en el transportador transportador1",
        )
        self.assertFalse(acciones[0].iniciada)


class TestCogerYSoltarTransportadorSueltos(unittest.TestCase):
    """``CogerTransportador`` y ``SoltarTransportador`` sin moverse entre medias."""

    def test_coger_y_soltar_sin_moverse(self) -> None:
        """Comprueba que un transportador cogido y soltado y su brazo acaban libres."""
        deposito = Localizacion("deposito")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        transportador = Transportador("transportador1", deposito, 4)

        acciones = [
            CogerTransportador(
                dron=dron,
                transportador=transportador,
                brazo=brazo,
                inicio_sim=0,
                duracion_sim=1,
            ),
            SoltarTransportador(
                dron=dron,
                transportador=transportador,
                brazo=brazo,
                inicio_sim=1,
                duracion_sim=1,
            ),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito],
            drones=[dron],
            cajas=[],
            personas=[],
            transportadores=[transportador],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertIsNone(transportador.propietario_actual)
        self.assertIsNone(brazo.reservado_por)

    def test_el_transportador_sigue_sujeto_hasta_que_termina_soltar(self) -> None:
        """Comprueba que ``SoltarTransportador`` libera el transportador al terminar."""
        deposito = Localizacion("deposito")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        transportador = Transportador("transportador1", deposito, 4)

        acciones = [
            CogerTransportador(
                dron=dron,
                transportador=transportador,
                brazo=brazo,
                inicio_sim=0,
                duracion_sim=1,
            ),
            SoltarTransportador(
                dron=dron,
                transportador=transportador,
                brazo=brazo,
                inicio_sim=1,
                duracion_sim=2,
            ),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito],
            drones=[dron],
            cajas=[],
            personas=[],
            transportadores=[transportador],
        )

        mundo._simulacion._reproducir()
        # A mitad de SoltarTransportador.
        mundo._simulacion._actualizar(2.0)

        self.assertIs(transportador.propietario_actual, dron)
        self.assertIs(brazo.reservado_por, transportador)

        mundo._simulacion._actualizar(10)

        self.assertIsNone(transportador.propietario_actual)
        self.assertIsNone(brazo.reservado_por)

    def test_no_se_puede_meter_una_caja_en_un_transportador_que_se_esta_soltando(
        self,
    ) -> None:
        """Comprueba que un transportador solo acepta cajas cuando acaba de soltarse.

        El segundo dron empieza a meter su caja en el transportador en t=2,
        mientras el primero todavía lo está soltando (de t=1 a t=3).
        """
        deposito = Localizacion("deposito")
        brazo1 = Brazo("brazo1")
        brazo2 = Brazo("brazo2")
        dron1 = Dron("dron1", deposito, [brazo1])
        dron2 = Dron("dron2", deposito, [brazo2])
        caja = Caja("caja1", deposito, "comida")
        transportador = Transportador("transportador1", deposito, 4)

        acciones = [
            CogerTransportador(
                dron1, transportador, brazo1, inicio_sim=0, duracion_sim=1
            ),
            CogerCaja(dron2, brazo2, caja, inicio_sim=0, duracion_sim=1),
            SoltarTransportador(
                dron1, transportador, brazo1, inicio_sim=1, duracion_sim=2
            ),
            PonerCajaEnTransportador(
                dron2, brazo2, caja, transportador, inicio_sim=2, duracion_sim=1
            ),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito],
            drones=[dron1, dron2],
            cajas=[caja],
            personas=[],
            transportadores=[transportador],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertFalse(informe.ejecutable)
        self.assertIn("transportador1", informe.error or "")
        self.assertIs(brazo2.contenido, caja)

    def test_soltar_un_transportador_que_nadie_sujeta_falla_al_empezar(self) -> None:
        """Comprueba que no se puede soltar un transportador que ningún dron sujeta."""
        deposito = Localizacion("deposito")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        transportador = Transportador("transportador1", deposito, 4)

        acciones = [
            SoltarTransportador(
                dron, transportador, brazo, inicio_sim=0, duracion_sim=1
            ),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito],
            drones=[dron],
            cajas=[],
            personas=[],
            transportadores=[transportador],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertFalse(informe.ejecutable)
        self.assertIn(
            "el dron dron1 no puede soltar el transportador transportador1, "
            "ningún dron lo sujeta",
            informe.error or "",
        )
        self.assertFalse(acciones[0].iniciada)

    def test_soltar_un_transportador_de_otro_dron_falla_al_empezar(self) -> None:
        """Comprueba que un dron no puede soltar el transportador que sujeta otro."""
        deposito = Localizacion("deposito")
        brazo1 = Brazo("brazo1")
        brazo2 = Brazo("brazo2")
        dron1 = Dron("dron1", deposito, [brazo1])
        dron2 = Dron("dron2", deposito, [brazo2])
        transportador = Transportador("transportador1", deposito, 4)

        acciones = [
            CogerTransportador(
                dron2, transportador, brazo2, inicio_sim=0, duracion_sim=1
            ),
            SoltarTransportador(
                dron1, transportador, brazo1, inicio_sim=1, duracion_sim=1
            ),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito],
            drones=[dron1, dron2],
            cajas=[],
            personas=[],
            transportadores=[transportador],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertFalse(informe.ejecutable)
        self.assertIn(
            "el dron dron1 no puede soltar el transportador transportador1, "
            "lo sujeta el dron dron2",
            informe.error or "",
        )
        self.assertFalse(acciones[1].iniciada)
        self.assertIs(transportador.propietario_actual, dron2)


class TestMoverTransportadorDePrincipioAFin(unittest.TestCase):
    """``MoverTransportador``: coger, mover y soltar en una sola acción."""

    def test_coger_mover_soltar_ocurre_entero(self) -> None:
        """Comprueba que el dron y el transportador llegan y que este se suelta."""
        deposito = Localizacion("deposito")
        localizacion1 = Localizacion("localizacion1")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        transportador = Transportador("transportador1", deposito, 4)

        acciones = [
            MoverTransportador(
                dron=dron,
                transportador=transportador,
                brazo=brazo,
                origen=deposito,
                destino=localizacion1,
                inicio_sim=0,
                duracion_sim=1,
            ),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito, localizacion1],
            drones=[dron],
            cajas=[],
            personas=[],
            transportadores=[transportador],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.05)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertEqual(dron.localizacion, localizacion1)
        self.assertEqual(transportador.localizacion, localizacion1)
        self.assertIsNone(transportador.propietario_actual)

    def test_origen_incorrecto_falla_al_empezar_sin_coger(self) -> None:
        """Comprueba que falla en ``inicio_sim`` si el dron no está en ``origen``.

        El origen se comprueba antes de coger el transportador, así que la acción
        no llega a empezar: el transportador y el brazo siguen libres, y el dron
        sigue donde estaba.
        """
        deposito = Localizacion("deposito")
        localizacion1 = Localizacion("localizacion1")
        origen_incorrecto = Localizacion("origen-incorrecto")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        transportador = Transportador("transportador1", deposito, 4)

        acciones = [
            MoverTransportador(
                dron=dron,
                transportador=transportador,
                brazo=brazo,
                origen=origen_incorrecto,
                destino=localizacion1,
                inicio_sim=0,
                duracion_sim=1,
            ),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito, localizacion1, origen_incorrecto],
            drones=[dron],
            cajas=[],
            personas=[],
            transportadores=[transportador],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.05)

        self.assertFalse(informe.ejecutable)
        self.assertIn(
            "no está en la localización origen-incorrecto", informe.error or ""
        )
        self.assertFalse(acciones[0].iniciada)
        self.assertIsNone(transportador.propietario_actual)
        self.assertIsNone(brazo.reservado_por)
        self.assertEqual(dron.localizacion, deposito)


class TestOrigenDeMover(unittest.TestCase):
    """``Mover``: el origen es una condición ``at start``."""

    def test_origen_incorrecto_falla_al_empezar(self) -> None:
        """Comprueba que un ``Mover`` desde donde no está el dron falla al empezar."""
        deposito = Localizacion("deposito")
        localizacion1 = Localizacion("localizacion1")
        localizacion2 = Localizacion("localizacion2")
        dron = Dron("dron1", deposito, [Brazo("brazo")])

        acciones = [
            Mover(dron, localizacion1, localizacion2, inicio_sim=0, duracion_sim=3)
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito, localizacion1, localizacion2],
            drones=[dron],
            cajas=[],
            personas=[],
        )
        informe = ejecutar_plan(mundo, paso_tiempo=0.5)

        self.assertFalse(informe.ejecutable)
        self.assertIn(
            "el dron dron1 no está en la localización localizacion1, "
            "está en la localización deposito",
            informe.error or "",
        )
        self.assertFalse(acciones[0].iniciada)
        self.assertEqual(dron.localizacion, deposito)


class TestMensajeDeRegistroDeMover(unittest.TestCase):
    """El mensaje que registra un dron cuando se mueve dice lo que lleva."""

    def test_mensaje_sin_carga(self) -> None:
        """Comprueba el único mensaje que registra un dron sin carga al moverse.

        Solo nombra el origen y el destino, sin la parte de lo que lleva.
        """
        deposito = Localizacion("deposito")
        localizacion1 = Localizacion("localizacion1")
        dron = Dron("dron1", deposito, [Brazo("brazo")])

        acciones = [Mover(dron, deposito, localizacion1, inicio_sim=0, duracion_sim=1)]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito, localizacion1],
            drones=[dron],
            cajas=[],
            personas=[],
        )
        with self.assertLogs("simulador_pddl.objetos.dron", level="INFO") as registros:
            informe = ejecutar_plan(mundo, paso_tiempo=0.5)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertEqual(
            [registro.getMessage() for registro in registros.records],
            [f"El dron dron1 se ha movido de {deposito} a {localizacion1}"],
        )

    def test_mensaje_con_cajas_y_un_transportador(self) -> None:
        """Comprueba el plural de las cajas y el singular del transportador."""
        deposito = Localizacion("deposito")
        localizacion1 = Localizacion("localizacion1")
        brazos = [Brazo("brazo1"), Brazo("brazo2"), Brazo("brazo3")]
        dron = Dron("dron1", deposito, brazos)
        cajas = [Caja("caja1", deposito, "comida"), Caja("caja2", deposito, "medicina")]
        transportador = Transportador("transportador1", deposito, 4)

        acciones = [
            CogerCaja(dron, brazos[0], cajas[0], inicio_sim=0, duracion_sim=1),
            CogerCaja(dron, brazos[1], cajas[1], inicio_sim=0, duracion_sim=1),
            CogerTransportador(
                dron, transportador, brazos[2], inicio_sim=0, duracion_sim=1
            ),
            Mover(dron, deposito, localizacion1, inicio_sim=1, duracion_sim=1),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito, localizacion1],
            drones=[dron],
            cajas=cajas,
            personas=[],
            transportadores=[transportador],
        )
        with self.assertLogs("simulador_pddl.objetos.dron", level="INFO") as registros:
            informe = ejecutar_plan(mundo, paso_tiempo=0.5)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertEqual(
            registros.records[-1].getMessage(),
            f"El dron dron1 se ha movido de {deposito} a {localizacion1} "
            "con 2 cajas y 1 transportador",
        )

    def test_mensaje_con_una_caja(self) -> None:
        """Comprueba el singular de una sola caja, sin transportador."""
        deposito = Localizacion("deposito")
        localizacion1 = Localizacion("localizacion1")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        caja = Caja("caja1", deposito, "comida")

        acciones = [
            CogerCaja(dron, brazo, caja, inicio_sim=0, duracion_sim=1),
            Mover(dron, deposito, localizacion1, inicio_sim=1, duracion_sim=1),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito, localizacion1],
            drones=[dron],
            cajas=[caja],
            personas=[],
        )
        with self.assertLogs("simulador_pddl.objetos.dron", level="INFO") as registros:
            informe = ejecutar_plan(mundo, paso_tiempo=0.5)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertEqual(
            registros.records[-1].getMessage(),
            f"El dron dron1 se ha movido de {deposito} a {localizacion1} con 1 caja",
        )

    def test_mensaje_con_transportadores_y_sin_cajas(self) -> None:
        """Comprueba el plural de los transportadores cuando no lleva cajas."""
        deposito = Localizacion("deposito")
        localizacion1 = Localizacion("localizacion1")
        brazos = [Brazo("brazo1"), Brazo("brazo2")]
        dron = Dron("dron1", deposito, brazos)
        transportadores = [
            Transportador("transportador1", deposito, 4),
            Transportador("transportador2", deposito, 4),
        ]

        acciones = [
            CogerTransportador(
                dron, transportadores[0], brazos[0], inicio_sim=0, duracion_sim=1
            ),
            CogerTransportador(
                dron, transportadores[1], brazos[1], inicio_sim=0, duracion_sim=1
            ),
            Mover(dron, deposito, localizacion1, inicio_sim=1, duracion_sim=1),
        ]
        mundo = Mundo(
            acciones,
            localizaciones=[deposito, localizacion1],
            drones=[dron],
            cajas=[],
            personas=[],
            transportadores=transportadores,
        )
        with self.assertLogs("simulador_pddl.objetos.dron", level="INFO") as registros:
            informe = ejecutar_plan(mundo, paso_tiempo=0.5)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertEqual(
            registros.records[-1].getMessage(),
            f"El dron dron1 se ha movido de {deposito} a {localizacion1} "
            "con 2 transportadores",
        )


class TestTiemposDePonerCajaEnTransportador(unittest.TestCase):
    """Poner una caja reserva un hueco al empezar y mete la caja al final."""

    def setUp(self) -> None:
        """Crea dos drones, dos cajas y un transportador con sitio para una caja."""
        self.deposito = Localizacion("deposito")
        self.localizacion1 = Localizacion("localizacion1")
        self.brazo1 = Brazo("brazo1")
        self.brazo2 = Brazo("brazo2")
        self.dron1 = Dron("dron1", self.deposito, [self.brazo1])
        self.dron2 = Dron("dron2", self.deposito, [self.brazo2])
        self.caja1 = Caja("caja1", self.deposito, "comida")
        self.caja2 = Caja("caja2", self.deposito, "comida")
        self.transportador = Transportador("transportador1", self.deposito, 1)

    def _objetos(self) -> dict[str, list[Any]]:
        """Devuelve los objetos del problema, con su transportador."""
        return {
            "localizaciones": [self.deposito, self.localizacion1],
            "drones": [self.dron1, self.dron2],
            "cajas": [self.caja1, self.caja2],
            "personas": [],
            "transportadores": [self.transportador],
        }

    def test_la_caja_sigue_en_el_brazo_hasta_que_termina_la_carga(self) -> None:
        """Comprueba que durante la carga la caja nunca se queda sin quien la sujete."""
        acciones = [
            CogerCaja(
                self.dron1, self.brazo1, self.caja1, inicio_sim=0, duracion_sim=1
            ),
            PonerCajaEnTransportador(
                self.dron1,
                self.brazo1,
                self.caja1,
                self.transportador,
                inicio_sim=1,
                duracion_sim=4,
            ),
        ]
        mundo = Mundo(acciones, **self._objetos())

        mundo._simulacion._reproducir()
        # A mitad de PonerCajaEnTransportador.
        mundo._simulacion._actualizar(3.0)

        self.assertIs(self.brazo1.contenido, self.caja1)
        self.assertIs(self.caja1.propietario_actual, self.dron1)
        self.assertEqual(self.transportador.cajas_dentro, [])

        mundo._simulacion._actualizar(10)

        self.assertIsNone(self.brazo1.contenido)
        self.assertIs(self.caja1.propietario_actual, self.transportador)
        self.assertEqual(self.transportador.cajas_dentro, [self.caja1])

    def test_el_transportador_no_se_puede_llevar_durante_una_carga(self) -> None:
        """Comprueba que el transportador no se mueve mientras se le mete una caja."""
        acciones = [
            CogerCaja(
                self.dron1, self.brazo1, self.caja1, inicio_sim=0, duracion_sim=1
            ),
            PonerCajaEnTransportador(
                self.dron1,
                self.brazo1,
                self.caja1,
                self.transportador,
                inicio_sim=1,
                duracion_sim=4,
            ),
            MoverTransportador(
                self.dron2,
                self.transportador,
                self.brazo2,
                self.deposito,
                self.localizacion1,
                inicio_sim=2,
                duracion_sim=1,
            ),
        ]
        mundo = Mundo(acciones, **self._objetos())
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertFalse(informe.ejecutable)
        self.assertIn("transportador1", informe.error or "")
        self.assertEqual(self.transportador.localizacion, self.deposito)
        self.assertIsNone(self.transportador.propietario_actual)
        self.assertIs(self.brazo1.contenido, self.caja1)
        self.assertEqual(self.transportador.cajas_dentro, [])

    def test_segunda_carga_solapada_en_un_transportador_lleno_falla_al_empezar(
        self,
    ) -> None:
        """Comprueba que una carga en curso ya ocupa su hueco del transportador.

        El transportador tiene sitio para una caja. La segunda carga empieza en
        t=2, mientras la primera (de 1 a 4) sigue en curso, así que es la segunda
        la que falla, al empezar, y su caja se queda en su brazo.
        """
        acciones = [
            CogerCaja(
                self.dron1, self.brazo1, self.caja1, inicio_sim=0, duracion_sim=1
            ),
            CogerCaja(
                self.dron2, self.brazo2, self.caja2, inicio_sim=0, duracion_sim=1
            ),
            PonerCajaEnTransportador(
                self.dron1,
                self.brazo1,
                self.caja1,
                self.transportador,
                inicio_sim=1,
                duracion_sim=3,
            ),
            PonerCajaEnTransportador(
                self.dron2,
                self.brazo2,
                self.caja2,
                self.transportador,
                inicio_sim=2,
                duracion_sim=1,
            ),
        ]
        mundo = Mundo(acciones, **self._objetos())
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertFalse(informe.ejecutable)
        self.assertIn("capacidad", informe.error or "")
        self.assertEqual(informe.acciones_terminadas, 2)
        self.assertIs(self.brazo2.contenido, self.caja2)
        self.assertEqual(self.transportador.cajas_dentro, [])

    def test_el_hueco_vuelve_a_quedar_libre_al_sacar_la_caja(self) -> None:
        """Comprueba que una carga y una descarga no dejan huecos reservados."""
        acciones = [
            CogerCaja(
                self.dron1, self.brazo1, self.caja1, inicio_sim=0, duracion_sim=1
            ),
            CogerCaja(
                self.dron2, self.brazo2, self.caja2, inicio_sim=0, duracion_sim=1
            ),
            PonerCajaEnTransportador(
                self.dron1,
                self.brazo1,
                self.caja1,
                self.transportador,
                inicio_sim=1,
                duracion_sim=1,
            ),
            SacarCajaDeTransportador(
                self.dron1,
                self.brazo1,
                self.caja1,
                self.transportador,
                inicio_sim=2,
                duracion_sim=1,
            ),
            PonerCajaEnTransportador(
                self.dron2,
                self.brazo2,
                self.caja2,
                self.transportador,
                inicio_sim=3,
                duracion_sim=1,
            ),
        ]
        mundo = Mundo(acciones, **self._objetos())
        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertEqual(self.transportador.cajas_dentro, [self.caja2])
        self.assertIs(self.brazo1.contenido, self.caja1)

    def test_reiniciar_durante_una_carga_libera_el_hueco_reservado(self) -> None:
        """Comprueba que ``reiniciar()`` a mitad de una carga no deja huecos reservados.

        Después del reinicio el transportador se puede coger, y el plan se vuelve a
        ejecutar.
        """
        acciones = [
            CogerCaja(
                self.dron1, self.brazo1, self.caja1, inicio_sim=0, duracion_sim=1
            ),
            PonerCajaEnTransportador(
                self.dron1,
                self.brazo1,
                self.caja1,
                self.transportador,
                inicio_sim=1,
                duracion_sim=4,
            ),
            CogerTransportador(
                self.dron2,
                self.transportador,
                self.brazo2,
                inicio_sim=5,
                duracion_sim=1,
            ),
        ]
        mundo = Mundo(acciones, **self._objetos())

        mundo._simulacion._reproducir()
        mundo._simulacion._actualizar(3.0)
        mundo.reiniciar()

        self.assertIsNone(self.brazo1.contenido)
        self.assertEqual(self.caja1.estado, Caja.DISPONIBLE)

        informe = ejecutar_plan(mundo, paso_tiempo=0.1)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertEqual(self.transportador.cajas_dentro, [self.caja1])
        self.assertIs(self.transportador.propietario_actual, self.dron2)

    def test_reiniciar_durante_una_descarga_deja_coger_el_transportador(self) -> None:
        """Comprueba que ``reiniciar()`` a mitad de una descarga libera todo.

        Un transportador no se puede coger mientras se saca una caja de él. Después
        del reinicio no hay ninguna descarga en curso, así que un plan nuevo sobre
        los mismos objetos puede cogerlo.
        """
        acciones = [
            CogerCaja(
                self.dron1, self.brazo1, self.caja1, inicio_sim=0, duracion_sim=1
            ),
            PonerCajaEnTransportador(
                self.dron1,
                self.brazo1,
                self.caja1,
                self.transportador,
                inicio_sim=1,
                duracion_sim=1,
            ),
            SacarCajaDeTransportador(
                self.dron1,
                self.brazo1,
                self.caja1,
                self.transportador,
                inicio_sim=2,
                duracion_sim=4,
            ),
        ]
        mundo = Mundo(acciones, **self._objetos())

        mundo._simulacion._reproducir()
        # A mitad de SacarCajaDeTransportador.
        mundo._simulacion._actualizar(4.0)
        mundo.reiniciar()

        coger = [
            CogerTransportador(
                self.dron2,
                self.transportador,
                self.brazo2,
                inicio_sim=0,
                duracion_sim=1,
            ),
        ]
        informe = ejecutar_plan(Mundo(coger, **self._objetos()), paso_tiempo=0.1)

        self.assertTrue(informe.ejecutable, informe.error)
        self.assertIs(self.transportador.propietario_actual, self.dron2)


if __name__ == "__main__":
    unittest.main()
