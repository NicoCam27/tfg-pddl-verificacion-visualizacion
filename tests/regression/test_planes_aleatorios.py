"""Pruebas de propiedades con planes generados al azar por Hypothesis.

Cada prueba comprueba algo que tiene que cumplirse con cualquier plan, no con
uno concreto: que un plan válido por construcción da ``"VÁLIDO"``, que el
informe no depende de ``paso_tiempo`` ni de en cuántas veces se avanza, y que
``reiniciar()`` no cambia el resultado. Hypothesis prueba cada propiedad con
muchos planes distintos.

El generador de este módulo no decide nada por sí mismo: cada decisión
(cuántos drones hay, qué acción se añade, cuánto dura...) la saca del ``data``
que Hypothesis da a la prueba. Así, Hypothesis conoce todas las decisiones, y si
un plan hace fallar una prueba, lo reduce: la repite con decisiones más
sencillas (menos drones, menos acciones...) mientras siga fallando, y muestra el
caso más pequeño que encuentra. Con ``derandomize=True`` cada ejecución prueba
los mismos planes, como cualquier otra prueba de la batería.

``generar_problema`` devuelve una descripción del problema hecha solo de
nombres y números, y ``construir_mundo`` crea con ella un ``Mundo`` con objetos
nuevos. Una misma descripción se construye tantas veces como haga falta, y cada
ejecución empieza desde cero.
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
import logging
import math
import unittest
from typing import TYPE_CHECKING, Any

from hypothesis import given, settings
from hypothesis import strategies as st

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
    from collections.abc import Callable, Sequence

    from simulador_pddl.acciones import Accion
    from simulador_pddl.objetivos import Objetivo

# Valores exactos en binario, para que las sumas de instantes no acumulen errores
# de redondeo que dependan del orden en que se hacen.
DURACIONES = (0.5, 1.0, 1.5, 2.0)
ESPERAS = (0.0, 0.0, 0.25, 1.0)
CONTENIDOS = ("comida", "medicina", "agua")

# Desde un paso más corto que cualquier acción hasta uno más largo que muchos
# planes enteros.
PASOS_TIEMPO = (0.1, 0.7, 5.0)

# Cuántos planes prueba cada prueba. ``derandomize=True`` hace que sean siempre
# los mismos, y ``deadline=None`` quita el límite de tiempo por plan, porque una
# simulación larga no es un error.
AJUSTES = settings(max_examples=200, deadline=None, derandomize=True)

# Una acción que el generador puede añadir: su tipo, los nombres de sus
# argumentos en el orden del constructor y los objetos que usa. Una acción de un
# brazo usa el brazo, y un movimiento usa todos los brazos del dron.
type Opcion = tuple[str, tuple[str, ...], tuple[str, ...]]


class Elector:
    """Saca cada decisión del generador del ``data`` de Hypothesis."""

    def __init__(self, data: st.DataObject) -> None:
        """Crea el elector sobre el ``data`` que recibe la prueba."""
        self._data = data

    def entero(self, minimo: int, maximo: int) -> int:
        """Devuelve un entero entre ``minimo`` y ``maximo``, los dos incluidos."""
        return self._data.draw(st.integers(minimo, maximo))

    def elegir[T](self, opciones: Sequence[T]) -> T:
        """Devuelve uno de los elementos de ``opciones``, que no está vacía."""
        return self._data.draw(st.sampled_from(opciones))


@dataclasses.dataclass(frozen=True)
class Paso:
    """Una acción del plan, descrita con los nombres de sus objetos.

    Attributes:
        tipo: El nombre de la clase de la acción, p. ej. ``"CogerCaja"``.
        argumentos: Los nombres de sus objetos, en el orden del constructor.
        inicio: Su ``inicio_sim``.
        duracion: Su ``duracion_sim``.
    """

    tipo: str
    argumentos: tuple[str, ...]
    inicio: float
    duracion: float


@dataclasses.dataclass(frozen=True)
class Problema:
    """Un problema y su plan, descritos solo con nombres y números.

    Attributes:
        localizaciones: Los nombres de las localizaciones.
        contenidos: Los nombres de los contenidos.
        drones: Nombre, localización y nombres de los brazos de cada dron.
        transportadores: Nombre, localización y capacidad de cada transportador.
        cajas: Nombre, localización y contenido de cada caja.
        personas: Nombre, localización y necesidades de cada persona.
        pasos: Las acciones del plan.
        objetivos: Tipo y nombres de los objetos de cada objetivo, p. ej.
            ``("PersonaTieneContenido", "persona0", "comida")``.
    """

    localizaciones: tuple[str, ...]
    contenidos: tuple[str, ...]
    drones: tuple[tuple[str, str, tuple[str, ...]], ...]
    transportadores: tuple[tuple[str, str, int], ...]
    cajas: tuple[tuple[str, str, str], ...]
    personas: tuple[tuple[str, str, tuple[str, ...]], ...]
    pasos: tuple[Paso, ...]
    objetivos: tuple[tuple[str, ...], ...]


@dataclasses.dataclass
class Modelo:
    """El estado del mundo según el generador, mientras escribe el plan.

    Attributes:
        localizacion_dron: La localización de cada dron.
        brazos_dron: Los brazos de cada dron.
        en_brazo: Lo que sujeta cada brazo, ``("caja", nombre)`` o
            ``("transportador", nombre)``, o ``None`` si está libre.
        caja: Dónde está cada caja: ``("suelo", localizacion)``,
            ``("brazo", brazo)``, ``("dentro", transportador)`` o
            ``("entregada", persona)``.
        contenido_caja: El contenido de cada caja.
        transportador: Dónde está cada transportador: ``("suelo", localizacion)``
            o ``("brazo", brazo)``.
        capacidad: La capacidad de cada transportador.
        dentro: Las cajas que hay dentro de cada transportador.
        localizacion_persona: La localización de cada persona.
        necesidades: Las necesidades que le quedan a cada persona.
        relojes: Para cada brazo, caja, transportador y persona, el instante en
            que termina la última acción que lo ha usado.
    """

    localizacion_dron: dict[str, str]
    brazos_dron: dict[str, tuple[str, ...]]
    en_brazo: dict[str, tuple[str, str] | None]
    caja: dict[str, tuple[str, str]]
    contenido_caja: dict[str, str]
    transportador: dict[str, tuple[str, str]]
    capacidad: dict[str, int]
    dentro: dict[str, list[str]]
    localizacion_persona: dict[str, str]
    necesidades: dict[str, list[str]]
    relojes: dict[str, float]


def generar_problema(elector: Elector) -> Problema:
    """Genera un problema pequeño y un plan válido para él.

    El generador lleva su propio modelo del estado y solo añade una acción si
    ese modelo dice que se puede ejecutar. Sigue las reglas de solapamiento de
    la biblioteca: cada brazo hace sus acciones una detrás de otra, pero los
    brazos de un mismo dron trabajan a la vez. Un movimiento ocupa el dron
    entero, así que empieza cuando han terminado todos sus brazos, y los brazos
    no vuelven a trabajar hasta que el dron llega. Una acción que usa una caja,
    un transportador o una persona empieza cuando ha terminado la última acción
    que los usó. Los drones distintos trabajan en paralelo.

    Los objetivos son las entregas que hace el plan y la posición final de cada
    dron y de cada transportador que acaba en el suelo, así que el plan los
    cumple todos: su veredicto tiene que ser ``"VÁLIDO"``.
    """
    localizaciones = tuple(f"loc{i}" for i in range(elector.entero(2, 4)))
    contenidos = CONTENIDOS[: elector.entero(1, len(CONTENIDOS))]

    drones = tuple(
        (
            f"dron{i}",
            elector.elegir(localizaciones),
            tuple(f"brazo{i}_{j}" for j in range(elector.entero(1, 2))),
        )
        for i in range(elector.entero(1, 3))
    )
    transportadores = tuple(
        (f"transportador{i}", elector.elegir(localizaciones), elector.entero(1, 3))
        for i in range(elector.entero(0, 1))
    )
    cajas = tuple(
        (f"caja{i}", elector.elegir(localizaciones), elector.elegir(contenidos))
        for i in range(elector.entero(1, 5))
    )
    personas = tuple(
        (
            f"persona{i}",
            elector.elegir(localizaciones),
            tuple(contenido for contenido in contenidos if elector.entero(0, 1)),
        )
        for i in range(elector.entero(1, 3))
    )

    modelo = Modelo(
        localizacion_dron={nombre: localizacion for nombre, localizacion, _ in drones},
        brazos_dron={nombre: brazos for nombre, _, brazos in drones},
        en_brazo={brazo: None for _, _, brazos in drones for brazo in brazos},
        caja={nombre: ("suelo", localizacion) for nombre, localizacion, _ in cajas},
        contenido_caja={nombre: contenido for nombre, _, contenido in cajas},
        transportador={
            nombre: ("suelo", localizacion)
            for nombre, localizacion, _ in transportadores
        },
        capacidad={nombre: capacidad for nombre, _, capacidad in transportadores},
        dentro={nombre: [] for nombre, _, _ in transportadores},
        localizacion_persona={
            nombre: localizacion for nombre, localizacion, _ in personas
        },
        necesidades={nombre: list(necesidades) for nombre, _, necesidades in personas},
        relojes={},
    )

    pasos: list[Paso] = []
    entregas: list[tuple[str, str]] = []
    for _ in range(elector.entero(0, 15)):
        dron = elector.elegir([nombre for nombre, _, _ in drones])
        opciones = acciones_posibles(modelo, dron, localizaciones)
        if not opciones:
            continue

        # Primero el tipo y después la acción concreta: si no, los tipos con muchas
        # variantes (``Mover`` tiene una por destino) dejarían poco sitio a los
        # demás.
        tipo = elector.elegir(sorted({opcion[0] for opcion in opciones}))
        _, argumentos, usados = elector.elegir(
            [opcion for opcion in opciones if opcion[0] == tipo]
        )
        inicio = max(modelo.relojes.get(nombre, 0.0) for nombre in usados)
        inicio += elector.elegir(ESPERAS)
        duracion = elector.elegir(DURACIONES)

        pasos.append(Paso(tipo, argumentos, inicio, duracion))
        for nombre in usados:
            modelo.relojes[nombre] = inicio + duracion
        entrega = aplicar(modelo, tipo, argumentos)
        if entrega is not None:
            entregas.append(entrega)

    objetivos: list[tuple[str, ...]] = [
        ("PersonaTieneContenido", persona, contenido) for persona, contenido in entregas
    ]
    objetivos += [
        ("DronEnLocalizacion", dron, modelo.localizacion_dron[dron])
        for dron, _, _ in drones
    ]
    objetivos += [
        ("TransportadorEnLocalizacion", nombre, estado[1])
        for nombre, estado in modelo.transportador.items()
        if estado[0] == "suelo"
    ]

    return Problema(
        localizaciones,
        contenidos,
        drones,
        transportadores,
        cajas,
        personas,
        tuple(pasos),
        tuple(objetivos),
    )


def acciones_posibles(
    modelo: Modelo, dron: str, localizaciones: tuple[str, ...]
) -> list[Opcion]:
    """Devuelve las acciones que el dron puede empezar en el estado del modelo.

    Solo se cogen, se sueltan, se meten o se sacan cajas de un transportador que
    está en el suelo, en la localización del dron.
    """
    aqui = modelo.localizacion_dron[dron]
    otras = [destino for destino in localizaciones if destino != aqui]
    todos_los_brazos = modelo.brazos_dron[dron]
    opciones: list[Opcion] = [
        ("Mover", (dron, aqui, destino), todos_los_brazos) for destino in otras
    ]

    cajas_aqui = [
        caja for caja, estado in modelo.caja.items() if estado == ("suelo", aqui)
    ]
    transportadores_aqui = [
        transportador
        for transportador, estado in modelo.transportador.items()
        if estado == ("suelo", aqui)
    ]
    personas_aqui = [
        persona
        for persona, localizacion in modelo.localizacion_persona.items()
        if localizacion == aqui
    ]

    for brazo in modelo.brazos_dron[dron]:
        sujeto = modelo.en_brazo[brazo]
        if sujeto is None:
            opciones += [
                ("CogerCaja", (dron, brazo, caja), (brazo, caja)) for caja in cajas_aqui
            ]
            for transportador in transportadores_aqui:
                opciones.append(
                    (
                        "CogerTransportador",
                        (dron, brazo, transportador),
                        (brazo, transportador),
                    )
                )
                opciones += [
                    (
                        "SacarCajaDeTransportador",
                        (dron, brazo, caja, transportador),
                        (brazo, caja, transportador),
                    )
                    for caja in modelo.dentro[transportador]
                ]
                opciones += [
                    (
                        "MoverTransportador",
                        (dron, brazo, transportador, aqui, destino),
                        (*todos_los_brazos, transportador),
                    )
                    for destino in otras
                ]
        elif sujeto[0] == "caja":
            caja = sujeto[1]
            opciones.append(("Soltar", (dron, brazo, caja), (brazo, caja)))
            opciones += [
                ("EntregarCaja", (dron, brazo, caja, persona), (brazo, caja, persona))
                for persona in personas_aqui
                if modelo.contenido_caja[caja] in modelo.necesidades[persona]
            ]
            opciones += [
                (
                    "PonerCajaEnTransportador",
                    (dron, brazo, caja, transportador),
                    (brazo, caja, transportador),
                )
                for transportador in transportadores_aqui
                if len(modelo.dentro[transportador]) < modelo.capacidad[transportador]
            ]
        else:
            transportador = sujeto[1]
            opciones.append(
                (
                    "SoltarTransportador",
                    (dron, brazo, transportador),
                    (brazo, transportador),
                )
            )

    return opciones


def aplicar(
    modelo: Modelo, tipo: str, argumentos: tuple[str, ...]
) -> tuple[str, str] | None:
    """Aplica al modelo el efecto completo de una acción.

    Returns:
        La persona y el contenido, si la acción es una entrega, o ``None``.
    """
    dron, *resto = argumentos
    aqui = modelo.localizacion_dron[dron]
    if tipo == "Mover":
        modelo.localizacion_dron[dron] = resto[1]
    elif tipo == "CogerCaja":
        brazo, caja = resto
        modelo.en_brazo[brazo] = ("caja", caja)
        modelo.caja[caja] = ("brazo", brazo)
    elif tipo == "Soltar":
        brazo, caja = resto
        modelo.en_brazo[brazo] = None
        modelo.caja[caja] = ("suelo", aqui)
    elif tipo == "EntregarCaja":
        brazo, caja, persona = resto
        modelo.en_brazo[brazo] = None
        modelo.caja[caja] = ("entregada", persona)
        modelo.necesidades[persona].remove(modelo.contenido_caja[caja])
        return persona, modelo.contenido_caja[caja]
    elif tipo == "PonerCajaEnTransportador":
        brazo, caja, transportador = resto
        modelo.en_brazo[brazo] = None
        modelo.caja[caja] = ("dentro", transportador)
        modelo.dentro[transportador].append(caja)
    elif tipo == "SacarCajaDeTransportador":
        brazo, caja, transportador = resto
        modelo.en_brazo[brazo] = ("caja", caja)
        modelo.caja[caja] = ("brazo", brazo)
        modelo.dentro[transportador].remove(caja)
    elif tipo == "CogerTransportador":
        brazo, transportador = resto
        modelo.en_brazo[brazo] = ("transportador", transportador)
        modelo.transportador[transportador] = ("brazo", brazo)
    elif tipo == "SoltarTransportador":
        brazo, transportador = resto
        modelo.en_brazo[brazo] = None
        modelo.transportador[transportador] = ("suelo", aqui)
    else:
        # MoverTransportador: el dron y el transportador acaban en el destino, y
        # el transportador queda en el suelo.
        _, transportador, _, destino = resto
        modelo.localizacion_dron[dron] = destino
        modelo.transportador[transportador] = ("suelo", destino)
    return None


def alterar(problema: Problema, elector: Elector) -> Problema:
    """Devuelve el problema con una acción cambiada, o sin cambios.

    El cambio quita la acción, la adelanta o la repite más tarde. El plan
    resultante puede seguir siendo válido o fallar de cualquier forma, y las
    propiedades que no dependen del veredicto se tienen que cumplir igual.
    """
    cambio = elector.elegir(("ninguno", "quitar", "adelantar", "repetir"))
    if cambio == "ninguno" or not problema.pasos:
        return problema

    pasos = list(problema.pasos)
    indice = elector.entero(0, len(pasos) - 1)
    paso = pasos[indice]
    if cambio == "quitar":
        del pasos[indice]
    elif cambio == "adelantar":
        inicio = max(0.0, paso.inicio - elector.elegir(DURACIONES))
        pasos[indice] = dataclasses.replace(paso, inicio=inicio)
    else:
        inicio = paso.inicio + elector.elegir(DURACIONES)
        pasos.append(dataclasses.replace(paso, inicio=inicio))
    return dataclasses.replace(problema, pasos=tuple(pasos))


CLASES_ACCION: dict[str, Callable[..., Accion]] = {
    clase.__name__: clase
    for clase in (
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
}

CLASES_OBJETIVO: dict[str, Callable[..., Objetivo]] = {
    clase.__name__: clase
    for clase in (
        DronEnLocalizacion,
        PersonaTieneContenido,
        TransportadorEnLocalizacion,
    )
}


def construir_mundo(problema: Problema) -> Mundo:
    """Crea un ``Mundo`` con objetos nuevos a partir de la descripción."""
    # Todos los objetos por su nombre, que el generador no repite entre tipos.
    objetos: dict[str, Any] = {}
    localizaciones = [Localizacion(nombre) for nombre in problema.localizaciones]
    contenidos = [Contenido(nombre) for nombre in problema.contenidos]
    objetos.update(
        {localizacion.nombre: localizacion for localizacion in localizaciones}
    )
    objetos.update({contenido.nombre: contenido for contenido in contenidos})

    drones = []
    for nombre, localizacion, nombres_brazos in problema.drones:
        brazos = [Brazo(brazo) for brazo in nombres_brazos]
        objetos.update(zip(nombres_brazos, brazos, strict=True))
        drones.append(Dron(nombre, objetos[localizacion], brazos))
    transportadores = [
        Transportador(nombre, objetos[localizacion], capacidad)
        for nombre, localizacion, capacidad in problema.transportadores
    ]
    cajas = [
        Caja(nombre, objetos[localizacion], objetos[contenido])
        for nombre, localizacion, contenido in problema.cajas
    ]
    personas = [
        Persona(
            nombre,
            objetos[localizacion],
            [objetos[contenido] for contenido in necesidades],
        )
        for nombre, localizacion, necesidades in problema.personas
    ]
    objetos.update({dron.nombre: dron for dron in drones})
    objetos.update(
        {transportador.nombre: transportador for transportador in transportadores}
    )
    objetos.update({caja.nombre: caja for caja in cajas})
    objetos.update({persona.nombre: persona for persona in personas})

    acciones = [
        CLASES_ACCION[paso.tipo](
            *(objetos[nombre] for nombre in paso.argumentos), paso.inicio, paso.duracion
        )
        for paso in problema.pasos
    ]
    objetivos = [
        CLASES_OBJETIVO[tipo](*(objetos[nombre] for nombre in nombres))
        for tipo, *nombres in problema.objetivos
    ]
    return Mundo(
        acciones,
        localizaciones=localizaciones,
        drones=drones,
        cajas=cajas,
        personas=personas,
        contenidos=contenidos,
        transportadores=transportadores,
        objetivos=objetivos,
    )


def datos_comparables(informe: InformeVerificacion) -> tuple[object, ...]:
    """Devuelve lo que tiene que coincidir entre dos ejecuciones del mismo plan.

    La acción fallida se compara por su descripción, porque cada ejecución crea
    sus propios objetos.
    """
    return (
        informe.veredicto,
        informe.error,
        None if informe.accion_fallida is None else informe.accion_fallida.desc,
        informe.fallo_en,
        informe.acciones_terminadas,
        tuple(
            (estado.cumplido, estado.logrado_en, estado.roto_en)
            for estado in informe.estados_objetivos
        ),
        tuple(estado.explicacion_fallo for estado in informe.estados_objetivos),
    )


class TestPlanesAleatorios(unittest.TestCase):
    """Las propiedades de la simulación se cumplen con planes generados al azar."""

    def setUp(self) -> None:
        """Silencia el registro."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    @AJUSTES
    @given(st.data())
    def test_los_planes_generados_son_validos(self, data: st.DataObject) -> None:
        """Comprueba que la biblioteca da por válido cada plan del generador.

        El generador escribe el plan con su propio modelo del estado, así que
        esta prueba compara la biblioteca con un modelo independiente.
        """
        problema = generar_problema(Elector(data))
        informe = construir_mundo(problema).avanzar_hasta(math.inf)

        self.assertEqual(
            informe.veredicto, InformeVerificacion.VALIDO, informe.resumen()
        )

    @AJUSTES
    @given(st.data())
    def test_el_resultado_no_depende_del_paso(self, data: st.DataObject) -> None:
        """Comprueba que cada plan da el mismo informe con cualquier ``paso_tiempo``."""
        elector = Elector(data)
        problema = alterar(generar_problema(elector), elector)
        esperado = datos_comparables(construir_mundo(problema).avanzar_hasta(math.inf))

        for paso_tiempo in PASOS_TIEMPO:
            with contextlib.redirect_stdout(io.StringIO()):
                informe = construir_mundo(problema).simulacion_texto(paso_tiempo)
            self.assertEqual(
                datos_comparables(informe), esperado, f"paso {paso_tiempo}"
            )

    @AJUSTES
    @given(st.data())
    def test_avanzar_a_trozos_al_azar_da_lo_mismo(self, data: st.DataObject) -> None:
        """Comprueba que avanzar a trozos al azar da el mismo informe."""
        elector = Elector(data)
        problema = alterar(generar_problema(elector), elector)
        esperado = datos_comparables(construir_mundo(problema).avanzar_hasta(math.inf))

        mundo = construir_mundo(problema)
        instante = 0.0
        for _ in range(elector.entero(1, 5)):
            instante += elector.elegir((0.25, 0.5, 1.0, 3.0))
            mundo.avanzar_hasta(instante)

        self.assertEqual(datos_comparables(mundo.avanzar_hasta(math.inf)), esperado)

    @AJUSTES
    @given(st.data())
    def test_reiniciar_no_cambia_el_resultado(self, data: st.DataObject) -> None:
        """Comprueba que un informe no cambia al reiniciar y que repetir da lo mismo."""
        elector = Elector(data)
        problema = alterar(generar_problema(elector), elector)
        mundo = construir_mundo(problema)
        primero = mundo.avanzar_hasta(math.inf)
        esperado = datos_comparables(primero)

        mundo.reiniciar()

        self.assertEqual(datos_comparables(primero), esperado)
        self.assertEqual(datos_comparables(mundo.avanzar_hasta(math.inf)), esperado)


if __name__ == "__main__":
    unittest.main()
