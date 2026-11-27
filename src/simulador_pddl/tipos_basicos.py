"""Validadores de los tipos básicos de Python, comunes a todo el paquete.

Comprueban solo el tipo: que un valor sea un int, un float o una cadena. No saben
nada del dominio, así que no importan nada del paquete y los pueden usar los
objetos, las acciones y ``Mundo``. Cada uno recibe el nombre del argumento para
escribir el mensaje, lanza ``TypeError`` si el tipo no es el esperado y, si es
correcto, devuelve el mismo valor, para que el comprobador de tipos sepa después
de qué tipo es.
El rango de cada argumento (``>= 0``, ``> 0``, finito...) lo comprueba quien
llama, porque cambia de un argumento a otro.
"""

from __future__ import annotations

from typing import Literal, overload


def validar_numero(valor: object, nombre: str) -> float:
    """Devuelve ``valor`` si es un int o un float.

    Args:
        valor: El valor que se comprueba.
        nombre: El nombre del argumento, para el mensaje de error.

    Raises:
        TypeError: Si ``valor`` no es un int o un float.
    """
    # bool es una subclase de int, así que True y False se rechazan expresamente.
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        msg_tipo = f"'{nombre}' debe ser un int o un float, se recibió {valor!r}"
        raise TypeError(msg_tipo)
    return valor


# Las dos firmas le dicen al comprobador de tipos que sin admite_none el
# resultado nunca es None, así que quien llama puede usarlo sin comprobar antes
# si es None.
@overload
def validar_entero(valor: object, nombre: str) -> int: ...
@overload
def validar_entero(
    valor: object, nombre: str, *, admite_none: Literal[True]
) -> int | None: ...
def validar_entero(
    valor: object, nombre: str, *, admite_none: bool = False
) -> int | None:
    """Devuelve ``valor`` si es un entero, o si es ``None`` y se admite.

    Args:
        valor: El valor que se comprueba.
        nombre: El nombre del argumento, para el mensaje de error.
        admite_none: Si ``None`` también es válido. Opcional: ``False`` por
            defecto.

    Raises:
        TypeError: Si ``valor`` no es un entero (ni ``None``, si se admite).
    """
    if admite_none and valor is None:
        return None
    # bool es una subclase de int, así que True y False se rechazan expresamente.
    if isinstance(valor, bool) or not isinstance(valor, int):
        o_none = " o None" if admite_none else ""
        msg_tipo = f"'{nombre}' debe ser un entero{o_none}, se recibió {valor!r}"
        raise TypeError(msg_tipo)
    return valor


def validar_cadena(valor: object, nombre: str) -> str:
    """Devuelve ``valor`` si es una cadena.

    Args:
        valor: El valor que se comprueba.
        nombre: El nombre del argumento, para el mensaje de error.

    Raises:
        TypeError: Si ``valor`` no es una cadena.
    """
    if not isinstance(valor, str):
        msg_tipo = f"'{nombre}' debe ser una cadena, se recibió {valor!r}"
        raise TypeError(msg_tipo)
    return valor
