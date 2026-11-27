"""Validadores, al construir, de los argumentos de las acciones.

Lanzan ``TypeError`` para un valor de tipo incorrecto y ``ValueError`` para un
valor del tipo correcto que no es válido: fuera de rango (por ejemplo, un
``inicio_sim`` negativo) o igual a otro argumento del que debe ser distinto (por
ejemplo, un ``origen`` igual al ``destino``). Los errores de ejecución se tratan
de otra forma: las acciones los devuelven como un mensaje (ver
``Accion._iniciar_ejecucion()`` y ``Accion._terminar_ejecucion()``).
"""

from __future__ import annotations

from math import isfinite
from typing import TYPE_CHECKING

from simulador_pddl.tipos_basicos import validar_numero

if TYPE_CHECKING:
    from simulador_pddl.objetos import Localizacion


def validar_inicio_sim(inicio_sim: object) -> None:
    """Lanza un error si ``inicio_sim`` no es un número finito, 0 o mayor.

    Raises:
        TypeError: Si ``inicio_sim`` no es un int o un float.
        ValueError: Si ``inicio_sim`` es negativo, NaN o infinito.
    """
    numero = validar_numero(inicio_sim, "inicio_sim")
    if not numero >= 0:
        msg_rango = f"'inicio_sim' debe ser 0 o mayor, se recibió {inicio_sim!r}"
        raise ValueError(msg_rango)
    # inf haría que la simulación no terminara nunca.
    if not isfinite(numero):
        msg_infinito = f"'inicio_sim' debe ser finito, se recibió {inicio_sim!r}"
        raise ValueError(msg_infinito)


def validar_duracion_sim(duracion_sim: object) -> None:
    """Lanza un error si ``duracion_sim`` no es un número finito mayor que 0.

    Raises:
        TypeError: Si ``duracion_sim`` no es un int o un float.
        ValueError: Si ``duracion_sim`` es 0, negativo, NaN o infinito.
    """
    numero = validar_numero(duracion_sim, "duracion_sim")
    if not numero > 0:
        msg_rango = f"'duracion_sim' debe ser mayor que 0, se recibió {duracion_sim!r}"
        raise ValueError(msg_rango)
    # inf haría que la simulación no terminara nunca.
    if not isfinite(numero):
        msg_infinito = f"'duracion_sim' debe ser finito, se recibió {duracion_sim!r}"
        raise ValueError(msg_infinito)


def validar_localizaciones_distintas(
    origen: Localizacion, destino: Localizacion
) -> None:
    """Lanza ``ValueError`` si ``origen`` y ``destino`` son la misma localización."""
    if origen == destino:
        msg_misma_localizacion = (
            "'origen' y 'destino' deben ser localizaciones distintas, se recibió "
            f"{origen} para los dos"
        )
        raise ValueError(msg_misma_localizacion)
