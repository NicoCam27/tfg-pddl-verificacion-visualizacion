"""Pruebas de que se pueden instanciar todas las acciones, objetos y objetivos.

``Accion`` es abstracta: una subclase a la que le falta ``objetos``,
``_iniciar_ejecucion()`` o ``_terminar_ejecucion()`` no se puede construir, y el
error solo aparece cuando un plan la usa. La primera prueba lo comprueba para las
nueve acciones. Las demás construyen los siete objetos y los tres objetivos y
comprueban que conservan sus argumentos y empiezan en su estado inicial.
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
from simulador_pddl.objetivos import (
    DronEnLocalizacion,
    PersonaTieneContenido,
    TransportadorEnLocalizacion,
)
from simulador_pddl.objetos import (
    Brazo,
    Caja,
    Contenido,
    Dron,
    Localizacion,
    Persona,
    Transportador,
)

# Los contenidos de las pruebas de este módulo. Un contenido no cambia,
# así que todas las pruebas pueden compartirlos.
COMIDA = Contenido("comida")
MEDICINA = Contenido("medicina")


TODAS_LAS_CLASES_ACCION = [
    Mover,
    CogerCaja,
    EntregarCaja,
    Soltar,
    MoverTransportador,
    CogerTransportador,
    SoltarTransportador,
    PonerCajaEnTransportador,
    SacarCajaDeTransportador,
]


class TestAccionesInstanciables(unittest.TestCase):
    """Cada clase de acción implementa los miembros abstractos de ``Accion``."""

    def test_cada_clase_de_accion_implementa_los_miembros_abstractos(self) -> None:
        """Comprueba que a ninguna clase de acción le queda un miembro abstracto."""
        for cls in TODAS_LAS_CLASES_ACCION:
            with self.subTest(cls=cls.__name__):
                for miembro in ("objetos", "_iniciar_ejecucion", "_terminar_ejecucion"):
                    self.assertIn(miembro, cls.__dict__)
                self.assertEqual(cls.__abstractmethods__, frozenset())


class TestObjetosInstanciables(unittest.TestCase):
    """Cada objeto del dominio se puede construir y conserva sus argumentos."""

    def setUp(self) -> None:
        """Crea una localización para los objetos que están en una."""
        self.deposito = Localizacion("deposito")

    def test_localizacion_instanciable(self) -> None:
        """Comprueba que una localización conserva su nombre y se compara por él.

        Dos localizaciones con el mismo nombre son iguales y tienen el mismo hash, y
        una localización no es igual a la cadena de su nombre.
        """
        self.assertEqual(self.deposito.nombre, "deposito")
        self.assertEqual(Localizacion("deposito"), self.deposito)
        self.assertEqual(len({Localizacion("deposito"), self.deposito}), 1)
        self.assertNotEqual(Localizacion("almacen"), self.deposito)
        self.assertNotEqual(self.deposito, "deposito")

    def test_contenido_instanciable(self) -> None:
        """Comprueba que un contenido conserva su nombre y se compara por él.

        Dos contenidos con el mismo nombre son iguales y tienen el mismo hash, y un
        contenido no es igual a la cadena de su nombre.
        """
        self.assertEqual(COMIDA.nombre, "comida")
        self.assertEqual(Contenido("comida"), COMIDA)
        self.assertEqual(len({Contenido("comida"), COMIDA}), 1)
        self.assertNotEqual(Contenido("agua"), COMIDA)
        self.assertNotEqual(COMIDA, "comida")

    def test_localizacion_y_contenido_con_el_mismo_nombre_son_distintos(self) -> None:
        """Comprueba que la igualdad por nombre solo vale entre objetos del mismo tipo.

        Una localización y un contenido que se llaman igual no son el mismo objeto,
        aunque los dos se comparen por su nombre.
        """
        localizacion = Localizacion("comida")

        self.assertNotEqual(localizacion, COMIDA)
        self.assertNotEqual(COMIDA, localizacion)
        self.assertEqual(len({localizacion, COMIDA}), 2)

    def test_brazo_instanciable(self) -> None:
        """Comprueba que un brazo nuevo conserva su nombre y no sujeta nada."""
        brazo = Brazo("brazo")

        self.assertEqual(brazo.nombre, "brazo")
        self.assertIsNone(brazo.caja)
        self.assertIsNone(brazo.transportador)

    def test_dron_instanciable(self) -> None:
        """Comprueba que un dron conserva su nombre, su localización y sus brazos."""
        izquierda = Brazo("izquierda")
        derecha = Brazo("derecha")
        dron = Dron("dron1", self.deposito, [izquierda, derecha])

        self.assertEqual(dron.nombre, "dron1")
        self.assertEqual(dron.localizacion, self.deposito)
        self.assertEqual(dron.brazos, [izquierda, derecha])

    def test_dron_sin_brazos_instanciable(self) -> None:
        """Comprueba que un dron se puede construir con una lista de brazos vacía."""
        dron = Dron("dron1", self.deposito, [])

        self.assertEqual(dron.brazos, [])

    def test_brazos_del_dron_pueden_ser_una_tupla(self) -> None:
        """Comprueba que una tupla de brazos se guarda como una lista."""
        izquierda = Brazo("izquierda")
        derecha = Brazo("derecha")
        dron = Dron("dron1", self.deposito, (izquierda, derecha))

        self.assertEqual(dron.brazos, [izquierda, derecha])

    def test_dron_guarda_su_propia_lista_de_brazos(self) -> None:
        """Comprueba que cambiar la lista que se dio a un dron no cambia el dron."""
        izquierda = Brazo("izquierda")
        brazos = [izquierda]
        dron = Dron("dron1", self.deposito, brazos)

        brazos.append(Brazo("derecha"))

        self.assertEqual(dron.brazos, [izquierda])

    def test_las_listas_que_devuelve_un_objeto_son_copias(self) -> None:
        """Comprueba que cambiar una lista que devuelve un objeto no cambia el objeto.

        Así, el estado de un objeto solo lo cambia la biblioteca al ejecutar un plan.
        """
        izquierda = Brazo("izquierda")
        dron = Dron("dron1", self.deposito, [izquierda])
        persona = Persona("persona1", self.deposito, COMIDA)
        transportador = Transportador("transportador1", self.deposito, 4)
        caja = Caja("caja1", self.deposito, COMIDA)

        dron.brazos.append(Brazo("derecha"))
        persona.necesidades.append(MEDICINA)
        persona.posee.append(caja)
        transportador.cajas_dentro.append(caja)

        self.assertEqual(dron.brazos, [izquierda])
        self.assertEqual(persona.necesidades, [COMIDA])
        self.assertEqual(persona.posee, [])
        self.assertEqual(transportador.cajas_dentro, [])

    def test_caja_instanciable(self) -> None:
        """Comprueba que una caja nueva conserva sus argumentos y está disponible."""
        caja = Caja("caja1", self.deposito, COMIDA)

        self.assertEqual(caja.nombre, "caja1")
        self.assertEqual(caja.localizacion, self.deposito)
        self.assertEqual(caja.contenido, COMIDA)
        self.assertEqual(caja.estado, Caja.DISPONIBLE)
        self.assertIsNone(caja.propietario_actual)

    def test_persona_instanciable_con_cada_forma_de_necesidades(self) -> None:
        """Comprueba que una persona puede no necesitar nada, un contenido o varios.

        Sea cual sea la forma, la persona guarda sus necesidades como una lista.
        """
        formas_necesidades: list[
            tuple[Contenido | list[Contenido] | None, list[Contenido]]
        ] = [
            (None, []),
            (COMIDA, [COMIDA]),
            ([COMIDA, MEDICINA], [COMIDA, MEDICINA]),
        ]

        for necesidades, esperado in formas_necesidades:
            with self.subTest(necesidades=necesidades):
                persona = Persona("persona1", self.deposito, necesidades)

                self.assertEqual(persona.nombre, "persona1")
                self.assertEqual(persona.localizacion, self.deposito)
                self.assertEqual(persona.necesidades, esperado)
                self.assertEqual(persona.posee, [])

    def test_persona_no_necesita_nada_por_defecto(self) -> None:
        """Comprueba que, sin ``necesidades``, la persona no necesita nada."""
        persona = Persona("persona1", self.deposito)

        self.assertEqual(persona.necesidades, [])

    def test_necesidades_de_la_persona_pueden_ser_una_tupla(self) -> None:
        """Comprueba que una tupla de necesidades se guarda como una lista."""
        persona = Persona("persona1", self.deposito, (COMIDA, MEDICINA))

        self.assertEqual(persona.necesidades, [COMIDA, MEDICINA])

    def test_transportador_instanciable(self) -> None:
        """Comprueba que un transportador nuevo conserva sus argumentos y está libre."""
        transportador = Transportador("transportador1", self.deposito, 4)

        self.assertEqual(transportador.nombre, "transportador1")
        self.assertEqual(transportador.localizacion, self.deposito)
        self.assertEqual(transportador.capacidad, 4)
        self.assertEqual(transportador.cajas_dentro, [])
        self.assertIsNone(transportador.propietario_actual)
        self.assertIsNone(transportador.brazo_actual)


class TestObjetivosInstanciables(unittest.TestCase):
    """Cada objetivo se puede construir y conserva sus argumentos."""

    def setUp(self) -> None:
        """Crea una localización para los objetos de los objetivos."""
        self.deposito = Localizacion("deposito")

    def test_persona_tiene_contenido_instanciable(self) -> None:
        """Comprueba que el objetivo conserva su persona y su contenido."""
        persona = Persona("persona1", self.deposito, COMIDA)
        objetivo = PersonaTieneContenido(persona, COMIDA)

        self.assertIs(objetivo.persona, persona)
        self.assertEqual(objetivo.contenido, COMIDA)

    def test_dron_en_localizacion_instanciable(self) -> None:
        """Comprueba que el objetivo conserva su dron y su localización."""
        dron = Dron("dron1", self.deposito, [Brazo("brazo")])
        meta = Localizacion("meta")
        objetivo = DronEnLocalizacion(dron, meta)

        self.assertIs(objetivo.dron, dron)
        self.assertEqual(objetivo.localizacion, meta)

    def test_transportador_en_localizacion_instanciable(self) -> None:
        """Comprueba que el objetivo conserva su transportador y su localización."""
        transportador = Transportador("transportador1", self.deposito, 4)
        meta = Localizacion("meta")
        objetivo = TransportadorEnLocalizacion(transportador, meta)

        self.assertIs(objetivo.transportador, transportador)
        self.assertEqual(objetivo.localizacion, meta)


if __name__ == "__main__":
    unittest.main()
