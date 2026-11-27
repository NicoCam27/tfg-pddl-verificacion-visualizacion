from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulador_pddl.objetos import (
        Contenido,
        Dron,
        Localizacion,
        Persona,
        Transportador,
    )

# Los objetos a los que puede referirse un objetivo: nunca un brazo ni una caja.
type ObjetoReferenciado = Contenido | Dron | Localizacion | Persona | Transportador


class Objetivo(ABC):
    """Un objetivo de un problema del dominio de logística con drones.

    Un objetivo es un predicado de la sección ``:goal`` de un problema PDDL. Se
    evalúa sobre el estado actual de los objetos, no sobre una copia. Un plan
    resuelve el problema si todos los objetivos se cumplen en el estado final.
    Mientras se ejecuta, también se anota cuándo empieza y deja de cumplirse cada
    uno (ver ``EstadoObjetivo``).

    Solo la biblioteca define subclases, así que sus métodos son privados. Una
    subclase tiene que implementar ``_se_cumple()``, ``_describir()``,
    ``_explicar_fallo()`` y ``_objetos_referenciados()``, y puede sobrescribir
    ``_validar_alcanzable()`` si hay estados iniciales en los que no se puede
    lograr.
    """

    def __str__(self) -> str:
        """Devuelve la descripción del objetivo."""
        return self._describir()

    @abstractmethod
    def _se_cumple(self) -> bool:
        """Devuelve si el objetivo se cumple en este momento.

        ``Simulacion`` lo llama al construirse, al reiniciarse y después de cada
        suceso, no solo al final del plan. Así el informe puede decir cuándo se
        logró el objetivo y cuándo dejó de cumplirse (``logrado_en`` y
        ``roto_en`` de ``EstadoObjetivo``).
        """

    @abstractmethod
    def _describir(self) -> str:
        """Devuelve lo que exige el objetivo, como una afirmación.

        Es el texto con el que aparece el objetivo en el resumen del informe, en
        el panel lateral de la ventana y en los errores que lanza ``Mundo`` al
        construirse. En minúscula y sin punto final, porque se inserta en otros
        textos, p. ej. ``"el dron dron1 está en la localización deposito"``.
        """

    @abstractmethod
    def _explicar_fallo(self) -> str:
        """Devuelve por qué el objetivo no se cumple en este momento.

        ``EstadoObjetivo`` lo llama cada vez que observa el objetivo y no se
        cumple, y guarda el texto en ``explicacion_fallo``, que el informe y el
        panel lateral muestran debajo del objetivo. Como ``_describir()``, en
        minúscula y sin punto final.
        """

    @abstractmethod
    def _objetos_referenciados(self) -> list[ObjetoReferenciado]:
        """Devuelve los objetos del dominio que menciona el objetivo.

        ``Simulacion`` comprueba con ellos que el objetivo solo menciona objetos
        declarados.
        """

    def _validar_alcanzable(self) -> None:
        """Lanza ``ValueError`` si ningún plan puede lograr el objetivo.

        ``Simulacion`` lo llama al construirse, sobre el estado inicial y después
        de comprobar que los objetos del objetivo se declararon. Por defecto no
        hace nada: un objetivo solo lo sobrescribe si hay estados iniciales en los
        que no se puede lograr, para rechazar el problema en lugar de dar el plan
        por no válido.
        """
        # No es abstracto a propósito: la mayoría de los objetivos no lo necesitan.
        return
