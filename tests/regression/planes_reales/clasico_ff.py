"""Plan de ff para el problema clásico.

Plan tal cual lo devuelve ff:

    step    0: COGER-CAJA DRON1 IZQUIERDO CAJA1 DEPOSITO
            1: COGER-CAJA DRON1 DERECHO CAJA2 DEPOSITO
            2: MOVER DRON1 DEPOSITO LOC1
            3: ENTREGAR-CAJA DRON1 IZQUIERDO CAJA1 PERSONA1 LOC1 COMIDA
            4: MOVER DRON1 LOC1 LOC2
            5: ENTREGAR-CAJA DRON1 DERECHO CAJA2 PERSONA2 LOC2 MEDICINA
            6: MOVER DRON1 LOC2 DEPOSITO

ff no tiene modelo temporal: numera pasos, no instantes. El paso i empieza en i
y dura 1.
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
    CogerCaja(dron1, derecho, caja2, 1, 1),
    Mover(dron1, deposito, loc1, 2, 1),
    EntregarCaja(dron1, izquierdo, caja1, persona1, 3, 1),
    Mover(dron1, loc1, loc2, 4, 1),
    EntregarCaja(dron1, derecho, caja2, persona2, 5, 1),
    Mover(dron1, loc2, deposito, 6, 1),
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
