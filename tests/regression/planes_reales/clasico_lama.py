"""Plan de LAMA para el problema clásico.

Plan tal cual lo devuelve LAMA:

    (coger-caja dron1 izquierdo caja1 deposito)
    (mover dron1 deposito loc1)
    (entregar-caja dron1 izquierdo caja1 persona1 loc1 comida)
    (mover dron1 loc1 deposito)
    (coger-caja dron1 izquierdo caja2 deposito)
    (mover dron1 deposito loc2)
    (entregar-caja dron1 izquierdo caja2 persona2 loc2 medicina)
    (mover dron1 loc2 deposito)

LAMA no tiene modelo temporal: devuelve una secuencia de acciones. La acción i empieza
en i y dura 1.
"""

from simulador_pddl import (
    Brazo,
    Caja,
    CogerCaja,
    Contenido,
    Dron,
    DronEnLocalizacion,
    EntregarCaja,
    Localizacion,
    Mover,
    Mundo,
    Persona,
    PersonaTieneContenido,
)

deposito = Localizacion("deposito")
loc1 = Localizacion("loc1")
loc2 = Localizacion("loc2")

izquierdo = Brazo("izquierdo")
derecho = Brazo("derecho")
dron1 = Dron("dron1", deposito, [izquierdo, derecho])

comida = Contenido("comida")
medicina = Contenido("medicina")

caja1 = Caja("caja1", deposito, comida)
caja2 = Caja("caja2", deposito, medicina)

persona1 = Persona("persona1", loc1, comida)
persona2 = Persona("persona2", loc2, medicina)

acciones = [
    CogerCaja(dron1, izquierdo, caja1, 0, 1),
    Mover(dron1, deposito, loc1, 1, 1),
    EntregarCaja(dron1, izquierdo, caja1, persona1, 2, 1),
    Mover(dron1, loc1, deposito, 3, 1),
    CogerCaja(dron1, izquierdo, caja2, 4, 1),
    Mover(dron1, deposito, loc2, 5, 1),
    EntregarCaja(dron1, izquierdo, caja2, persona2, 6, 1),
    Mover(dron1, loc2, deposito, 7, 1),
]

mundo = Mundo(
    acciones,
    localizaciones=[deposito, loc1, loc2],
    drones=[dron1],
    cajas=[caja1, caja2],
    personas=[persona1, persona2],
    contenidos=[comida, medicina],
    objetivos=[
        PersonaTieneContenido(persona1, comida),
        PersonaTieneContenido(persona2, medicina),
        DronEnLocalizacion(dron1, deposito),
    ],
)
