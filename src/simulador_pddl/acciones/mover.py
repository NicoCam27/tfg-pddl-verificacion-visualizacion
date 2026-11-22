from __future__ import annotations

from typing import TYPE_CHECKING, override

from simulador_pddl.acciones.accion import Accion
from simulador_pddl.acciones.utilidades_acciones import validar_localizaciones_distintas
from simulador_pddl.objetos.utilidades_objetos import (
    validar_objeto_dron,
    validar_objeto_localizacion,
)

if TYPE_CHECKING:
    from simulador_pddl.objetos import Dron, Localizacion, ObjetoDominio


class Mover(Accion):
    """Acción de mover en el dominio de logística con drones.

    El dron se desplaza de una localización a otra, llevando consigo lo que
    sujeten sus brazos.

    Cada objeto que se pasa como argumento se puede leer después como una
    propiedad de solo lectura con el mismo nombre, mientras que el resto de
    propiedades se describen en ``Accion``.

    Args:
        dron: El dron que se mueve.
        origen: La localización de salida (tiene que ser la localización actual
            del dron).
        destino: La localización de llegada (tiene que ser distinta del origen).
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
        origen: Localizacion,
        destino: Localizacion,
        inicio_sim: float,
        duracion_sim: float = 1.0,
        desc: str | None = None,
    ) -> None:
        # Validación de los argumentos específicos de esta acción
        validar_objeto_dron(dron)
        validar_objeto_localizacion(origen, "origen")
        validar_objeto_localizacion(destino, "destino")
        validar_localizaciones_distintas(origen, destino)

        # Objetos propios de la acción
        self._dron = dron
        self._origen = origen
        self._destino = destino

        super().__init__(inicio_sim=inicio_sim, duracion_sim=duracion_sim, desc=desc)

    @override
    def _iniciar_ejecucion(self) -> str | None:
        """Comprueba el origen del dron: ``Mover`` no tiene efectos ``at start``.

        La localización del dron debe corresponderse con el origen proporcionado y
        es una condición ``at start``, así que un origen incorrecto falla aquí
        en ``inicio_sim``. El dron entero está protegido frente a solapamientos en
        ``Simulacion._validar_sin_solapamientos_de_dron_o_brazo()``, así que todo
        el efecto se aplica en ``_terminar_ejecucion()``.
        """
        try:
            self._dron._exigir_en(self._origen)
            self._iniciada = True
        except (TypeError, ValueError) as e:
            return str(e)
        else:
            return None

    @override
    def _terminar_ejecucion(self) -> str | None:
        try:
            # ``at end``: el dron y todo lo que lleva consigo llegan al destino.
            self._dron._mover(self._destino)
            self._terminada = True
        except (TypeError, ValueError) as e:
            return str(e)
        else:
            return None

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
            "origen": self._origen,
            "destino": self._destino,
        }
