from __future__ import annotations

from typing import TYPE_CHECKING, override

from simulador_pddl.acciones.accion import Accion
from simulador_pddl.acciones.utilidades_acciones import validar_localizaciones_distintas
from simulador_pddl.objetos.utilidades_objetos import (
    validar_brazo_en_dron,
    validar_objeto_brazo,
    validar_objeto_dron,
    validar_objeto_localizacion,
    validar_objeto_transportador,
)

if TYPE_CHECKING:
    from simulador_pddl.objetos import (
        Brazo,
        Dron,
        Localizacion,
        ObjetoDominio,
        Transportador,
    )


class MoverTransportador(Accion):
    """Acción de mover transportador en el dominio de logística con drones.

    El dron coge un transportador con uno de sus brazos, lo lleva de una
    localización a otra y lo suelta allí.

    Mientras dura, ocupa el dron entero: el dron no puede empezar ninguna otra
    acción hasta que termine.

    Cada objeto que se pasa como argumento se puede leer después como una
    propiedad de solo lectura con el mismo nombre, mientras que el resto de
    propiedades se describen en ``Accion``.

    Args:
        dron: El dron que se mueve con el transportador.
        brazo: El brazo con el que se sujeta el transportador (tiene que
            pertenecer al dron y estar libre).
        transportador: El transportador que se mueve con el dron (ningún dron
            puede estar sujetándolo, ni se puede estar metiendo o sacando ninguna
            caja de él).
        origen: La localización de salida (tiene que ser la localización actual
            del dron y del transportador).
        destino: La localización de llegada (tiene que ser distinta del origen).
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
        origen: Localizacion,
        destino: Localizacion,
        inicio_sim: float,
        duracion_sim: float = 1.0,
        desc: str | None = None,
    ) -> None:
        # Validación de los argumentos específicos de esta acción
        validar_objeto_dron(dron)
        validar_objeto_brazo(brazo)
        validar_objeto_transportador(transportador)
        validar_objeto_localizacion(origen, "origen")
        validar_objeto_localizacion(destino, "destino")
        validar_localizaciones_distintas(origen, destino)
        validar_brazo_en_dron(dron, brazo)

        # Objetos propios de la acción
        self._dron = dron
        self._brazo = brazo
        self._transportador = transportador
        self._origen = origen
        self._destino = destino

        super().__init__(inicio_sim=inicio_sim, duracion_sim=duracion_sim, desc=desc)

    @override
    def _iniciar_ejecucion(self) -> str | None:
        """Comprueba el origen y coge el transportador por completo (``at start``).

        La localización del dron debe corresponderse con el origen proporcionado y
        es una condición ``at start``, así que se comprueba antes de coger: si
        el dron no está en ``origen``, la acción falla aquí y el transportador no
        llega a reclamarse. El inicio y el final de coger transportador se juntan
        en la fase inicial de esta acción. Esto es lo que establece la exclusividad,
        para que ningún otro dron pueda coger el mismo transportador mientras dura
        este movimiento.
        """
        try:
            self._dron._exigir_en(self._origen)
            self._dron._iniciar_coger_transportador(self._brazo, self._transportador)
            self._dron._terminar_coger_transportador(self._brazo, self._transportador)
            self._iniciada = True
        except ValueError as e:
            return str(e)
        else:
            return None

    @override
    def _terminar_ejecucion(self) -> str | None:
        """Mueve el dron y el transportador, y después lo suelta (``at end``).

        El dron y el transportador llegan al destino y después el dron suelta el
        transportador. El inicio y el final de soltar transportador se juntan en
        la fase final de esta acción.
        """
        try:
            self._dron._mover(self._destino)
            self._dron._iniciar_soltar_transportador(self._brazo, self._transportador)
            self._dron._terminar_soltar_transportador(self._brazo, self._transportador)
            self._terminada = True
        except ValueError as e:
            return str(e)
        else:
            return None

    @property
    def brazo(self) -> Brazo:
        """El brazo con el que se sujeta el transportador."""
        return self._brazo

    @property
    def transportador(self) -> Transportador:
        """El transportador que se mueve con el dron."""
        return self._transportador

    @property
    def origen(self) -> Localizacion:
        """La localización de salida."""
        return self._origen

    @property
    def destino(self) -> Localizacion:
        """La localización de llegada."""
        return self._destino

    @property
    @override
    def objetos(self) -> dict[str, ObjetoDominio]:
        return {
            "dron": self._dron,
            "brazo": self._brazo,
            "transportador": self._transportador,
            "origen": self._origen,
            "destino": self._destino,
        }
