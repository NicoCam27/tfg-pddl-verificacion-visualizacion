"""Pruebas que comprueban la descripción automática de cada acción.

``Accion.__init__()`` construye la descripción a partir del nombre de la clase y
del diccionario ``objetos`` de cada subclase, en el orden de sus claves. Los
textos esperados se escriben a mano a de forma deliberada: si se reordenan o se
renombran las claves de ``objetos``, la descripción cambia y estas pruebas fallan.
"""

import unittest

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
from simulador_pddl.objetos import (
    Brazo,
    Caja,
    Dron,
    Localizacion,
    Persona,
    Transportador,
)


class TestDescripcionAutomatica(unittest.TestCase):
    """La descripción que recibe una acción cuando no se da ninguna."""

    def setUp(self) -> None:
        """Crea un objeto de cada tipo para las acciones."""
        self.deposito = Localizacion("deposito")
        self.localizacion1 = Localizacion("localizacion1")
        self.brazo = Brazo("brazo")
        self.dron = Dron("dron1", self.deposito, [self.brazo])
        self.caja = Caja("caja1", self.deposito, "comida")
        self.persona = Persona("persona1", self.deposito, necesidades="comida")
        self.transportador = Transportador("transportador1", self.deposito, 4)

    def test_cada_accion_tiene_la_descripcion_automatica_esperada(self) -> None:
        """Comprueba la descripción generada de cada una de las nueve acciones."""
        casos = [
            (
                Mover(
                    dron=self.dron,
                    origen=self.deposito,
                    destino=self.localizacion1,
                    inicio_sim=0.5,
                    duracion_sim=2,
                ),
                (
                    "Mover(dron=dron1, origen=deposito, destino=localizacion1, "
                    "inicio_sim=0.5, duracion_sim=2)"
                ),
            ),
            (
                CogerCaja(
                    dron=self.dron,
                    brazo=self.brazo,
                    caja=self.caja,
                    inicio_sim=0.5,
                    duracion_sim=2,
                ),
                (
                    "CogerCaja(dron=dron1, brazo=brazo, caja=caja1, "
                    "inicio_sim=0.5, duracion_sim=2)"
                ),
            ),
            (
                EntregarCaja(
                    dron=self.dron,
                    brazo=self.brazo,
                    caja=self.caja,
                    persona=self.persona,
                    inicio_sim=0.5,
                    duracion_sim=2,
                ),
                (
                    "EntregarCaja(dron=dron1, brazo=brazo, caja=caja1, "
                    "persona=persona1, inicio_sim=0.5, duracion_sim=2)"
                ),
            ),
            (
                Soltar(
                    dron=self.dron,
                    brazo=self.brazo,
                    caja=self.caja,
                    inicio_sim=0.5,
                    duracion_sim=2,
                ),
                (
                    "Soltar(dron=dron1, brazo=brazo, caja=caja1, "
                    "inicio_sim=0.5, duracion_sim=2)"
                ),
            ),
            (
                CogerTransportador(
                    dron=self.dron,
                    transportador=self.transportador,
                    brazo=self.brazo,
                    inicio_sim=0.5,
                    duracion_sim=2,
                ),
                (
                    "CogerTransportador(dron=dron1, transportador=transportador1, "
                    "brazo=brazo, inicio_sim=0.5, duracion_sim=2)"
                ),
            ),
            (
                SoltarTransportador(
                    dron=self.dron,
                    transportador=self.transportador,
                    brazo=self.brazo,
                    inicio_sim=0.5,
                    duracion_sim=2,
                ),
                (
                    "SoltarTransportador(dron=dron1, transportador=transportador1, "
                    "brazo=brazo, inicio_sim=0.5, duracion_sim=2)"
                ),
            ),
            (
                MoverTransportador(
                    dron=self.dron,
                    transportador=self.transportador,
                    brazo=self.brazo,
                    origen=self.deposito,
                    destino=self.localizacion1,
                    inicio_sim=0.5,
                    duracion_sim=2,
                ),
                (
                    "MoverTransportador(dron=dron1, transportador=transportador1, "
                    "brazo=brazo, origen=deposito, destino=localizacion1, "
                    "inicio_sim=0.5, duracion_sim=2)"
                ),
            ),
            (
                PonerCajaEnTransportador(
                    dron=self.dron,
                    brazo=self.brazo,
                    caja=self.caja,
                    transportador=self.transportador,
                    inicio_sim=0.5,
                    duracion_sim=2,
                ),
                (
                    "PonerCajaEnTransportador(dron=dron1, brazo=brazo, caja=caja1, "
                    "transportador=transportador1, inicio_sim=0.5, duracion_sim=2)"
                ),
            ),
            (
                SacarCajaDeTransportador(
                    dron=self.dron,
                    brazo=self.brazo,
                    caja=self.caja,
                    transportador=self.transportador,
                    inicio_sim=0.5,
                    duracion_sim=2,
                ),
                (
                    "SacarCajaDeTransportador(dron=dron1, brazo=brazo, caja=caja1, "
                    "transportador=transportador1, inicio_sim=0.5, duracion_sim=2)"
                ),
            ),
        ]
        for accion, esperado in casos:
            with self.subTest(accion=type(accion).__name__):
                self.assertEqual(accion.desc, esperado)

    def test_una_descripcion_dada_se_conserva_tal_cual(self) -> None:
        """Comprueba que una descripción dada por el usuario no se sustituye."""
        accion = CogerCaja(
            dron=self.dron,
            brazo=self.brazo,
            caja=self.caja,
            inicio_sim=0,
            duracion_sim=1,
            desc="0.0000: (LOAD DRONE1 ARM BOX1 DEPOSIT) [D:1.00; C:1.00]",
        )
        self.assertEqual(
            accion.desc, "0.0000: (LOAD DRONE1 ARM BOX1 DEPOSIT) [D:1.00; C:1.00]"
        )

    def test_desc_none_genera_la_descripcion(self) -> None:
        """Comprueba que ``desc=None`` equivale a no dar ninguna descripción."""
        accion = CogerCaja(self.dron, self.brazo, self.caja, 0, desc=None)
        self.assertEqual(
            accion.desc,
            "CogerCaja(dron=dron1, brazo=brazo, caja=caja1, inicio_sim=0, "
            "duracion_sim=1.0)",
        )


if __name__ == "__main__":
    unittest.main()
