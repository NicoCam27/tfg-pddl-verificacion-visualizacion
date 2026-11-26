"""Plan de OPTIC-CLP para el problema temporal, con dos drones a la vez.

Plan tal cual lo devuelve OPTIC-CLP con la opción ``-N``, que da el primer plan
que encuentra sin optimizar su calidad (instante, acción y duración):

    0.000: (coger-caja dron1 derecho1 caja3 deposito)  [1.000]
    0.000: (coger-caja dron1 izquierdo1 caja2 deposito)  [1.000]
    0.000: (coger-caja dron2 brazo2 caja1 deposito)  [1.000]
    1.000: (mover dron1 deposito loc3)  [2.000]
    1.000: (mover dron2 deposito loc1)  [2.000]
    3.001: (entregar-caja dron1 derecho1 caja3 persona3 loc3 agua)  [1.000]
    3.001: (entregar-caja dron2 brazo2 caja1 persona1 loc1 comida)  [1.000]
    4.001: (mover dron1 loc3 loc2)  [2.000]
    4.001: (mover dron2 loc1 deposito)  [2.000]
    6.002: (entregar-caja dron1 izquierdo1 caja2 persona2 loc2 medicina)  [1.000]
    7.002: (mover dron1 loc2 deposito)  [2.000]

Se usan sus instantes y duraciones. Las acciones que empiezan en el mismo instante
se ejecutan a la vez: dron1 coge dos cajas con sus dos brazos mientras dron2 coge
la suya, y los dos drones vuelan y entregan en paralelo. OPTIC separa con un
margen de milésimas (3.001, 6.002) cada entrega del vuelo que la precede, porque
la entrega necesita que el dron haya llegado. En cambio, cada vuelo empieza en el
mismo instante en que termina la acción anterior, porque no necesita nada de ella.
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
loc3 = Localizacion("loc3")

izquierdo1 = Brazo("izquierdo1")
derecho1 = Brazo("derecho1")
brazo2 = Brazo("brazo2")
dron1 = Dron("dron1", deposito, [izquierdo1, derecho1])
dron2 = Dron("dron2", deposito, [brazo2])

comida = Contenido("comida")
medicina = Contenido("medicina")
agua = Contenido("agua")

caja1 = Caja("caja1", deposito, comida)
caja2 = Caja("caja2", deposito, medicina)
caja3 = Caja("caja3", deposito, agua)

persona1 = Persona("persona1", loc1, comida)
persona2 = Persona("persona2", loc2, medicina)
persona3 = Persona("persona3", loc3, agua)

acciones = [
    CogerCaja(dron1, derecho1, caja3, 0, 1),
    CogerCaja(dron1, izquierdo1, caja2, 0, 1),
    CogerCaja(dron2, brazo2, caja1, 0, 1),
    Mover(dron1, deposito, loc3, 1, 2),
    Mover(dron2, deposito, loc1, 1, 2),
    EntregarCaja(dron1, derecho1, caja3, persona3, 3.001, 1),
    EntregarCaja(dron2, brazo2, caja1, persona1, 3.001, 1),
    Mover(dron1, loc3, loc2, 4.001, 2),
    Mover(dron2, loc1, deposito, 4.001, 2),
    EntregarCaja(dron1, izquierdo1, caja2, persona2, 6.002, 1),
    Mover(dron1, loc2, deposito, 7.002, 2),
]

mundo = Mundo(
    acciones,
    localizaciones=[deposito, loc1, loc2, loc3],
    drones=[dron1, dron2],
    cajas=[caja1, caja2, caja3],
    personas=[persona1, persona2, persona3],
    contenidos=[comida, medicina, agua],
    objetivos=[
        PersonaTieneContenido(persona1, comida),
        PersonaTieneContenido(persona2, medicina),
        PersonaTieneContenido(persona3, agua),
        DronEnLocalizacion(dron1, deposito),
        DronEnLocalizacion(dron2, deposito),
    ],
)
