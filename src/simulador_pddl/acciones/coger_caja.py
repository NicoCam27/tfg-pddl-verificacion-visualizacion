from __future__ import annotations

from typing import TYPE_CHECKING, override

from simulador_pddl.acciones.accion import Accion
from simulador_pddl.objetos.utilidades_objetos import (
    validar_brazo_en_dron,
    validar_objeto_brazo,
    validar_objeto_caja,
    validar_objeto_dron,
)

if TYPE_CHECKING:
    from simulador_pddl.objetos import Brazo, Caja, Dron, ObjetoDominio


class CogerCaja(Accion):
    """Acción de coger caja en el dominio de logística con drones.

    El dron coge una caja de su localización con uno de sus brazos.

    Cada objeto que se pasa como argumento se puede leer después como una
    propiedad de solo lectura con el mismo nombre, mientras que el resto de
    propiedades se describen en ``Accion``.

    Args:
        dron: El dron que coge la caja.
        brazo: El brazo con el que se coge la caja (tiene que pertenecer al dron y
            estar libre).
        caja: La caja que se coge (tiene que estar disponible).
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
        inicio_sim: float,
        duracion_sim: float = 1.0,
        desc: str | None = None,
    ) -> None:
        # Validación de los argumentos específicos de esta acción
        validar_objeto_dron(dron)
        validar_objeto_brazo(brazo)
        validar_objeto_caja(caja)
        validar_brazo_en_dron(dron, brazo)

        # Objetos propios de la acción
        self._dron = dron
        self._brazo = brazo
        self._caja = caja

        super().__init__(inicio_sim=inicio_sim, duracion_sim=duracion_sim, desc=desc)

    @override
    def _iniciar_ejecucion(self) -> str | None:
        try:
            # ``at start``: la caja deja de estar disponible, así que ninguna otra
            # acción solapada puede cogerla.
            self._dron._iniciar_coger_caja(self._brazo, self._caja)
            self._iniciada = True
        except ValueError as e:
            return str(e)
        else:
            return None

    @override
    def _terminar_ejecucion(self) -> str | None:
        try:
            # ``at end``: el brazo pasa formalmente a sujetar la caja.
            self._dron._terminar_coger_caja(self._brazo, self._caja)
            self._terminada = True
        except ValueError as e:
            return str(e)
        else:
            return None

    @property
    def brazo(self) -> Brazo:
        """El brazo con el que se coge la caja."""
        return self._brazo

    @property
    def caja(self) -> Caja:
        """La caja que se coge."""
        return self._caja

    @property
    @override
    def objetos(self) -> dict[str, ObjetoDominio]:
        return {"dron": self._dron, "brazo": self._brazo, "caja": self._caja}
