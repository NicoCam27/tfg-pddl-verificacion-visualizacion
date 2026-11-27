"""Instantánea y restauración del estado de la simulación.

Una ``InstantaneaMundo`` captura, de cada objeto que participa en una simulación
(drones, brazos, cajas, personas y, si los hay, transportadores), el estado que
la simulación puede cambiar, y más tarde puede devolver todos los objetos a ese
mismo estado, que es lo que hace falta para reiniciar una simulación.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulador_pddl.objetos import (
        Caja,
        Dron,
        ObjetoDominio,
        Persona,
        Transportador,
    )


def _copiar_valor(valor: object) -> object:
    """Devuelve una copia de ``valor`` si es una lista, y el propio ``valor`` si no.

    Las listas ya se guardan como copias al capturar, y se vuelven a copiar al
    restaurar. Si la instantánea y el mundo compartieran una lista, cambiar el
    mundo después de un reinicio cambiaría también la instantánea, y un segundo
    reinicio ya no volvería al estado inicial.
    """
    if isinstance(valor, list):
        return list(valor)
    return valor


class InstantaneaMundo:
    """InstantaneaMundo guarda el estado de un mundo para poder restaurarlo después.

    ``Simulacion`` crea una al construirse, con ``InstantaneaMundo._capturar()``
    (no con el constructor), y la restaura en ``_reiniciar()``. El estado se
    restaura en las mismas instancias.

    No guarda el estado de las acciones ni el de la propia simulación (el reloj,
    el error): ``Simulacion._reiniciar()`` los devuelve siempre al principio de
    una ejecución, con todas las acciones sin empezar (``Accion._reiniciar()``),
    que es como están siempre al construirla.

    Args:
        registros: Para cada objeto, el valor de cada uno de sus atributos
            privados que una simulación puede cambiar, indexado por el nombre
            del atributo.
    """

    def __init__(self, registros: dict[ObjetoDominio, dict[str, object]]) -> None:
        # Las claves son los propios objetos, no copias. Solo su estado se guarda
        # aparte, en los valores. Las acciones del plan apuntan a esas instancias,
        # así que el estado tiene que volver a ellas.
        self._registros = registros

    def __repr__(self) -> str:
        return f"InstantaneaMundo(objetos={len(self._registros)})"

    @classmethod
    def _capturar(
        cls,
        drones: list[Dron],
        cajas: list[Caja],
        personas: list[Persona],
        transportadores: list[Transportador],
    ) -> InstantaneaMundo:
        """Captura el estado actual de cada objeto del mundo.

        Las listas no se comprueban aquí: ``Simulacion`` las valida al
        construirse, antes de capturar. ``transportadores`` nunca es ``None``: en
        un problema sin transportadores, ``Simulacion`` pasa una lista vacía.
        """
        # Un registro por objeto: el valor de cada atributo privado, indexado por
        # su nombre, para que _restaurar() lo escriba con setattr().
        registros: dict[ObjetoDominio, dict[str, object]] = {}

        # Solo se captura el estado que una simulación puede cambiar. Los
        # nombres, los contenidos de las cajas, las capacidades de los
        # transportadores, los brazos de un dron y la localización de una persona
        # se fijan al crear cada objeto y nada los cambia después (sus propiedades
        # son de solo lectura y ningún método de la biblioteca los modifica), así
        # que un reinicio nunca necesita restaurarlos. Lo que al capturar suele
        # estar vacío (las reservas de los brazos y las cargas y descargas en
        # curso) también se captura, para que un reinicio a mitad de una acción
        # lo vacíe.
        for caja in cajas:
            registros[caja] = {
                "_localizacion": caja.localizacion,
                "_estado": caja.estado,
                "_propietario_actual": caja.propietario_actual,
            }

        for dron in drones:
            registros[dron] = {
                "_localizacion": dron.localizacion,
            }
            for brazo in dron.brazos:
                registros[brazo] = {
                    "_caja": brazo.caja,
                    "_transportador": brazo.transportador,
                }

        for transportador in transportadores:
            registros[transportador] = {
                "_localizacion": transportador.localizacion,
                "_cajas_dentro": transportador.cajas_dentro,
                "_cajas_entrantes": list(transportador._cajas_entrantes),
                "_cajas_salientes": list(transportador._cajas_salientes),
                "_propietario_actual": transportador.propietario_actual,
                "_brazo_actual": transportador.brazo_actual,
            }

        for persona in personas:
            registros[persona] = {
                "_necesidades": persona.necesidades,
                "_posee": persona.posee,
            }

        return cls(registros)

    def _restaurar(self) -> None:
        """Devuelve cada objeto capturado a su estado de la instantánea.

        Los atributos privados se escriben directamente, no mediante los métodos
        de los objetos, por dos razones. Muchos métodos solo cambian el estado en
        un sentido, el de la ejecución, y no tienen un método inverso:
        ``Persona._anadir_caja_poseida()`` quita una necesidad, pero ninguno la
        devuelve. Y los que sí servirían tienen efectos o comprobaciones propios
        de la ejecución: ``Dron._mover()`` mueve también lo que lleva el dron, y
        ``Caja._asignar_a()`` exige que la caja esté disponible, cosa que a mitad
        de la restauración puede no cumplirse todavía. La instantánea guarda un
        estado que era coherente en conjunto, así que escribirlo atributo a
        atributo, en cualquier orden, devuelve ese estado coherente.

        Las listas se escriben como copias, para que la instantánea se pueda
        restaurar más de una vez.
        """
        for objeto_dominio, valores in self._registros.items():
            for atributo, valor in valores.items():
                setattr(objeto_dominio, atributo, _copiar_valor(valor))
