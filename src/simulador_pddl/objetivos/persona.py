from __future__ import annotations

from typing import TYPE_CHECKING, override

from simulador_pddl.objetivos.objetivo import Objetivo
from simulador_pddl.objetos.utilidades_objetos import (
    describir_necesidades,
    validar_objeto_contenido,
    validar_objeto_persona,
)

if TYPE_CHECKING:
    from simulador_pddl.objetivos.objetivo import ObjetoReferenciado
    from simulador_pddl.objetos import Contenido, Persona


class PersonaTieneContenido(Objetivo):
    """Objetivo persona tiene contenido del dominio de logística con drones.

    Se cumple cuando la persona posee al menos una caja con ``contenido``. Una
    persona empieza sin cajas y solo posee las que se le entregan, así que el
    objetivo se logra cuando termina un ``EntregarCaja`` (``at end``) con una caja
    de ese contenido. ``EntregarCaja`` solo entrega cajas con algo que la persona
    necesita, así que ``Mundo`` rechaza el objetivo si ``contenido`` no es una de
    sus necesidades: ningún plan podría lograrlo.

    Args:
        persona: La persona que tiene que poseer la caja.
        contenido: El contenido que tiene que tener la caja, p. ej.
            ``Contenido("comida")``.
    """

    def __init__(self, persona: Persona, contenido: Contenido) -> None:
        validar_objeto_persona(persona)
        validar_objeto_contenido(contenido)

        self._persona = persona
        self._contenido = contenido

    def __repr__(self) -> str:
        return f"PersonaTieneContenido({self._persona!r}, {self._contenido!r})"

    @override
    def _se_cumple(self) -> bool:
        return any(caja.contenido == self._contenido for caja in self._persona.posee)

    @override
    def _describir(self) -> str:
        return (
            f"la persona {self._persona.nombre} posee una caja con el contenido "
            f"'{self._contenido}'"
        )

    @override
    def _explicar_fallo(self) -> str:
        cajas_poseidas = self._persona.posee

        if not cajas_poseidas:
            return f"la persona {self._persona.nombre} no posee ninguna caja"

        # Se muestra el contenido de cada caja porque la persona puede necesitar
        # varios contenidos: puede haber recibido cajas con uno de ellos y no con
        # el que pide el objetivo. Este método solo se llama si el objetivo no se
        # cumple, así que ninguna caja tiene ese contenido.
        texto_cajas = ", ".join(
            f"{caja.nombre} ('{caja.contenido}')" for caja in cajas_poseidas
        )

        if len(cajas_poseidas) == 1:
            return (
                f"la persona {self._persona.nombre} posee la caja {texto_cajas}, "
                f"que no tiene el contenido '{self._contenido}'"
            )
        return (
            f"la persona {self._persona.nombre} posee las cajas {texto_cajas}, "
            f"pero ninguna tiene el contenido '{self._contenido}'"
        )

    @override
    def _objetos_referenciados(self) -> list[ObjetoReferenciado]:
        return [self._persona, self._contenido]

    @override
    def _validar_alcanzable(self) -> None:
        """Lanza ``ValueError`` si la persona no necesita ``contenido``.

        Una persona solo recibe cajas con algo que necesita, y sus necesidades
        nunca aumentan, así que sin esa necesidad el objetivo solo se puede
        cumplir si ya se cumple (la persona posee ya una caja con ``contenido``).
        En un problema recién creado eso no pasa, porque una persona empieza sin
        cajas. Solo pasa si el mundo se construye sobre objetos que otro mundo ya
        usó. En ese caso el objetivo está logrado, así que no se rechaza como
        inalcanzable.
        """
        if self._se_cumple() or self._contenido in self._persona.necesidades:
            return

        msg_objetivo_inalcanzable = (
            f"el objetivo {self._describir()!r} no se puede lograr: la persona "
            f"{self._persona.nombre} "
            f"{describir_necesidades(self._persona.necesidades)}, y solo se le "
            "pueden entregar cajas con algo que necesita"
        )
        raise ValueError(msg_objetivo_inalcanzable)

    @property
    def persona(self) -> Persona:
        """La persona que tiene que poseer la caja."""
        return self._persona

    @property
    def contenido(self) -> Contenido:
        """El contenido que tiene que tener una de las cajas de la persona."""
        return self._contenido
