from __future__ import annotations

from typing import TYPE_CHECKING

from simulador_pddl.objetos.utilidades_objetos import validar_nombre

if TYPE_CHECKING:
    # Solo para las anotaciones de tipo: importarlos al ejecutar sería circular.
    from simulador_pddl.objetos.caja import Caja
    from simulador_pddl.objetos.transportador import Transportador


class Brazo:
    """Brazo representa un brazo en el dominio de logística con drones.

    Un brazo se crea con su nombre y se le da a un ``Dron`` al construirlo. Puede
    estar libre, sujetar una caja (``contenido``) o estar reservado por un
    transportador que lleva (``reservado_por``), pero solo una de estas cosas a la
    vez. Cada brazo tiene que pertenecer a un solo dron.

    Args:
        nombre: El nombre del brazo en el dominio.
    """

    def __init__(self, nombre: str) -> None:
        validar_nombre(nombre)

        self._nombre = nombre
        self._contenido: Caja | None = None
        self._reservado_por: Transportador | None = None

    def __repr__(self) -> str:
        return f"Brazo({self._nombre!r})"

    def __str__(self) -> str:
        contenido = self._contenido.nombre if self._contenido is not None else None
        reservado_por = (
            self._reservado_por.nombre if self._reservado_por is not None else None
        )
        return (
            f"Brazo(nombre={self._nombre}, contenido={contenido}, "
            f"reservado_por={reservado_por})"
        )

    def _poner_reservado_por(self, transportador: Transportador) -> None:
        self._reservado_por = transportador

    def _quitar_reservado_por(self) -> None:
        self._reservado_por = None

    def _poner_contenido(self, caja: Caja) -> None:
        self._contenido = caja

    def _quitar_contenido(self) -> None:
        self._contenido = None

    def _exigir_sin_caja(self) -> None:
        """Lanza ``ValueError`` si el brazo sujeta una caja."""
        if self._contenido is not None:
            msg_brazo_con_caja = (
                f"el brazo {self._nombre} ya sujeta la caja {self._contenido.nombre}"
            )
            raise ValueError(msg_brazo_con_caja)

    def _exigir_sin_transportador(self) -> None:
        """Lanza ``ValueError`` si el brazo está reservado para un transportador."""
        if self._reservado_por is not None:
            msg_brazo_reservado = (
                f"el brazo {self._nombre} ya está reservado para llevar "
                f"el transportador {self._reservado_por.nombre}"
            )
            raise ValueError(msg_brazo_reservado)

    def _exigir_libre(self) -> None:
        """Lanza ``ValueError`` si el brazo sujeta una caja o lleva un transportador."""
        self._exigir_sin_caja()
        self._exigir_sin_transportador()

    def _exigir_sujetando(self, caja: Caja) -> None:
        """Lanza ``ValueError`` si el brazo no sujeta ``caja``."""
        if self._contenido is caja:
            return

        if self._reservado_por is not None:
            estado_brazo = (
                "está reservado para llevar el transportador "
                f"{self._reservado_por.nombre}"
            )
        elif self._contenido is not None:
            estado_brazo = f"sujeta la caja {self._contenido.nombre}"
        else:
            estado_brazo = "está vacío"
        msg_contenido_brazo = (
            f"el brazo {self._nombre} no sujeta la caja {caja.nombre}, {estado_brazo}"
        )
        raise ValueError(msg_contenido_brazo)

    @property
    def nombre(self) -> str:
        """El nombre del brazo."""
        return self._nombre

    @property
    def contenido(self) -> Caja | None:
        """La caja que sujeta este brazo, o ``None`` si no sujeta ninguna."""
        return self._contenido

    @property
    def reservado_por(self) -> Transportador | None:
        """El transportador que lleva este brazo, o ``None`` si no lleva ninguno."""
        return self._reservado_por
