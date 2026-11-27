from __future__ import annotations

from typing import TYPE_CHECKING, override

from simulador_pddl.acciones.accion import Accion
from simulador_pddl.objetos.utilidades_objetos import (
    validar_brazo_en_dron,
    validar_objeto_brazo,
    validar_objeto_dron,
    validar_objeto_transportador,
)

if TYPE_CHECKING:
    from simulador_pddl.objetos import Brazo, Dron, ObjetoDominio, Transportador


class CogerTransportador(Accion):
    """Acción de coger transportador en el dominio de logística con drones.

    El dron coge un transportador de su localización con uno de sus brazos, para
    llevarlo.

    Mientras dura, ocupa solo el brazo: el dron puede hacer a la vez otra acción
    con otro brazo, pero no otra con el mismo brazo ni moverse.

    Cada objeto que se pasa como argumento se puede leer después como una
    propiedad de solo lectura con el mismo nombre, mientras que el resto de
    propiedades se describen en ``Accion``.

    Args:
        dron: El dron que coge el transportador.
        brazo: El brazo con el que se coge el transportador (tiene que pertenecer
            al dron y estar libre).
        transportador: El transportador que va a sujetar el dron (ningún dron
            puede estar sujetándolo, ni se puede estar metiendo o sacando ninguna
            caja de él).
        inicio_sim: El instante de la simulación en el que empieza la acción.
            Tiene que ser un número finito, 0 o mayor. En un plan clásico, el
            índice del paso.
        duracion_sim: Opcional. La duración de la acción en la simulación.
            Tiene que ser un número finito mayor que 0. Por defecto es 1, la
            duración de un paso en un plan clásico.
        desc: Opcional. Una descripción de la acción que se muestra al usuario.
            Si es ``None`` (por defecto), se genera automáticamente.
    """

    def __init__(
        self,
        dron: Dron,
        brazo: Brazo,
        transportador: Transportador,
        inicio_sim: float,
        duracion_sim: float = 1.0,
        desc: str | None = None,
    ) -> None:
        # Validación de los argumentos específicos de esta acción
        validar_objeto_dron(dron)
        validar_objeto_brazo(brazo)
        validar_objeto_transportador(transportador)
        validar_brazo_en_dron(dron, brazo)

        # Objetos propios de la acción
        self._dron = dron
        self._brazo = brazo
        self._transportador = transportador

        super().__init__(inicio_sim=inicio_sim, duracion_sim=duracion_sim, desc=desc)

    @override
    def _iniciar_ejecucion(self) -> str | None:
        """Reclama el transportador con el brazo (``at start``).

        El transportador deja de estar libre, así que ningún otro dron puede
        cogerlo mientras tanto.
        """
        try:
            self._dron._iniciar_coger_transportador(self._brazo, self._transportador)
            self._iniciada = True
        except ValueError as e:
            return str(e)
        else:
            return None

    @override
    def _terminar_ejecucion(self) -> str | None:
        """Reserva el brazo para el transportador (``at end``)."""
        try:
            self._dron._terminar_coger_transportador(self._brazo, self._transportador)
            self._terminada = True
        except ValueError as e:
            return str(e)
        else:
            return None

    @property
    def brazo(self) -> Brazo:
        """El brazo con el que se coge el transportador."""
        return self._brazo

    @property
    def transportador(self) -> Transportador:
        """El transportador que va a sujetar el dron."""
        return self._transportador

    @property
    @override
    def objetos(self) -> dict[str, ObjetoDominio]:
        return {
            "dron": self._dron,
            "brazo": self._brazo,
            "transportador": self._transportador,
        }
