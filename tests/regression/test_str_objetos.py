"""Pruebas de ``str()`` y ``repr()`` de los objetos, acciones, objetivos e informes.

Los objetos relacionados se imprimen entre sí por su nombre, nunca enteros: si
una caja imprimiera entero a su propietario y el propietario imprimiera la caja
de vuelta, ``str()`` no terminaría nunca. Las primeras pruebas construyen esas
situaciones (una caja entregada y su persona, una caja sujeta por un brazo, un
transportador sujeto) y comprueban que ``str()`` muestra los nombres de los
objetos relacionados.

Las demás comprueban ``repr()`` de los objetivos y las acciones, que es lo que
muestra una lista de ellos, y del mundo, la simulación, la instantánea y el
informe.
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
    CogerTransportador,
    Contenido,
    Dron,
    DronEnLocalizacion,
    EntregarCaja,
    Localizacion,
    Mover,
    MoverTransportador,
    Mundo,
    Persona,
    PersonaTieneContenido,
    PonerCajaEnTransportador,
    Transportador,
    TransportadorEnLocalizacion,
)

if TYPE_CHECKING:
    from simulador_pddl import Accion


# Los contenidos de los problemas de este módulo. Un contenido no cambia al
# ejecutar un plan, así que todas las pruebas pueden compartirlos.
COMIDA = Contenido("comida")
CONTENIDOS = (COMIDA,)


class TestStrObjetos(unittest.TestCase):
    """``str()`` de objetos que se sujetan o se poseen entre sí."""

    def setUp(self) -> None:
        """Silencia el registro y crea un objeto de cada tipo."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.deposito = Localizacion("deposito")
        self.brazo = Brazo("brazo")
        self.dron = Dron("dron1", self.deposito, [self.brazo])
        self.caja = Caja("caja1", self.deposito, COMIDA)
        self.persona = Persona("persona1", self.deposito, COMIDA)
        self.transportador = Transportador("transportador1", self.deposito, 2)

    def ejecutar_plan(self, acciones: list[Accion]) -> None:
        """Ejecuta las acciones como un plan y comprueba que es ejecutable."""
        mundo = Mundo(
            acciones,
            localizaciones=[self.deposito],
            drones=[self.dron],
            cajas=[self.caja],
            personas=[self.persona],
            contenidos=CONTENIDOS,
            transportadores=[self.transportador],
            objetivos=[],
        )
        with contextlib.redirect_stdout(io.StringIO()):
            informe = mundo.simulacion_texto()
        self.assertTrue(informe.ejecutable, informe.error)

    def test_caja_entregada_y_su_persona(self) -> None:
        """Comprueba ``str()`` de una caja entregada y de la persona que la tiene."""
        self.ejecutar_plan(
            [
                CogerCaja(self.dron, self.brazo, self.caja, 0, 1),
                EntregarCaja(self.dron, self.brazo, self.caja, self.persona, 1, 1),
            ]
        )

        self.assertIn("propietario_actual=persona1", str(self.caja))
        self.assertIn("posee=['caja1']", str(self.persona))

    def test_caja_transportada_su_brazo_y_su_dron(self) -> None:
        """Comprueba ``str()`` de una caja transportada, de su brazo y de su dron."""
        self.ejecutar_plan([CogerCaja(self.dron, self.brazo, self.caja, 0, 1)])

        self.assertIn("propietario_actual=dron1", str(self.caja))
        self.assertIn("contenido=caja1", str(self.brazo))
        self.assertIn("contenido=caja1", str(self.dron))

    def test_transportador_sujeto_su_brazo_y_su_dron(self) -> None:
        """Comprueba ``str()`` de un transportador sujeto, su brazo, dron y caja."""
        self.ejecutar_plan(
            [
                CogerCaja(self.dron, self.brazo, self.caja, 0, 1),
                PonerCajaEnTransportador(
                    self.dron, self.brazo, self.caja, self.transportador, 1, 1
                ),
                CogerTransportador(self.dron, self.transportador, self.brazo, 2, 1),
            ]
        )

        self.assertIn("cajas_dentro=['caja1']", str(self.transportador))
        self.assertIn("propietario_actual=dron1", str(self.transportador))
        self.assertIn("brazo_actual=brazo", str(self.transportador))
        self.assertIn("reservado_por=transportador1", str(self.brazo))
        self.assertIn("propietario_actual=transportador1", str(self.caja))
        self.assertIn("reservado_por=transportador1", str(self.dron))

    def test_objetos_sin_nada_relacionado(self) -> None:
        """Comprueba ``str()`` de objetos que no sujetan nada ni tienen propietario."""
        self.assertIn("propietario_actual=nadie", str(self.caja))
        self.assertIn("contenido=None, reservado_por=None", str(self.brazo))
        self.assertIn("posee=[]", str(self.persona))
        self.assertIn(
            "propietario_actual=nadie, brazo_actual=None", str(self.transportador)
        )

    def test_contenido_en_una_caja_y_en_una_persona(self) -> None:
        """Comprueba que un contenido se muestra por su nombre.

        ``repr()`` es la llamada que lo construye, y ``str()``, solo el nombre,
        como en una localización.
        """
        self.assertEqual(repr(COMIDA), "Contenido('comida')")
        self.assertEqual(str(COMIDA), "comida")
        self.assertIn("contenido=comida", str(self.caja))
        self.assertIn("necesidades=['comida']", str(self.persona))


class TestReprObjetivos(unittest.TestCase):
    """``repr()`` de cada tipo de objetivo."""

    def setUp(self) -> None:
        """Crea los objetos a los que se refieren los objetivos."""
        self.deposito = Localizacion("deposito")
        self.dron = Dron("dron1", self.deposito, [Brazo("brazo")])
        self.persona = Persona("persona1", self.deposito, COMIDA)
        self.transportador = Transportador("transportador1", self.deposito, 2)

    def test_persona_tiene_contenido(self) -> None:
        """Comprueba que el objetivo muestra su persona y su contenido.

        ``repr()`` muestra la llamada que lo construye, y ``str()``, su descripción.
        """
        objetivo = PersonaTieneContenido(self.persona, COMIDA)
        self.assertEqual(
            repr(objetivo),
            "PersonaTieneContenido(Persona('persona1'), Contenido('comida'))",
        )
        self.assertEqual(str(objetivo), objetivo._describir())

    def test_dron_en_localizacion(self) -> None:
        """Comprueba que el objetivo muestra su dron y su localización."""
        objetivo = DronEnLocalizacion(self.dron, self.deposito)
        self.assertEqual(
            repr(objetivo),
            "DronEnLocalizacion(Dron('dron1'), Localizacion('deposito'))",
        )

    def test_transportador_en_localizacion(self) -> None:
        """Comprueba que el objetivo muestra su transportador y su localización."""
        objetivo = TransportadorEnLocalizacion(self.transportador, self.deposito)
        self.assertEqual(
            repr(objetivo),
            "TransportadorEnLocalizacion(Transportador('transportador1'), "
            "Localizacion('deposito'))",
        )

    def test_una_lista_de_objetivos_muestra_cada_objetivo(self) -> None:
        """Comprueba que una lista de objetivos no muestra direcciones de memoria."""
        objetivos = [
            PersonaTieneContenido(self.persona, COMIDA),
            DronEnLocalizacion(self.dron, self.deposito),
        ]
        self.assertEqual(
            str(objetivos),
            "[PersonaTieneContenido(Persona('persona1'), Contenido('comida')), "
            "DronEnLocalizacion(Dron('dron1'), Localizacion('deposito'))]",
        )
        self.assertEqual(str(objetivos[0]), objetivos[0]._describir())


class TestReprAcciones(unittest.TestCase):
    """``repr()`` de las acciones: la llamada que construye cada una."""

    def setUp(self) -> None:
        """Crea los objetos que usan las acciones."""
        self.deposito = Localizacion("deposito")
        self.loc1 = Localizacion("loc1")
        self.brazo = Brazo("brazo")
        self.dron = Dron("dron1", self.deposito, [self.brazo])
        self.caja = Caja("caja1", self.deposito, COMIDA)
        self.transportador = Transportador("transportador1", self.deposito, 2)

    def test_objetos_en_el_orden_de_los_argumentos(self) -> None:
        """Comprueba que los objetos aparecen como se pasan, y después los tiempos."""
        accion = MoverTransportador(
            self.dron, self.transportador, self.brazo, self.deposito, self.loc1, 2, 1.5
        )
        self.assertEqual(
            repr(accion),
            "MoverTransportador(Dron('dron1'), Transportador('transportador1'), "
            "Brazo('brazo'), Localizacion('deposito'), Localizacion('loc1'), "
            "inicio_sim=2, duracion_sim=1.5)",
        )

    def test_desc_no_se_muestra(self) -> None:
        """Comprueba que una descripción dada por el usuario no cambia ``repr()``."""
        accion = CogerCaja(self.dron, self.brazo, self.caja, 0, desc="(load d1 b1)")
        self.assertEqual(
            repr(accion),
            "CogerCaja(Dron('dron1'), Brazo('brazo'), Caja('caja1'), "
            "inicio_sim=0, duracion_sim=1.0)",
        )
        self.assertEqual(accion.desc, "(load d1 b1)")

    def test_una_lista_de_acciones_muestra_cada_accion(self) -> None:
        """Comprueba que imprimir un plan no muestra direcciones de memoria."""
        plan = [Mover(self.dron, self.deposito, self.loc1, 0, 1)]
        self.assertEqual(
            str(plan),
            "[Mover(Dron('dron1'), Localizacion('deposito'), Localizacion('loc1'), "
            "inicio_sim=0, duracion_sim=1)]",
        )


class TestReprMundoEInforme(unittest.TestCase):
    """``repr()`` del mundo, su simulación, su instantánea y su informe."""

    def setUp(self) -> None:
        """Silencia el registro y crea un mundo con una acción y un objetivo."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        deposito = Localizacion("deposito")
        loc1 = Localizacion("loc1")
        dron = Dron("dron1", deposito, [Brazo("brazo")])
        self.mundo = Mundo(
            [Mover(dron, deposito, loc1, 0, 1)],
            localizaciones=[deposito, loc1],
            drones=[dron],
            cajas=[],
            personas=[],
            contenidos=[],
            objetivos=[DronEnLocalizacion(dron, loc1)],
        )

    def test_mundo_y_simulacion(self) -> None:
        """Comprueba ``repr()`` del mundo y de su simulación.

        Ambos cuentan acciones y objetivos. La simulación muestra además su tiempo.
        """
        self.assertEqual(repr(self.mundo), "Mundo(acciones=1, objetivos=1)")
        self.assertEqual(
            repr(self.mundo._simulacion),
            "Simulacion(acciones=1, objetivos=1, tiempo_simulacion=0.0)",
        )

    def test_instantanea(self) -> None:
        """Comprueba que la instantánea muestra cuántos objetos capturó."""
        # Un dron y su brazo: el mundo no tiene cajas, personas ni transportadores.
        self.assertEqual(
            repr(self.mundo._simulacion._instantanea_inicial),
            "InstantaneaMundo(objetos=2)",
        )

    def test_informe_y_estado_de_objetivo(self) -> None:
        """Comprueba que el informe muestra su veredicto y cada estado, su objetivo."""
        antes = self.mundo.verificar()
        self.assertEqual(repr(antes), "InformeVerificacion(veredicto='INCOMPLETO')")
        self.assertEqual(
            repr(antes.estados_objetivos),
            "[EstadoObjetivo(DronEnLocalizacion(Dron('dron1'), Localizacion('loc1')), "
            "cumplido=False)]",
        )

        with contextlib.redirect_stdout(io.StringIO()):
            despues = self.mundo.simulacion_texto()
        self.assertEqual(repr(despues), "InformeVerificacion(veredicto='VÁLIDO')")
        self.assertEqual(
            repr(despues.estados_objetivos[0]),
            "EstadoObjetivo(DronEnLocalizacion(Dron('dron1'), Localizacion('loc1')), "
            "cumplido=True)",
        )
        # str() de un informe sigue siendo su resumen.
        self.assertEqual(str(despues), despues.resumen())


if __name__ == "__main__":
    unittest.main()
