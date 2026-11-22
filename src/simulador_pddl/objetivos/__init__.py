"""objetivos: Los objetivos de un problema del dominio de logística con drones.

Cada clase es un tipo de predicado de la sección ``:goal`` de un problema PDDL.
Los objetivos se reúnen en una lista y se pasan a ``Mundo`` junto con las
acciones y los objetos. Un plan resuelve el problema solo si todos los
objetivos se cumplen cuando el plan termina. Mientras el plan se ejecuta, la
simulación también anota cuándo se logró cada objetivo y cuándo dejó de
cumplirse.

Objetivos disponibles:
    PersonaTieneContenido, DronEnLocalizacion, TransportadorEnLocalizacion.
``Objetivo`` es su clase base abstracta.

Ejemplo:
    from simulador_pddl import Mundo
    from simulador_pddl.acciones import CogerCaja, EntregarCaja, Mover
    from simulador_pddl.objetivos import DronEnLocalizacion, PersonaTieneContenido
    from simulador_pddl.objetos import Brazo, Caja, Dron, Localizacion, Persona

    deposito = Localizacion("deposito")
    localizacion1 = Localizacion("localizacion1")
    brazo_izquierdo = Brazo("brazo-izquierdo")
    dron1 = Dron("dron1", deposito, [brazo_izquierdo])
    caja1 = Caja("caja1", deposito, "comida")
    persona1 = Persona("persona1", localizacion1, "comida")

    acciones = [
        CogerCaja(dron1, brazo_izquierdo, caja1, inicio_sim=0, duracion_sim=1),
        Mover(dron1, deposito, localizacion1, inicio_sim=1, duracion_sim=2),
        EntregarCaja(dron1, brazo_izquierdo, caja1, persona1, inicio_sim=3),
    ]
    objetivos = [
        PersonaTieneContenido(persona1, "comida"),
        DronEnLocalizacion(dron1, localizacion1),
    ]

    mundo = Mundo(
        acciones,
        localizaciones=[deposito, localizacion1],
        drones=[dron1],
        cajas=[caja1],
        personas=[persona1],
        objetivos=objetivos,
    )
    informe = mundo.simulacion_texto()
    print(informe.es_valido)
"""

from simulador_pddl.objetivos.localizacion import (
    DronEnLocalizacion,
    TransportadorEnLocalizacion,
)
from simulador_pddl.objetivos.objetivo import Objetivo
from simulador_pddl.objetivos.persona import PersonaTieneContenido

__all__ = [
    "DronEnLocalizacion",
    "Objetivo",
    "PersonaTieneContenido",
    "TransportadorEnLocalizacion",
]
