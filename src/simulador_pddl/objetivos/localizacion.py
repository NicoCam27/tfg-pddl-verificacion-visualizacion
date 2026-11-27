from __future__ import annotations

from typing import TYPE_CHECKING, override

from simulador_pddl.objetivos.objetivo import Objetivo
from simulador_pddl.objetos import Dron, Transportador
from simulador_pddl.objetos.utilidades_objetos import (
    validar_objeto_dron,
    validar_objeto_localizacion,
    validar_objeto_transportador,
)

if TYPE_CHECKING:
    from simulador_pddl.objetivos.objetivo import ObjetoReferenciado
    from simulador_pddl.objetos import Localizacion


class _EnLocalizacion[T: (Dron, Transportador)](Objetivo):
    """Un objetivo que se cumple cuando un objeto está en una localización.

    Una subclase tiene que definir ``_ETIQUETA``, el tipo de su objeto con el
    artículo, que encabeza la descripción del objetivo y la explicación de su
    fallo (p. ej. ``"el dron dron1 está en la localización deposito"``). También
    tiene que validar su objeto antes de llamar a ``_EnLocalizacion.__init__()``,
    que solo valida la localización: solo la subclase sabe qué tipo de objeto
    acepta.

    Args:
        objeto_dominio: El dron o el transportador cuya localización se comprueba.
        localizacion: La localización donde tiene que estar el objeto al final
            del plan.
    """

    # Etiqueta genérica del tipo de objeto, que usan _describir() y _explicar_fallo().
    _ETIQUETA = "el objeto"

    def __init__(self, objeto_dominio: T, localizacion: Localizacion) -> None:
        validar_objeto_localizacion(localizacion)

        self._objeto_dominio: T = objeto_dominio
        self._localizacion = localizacion

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}({self._objeto_dominio!r}, {self._localizacion!r})"
        )

    @override
    def _se_cumple(self) -> bool:
        return self._objeto_dominio.localizacion == self._localizacion

    @override
    def _describir(self) -> str:
        return (
            f"{self._ETIQUETA} {self._objeto_dominio.nombre} está en la localización "
            f"{self._localizacion.nombre}"
        )

    @override
    def _explicar_fallo(self) -> str:
        return (
            f"{self._ETIQUETA} {self._objeto_dominio.nombre} está en la localización "
            f"{self._objeto_dominio.localizacion.nombre}, no en la localización "
            f"{self._localizacion.nombre}"
        )

    @override
    def _objetos_referenciados(self) -> list[ObjetoReferenciado]:
        return [self._objeto_dominio, self._localizacion]

    @property
    def localizacion(self) -> Localizacion:
        """La localización donde tiene que estar el objeto al final del plan."""
        return self._localizacion


class DronEnLocalizacion(_EnLocalizacion[Dron]):
    """Objetivo dron en localización del dominio de logística con drones.

    Se cumple cuando el dron está en ``localizacion``. Un dron que vuela sigue en
    su origen hasta que termina el movimiento, porque ``Mover`` y
    ``MoverTransportador`` cambian su localización al final (``at end``).

    Args:
        dron: El dron cuya localización se comprueba.
        localizacion: La localización donde tiene que estar el dron al final del
            plan.
    """

    # Etiqueta del tipo dron, que usan _describir() y _explicar_fallo().
    _ETIQUETA = "el dron"

    def __init__(self, dron: Dron, localizacion: Localizacion) -> None:
        validar_objeto_dron(dron)
        super().__init__(dron, localizacion)

    @property
    def dron(self) -> Dron:
        """El dron cuya localización se comprueba."""
        return self._objeto_dominio


class TransportadorEnLocalizacion(_EnLocalizacion[Transportador]):
    """Objetivo transportador en localización del dominio de logística con drones.

    Se cumple cuando el transportador está en ``localizacion``. Un transportador
    que un dron lleva consigo sigue en su origen hasta que termina el
    movimiento, porque ``Mover`` y ``MoverTransportador`` cambian su
    localización al final (``at end``).

    Args:
        transportador: El transportador cuya localización se comprueba.
        localizacion: La localización donde tiene que estar el transportador al
            final del plan.
    """

    # Etiqueta del tipo transportador, que usan _describir() y _explicar_fallo().
    _ETIQUETA = "el transportador"

    def __init__(
        self, transportador: Transportador, localizacion: Localizacion
    ) -> None:
        validar_objeto_transportador(transportador)
        super().__init__(transportador, localizacion)

    @property
    def transportador(self) -> Transportador:
        """El transportador cuya localización se comprueba."""
        return self._objeto_dominio
