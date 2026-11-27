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


class SoltarTransportador(Accion):
    """Acción de soltar transportador en el dominio de logística con drones.

    El dron suelta el transportador que lleva, que se queda en la localización
    del dron. El transportador vuelve a estar libre cuando termina la acción.

    Cada objeto que se pasa como argumento se puede leer después como una
    propiedad de solo lectura con el mismo nombre, mientras que el resto de
    propiedades se describen en ``Accion``.

    Args:
        dron: El dron que sujeta ahora el transportador.
        brazo: El brazo que sujeta ahora el transportador (tiene que pertenecer al
            dron).
        transportador: El transportador que suelta el dron (lo tiene que sujetar
            el dron con el brazo).
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
        try:
            # ``at start``: se comprueba que se puede soltar. El dron aún sujeta el
            # transportador.
            self._dron._iniciar_soltar_transportador(self._brazo, self._transportador)
            self._iniciada = True
        except ValueError as e:
            return str(e)
        else:
            return None

    @override
    def _terminar_ejecucion(self) -> str | None:
        try:
            # ``at end``: el dron suelta el transportador, que vuelve a estar libre.
            self._dron._terminar_soltar_transportador(self._brazo, self._transportador)
            self._terminada = True
        except ValueError as e:
            return str(e)
        else:
            return None

    @property
    def brazo(self) -> Brazo:
        """El brazo que sujeta ahora el transportador."""
        return self._brazo

    @property
    def transportador(self) -> Transportador:
        """El transportador que suelta el dron."""
        return self._transportador

    @property
    @override
    def objetos(self) -> dict[str, ObjetoDominio]:
        return {
            "dron": self._dron,
            "brazo": self._brazo,
            "transportador": self._transportador,
        }
