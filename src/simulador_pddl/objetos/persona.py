from __future__ import annotations

from typing import TYPE_CHECKING

from simulador_pddl.objetos.contenido import Contenido
from simulador_pddl.objetos.utilidades_objetos import (
    validar_necesidades,
    validar_nombre,
    validar_objeto_localizacion,
)

if TYPE_CHECKING:
    from simulador_pddl.objetos.caja import Caja
    from simulador_pddl.objetos.localizacion import Localizacion


class Persona:
    """Persona representa una persona en el dominio de logística con drones.

    Una persona no se mueve de su localización y tiene necesidades, que se
    cubren entregándole cajas. Las cajas que se le entregan quedan en ``posee``.

    Args:
        nombre: El nombre de la persona en el dominio.
        localizacion: La localización donde está la persona.
        necesidades: El contenido que necesita la persona, o una lista o una tupla
            de contenidos. Opcional: por defecto la persona no necesita nada. En
            todos los casos la persona guarda sus necesidades como una lista.
    """

    def __init__(
        self,
        nombre: str,
        localizacion: Localizacion,
        necesidades: Contenido | list[Contenido] | tuple[Contenido, ...] | None = None,
    ) -> None:
        validar_nombre(nombre)
        validar_objeto_localizacion(localizacion)
        validar_necesidades(necesidades)

        self._nombre = nombre
        self._localizacion = localizacion

        self._posee: list[Caja] = []

        # Las necesidades se guardan en una lista propia de la persona, para que
        # los cambios posteriores en la lista de quien llama no le afecten.
        if necesidades is None:
            self._necesidades: list[Contenido] = []
        elif isinstance(necesidades, Contenido):
            self._necesidades = [necesidades]
        else:
            self._necesidades = list(necesidades)

    def __repr__(self) -> str:
        return f"Persona({self._nombre!r})"

    def __str__(self) -> str:
        necesidades = [necesidad.nombre for necesidad in self._necesidades]
        posee = [caja.nombre for caja in self._posee]
        return (
            f"Persona(nombre={self._nombre}, localizacion={self._localizacion}, "
            f"necesidades={necesidades}, posee={posee})"
        )

    # ------------------------------------------------------------------
    # Cajas que posee
    # ------------------------------------------------------------------

    def _anadir_caja_poseida(self, caja: Caja) -> None:
        """Entrega la caja a la persona y quita su contenido de las necesidades.

        Aquí no se comprueba nada: quien llama se asegura de que la persona
        necesita el contenido de la caja y de que aún no la posee.
        """
        self._posee.append(caja)
        caja._entregar_a(self)
        self._necesidades.remove(caja.contenido)

    def _exigir_no_poseida(self, caja: Caja) -> None:
        """Lanza ``ValueError`` si la persona ya posee ``caja``."""
        if caja in self._posee:
            msg_caja_poseida = (
                f"la caja {caja.nombre} no se puede entregar a la persona "
                f"{self._nombre}, ya la posee"
            )
            raise ValueError(msg_caja_poseida)

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def nombre(self) -> str:
        """El nombre de la persona."""
        return self._nombre

    @property
    def localizacion(self) -> Localizacion:
        """La localización donde está la persona."""
        return self._localizacion

    @property
    def necesidades(self) -> list[Contenido]:
        """Lo que la persona aún necesita, como copia de la lista interna."""
        return list(self._necesidades)

    @property
    def posee(self) -> list[Caja]:
        """Las cajas entregadas a la persona, como copia de la lista interna."""
        return list(self._posee)
