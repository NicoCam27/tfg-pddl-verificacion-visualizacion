from __future__ import annotations

from typing import TYPE_CHECKING

from simulador_pddl.objetos.utilidades_objetos import (
    con_articulo,
    con_preposicion_a,
    validar_objeto_contenido,
    validar_objeto_localizacion,
)
from simulador_pddl.tipos_basicos import validar_cadena

if TYPE_CHECKING:
    from simulador_pddl.objetos.contenido import Contenido
    from simulador_pddl.objetos.dron import Dron
    from simulador_pddl.objetos.localizacion import Localizacion
    from simulador_pddl.objetos.persona import Persona
    from simulador_pddl.objetos.transportador import Transportador


class Caja:
    """Caja representa una caja en el dominio de logística con drones.

    Una caja puede estar disponible en una localización, sujeta por el brazo de
    un dron, dentro de un transportador o entregada a una persona. Su ``estado``
    es ``DISPONIBLE``, ``TRANSPORTADA`` (en un brazo o en un transportador) o
    ``ENTREGADA``, y ``propietario_actual`` dice quién la tiene. Se mueve con
    quien la lleva, así que siempre tiene una localización.

    Args:
        nombre: El nombre de la caja en el dominio.
        localizacion: La localización donde empieza la caja.
        contenido: Lo que contiene la caja, p. ej. ``Contenido("comida")``. Solo
            se puede entregar a una persona que lo necesita.
    """

    DISPONIBLE = "disponible"
    TRANSPORTADA = "transportada"
    ENTREGADA = "entregada"

    def __init__(
        self, nombre: str, localizacion: Localizacion, contenido: Contenido
    ) -> None:
        validar_cadena(nombre, "nombre")
        validar_objeto_localizacion(localizacion)
        validar_objeto_contenido(contenido)

        self._nombre = nombre
        self._localizacion = localizacion
        self._contenido = contenido
        self._estado = self.DISPONIBLE
        self._propietario_actual: Dron | Transportador | Persona | None = None

    def __repr__(self) -> str:
        return f"Caja({self._nombre!r})"

    def __str__(self) -> str:
        return (
            f"Caja(nombre={self._nombre}, localizacion={self._localizacion}, "
            f"contenido={self._contenido}, estado={self._estado}, "
            f"propietario_actual={self._nombre_propietario()})"
        )

    def _asignar_a(self, propietario: Dron | Transportador) -> None:
        """Asigna la caja a un dron o a un transportador, si está disponible.

        Raises:
            ValueError: Si la caja no estaba disponible.
        """
        if self._estado != self.DISPONIBLE:
            msg_propietario_caja = (
                f"la caja {self._nombre} no se puede coger, "
                f"pertenece {con_preposicion_a(self._describir_propietario())}"
            )
            raise ValueError(msg_propietario_caja)

        self._estado = self.TRANSPORTADA
        self._propietario_actual = propietario

    def _entregar_a(self, persona: Persona) -> None:
        """Entrega la caja a una persona: desde ahora la persona es su propietaria.

        Aquí no se comprueba nada: quien llama se asegura de que la caja está
        disponible y en la localización de la persona.
        """
        self._estado = self.ENTREGADA
        self._propietario_actual = persona

    def _liberar(self) -> None:
        """Deja la caja disponible otra vez.

        Aquí no se comprueba nada: la caja se libera siempre de su propietario
        actual, que es el dron cuyo brazo la sujeta o el transportador que la
        tiene dentro.
        """
        self._estado = self.DISPONIBLE
        self._propietario_actual = None

    def _nombre_propietario(self) -> str:
        """Devuelve el nombre del propietario actual, o ``"nadie"`` si no lo hay."""
        return (
            self._propietario_actual.nombre
            if self._propietario_actual is not None
            else "nadie"
        )

    def _describir_propietario(self) -> str:
        """Devuelve el propietario actual con su tipo, p. ej. ``"el dron dron1"``.

        ``"nadie"`` si la caja no tiene propietario. Lo usan los mensajes de
        error, porque nombran cada objeto con su tipo. ``__str__()`` usa
        ``_nombre_propietario()``.
        """
        if self._propietario_actual is None:
            return "nadie"
        return con_articulo(self._propietario_actual)

    def _mover(self, destino: Localizacion) -> None:
        """Cambia la localización de la caja.

        Aquí no se comprueba nada. La caja solo se mueve con su propietario: la
        mueven ``Dron._mover()``, si la sujeta un brazo del dron, o
        ``Transportador._mover()``, si está dentro del transportador. Los dos
        cambian antes su propia localización, así que la caja acaba donde está
        su propietario.
        """
        self._localizacion = destino

    @property
    def nombre(self) -> str:
        """El nombre de la caja."""
        return self._nombre

    @property
    def localizacion(self) -> Localizacion:
        """La localización donde está ahora la caja."""
        return self._localizacion

    @property
    def contenido(self) -> Contenido:
        """Lo que contiene la caja, p. ej. ``Contenido("comida")``."""
        return self._contenido

    @property
    def estado(self) -> str:
        """El estado de la caja: ``DISPONIBLE``, ``TRANSPORTADA`` o ``ENTREGADA``.

        ``DISPONIBLE``: en una localización, sin propietario. ``TRANSPORTADA``:
        la sujeta el brazo de un dron o está dentro de un transportador (también
        cuando nadie lleva el transportador). ``ENTREGADA``: la posee una persona.
        """
        return self._estado

    @property
    def propietario_actual(self) -> Dron | Transportador | Persona | None:
        """El propietario de la caja, o ``None`` si la caja está disponible.

        El propietario es el dron que sujeta la caja con uno de sus brazos, el
        transportador en el que está la caja, o la persona a la que se entregó.
        """
        return self._propietario_actual
