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


class SacarCajaDeTransportador(Accion):
    """Acción de sacar caja de transportador en el dominio de logística con drones.

    El dron saca una caja de un transportador que está en su localización con
    uno de sus brazos.

    Mientras dura, ocupa solo el brazo: el dron puede hacer a la vez otra acción
    con otro brazo, pero no otra con el mismo brazo ni moverse.

    Cada objeto que se pasa como argumento se puede leer después como una
    propiedad de solo lectura con el mismo nombre, mientras que el resto de
    propiedades se describen en ``Accion``.

    Args:
        dron: El dron que saca la caja del transportador.
        brazo: El brazo con el que se saca la caja del transportador (tiene que
            pertenecer al dron y estar libre).
        caja: La caja que se saca del transportador (tiene que estar dentro del
            transportador).
        transportador: El transportador que tiene la caja dentro (ningún dron
            puede estar sujetándolo en este momento).
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
        """Saca la caja del transportador y la reclama para el dron (``at start``).

        El transportador no se puede coger hasta el final de la acción.
        """
        try:
            self._dron._iniciar_sacar_caja_de_transportador(
                self._brazo, self._caja, self._transportador
            )
            self._iniciada = True
        except ValueError as e:
            return str(e)
        else:
            return None

    @override
    def _terminar_ejecucion(self) -> str | None:
        """Hace que el brazo sujete formalmente la caja (``at end``).

        Desde este momento, el transportador se puede volver a coger.
        """
        try:
            self._dron._terminar_sacar_caja_de_transportador(
                self._brazo, self._caja, self._transportador
            )
            self._terminada = True
        except ValueError as e:
            return str(e)
        else:
            return None

    @property
    def brazo(self) -> Brazo:
        """El brazo con el que se saca la caja del transportador."""
        return self._brazo

    @property
    def caja(self) -> Caja:
        """La caja que se saca del transportador."""
        return self._caja

    @property
    def transportador(self) -> Transportador:
        """El transportador que tiene la caja dentro."""
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
