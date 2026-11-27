from __future__ import annotations

from typing import TYPE_CHECKING

from simulador_pddl.tipos_basicos import validar_cadena

if TYPE_CHECKING:
    # Solo para las anotaciones de tipo: importarlos al ejecutar sería circular.
    from simulador_pddl.objetos.caja import Caja
    from simulador_pddl.objetos.transportador import Transportador


class Brazo:
    """Brazo representa un brazo en el dominio de logística con drones.

    Un brazo se crea con su nombre y se le da a un ``Dron`` al construirlo. Puede
    estar libre, sujetar una caja (``caja``) o estar reservado por un
    transportador que lleva (``transportador``), pero solo una de estas cosas a la
    vez. Cada brazo tiene que pertenecer a un solo dron.

    Args:
        nombre: El nombre del brazo en el dominio.
    """

    def __init__(self, nombre: str) -> None:
        validar_cadena(nombre, "nombre")

        self._nombre = nombre
        self._caja: Caja | None = None
        self._transportador: Transportador | None = None

    def __repr__(self) -> str:
        return f"Brazo({self._nombre!r})"

    def __str__(self) -> str:
        caja = self._caja.nombre if self._caja is not None else None
        transportador = (
            self._transportador.nombre if self._transportador is not None else None
        )
        return (
            f"Brazo(nombre={self._nombre}, caja={caja}, transportador={transportador})"
        )

    def _poner_transportador(self, transportador: Transportador) -> None:
        self._transportador = transportador

    def _quitar_transportador(self) -> None:
        self._transportador = None

    def _poner_caja(self, caja: Caja) -> None:
        self._caja = caja

    def _quitar_caja(self) -> None:
        self._caja = None

    def _exigir_sin_caja(self) -> None:
        """Lanza ``ValueError`` si el brazo sujeta una caja."""
        if self._caja is not None:
            msg_brazo_con_caja = (
                f"el brazo {self._nombre} ya sujeta la caja {self._caja.nombre}"
            )
            raise ValueError(msg_brazo_con_caja)

    def _exigir_sin_transportador(self) -> None:
        """Lanza ``ValueError`` si el brazo está reservado para un transportador."""
        if self._transportador is not None:
            msg_brazo_reservado = (
                f"el brazo {self._nombre} ya está reservado para llevar "
                f"el transportador {self._transportador.nombre}"
            )
            raise ValueError(msg_brazo_reservado)

    def _exigir_libre(self) -> None:
        """Lanza ``ValueError`` si el brazo sujeta una caja o lleva un transportador."""
        self._exigir_sin_caja()
        self._exigir_sin_transportador()

    def _exigir_sujetando(self, caja: Caja) -> None:
        """Lanza ``ValueError`` si el brazo no sujeta ``caja``."""
        if self._caja is caja:
            return

        if self._transportador is not None:
            estado_brazo = (
                "está reservado para llevar el transportador "
                f"{self._transportador.nombre}"
            )
        elif self._caja is not None:
            estado_brazo = f"sujeta la caja {self._caja.nombre}"
        else:
            estado_brazo = "está vacío"
        msg_caja_brazo = (
            f"el brazo {self._nombre} no sujeta la caja {caja.nombre}, {estado_brazo}"
        )
        raise ValueError(msg_caja_brazo)

    @property
    def nombre(self) -> str:
        """El nombre del brazo."""
        return self._nombre

    @property
    def caja(self) -> Caja | None:
        """La caja que sujeta este brazo, o ``None`` si no sujeta ninguna."""
        return self._caja

    @property
    def transportador(self) -> Transportador | None:
        """El transportador que lleva este brazo, o ``None`` si no lleva ninguno."""
        return self._transportador
