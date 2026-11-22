"""Validadores de los argumentos de los objetos, las acciones y los objetivos.

Cada función comprueba un argumento al construir: lanza ``TypeError`` o
``ValueError`` con un mensaje que nombra el argumento, o devuelve ``None``. Al
final están las funciones que escriben partes de los mensajes:
``con_articulo()`` y ``con_preposicion_a()`` escriben un objeto con su artículo,
``tipo_en_plural()`` y ``describir_cantidad()``, un tipo en plural o con una
cantidad, y ``describir_necesidades()``, lo que necesita una persona.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulador_pddl.objetos import ObjetoDominio
    from simulador_pddl.objetos.brazo import Brazo
    from simulador_pddl.objetos.dron import Dron

# Validadores de los argumentos de cada objeto
# Cada validador de un tipo de objeto importa su clase dentro de la función, para
# evitar una importación circular.


def validar_objeto_brazo(brazo: object) -> None:
    """Lanza ``TypeError`` si ``brazo`` no es un ``Brazo``."""
    from simulador_pddl.objetos.brazo import Brazo

    if not isinstance(brazo, Brazo):
        msg_objeto_brazo = f"'brazo' debe ser un objeto Brazo, se recibió {brazo!r}"
        raise TypeError(msg_objeto_brazo)


def validar_objeto_caja(caja: object) -> None:
    """Lanza ``TypeError`` si ``caja`` no es una ``Caja``."""
    from simulador_pddl.objetos.caja import Caja

    if not isinstance(caja, Caja):
        msg_objeto_caja = f"'caja' debe ser un objeto Caja, se recibió {caja!r}"
        raise TypeError(msg_objeto_caja)


def validar_objeto_transportador(transportador: object) -> None:
    """Lanza ``TypeError`` si ``transportador`` no es un ``Transportador``."""
    from simulador_pddl.objetos.transportador import Transportador

    if not isinstance(transportador, Transportador):
        msg_objeto_transportador = (
            "'transportador' debe ser un objeto Transportador, "
            f"se recibió {transportador!r}"
        )
        raise TypeError(msg_objeto_transportador)


def validar_objeto_dron(dron: object) -> None:
    """Lanza ``TypeError`` si ``dron`` no es un ``Dron``."""
    from simulador_pddl.objetos.dron import Dron

    if not isinstance(dron, Dron):
        msg_objeto_dron = f"'dron' debe ser un objeto Dron, se recibió {dron!r}"
        raise TypeError(msg_objeto_dron)


def validar_objeto_localizacion(
    localizacion: object, nombre: str = "localizacion"
) -> None:
    """Lanza ``TypeError`` si ``localizacion`` no es una ``Localizacion``.

    ``nombre`` es el nombre del argumento que aparece en el mensaje de error.
    Hace falta porque una localización llega en argumentos con nombres
    distintos: ``localizacion`` en los objetos y los objetivos, y ``origen`` y
    ``destino`` en ``Mover`` y ``MoverTransportador``. Así el mensaje nombra el
    argumento que dio el usuario, p. ej. ``'destino' debe ser un objeto
    Localizacion``.
    """
    from simulador_pddl.objetos.localizacion import Localizacion

    if not isinstance(localizacion, Localizacion):
        msg_objeto_localizacion = (
            f"'{nombre}' debe ser un objeto Localizacion, se recibió {localizacion!r}"
        )
        raise TypeError(msg_objeto_localizacion)


def validar_objeto_persona(persona: object) -> None:
    """Lanza ``TypeError`` si ``persona`` no es una ``Persona``."""
    from simulador_pddl.objetos.persona import Persona

    if not isinstance(persona, Persona):
        msg_objeto_persona = (
            f"'persona' debe ser un objeto Persona, se recibió {persona!r}"
        )
        raise TypeError(msg_objeto_persona)


def validar_contenido(contenido: object) -> None:
    """Lanza ``TypeError`` si ``contenido`` no es una cadena."""
    # TODO(NicoCam27): validar un objeto Contenido en lugar de una cadena.
    # CONTENT-1
    if not isinstance(contenido, str):
        msg_contenido = f"'contenido' debe ser una cadena, se recibió {contenido!r}"
        raise TypeError(msg_contenido)


def validar_necesidades(necesidades: object) -> None:
    """Lanza ``TypeError`` si ``necesidades`` no tiene un tipo válido.

    Los valores válidos son ``None``, una cadena, y una lista o una tupla de cadenas.
    """
    # TODO(NicoCam27): validar una lista de objetos Contenido en lugar de cadenas.
    # CONTENT-1
    es_grupo_de_cadenas = isinstance(necesidades, (list, tuple)) and all(
        isinstance(necesidad, str) for necesidad in necesidades
    )
    if (
        necesidades is not None
        and not isinstance(necesidades, str)
        and not es_grupo_de_cadenas
    ):
        msg_necesidades = (
            "'necesidades' debe ser una cadena, o una lista o una tupla de cadenas, "
            f"se recibió {necesidades!r}"
        )
        raise TypeError(msg_necesidades)


def validar_lista_brazos(brazos: object) -> None:
    """Lanza un error si ``brazos`` no es una lista o una tupla de brazos distintos.

    Raises:
        TypeError: Si ``brazos`` no es una lista o una tupla, o contiene algo que
            no es un brazo.
        ValueError: Si un brazo aparece más de una vez.
    """
    from simulador_pddl.objetos.brazo import Brazo

    if not isinstance(brazos, (list, tuple)):
        msg_lista = f"'brazos' debe ser una lista o una tupla, se recibió {brazos!r}"
        raise TypeError(msg_lista)

    if not all(isinstance(brazo, Brazo) for brazo in brazos):
        msg_lista_brazos = (
            f"'brazos' solo puede contener objetos Brazo, se recibió {brazos!r}"
        )
        raise TypeError(msg_lista_brazos)

    if len(brazos) != len(set(brazos)):
        msg_lista_brazos_unicos = (
            "'brazos' debe contener objetos Brazo distintos, "
            "un mismo objeto Brazo no puede aparecer más de una vez"
        )
        raise ValueError(msg_lista_brazos_unicos)


def validar_nombre(nombre: object) -> None:
    """Lanza ``TypeError`` si ``nombre`` no es una cadena."""
    if not isinstance(nombre, str):
        msg_nombre = f"'nombre' debe ser una cadena, se recibió {nombre!r}"
        raise TypeError(msg_nombre)


def validar_capacidad(capacidad: object) -> None:
    """Lanza un error si ``capacidad`` no es un entero mayor que 0.

    Raises:
        TypeError: Si ``capacidad`` no es un entero.
        ValueError: Si ``capacidad`` es 0 o negativa.
    """
    # bool es una subclase de int, así que True y False se rechazan expresamente.
    if isinstance(capacidad, bool) or not isinstance(capacidad, int):
        msg_tipo_capacidad = f"'capacidad' debe ser un entero, se recibió {capacidad!r}"
        raise TypeError(msg_tipo_capacidad)

    if capacidad < 1:
        msg_rango_capacidad = (
            f"'capacidad' debe ser mayor que 0, se recibió {capacidad!r}"
        )
        raise ValueError(msg_rango_capacidad)


# Validación de a qué dron pertenece un brazo


def validar_brazo_en_dron(dron: Dron, brazo: Brazo) -> None:
    """Lanza ``ValueError`` si ``brazo`` no es uno de los brazos de ``dron``."""
    if brazo not in dron.brazos:
        msg_propietario_brazo = (
            f"el brazo {brazo.nombre} no forma parte del dron {dron.nombre}"
        )
        raise ValueError(msg_propietario_brazo)


# Objetos con su artículo, para los mensajes de error


# El artículo, el nombre y el plural de cada tipo de objeto.
_GRAMATICA_TIPOS = {
    "Brazo": ("el", "brazo", "brazos"),
    "Caja": ("la", "caja", "cajas"),
    "Dron": ("el", "dron", "drones"),
    "Localizacion": ("la", "localización", "localizaciones"),
    "Persona": ("la", "persona", "personas"),
    "Transportador": ("el", "transportador", "transportadores"),
}


def con_articulo(objeto: ObjetoDominio) -> str:
    """Devuelve el objeto con su artículo y su tipo, p. ej. ``"la caja caja1"``."""
    articulo, tipo, _ = _GRAMATICA_TIPOS[type(objeto).__name__]
    return f"{articulo} {tipo} {objeto.nombre}"


def tipo_en_plural(objeto: ObjetoDominio) -> str:
    """Devuelve el tipo del objeto en plural, p. ej. ``"cajas"``."""
    _, _, plural = _GRAMATICA_TIPOS[type(objeto).__name__]
    return plural


def describir_cantidad(numero: int, tipo: type[ObjetoDominio]) -> str:
    """Devuelve ``numero`` con el nombre del tipo, en singular o en plural.

    P. ej. ``"1 caja"`` o ``"2 cajas"``.
    """
    _, singular, plural = _GRAMATICA_TIPOS[tipo.__name__]
    return f"{numero} {singular if numero == 1 else plural}"


def con_preposicion_a(texto: str) -> str:
    """Devuelve ``texto`` precedido de ``"a"``, p. ej. ``"al dron dron1"``.

    ``texto`` empieza por su artículo (lo que devuelve ``con_articulo()``) o es
    ``"nadie"`` (lo que devuelve ``Caja._describir_propietario()`` para una caja
    sin propietario). ``"a"`` y ``"el"`` se contraen en ``"al"``:
    ``"el dron dron1"`` da ``"al dron dron1"``, y ``"la persona persona1"``,
    ``"a la persona persona1"``.
    """
    if texto.startswith("el "):
        return "al " + texto.removeprefix("el ")
    return "a " + texto


# Necesidades de una persona, para los mensajes de error


def describir_necesidades(necesidades: list[str]) -> str:
    """Devuelve lo que necesita una persona, p. ej. ``"necesita 'comida' y 'agua'"``.

    ``"no necesita nada"`` si la lista está vacía.
    """
    if not necesidades:
        return "no necesita nada"
    contenidos = [repr(necesidad) for necesidad in necesidades]
    if len(contenidos) == 1:
        return f"necesita {contenidos[0]}"
    return f"necesita {', '.join(contenidos[:-1])} y {contenidos[-1]}"
