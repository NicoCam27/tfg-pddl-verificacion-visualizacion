from __future__ import annotations

from typing import TYPE_CHECKING, override

from simulador_pddl.acciones.accion import Accion
from simulador_pddl.objetos.utilidades_objetos import (
    validar_brazo_en_dron,
    validar_objeto_brazo,
    validar_objeto_caja,
    validar_objeto_dron,
    validar_objeto_transportador,
)

if TYPE_CHECKING:
    from simulador_pddl.objetos import Brazo, Caja, Dron, ObjetoDominio, Transportador


class PonerCajaEnTransportador(Accion):
    """Acción de poner caja en transportador en el dominio de logística con drones.

    El dron mete la caja que sujeta con uno de sus brazos en un transportador que
    está en su localización. La caja está dentro del transportador cuando
    termina la acción. Desde el inicio, se reserva un hueco en el transportador y
    no se puede coger el transportador.

    Mientras dura, ocupa solo el brazo: el dron puede hacer a la vez otra acción
    con otro brazo, pero no otra con el mismo brazo ni moverse.

    Cada objeto que se pasa como argumento se puede leer después como una
    propiedad de solo lectura con el mismo nombre, mientras que el resto de
    propiedades se describen en ``Accion``.

    Args:
        dron: El dron que mete la caja en el transportador.
        brazo: El brazo con el que se mete la caja en el transportador (tiene que
            pertenecer al dron).
        caja: La caja que se mete en el transportador (la tiene que sujetar el
            brazo).
        transportador: El transportador en el que se mete la caja (ningún dron
            puede estar sujetándolo en este momento).
        inicio_sim: El instante de la simulación en el que empieza la acción.
            Tiene que ser >= 0. En un plan clásico, el índice del paso.
        duracion_sim: Opcional. La duración de la acción en la simulación.
            Tiene que ser > 0. Por defecto es 1, la duración de un paso en un
            plan clásico.
        desc: Opcional. Una descripción de la acción que se muestra al usuario.
            Si es ``None`` (por defecto), se genera automáticamente.
    """

    def __init__(
        self,
        dron: Dron,
        brazo: Brazo,
        caja: Caja,
        transportador: Transportador,
        inicio_sim: float,
        duracion_sim: float = 1.0,
        desc: str | None = None,
    ) -> None:
        # Validación de los argumentos específicos de esta acción
        validar_objeto_dron(dron)
        validar_objeto_brazo(brazo)
        validar_objeto_caja(caja)
        validar_objeto_transportador(transportador)
        validar_brazo_en_dron(dron, brazo)

        # Objetos propios de la acción
        self._dron = dron
        self._brazo = brazo
        self._caja = caja
        self._transportador = transportador

        super().__init__(inicio_sim=inicio_sim, duracion_sim=duracion_sim, desc=desc)

    @override
    def _iniciar_ejecucion(self) -> str | None:
        """Reserva un hueco del transportador para la caja (``at start``).

        La caja sigue en el brazo hasta el final de la acción.
        """
        try:
            self._dron._iniciar_poner_caja_en_transportador(
                self._brazo, self._caja, self._transportador
            )
            self._iniciada = True
        except ValueError as e:
            return str(e)
        else:
            return None

    @override
    def _terminar_ejecucion(self) -> str | None:
        """Saca la caja del brazo y la mete en el transportador (``at end``)."""
        try:
            self._dron._terminar_poner_caja_en_transportador(
                self._brazo, self._caja, self._transportador
            )
            self._terminada = True
        except ValueError as e:
            return str(e)
        else:
            return None

    @property
    def brazo(self) -> Brazo:
        """El brazo con el que se mete la caja en el transportador."""
        return self._brazo

    @property
    def caja(self) -> Caja:
        """La caja que se mete en el transportador."""
        return self._caja

    @property
    def transportador(self) -> Transportador:
        """El transportador en el que se mete la caja."""
        return self._transportador

    @property
    @override
    def objetos(self) -> dict[str, ObjetoDominio]:
        return {
            "dron": self._dron,
            "brazo": self._brazo,
            "caja": self._caja,
            "transportador": self._transportador,
        }
