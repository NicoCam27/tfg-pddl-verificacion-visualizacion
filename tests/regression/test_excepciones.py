"""Pruebas de los errores que se lanzan al construir algo con argumentos incorrectos.

Los objetos, las acciones, los objetivos y ``Mundo`` comprueban sus argumentos al
construirse: un valor de tipo incorrecto lanza ``TypeError``, y un valor del tipo
correcto que no está permitido lanza ``ValueError``. Un error que ocurre mientras
se ejecuta un plan no se lanza: se devuelve en el ``InformeVerificacion`` (ver
``test_flujos_acciones.py``). Lo que se comprueba al construir no se puede
escribir después (``AttributeError``): ni los atributos de un objeto o de un
objetivo, ni los valores y los objetos de una acción.
"""

from __future__ import annotations

import contextlib
import io
import logging
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
from simulador_pddl.simulacion import InformeVerificacion

if TYPE_CHECKING:
    from simulador_pddl.acciones import Accion

# Los contenidos de los problemas de este módulo. Un contenido no cambia al
# ejecutar un plan, así que todas las pruebas pueden compartirlos.
COMIDA = Contenido("comida")
MEDICINA = Contenido("medicina")
CONTENIDOS = (COMIDA, MEDICINA)


# Valores que no son una cadena, para los argumentos que tienen que serlo.
NO_CADENAS = (
    5,
    -2.0,
    True,
    ["nombre_en_lista"],
    ("nombre_en_tupla",),
    {"nombre": "nombre_en_diccionario"},
    {"nombre_en_conjunto"},
    None,
    b"nombre_en_bytes",
)

# Valores que no son una localización.
NO_LOCALIZACIONES = ("deposito", 5, None, ["deposito"])

# Valores que no son un contenido. Una cadena tampoco lo es.
NO_CONTENIDOS = ("comida", 5, None, [COMIDA])

# Valores que no son un número, para inicio_sim y duracion_sim. Un bool es un int
# para Python, pero no un tiempo.
NO_NUMEROS = ("1", None, True, [1])


class TestExcepcionesObjetos(unittest.TestCase):
    """Cada objeto del dominio rechaza argumentos incorrectos al construirse."""

    def setUp(self) -> None:
        """Crea una localización y un brazo, que necesitan los demás objetos."""
        self.deposito = Localizacion("deposito")
        self.brazo = Brazo("brazo")

    def test_brazo_incorrecto(self) -> None:
        """Comprueba que un brazo rechaza un nombre que no es una cadena."""
        for nombre in NO_CADENAS:
            with self.subTest(nombre=nombre), self.assertRaises(TypeError):
                Brazo(nombre)  # type: ignore[arg-type]

    def test_localizacion_incorrecta(self) -> None:
        """Comprueba que una localización rechaza un nombre que no es una cadena."""
        for nombre in NO_CADENAS:
            with self.subTest(nombre=nombre), self.assertRaises(TypeError):
                Localizacion(nombre)  # type: ignore[arg-type]

    def test_contenido_incorrecto(self) -> None:
        """Comprueba que un contenido rechaza un nombre que no es una cadena."""
        for nombre in NO_CADENAS:
            with self.subTest(nombre=nombre), self.assertRaises(TypeError):
                Contenido(nombre)  # type: ignore[arg-type]

    def test_nombre_de_localizacion_y_contenido_es_de_solo_lectura(self) -> None:
        """Comprueba que una localización o un contenido no puede cambiar de nombre.

        Los dos se comparan por nombre, y su hash depende de él.
        """
        for objeto in (Localizacion("deposito"), Contenido("comida")):
            with self.subTest(objeto=objeto), self.assertRaises(AttributeError):
                objeto.nombre = "otro"  # type: ignore[misc]

    def test_atributos_de_los_objetos_son_de_solo_lectura(self) -> None:
        """Comprueba que ningún atributo de los demás objetos se escribe desde fuera.

        Su estado solo lo cambia la biblioteca al ejecutar un plan, así que
        escribirlo a mano se saltaría las reglas del dominio.
        """
        atributos = {
            self.brazo: ("nombre", "caja", "transportador"),
            Caja("caja1", self.deposito, COMIDA): (
                "nombre",
                "localizacion",
                "contenido",
                "estado",
                "propietario_actual",
            ),
            Dron("dron1", self.deposito, [Brazo("otro-brazo")]): (
                "nombre",
                "localizacion",
                "brazos",
            ),
            Persona("persona1", self.deposito, COMIDA): (
                "nombre",
                "localizacion",
                "necesidades",
                "posee",
            ),
            Transportador("transportador1", self.deposito, 4): (
                "nombre",
                "localizacion",
                "capacidad",
                "cajas_dentro",
                "propietario_actual",
                "brazo_actual",
            ),
        }
        for objeto, nombres in atributos.items():
            for atributo in nombres:
                with (
                    self.subTest(objeto=objeto, atributo=atributo),
                    self.assertRaises(AttributeError),
                ):
                    setattr(objeto, atributo, None)

    def test_caja_incorrecta(self) -> None:
        """Comprueba que una caja rechaza argumentos incorrectos.

        Un nombre, una localización o un contenido de otro tipo lanzan ``TypeError``.
        """
        for nombre in NO_CADENAS:
            with self.subTest(nombre=nombre), self.assertRaises(TypeError):
                Caja(nombre, self.deposito, COMIDA)  # type: ignore[arg-type]

        for localizacion in NO_LOCALIZACIONES:
            with self.subTest(localizacion=localizacion), self.assertRaises(TypeError):
                Caja("caja1", localizacion, COMIDA)  # type: ignore[arg-type]

        for contenido in NO_CONTENIDOS:
            with self.subTest(contenido=contenido), self.assertRaises(TypeError):
                Caja("caja1", self.deposito, contenido)  # type: ignore[arg-type]

    def test_transportador_incorrecto(self) -> None:
        """Comprueba que un transportador rechaza argumentos incorrectos."""
        for nombre in NO_CADENAS:
            with self.subTest(nombre=nombre), self.assertRaises(TypeError):
                Transportador(nombre, self.deposito, 4)  # type: ignore[arg-type]

        for localizacion in NO_LOCALIZACIONES:
            with self.subTest(localizacion=localizacion), self.assertRaises(TypeError):
                Transportador("transportador1", localizacion, 4)  # type: ignore[arg-type]

        for capacidad in ("4", 4.0, None, True, [4]):
            with self.subTest(capacidad=capacidad), self.assertRaises(TypeError):
                Transportador("transportador1", self.deposito, capacidad)  # type: ignore[arg-type]

    def test_capacidad_del_transportador_tiene_que_ser_mayor_que_cero(self) -> None:
        """Comprueba que una capacidad de 0 o menos lanza ``ValueError``."""
        for capacidad in (0, -1):
            with self.subTest(capacidad=capacidad), self.assertRaises(ValueError):
                Transportador("transportador1", self.deposito, capacidad)

    def test_dron_incorrecto(self) -> None:
        """Comprueba que un dron rechaza nombre, localización o brazos incorrectos."""
        for nombre in NO_CADENAS:
            with self.subTest(nombre=nombre), self.assertRaises(TypeError):
                Dron(nombre, self.deposito, [self.brazo])  # type: ignore[arg-type]

        for localizacion in NO_LOCALIZACIONES:
            with self.subTest(localizacion=localizacion), self.assertRaises(TypeError):
                Dron("dron1", localizacion, [self.brazo])  # type: ignore[arg-type]

        # Los brazos llegan en una lista o una tupla que solo contiene brazos.
        for brazos in (
            self.brazo,
            "brazo",
            None,
            {self.brazo},
            ["brazo"],
            (self.brazo, None),
        ):
            with self.subTest(brazos=brazos), self.assertRaises(TypeError):
                Dron("dron1", self.deposito, brazos)  # type: ignore[arg-type]

    def test_brazos_del_dron_tienen_que_ser_distintos(self) -> None:
        """Comprueba que repetir un brazo en un dron lanza ``ValueError``."""
        with self.assertRaises(ValueError):
            Dron("dron1", self.deposito, [self.brazo, self.brazo])

    def test_necesidades_de_una_persona_tienen_que_ser_distintas(self) -> None:
        """Comprueba que un contenido repetido en las necesidades lanza ``ValueError``.

        Dos contenidos con el mismo nombre son el mismo contenido, aunque sean
        objetos distintos.
        """
        for necesidades in (
            [COMIDA, COMIDA],
            [COMIDA, Contenido("comida")],
            (COMIDA, MEDICINA, COMIDA),
        ):
            with self.subTest(necesidades=necesidades):
                with self.assertRaises(ValueError) as contexto:
                    Persona("persona1", self.deposito, necesidades)
                self.assertEqual(
                    str(contexto.exception),
                    "'necesidades' no puede repetir contenidos, "
                    "el contenido comida aparece más de una vez",
                )

    def test_persona_incorrecta(self) -> None:
        """Comprueba que una persona rechaza argumentos incorrectos."""
        for nombre in NO_CADENAS:
            with self.subTest(nombre=nombre), self.assertRaises(TypeError):
                Persona(nombre, self.deposito, COMIDA)  # type: ignore[arg-type]

        for localizacion in NO_LOCALIZACIONES:
            with self.subTest(localizacion=localizacion), self.assertRaises(TypeError):
                Persona("persona1", localizacion, COMIDA)  # type: ignore[arg-type]

        # Las necesidades son un contenido, o una lista o una tupla de contenidos, y
        # una cadena no es un contenido.
        for necesidades in (
            "comida",
            ["comida"],
            5,
            True,
            {COMIDA},
            [COMIDA, 5],
            (COMIDA, 5),
            [None],
        ):
            with self.subTest(necesidades=necesidades), self.assertRaises(TypeError):
                Persona("persona1", self.deposito, necesidades)  # type: ignore[arg-type]


class TestExcepcionesAcciones(unittest.TestCase):
    """Cada acción rechaza argumentos incorrectos al construirse."""

    def setUp(self) -> None:
        """Crea un objeto de cada tipo y un brazo que no es de ningún dron."""
        self.deposito = Localizacion("deposito")
        self.localizacion1 = Localizacion("localizacion1")
        self.brazo = Brazo("brazo")
        self.otro_brazo = Brazo("otro-brazo")
        self.dron = Dron("dron1", self.deposito, [self.brazo])
        self.caja = Caja("caja1", self.deposito, COMIDA)
        self.persona = Persona("persona1", self.deposito, COMIDA)
        self.transportador = Transportador("transportador1", self.deposito, 4)

    def _argumentos_objeto(self) -> dict[type[Accion], dict[str, Any]]:
        """Devuelve valores válidos de los argumentos objeto de cada clase de acción."""
        dron, brazo, caja = self.dron, self.brazo, self.caja
        transportador = self.transportador
        return {
            Mover: {
                "dron": dron,
                "origen": self.deposito,
                "destino": self.localizacion1,
            },
            CogerCaja: {"dron": dron, "brazo": brazo, "caja": caja},
            EntregarCaja: {
                "dron": dron,
                "brazo": brazo,
                "caja": caja,
                "persona": self.persona,
            },
            Soltar: {"dron": dron, "brazo": brazo, "caja": caja},
            CogerTransportador: {
                "dron": dron,
                "transportador": transportador,
                "brazo": brazo,
            },
            SoltarTransportador: {
                "dron": dron,
                "transportador": transportador,
                "brazo": brazo,
            },
            MoverTransportador: {
                "dron": dron,
                "transportador": transportador,
                "brazo": brazo,
                "origen": self.deposito,
                "destino": self.localizacion1,
            },
            PonerCajaEnTransportador: {
                "dron": dron,
                "brazo": brazo,
                "caja": caja,
                "transportador": transportador,
            },
            SacarCajaDeTransportador: {
                "dron": dron,
                "brazo": brazo,
                "caja": caja,
                "transportador": transportador,
            },
        }

    def test_argumentos_validos_construyen_todas_las_acciones(self) -> None:
        """Comprueba que los argumentos de los que parten las otras pruebas son válidos.

        Sin esto, una prueba de abajo podría pasar por un error en
        ``_argumentos_objeto()`` y no por el valor incorrecto que prueba.
        """
        for cls, argumentos in self._argumentos_objeto().items():
            with self.subTest(cls=cls.__name__):
                cls(**argumentos, inicio_sim=0, duracion_sim=1)

    def test_tipo_de_objeto_incorrecto_en_cualquier_argumento(self) -> None:
        """Comprueba que cada acción rechaza un argumento objeto de otro tipo."""
        for cls, argumentos in self._argumentos_objeto().items():
            for argumento in argumentos:
                incorrecto = {**argumentos, argumento: "no es un objeto"}
                with (
                    self.subTest(cls=cls.__name__, argumento=argumento),
                    self.assertRaises(TypeError),
                ):
                    cls(**incorrecto, inicio_sim=0, duracion_sim=1)

    def test_brazo_de_otro_dron(self) -> None:
        """Comprueba que una acción rechaza un brazo que no es de su dron."""
        for cls, argumentos in self._argumentos_objeto().items():
            if "brazo" not in argumentos:
                continue
            incorrecto = {**argumentos, "brazo": self.otro_brazo}
            with self.subTest(cls=cls.__name__), self.assertRaises(ValueError):
                cls(**incorrecto, inicio_sim=0, duracion_sim=1)

    def test_tipo_de_inicio_sim_incorrecto(self) -> None:
        """Comprueba que un ``inicio_sim`` no numérico lanza ``TypeError``."""
        for inicio_sim in NO_NUMEROS:
            with self.subTest(inicio_sim=inicio_sim), self.assertRaises(TypeError):
                CogerCaja(self.dron, self.brazo, self.caja, inicio_sim)  # type: ignore[arg-type]

    def test_inicio_sim_tiene_que_ser_cero_o_mayor_y_finito(self) -> None:
        """Comprueba que se rechaza un ``inicio_sim`` negativo, infinito o NaN."""
        for inicio_sim in (-1, -0.5, float("inf"), float("nan")):
            with self.subTest(inicio_sim=inicio_sim), self.assertRaises(ValueError):
                CogerCaja(self.dron, self.brazo, self.caja, inicio_sim)

    def test_tipo_de_duracion_sim_incorrecto(self) -> None:
        """Comprueba que una ``duracion_sim`` no numérica lanza ``TypeError``."""
        for duracion_sim in NO_NUMEROS:
            with (
                self.subTest(duracion_sim=duracion_sim),
                self.assertRaises(TypeError),
            ):
                CogerCaja(self.dron, self.brazo, self.caja, 0, duracion_sim)  # type: ignore[arg-type]

    def test_duracion_sim_tiene_que_ser_mayor_que_cero_y_finita(self) -> None:
        """Comprueba que se rechaza una ``duracion_sim`` fuera de rango.

        Una de 0 o menos, infinita o NaN lanza ``ValueError``.
        """
        for duracion_sim in (0, -1, float("inf"), float("nan")):
            with (
                self.subTest(duracion_sim=duracion_sim),
                self.assertRaises(ValueError),
            ):
                CogerCaja(self.dron, self.brazo, self.caja, 0, duracion_sim)

    def test_tipo_de_desc_incorrecto(self) -> None:
        """Comprueba que una ``desc`` que no es una cadena lanza ``TypeError``."""
        for desc in (5, ["una descripción"]):
            with self.subTest(desc=desc), self.assertRaises(TypeError):
                CogerCaja(self.dron, self.brazo, self.caja, 0, 1, desc)  # type: ignore[arg-type]

    def test_cada_accion_comprueba_sus_tiempos(self) -> None:
        """Comprueba que todas las acciones validan sus tiempos, no solo una."""
        for cls, argumentos in self._argumentos_objeto().items():
            nombre = cls.__name__
            with (
                self.subTest(cls=nombre, incorrecto="inicio"),
                self.assertRaises(ValueError),
            ):
                cls(**argumentos, inicio_sim=-1, duracion_sim=1)
            with (
                self.subTest(cls=nombre, incorrecto="duracion"),
                self.assertRaises(ValueError),
            ):
                cls(**argumentos, inicio_sim=0, duracion_sim=0)

    def test_acciones_de_movimiento_rechazan_el_mismo_origen_y_destino(self) -> None:
        """Comprueba que los movimientos piden dos localizaciones distintas.

        La comprobación no depende del estado, así que se hace al construir la
        acción, no al ejecutarla.
        """
        for cls, argumentos in self._argumentos_objeto().items():
            if "origen" not in argumentos:
                continue
            mismo = {**argumentos, "destino": argumentos["origen"]}
            with self.subTest(cls=cls.__name__), self.assertRaises(ValueError):
                cls(**mismo, inicio_sim=0, duracion_sim=1)

    def test_atributos_validados_son_de_solo_lectura(self) -> None:
        """Comprueba que los valores validados de una acción no se escriben.

        Son los tiempos, la ``desc``, los indicadores y los objetos. ``Mundo`` los
        valida una vez, al construirse, así que escribirlos después se saltaría sus
        comprobaciones.
        """
        solo_lectura = (
            "inicio_sim",
            "duracion_sim",
            "tiempo_fin",
            "desc",
            "iniciada",
            "terminada",
        )
        for cls, argumentos in self._argumentos_objeto().items():
            accion = cls(**argumentos, inicio_sim=1, duracion_sim=2)
            # Los argumentos objeto de cada acción, p. ej. "dron", "brazo", "caja".
            for atributo in (*solo_lectura, *argumentos):
                with (
                    self.subTest(cls=cls.__name__, atributo=atributo),
                    self.assertRaises(AttributeError),
                ):
                    setattr(accion, atributo, 0)
            self.assertEqual(accion.tiempo_fin, 3)


class TestExcepcionesObjetivos(unittest.TestCase):
    """Cada objetivo rechaza argumentos incorrectos al construirse.

    Después, los objetos a los que se refiere no se pueden cambiar.
    """

    def setUp(self) -> None:
        """Crea un objeto de cada tipo al que se puede referir un objetivo."""
        self.deposito = Localizacion("deposito")
        self.dron = Dron("dron1", self.deposito, [Brazo("brazo")])
        self.persona = Persona("persona1", self.deposito, COMIDA)
        self.transportador = Transportador("transportador1", self.deposito, 4)

    def test_persona_tiene_contenido_incorrecto(self) -> None:
        """Comprueba que el objetivo rechaza argumentos incorrectos.

        Una persona o un contenido de otro tipo lanzan ``TypeError``.
        """
        for persona in ("persona1", None, self.dron):
            with self.subTest(persona=persona), self.assertRaises(TypeError):
                PersonaTieneContenido(persona, COMIDA)  # type: ignore[arg-type]

        for contenido in NO_CONTENIDOS:
            with self.subTest(contenido=contenido), self.assertRaises(TypeError):
                PersonaTieneContenido(self.persona, contenido)  # type: ignore[arg-type]

    def test_dron_en_localizacion_incorrecto(self) -> None:
        """Comprueba que el objetivo rechaza argumentos incorrectos.

        Un dron o una localización de otro tipo lanzan ``TypeError``.
        """
        for dron in ("dron1", None, self.transportador):
            with self.subTest(dron=dron), self.assertRaises(TypeError):
                DronEnLocalizacion(dron, self.deposito)  # type: ignore[arg-type]

        for localizacion in NO_LOCALIZACIONES:
            with self.subTest(localizacion=localizacion), self.assertRaises(TypeError):
                DronEnLocalizacion(self.dron, localizacion)  # type: ignore[arg-type]

    def test_transportador_en_localizacion_incorrecto(self) -> None:
        """Comprueba que el objetivo rechaza argumentos incorrectos.

        Un transportador o una localización de otro tipo lanzan ``TypeError``.
        """
        for transportador in ("transportador1", None, self.dron):
            with (
                self.subTest(transportador=transportador),
                self.assertRaises(TypeError),
            ):
                TransportadorEnLocalizacion(transportador, self.deposito)  # type: ignore[arg-type]

        for localizacion in NO_LOCALIZACIONES:
            with self.subTest(localizacion=localizacion), self.assertRaises(TypeError):
                TransportadorEnLocalizacion(self.transportador, localizacion)  # type: ignore[arg-type]

    def test_atributos_de_los_objetivos_son_de_solo_lectura(self) -> None:
        """Comprueba que los objetos de un objetivo no se cambian tras construirlo.

        ``Mundo`` comprueba al construirse que cada objetivo se puede lograr, así
        que cambiarlos después se saltaría esa comprobación.
        """
        atributos = {
            PersonaTieneContenido(self.persona, COMIDA): ("persona", "contenido"),
            DronEnLocalizacion(self.dron, self.deposito): ("dron", "localizacion"),
            TransportadorEnLocalizacion(self.transportador, self.deposito): (
                "transportador",
                "localizacion",
            ),
        }
        for objetivo, nombres in atributos.items():
            for atributo in nombres:
                with (
                    self.subTest(objetivo=objetivo, atributo=atributo),
                    self.assertRaises(AttributeError),
                ):
                    setattr(objetivo, atributo, None)


class TestExcepcionesSimulacion(unittest.TestCase):
    """``Mundo`` rechaza un plan o un problema que no está bien formado."""

    def setUp(self) -> None:
        """Crea un problema pequeño y un plan de una acción que es válido para él."""
        self.deposito = Localizacion("deposito")
        self.brazo = Brazo("brazo")
        self.dron = Dron("dron1", self.deposito, [self.brazo])
        self.caja = Caja("caja1", self.deposito, COMIDA)
        self.persona = Persona("persona1", self.deposito, COMIDA)
        self.transportador = Transportador("transportador1", self.deposito, 4)

        self.coger_caja = CogerCaja(self.dron, self.brazo, self.caja, inicio_sim=0)
        self.objetivo = PersonaTieneContenido(self.persona, COMIDA)

    def _objetos(self) -> dict[str, list[Any]]:
        """Devuelve los objetos del problema, sin lista de transportadores."""
        return {
            "localizaciones": [self.deposito],
            "drones": [self.dron],
            "cajas": [self.caja],
            "personas": [self.persona],
            "contenidos": list(CONTENIDOS),
        }

    def test_argumentos_validos_construyen_un_mundo(self) -> None:
        """Comprueba que el plan y el problema de partida de las pruebas son válidos."""
        Mundo([self.coger_caja], **self._objetos(), objetivos=[self.objetivo])

    def test_acciones_objetos_y_objetivos_pueden_ser_tuplas(self) -> None:
        """Comprueba que cada lista que recibe ``Mundo`` se puede dar como una tupla.

        La simulación guarda siempre listas propias, aunque reciba tuplas.
        """
        mundo = Mundo(
            (self.coger_caja,),
            localizaciones=(self.deposito,),
            drones=(self.dron,),
            cajas=(self.caja,),
            personas=(self.persona,),
            contenidos=(COMIDA,),
            transportadores=(self.transportador,),
            objetivos=(self.objetivo,),
        )

        simulacion = mundo._simulacion
        self.assertEqual(simulacion._acciones, [self.coger_caja])
        self.assertEqual(simulacion._localizaciones, [self.deposito])
        self.assertEqual(simulacion._drones, [self.dron])
        self.assertEqual(simulacion._cajas, [self.caja])
        self.assertEqual(simulacion._personas, [self.persona])
        self.assertEqual(simulacion._transportadores, [self.transportador])
        self.assertEqual(simulacion._objetivos, [self.objetivo])

    def test_tipo_de_acciones_incorrecto(self) -> None:
        """Comprueba que ``acciones`` tiene que ser una lista o una tupla."""
        for acciones in (
            150,
            "acciones",
            self.coger_caja,
            {"coger_caja": self.coger_caja},
            {self.coger_caja},
        ):
            with self.subTest(acciones=acciones), self.assertRaises(TypeError):
                Mundo(acciones, **self._objetos())  # type: ignore[arg-type]

    def test_tipo_interno_de_la_lista_de_acciones_incorrecto(self) -> None:
        """Comprueba que ``acciones`` solo puede contener acciones."""
        for acciones in (
            [1, 2, 3],
            [self.coger_caja, "coger_caja"],
            [self.coger_caja, None],
        ):
            with self.subTest(acciones=acciones), self.assertRaises(TypeError):
                Mundo(acciones, **self._objetos())  # type: ignore[arg-type]

    def test_los_objetos_se_dan_por_nombre(self) -> None:
        """Comprueba que los objetos no se aceptan como una lista posicional.

        Cada tipo de objeto tiene su propio argumento por nombre, así que la forma
        posicional, ``Mundo(acciones, [localizaciones, drones, cajas, personas])``,
        se rechaza.
        """
        objetos = list(self._objetos().values())
        with self.assertRaises(TypeError):
            # Se pasa la forma posicional deliberadamente.
            Mundo([self.coger_caja], objetos)  # type: ignore[misc, call-arg, arg-type]

    def test_cada_tipo_de_objeto_es_obligatorio(self) -> None:
        """Comprueba que omitir un tipo de objeto obligatorio lanza ``TypeError``."""
        for ausente in ("localizaciones", "drones", "cajas", "personas", "contenidos"):
            objetos = self._objetos()
            del objetos[ausente]
            with self.subTest(ausente=ausente), self.assertRaises(TypeError):
                Mundo([self.coger_caja], **objetos)

    def test_acciones_none(self) -> None:
        """Comprueba que dar ``None`` como ``acciones`` lanza ``TypeError``."""
        with self.assertRaises(TypeError):
            Mundo(None, **self._objetos())  # type: ignore[arg-type]

    def test_tipo_interno_de_los_objetos_incorrecto(self) -> None:
        """Comprueba que cada tipo de objeto es una lista o tupla de su propio tipo."""
        # Se sustituye una lista cada vez por algo que no es una lista.
        for nombre in (
            "localizaciones",
            "drones",
            "cajas",
            "personas",
            "contenidos",
            "transportadores",
        ):
            for incorrecto in (None, 5, "no es una lista"):
                if nombre == "transportadores" and incorrecto is None:
                    continue  # None significa "sin transportadores", que es válido.
                objetos: dict[str, Any] = {**self._objetos(), nombre: incorrecto}
                with (
                    self.subTest(nombre=nombre, incorrecto=incorrecto),
                    self.assertRaises(TypeError),
                ):
                    Mundo([self.coger_caja], **objetos)

        # Una lista cada vez recibe un objeto de otro tipo.
        for nombre in ("localizaciones", "drones", "cajas", "personas", "contenidos"):
            objetos = self._objetos()
            objetos[nombre].append(self.transportador)
            with self.subTest(elemento_incorrecto=nombre), self.assertRaises(TypeError):
                Mundo([self.coger_caja], **objetos)

        # Lo mismo para la lista opcional de transportadores.
        with self.assertRaises(TypeError):
            Mundo([self.coger_caja], **self._objetos(), transportadores=[self.caja])  # type: ignore[list-item]

    def test_accion_con_un_objeto_no_declarado(self) -> None:
        """Comprueba que una acción solo puede usar los objetos que se dieron."""
        otra_localizacion = Localizacion("otra-localizacion")
        otro_brazo = Brazo("otro-brazo")
        otro_dron = Dron("dron2", self.deposito, [otro_brazo])
        otra_caja = Caja("caja2", self.deposito, COMIDA)
        otra_persona = Persona("persona2", self.deposito, COMIDA)

        no_declarado = {
            "dron": (
                CogerCaja(otro_dron, otro_brazo, self.caja, inicio_sim=0),
                "el dron dron2 no aparece en la lista de drones dada",
            ),
            "caja": (
                CogerCaja(self.dron, self.brazo, otra_caja, inicio_sim=0),
                "la caja caja2 no aparece en la lista de cajas dada",
            ),
            "persona": (
                EntregarCaja(
                    self.dron, self.brazo, self.caja, otra_persona, inicio_sim=1
                ),
                "la persona persona2 no aparece en la lista de personas dada",
            ),
            "localizacion": (
                Mover(self.dron, self.deposito, otra_localizacion, inicio_sim=1),
                (
                    "la localización otra-localizacion no aparece en la lista de "
                    "localizaciones dada"
                ),
            ),
        }

        for tipo, (accion, mensaje) in no_declarado.items():
            with self.subTest(no_declarado=tipo):
                with self.assertRaises(ValueError) as contexto:
                    Mundo([accion], **self._objetos())
                self.assertEqual(str(contexto.exception), mensaje)

    def test_accion_de_transportador_sin_lista_de_transportadores(self) -> None:
        """Comprueba que una acción de transportador exige transportadores."""
        coger = CogerTransportador(
            self.dron, self.brazo, self.transportador, inicio_sim=0
        )

        with self.assertRaises(ValueError) as contexto:
            Mundo([coger], **self._objetos())
        self.assertEqual(
            str(contexto.exception),
            "la acción CogerTransportador no se puede realizar si no se dan "
            "transportadores",
        )

        # Con la lista, pero sin ese transportador en ella.
        with self.assertRaises(ValueError) as contexto:
            Mundo([coger], **self._objetos(), transportadores=[])
        self.assertEqual(
            str(contexto.exception),
            "el transportador transportador1 no aparece en la lista de "
            "transportadores dada",
        )

    def test_tipo_de_objetivos_incorrecto(self) -> None:
        """Comprueba que ``objetivos`` es una lista o tupla de objetivos."""
        for objetivos in (
            5,
            "objetivos",
            self.objetivo,
            [1],
            [self.objetivo, "objetivo"],
        ):
            with self.subTest(objetivos=objetivos), self.assertRaises(TypeError):
                Mundo([self.coger_caja], **self._objetos(), objetivos=objetivos)  # type: ignore[arg-type]

    def test_el_error_de_un_argumento_opcional_menciona_none(self) -> None:
        """Comprueba que el error de los argumentos opcionales menciona ``None``.

        ``transportadores`` y ``objetivos`` también aceptan ``None``, que significa
        que no se dan, así que su mensaje de error incluye ``None`` entre los
        valores válidos. El de un argumento obligatorio, como ``drones``, no lo
        incluye.
        """
        for nombre in ("transportadores", "objetivos"):
            with self.subTest(nombre=nombre):
                with self.assertRaises(TypeError) as contexto:
                    Mundo([self.coger_caja], **self._objetos(), **{nombre: 5})  # type: ignore[arg-type]
                self.assertEqual(
                    str(contexto.exception),
                    f"'{nombre}' debe ser una lista, una tupla o None, se recibió 5",
                )

        with self.assertRaises(TypeError) as contexto:
            Mundo([self.coger_caja], **{**self._objetos(), "drones": 5})  # type: ignore[arg-type]
        self.assertEqual(
            str(contexto.exception),
            "'drones' debe ser una lista o una tupla, se recibió 5",
        )

    def test_caja_o_persona_con_un_contenido_no_declarado(self) -> None:
        """Comprueba que las cajas y las personas solo usan contenidos que se dieron.

        Un contenido mal escrito daría un veredicto falso sobre el plan, así que se
        rechaza al construir el mundo.
        """
        agua = Contenido("agua")
        no_declarado: dict[str, tuple[dict[str, list[Any]], str]] = {
            "caja": (
                {"cajas": [self.caja, Caja("caja2", self.deposito, agua)]},
                (
                    "la caja caja2 tiene el contenido agua, que no aparece en la "
                    "lista de contenidos dada"
                ),
            ),
            "necesidad": (
                {"personas": [self.persona, Persona("persona2", self.deposito, agua)]},
                (
                    "la persona persona2 necesita el contenido agua, que no aparece "
                    "en la lista de contenidos dada"
                ),
            ),
        }

        for tipo, (cambio, mensaje) in no_declarado.items():
            with self.subTest(no_declarado=tipo):
                with self.assertRaises(ValueError) as contexto:
                    Mundo([self.coger_caja], **{**self._objetos(), **cambio})
                self.assertEqual(str(contexto.exception), mensaje)

    def test_objeto_en_una_localizacion_no_declarada(self) -> None:
        """Comprueba que los objetos del problema solo están en localizaciones dadas.

        Un objeto en una localización no declarada no se podría dibujar en la
        ventana, así que se rechaza al construir el mundo.
        """
        almacen = Localizacion("almacen")
        no_declarada: dict[str, tuple[dict[str, list[Any]], str]] = {
            "dron": (
                {"drones": [self.dron, Dron("dron2", almacen, [Brazo("otro-brazo")])]},
                (
                    "el dron dron2 está en la localización almacen, que no aparece "
                    "en la lista de localizaciones dada"
                ),
            ),
            "caja": (
                {"cajas": [self.caja, Caja("caja2", almacen, COMIDA)]},
                (
                    "la caja caja2 está en la localización almacen, que no aparece "
                    "en la lista de localizaciones dada"
                ),
            ),
            "persona": (
                {"personas": [self.persona, Persona("persona2", almacen, COMIDA)]},
                (
                    "la persona persona2 está en la localización almacen, que no "
                    "aparece en la lista de localizaciones dada"
                ),
            ),
            "transportador": (
                {"transportadores": [Transportador("transportador2", almacen, 4)]},
                (
                    "el transportador transportador2 está en la localización "
                    "almacen, que no aparece en la lista de localizaciones dada"
                ),
            ),
        }

        for tipo, (cambio, mensaje) in no_declarada.items():
            with self.subTest(no_declarada=tipo):
                with self.assertRaises(ValueError) as contexto:
                    Mundo([self.coger_caja], **{**self._objetos(), **cambio})
                self.assertEqual(str(contexto.exception), mensaje)

    def test_brazo_de_dos_drones(self) -> None:
        """Comprueba que un brazo no puede pertenecer a dos drones.

        Los dos drones compartirían lo que sujeta el brazo, y un plan imposible
        podría ejecutarse sin ningún error.
        """
        otro_dron = Dron("dron2", self.deposito, [self.brazo])

        with self.assertRaises(ValueError) as contexto:
            Mundo(
                [self.coger_caja],
                **{**self._objetos(), "drones": [self.dron, otro_dron]},
            )

        self.assertEqual(
            str(contexto.exception),
            "el brazo brazo no puede pertenecer a más de un dron, pertenece al "
            "dron dron1 y al dron dron2",
        )

    def test_nombre_repetido(self) -> None:
        """Comprueba que dos objetos del problema no pueden llamarse igual.

        En PDDL todos los objetos comparten un único espacio de nombres, así que el
        nombre tiene que ser único aunque los objetos sean de tipos distintos. Un
        mismo objeto repetido en una lista también se rechaza.
        """
        repetido: dict[str, tuple[dict[str, list[Any]], str]] = {
            "misma localizacion": (
                {"localizaciones": [self.deposito, self.deposito]},
                (
                    "la localización deposito aparece más de una vez en la lista "
                    "de localizaciones dada"
                ),
            ),
            "localizacion": (
                {"localizaciones": [self.deposito, Localizacion("deposito")]},
                "hay más de una localización con el nombre deposito",
            ),
            "mismo dron": (
                {"drones": [self.dron, self.dron]},
                "el dron dron1 aparece más de una vez en la lista de drones dada",
            ),
            "dron": (
                {
                    "drones": [
                        self.dron,
                        Dron("dron1", self.deposito, [Brazo("otro-brazo")]),
                    ]
                },
                "hay más de un dron con el nombre dron1",
            ),
            "brazo": (
                {"drones": [self.dron, Dron("dron2", self.deposito, [Brazo("brazo")])]},
                "hay más de un brazo con el nombre brazo",
            ),
            "caja": (
                {"cajas": [self.caja, Caja("caja1", self.deposito, COMIDA)]},
                "hay más de una caja con el nombre caja1",
            ),
            "persona": (
                {
                    "personas": [
                        self.persona,
                        Persona("persona1", self.deposito, COMIDA),
                    ]
                },
                "hay más de una persona con el nombre persona1",
            ),
            "contenido": (
                {"contenidos": [COMIDA, Contenido("comida")]},
                "hay más de un contenido con el nombre comida",
            ),
            "transportador": (
                {
                    "transportadores": [
                        self.transportador,
                        Transportador("transportador1", self.deposito, 4),
                    ]
                },
                "hay más de un transportador con el nombre transportador1",
            ),
            "dron y caja": (
                {"cajas": [self.caja, Caja("dron1", self.deposito, COMIDA)]},
                "el dron dron1 y la caja dron1 tienen el mismo nombre",
            ),
            "localizacion y contenido": (
                {"contenidos": [*CONTENIDOS, Contenido("deposito")]},
                (
                    "la localización deposito y el contenido deposito tienen el mismo "
                    "nombre"
                ),
            ),
        }

        for caso, (cambio, mensaje) in repetido.items():
            with self.subTest(repetido=caso):
                with self.assertRaises(ValueError) as contexto:
                    Mundo([self.coger_caja], **{**self._objetos(), **cambio})
                self.assertEqual(str(contexto.exception), mensaje)

    def test_objetivo_con_un_objeto_no_declarado(self) -> None:
        """Comprueba que un objetivo solo se puede referir a objetos que se dieron."""
        otra_localizacion = Localizacion("otra-localizacion")
        otro_dron = Dron("dron2", self.deposito, [Brazo("otro-brazo")])
        otra_persona = Persona("persona2", self.deposito, COMIDA)

        # Cada mensaje nombra el objeto con su artículo, contraído con "a" si hace
        # falta ("al dron dron2").
        no_declarado = {
            "persona": (
                PersonaTieneContenido(otra_persona, COMIDA),
                (
                    'el objetivo "la persona persona2 posee una caja con el contenido '
                    "'comida'\" se refiere a la persona persona2, que no aparece en la "
                    "lista de personas dada"
                ),
            ),
            "dron": (
                DronEnLocalizacion(otro_dron, self.deposito),
                (
                    "el objetivo 'el dron dron2 está en la localización deposito' se "
                    "refiere al dron dron2, que no aparece en la lista de drones dada"
                ),
            ),
            "localizacion": (
                DronEnLocalizacion(self.dron, otra_localizacion),
                (
                    "el objetivo 'el dron dron1 está en la localización "
                    "otra-localizacion' se refiere a la localización "
                    "otra-localizacion, que no aparece en la lista de "
                    "localizaciones dada"
                ),
            ),
            "contenido": (
                PersonaTieneContenido(self.persona, Contenido("agua")),
                (
                    'el objetivo "la persona persona1 posee una caja con el contenido '
                    "'agua'\" se refiere al contenido agua, que no aparece en la "
                    "lista de contenidos dada"
                ),
            ),
            # El problema de _objetos() no tiene lista de transportadores.
            "transportador": (
                TransportadorEnLocalizacion(self.transportador, self.deposito),
                (
                    "el objetivo 'el transportador transportador1 está en la "
                    "localización deposito' se refiere a un transportador, pero no se "
                    "dan transportadores"
                ),
            ),
        }

        for tipo, (objetivo, mensaje) in no_declarado.items():
            with self.subTest(no_declarado=tipo):
                with self.assertRaises(ValueError) as contexto:
                    Mundo([self.coger_caja], **self._objetos(), objetivos=[objetivo])
                self.assertEqual(str(contexto.exception), mensaje)

    def test_objetivo_con_un_contenido_que_la_persona_no_necesita(self) -> None:
        """Comprueba que se rechaza un objetivo que ningún plan puede lograr.

        ``EntregarCaja`` solo entrega cajas con algo que la persona necesita, así
        que una persona que necesita comida nunca podrá poseer una caja de
        medicina.
        """
        objetivo = PersonaTieneContenido(self.persona, MEDICINA)

        with self.assertRaises(ValueError) as contexto:
            Mundo([self.coger_caja], **self._objetos(), objetivos=[objetivo])

        self.assertIn("persona1", str(contexto.exception))
        self.assertIn("medicina", str(contexto.exception))
        self.assertIn(
            "la persona persona1 necesita 'comida', y solo se le pueden entregar",
            str(contexto.exception),
        )

    def test_objetivo_para_una_persona_sin_necesidades(self) -> None:
        """Comprueba que el mensaje dice que la persona no necesita nada."""
        persona_sin_necesidades = Persona("persona2", self.deposito)
        objetivo = PersonaTieneContenido(persona_sin_necesidades, COMIDA)
        objetos = self._objetos() | {"personas": [persona_sin_necesidades]}

        with self.assertRaises(ValueError) as contexto:
            Mundo([self.coger_caja], **objetos, objetivos=[objetivo])  # type: ignore[arg-type]

        self.assertIn("la persona persona2 no necesita nada", str(contexto.exception))

    def test_objetivo_ya_cumplido_se_acepta_sin_la_necesidad(self) -> None:
        """Comprueba que un objetivo que ya se cumple no se rechaza.

        Tras entregar la caja de comida, la persona ya no necesita comida, pero
        la posee. Lo habitual es que cada mundo tenga sus propios objetos, pero si
        se construye uno nuevo sobre los mismos, parte de un estado en el que el
        objetivo ya se cumple, así que no lo rechaza como inalcanzable.
        """
        entregar_caja = EntregarCaja(
            self.dron, self.brazo, self.caja, self.persona, inicio_sim=1
        )
        mundo = Mundo(
            [self.coger_caja, entregar_caja],
            **self._objetos(),
            objetivos=[self.objetivo],
        )
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        with contextlib.redirect_stdout(io.StringIO()):
            mundo.simulacion_texto()
        self.assertNotIn(COMIDA, self.persona.necesidades)

        mundo_siguiente = Mundo([], **self._objetos(), objetivos=[self.objetivo])

        self.assertEqual(
            mundo_siguiente.verificar().veredicto, InformeVerificacion.VALIDO
        )


class TestExcepcionesSimulacionTexto(unittest.TestCase):
    """``simulacion_texto()`` rechaza un ``paso_tiempo`` incorrecto."""

    def setUp(self) -> None:
        """Crea un mundo con un plan de una acción."""
        deposito = Localizacion("deposito")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        caja = Caja("caja1", deposito, COMIDA)
        self.mundo = Mundo(
            [CogerCaja(dron, brazo, caja, inicio_sim=0)],
            localizaciones=[deposito],
            drones=[dron],
            cajas=[caja],
            personas=[],
            contenidos=[COMIDA],
        )

    def test_paso_tiempo_tiene_que_ser_un_int_o_un_float(self) -> None:
        """Comprueba que un ``paso_tiempo`` de tipo incorrecto lanza ``TypeError``."""
        for paso_tiempo in ("0.1", None, True):
            with self.subTest(paso_tiempo=paso_tiempo), self.assertRaises(TypeError):
                self.mundo.simulacion_texto(paso_tiempo)  # type: ignore[arg-type]

    def test_paso_tiempo_tiene_que_ser_mayor_que_cero(self) -> None:
        """Comprueba que un ``paso_tiempo`` de 0 o menos lanza ``ValueError``."""
        for paso_tiempo in (0, -1, float("nan")):
            with self.subTest(paso_tiempo=paso_tiempo), self.assertRaises(ValueError):
                self.mundo.simulacion_texto(paso_tiempo)


if __name__ == "__main__":
    unittest.main()
