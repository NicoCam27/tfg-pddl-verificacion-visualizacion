from __future__ import annotations

from typing import TYPE_CHECKING, override

from simulador_pddl.acciones.accion import Accion
from simulador_pddl.objetos.utilidades_objetos import (
    validar_brazo_en_dron,
    validar_objeto_brazo,
    validar_objeto_caja,
    validar_objeto_dron,
    validar_objeto_persona,
)

if TYPE_CHECKING:
    from simulador_pddl.objetos import Brazo, Caja, Dron, ObjetoDominio, Persona


class EntregarCaja(Accion):
    """Acción de entregar caja en el dominio de logística con drones.

    El dron entrega la caja que sujeta con uno de sus brazos a una persona que
    está en su localización. La persona tiene la caja cuando termina la acción.

    Mientras dura, ocupa solo el brazo: el dron puede hacer a la vez otra acción
    con otro brazo, pero no otra con el mismo brazo ni moverse.

    Cada objeto que se pasa como argumento se puede leer después como una
    propiedad de solo lectura con el mismo nombre, mientras que el resto de
    propiedades se describen en ``Accion``.

    Args:
        dron: El dron que entrega la caja.
        brazo: El brazo que sujeta ahora la caja (tiene que pertenecer al dron).
        caja: La caja que se entrega (la tiene que sujetar el brazo).
        persona: La persona que recibe la caja (tiene que necesitar su contenido).
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
        persona: Persona,
        inicio_sim: float,
        duracion_sim: float = 1.0,
        desc: str | None = None,
    ) -> None:
        # Validación de los argumentos específicos de esta acción
        validar_objeto_dron(dron)
        validar_objeto_brazo(brazo)
        validar_objeto_caja(caja)
        validar_objeto_persona(persona)
        validar_brazo_en_dron(dron, brazo)

        # Objetos propios de la acción
        self._dron = dron
        self._brazo = brazo
        self._caja = caja
        self._persona = persona

        super().__init__(inicio_sim=inicio_sim, duracion_sim=duracion_sim, desc=desc)

    @override
    def _iniciar_ejecucion(self) -> str | None:
        """Comprueba que la caja se puede entregar (``at start``).

        La caja sigue en el brazo hasta el final de la acción.
        """
        try:
            self._dron._iniciar_entregar_caja(self._brazo, self._caja, self._persona)
            self._iniciada = True
        except ValueError as e:
            return str(e)
        else:
            return None

    @override
    def _terminar_ejecucion(self) -> str | None:
        """Entrega la caja a la persona y deja libre el brazo (``at end``)."""
        try:
            self._dron._terminar_entregar_caja(self._brazo, self._caja, self._persona)
            self._terminada = True
        except ValueError as e:
            return str(e)
        else:
            return None

    @property
    def brazo(self) -> Brazo:
        """El brazo que sujeta ahora la caja."""
        return self._brazo

    @property
    def caja(self) -> Caja:
        """La caja que se entrega."""
        return self._caja

    @property
    def persona(self) -> Persona:
        """La persona que recibe la caja."""
        return self._persona

    @property
    @override
    def objetos(self) -> dict[str, ObjetoDominio]:
        return {
            "dron": self._dron,
            "brazo": self._brazo,
            "caja": self._caja,
            "persona": self._persona,
        }
