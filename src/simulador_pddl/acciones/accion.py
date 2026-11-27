from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from simulador_pddl.acciones.utilidades_acciones import (
    validar_duracion_sim,
    validar_inicio_sim,
)
from simulador_pddl.tipos_basicos import validar_cadena

if TYPE_CHECKING:
    from simulador_pddl.objetos import Dron, ObjetoDominio


class Accion(ABC):
    """Una acción del dominio de logística con drones.

    Las acciones son operaciones que realizan los drones, cada una con un inicio
    y una duración concretos. Pueden afectar al propio dron, a sus brazos, a las
    cajas y a los transportadores (por ejemplo: mover, coger, entregar, soltar...).

    Una subclase debe asignar el objeto ``_dron`` y sus demás objetos (como
    atributos privados, cada uno con una propiedad de solo lectura) antes de
    llamar a ``Accion.__init__()``, e implementar ``objetos``,
    ``_iniciar_ejecucion()`` y ``_terminar_ejecucion()``.

    ``dron``, ``inicio_sim``, ``duracion_sim``, ``tiempo_fin``, ``desc``,
    ``iniciada``, ``terminada`` y los objetos de cada subclase son propiedades
    de solo lectura y no pueden modificarse una vez creada la instancia de la acción.
    Esta restricción garantiza la integridad de la acción, ``Mundo`` valida dicho plan
    durante su construcción. Permitir modificaciones posteriores podría invalidar
    las comprobaciones realizadas sin que estas se ejecutasen nuevamente.

    Args:
        inicio_sim: El instante de la simulación en el que empieza la acción.
            Tiene que ser >= 0. En un plan clásico, el índice del paso.
        duracion_sim: La duración de la acción en la simulación. Tiene que
            ser > 0. En un plan clásico, 1.
        desc: Opcional. Una descripción de la acción que se muestra al usuario. Si
            es ``None`` (por defecto), se genera una a partir de los objetos y los
            tiempos de la acción.
    """

    # Todas las acciones del dominio las realiza un dron. Las subclases asignan
    # el objeto dron antes de llamar a Accion.__init__().
    _dron: Dron

    def __init__(
        self,
        inicio_sim: float,
        duracion_sim: float,
        desc: str | None = None,
    ) -> None:
        # Se validan los argumentos aquí para no repetir en cada subclase la
        # validación de estos argumentos, cada subclase valida sus demás argumentos.
        validar_inicio_sim(inicio_sim)
        validar_duracion_sim(duracion_sim)
        if desc is not None:
            validar_cadena(desc, "desc")

        # Descripción automática (si no se proporciona ninguna)
        if desc is None:
            args = ", ".join(
                f"{rol}={objeto_dominio.nombre}"
                for rol, objeto_dominio in self.objetos.items()
            )
            desc = (
                f"{type(self).__name__}({args}, inicio_sim={inicio_sim}, "
                f"duracion_sim={duracion_sim})"
            )

        self._inicio_sim = inicio_sim
        self._duracion_sim = duracion_sim

        self._desc = desc
        self._iniciada = False
        self._terminada = False

    def __repr__(self) -> str:
        """Devuelve la acción como la llamada que la construye, sin ``desc``."""
        objetos = ", ".join(
            repr(objeto_dominio) for objeto_dominio in self.objetos.values()
        )
        return (
            f"{type(self).__name__}({objetos}, inicio_sim={self._inicio_sim!r}, "
            f"duracion_sim={self._duracion_sim!r})"
        )

    # ------------------------------------------------------------------
    # Fases de la acción
    # ------------------------------------------------------------------

    def _reiniciar(self) -> None:
        self._iniciada = False
        self._terminada = False

    @abstractmethod
    def _iniciar_ejecucion(self) -> str | None:
        """Aplica los efectos ``at start`` de la acción.

        Es la primera fase de la acción, que sigue el modelo de las acciones
        durativas de PDDL. Si los efectos se pueden aplicar, se activa
        ``iniciada``.

        Returns:
            ``None`` si se aplicaron los efectos, o el mensaje de error si la
            acción no puede empezar en el estado actual.
        """

    @abstractmethod
    def _terminar_ejecucion(self) -> str | None:
        """Aplica los efectos ``at end`` de la acción.

        Es la segunda fase de la acción, que sigue el modelo de las acciones
        durativas de PDDL. Si los efectos se pueden aplicar, se activa
        ``terminada``.

        Returns:
            ``None`` si se aplicaron los efectos, o el mensaje de error si la
            acción no puede terminar en el estado actual.
        """

    def _progreso(self, tiempo_sim: float) -> float:
        """Devuelve el progreso de la acción en ``tiempo_sim``, de 0.0 a 1.0."""
        return (
            0.0
            if not self._iniciada
            else 1.0
            if self._terminada
            else min(1.0, (tiempo_sim - self._inicio_sim) / self._duracion_sim)
        )

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def dron(self) -> Dron:
        """El dron del dominio que realiza la acción."""
        return self._dron

    @property
    def inicio_sim(self) -> float:
        """El instante de la simulación en el que empieza la acción."""
        return self._inicio_sim

    @property
    def duracion_sim(self) -> float:
        """La duración de la acción en la simulación."""
        return self._duracion_sim

    @property
    def tiempo_fin(self) -> float:
        """El instante en el que termina la acción, ``inicio_sim + duracion_sim``."""
        return self._inicio_sim + self._duracion_sim

    @property
    def desc(self) -> str:
        """La descripción que se muestra al usuario (generada si no se dio ninguna)."""
        return self._desc

    @property
    def iniciada(self) -> bool:
        """Indica si se han aplicado los efectos ``at start``."""
        return self._iniciada

    @property
    def terminada(self) -> bool:
        """Indica si se han aplicado los efectos ``at end``."""
        return self._terminada

    @property
    @abstractmethod
    def objetos(self) -> dict[str, ObjetoDominio]:
        """Los objetos del dominio asociados a la acción, indexados por su rol.

        De solo lectura. Se construye a partir de los atributos de la subclase.
        """

    @property
    def _en_curso(self) -> bool:
        """Indica si la acción ha empezado y todavía no ha terminado."""
        return self._iniciada and not self._terminada
