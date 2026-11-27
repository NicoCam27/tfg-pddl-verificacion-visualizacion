"""Plan de LPG-td para el problema clásico.

Plan tal cual lo devuelve LPG-td (instante, acción y duración):

    0:   (COGER-CAJA DRON1 DERECHO CAJA2 DEPOSITO) [1]
    1:   (MOVER DRON1 DEPOSITO LOC2) [1]
    2:   (ENTREGAR-CAJA DRON1 DERECHO CAJA2 PERSONA2 LOC2 MEDICINA) [1]
    3:   (MOVER DRON1 LOC2 DEPOSITO) [1]
    4:   (COGER-CAJA DRON1 DERECHO CAJA1 DEPOSITO) [1]
    5:   (MOVER DRON1 DEPOSITO LOC1) [1]
    6:   (ENTREGAR-CAJA DRON1 DERECHO CAJA1 PERSONA1 LOC1 COMIDA) [1]
    7:   (MOVER DRON1 LOC1 DEPOSITO) [1]

En un dominio clásico, LPG-td asigna a cada acción duración 1 y las coloca una detrás de
otra. Se usan sus instantes y duraciones.
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
    CogerCaja(dron1, derecho, caja2, 0, 1),
    Mover(dron1, deposito, loc2, 1, 1),
    EntregarCaja(dron1, derecho, caja2, persona2, 2, 1),
    Mover(dron1, loc2, deposito, 3, 1),
    CogerCaja(dron1, derecho, caja1, 4, 1),
    Mover(dron1, deposito, loc1, 5, 1),
    EntregarCaja(dron1, derecho, caja1, persona1, 6, 1),
    Mover(dron1, loc1, deposito, 7, 1),
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
