"""Dos drones, diez personas y un transportador, en la ventana de pygame.

``dron1`` entrega una caja a cada persona, de una en una, salvo a ``persona10``:
su caja se suelta a su lado en lugar de entregarse, así que el plan se ejecuta
sin errores pero no resuelve el problema (el veredicto es ``"NO RESUELVE"``).
``dron2`` lleva una caja en el transportador y la suelta. Imprime el veredicto
cuando se cierra la ventana.
"""

from simulador_pddl.acciones import (
    CogerCaja,
    CogerTransportador,
    EntregarCaja,
    Mover,
    PonerCajaEnTransportador,
    SacarCajaDeTransportador,
    Soltar,
    SoltarTransportador,
)
from simulador_pddl.mundo import Mundo
from simulador_pddl.objetivos import DronEnLocalizacion, PersonaTieneContenido
from simulador_pddl.objetos import (
    Brazo,
    Caja,
    Contenido,
    Dron,
    Localizacion,
    Persona,
    Transportador,
)

deposito = Localizacion("deposito")
localizacion1 = Localizacion("localizacion1")
localizacion2 = Localizacion("localizacion2")
localizacion3 = Localizacion("localizacion3")
localizacion4 = Localizacion("localizacion4")
localizacion5 = Localizacion("localizacion5")
localizacion6 = Localizacion("localizacion6")
localizacion7 = Localizacion("localizacion7")
localizacion8 = Localizacion("localizacion8")
localizacion9 = Localizacion("localizacion9")
localizacion10 = Localizacion("localizacion10")

localizaciones = [
    deposito,
    localizacion1,
    localizacion2,
    localizacion3,
    localizacion4,
    localizacion5,
    localizacion6,
    localizacion7,
    localizacion8,
    localizacion9,
    localizacion10,
]

izq = Brazo("izq")
der = Brazo("der")

izq2 = Brazo("izq2")
der2 = Brazo("der2")

dron1 = Dron("dron1", deposito, [izq, der])
dron2 = Dron("dron2", deposito, [izq2, der2])

comida = Contenido("comida")
medicina = Contenido("medicina")

caja1 = Caja("caja1", deposito, comida)
caja2 = Caja("caja2", deposito, medicina)
caja3 = Caja("caja3", deposito, medicina)
caja4 = Caja("caja4", deposito, medicina)
caja5 = Caja("caja5", deposito, medicina)
caja6 = Caja("caja6", deposito, medicina)
caja7 = Caja("caja7", deposito, medicina)
caja8 = Caja("caja8", deposito, medicina)
caja9 = Caja("caja9", deposito, medicina)
caja10 = Caja("caja10", deposito, medicina)

caja11 = Caja("caja11", deposito, comida)

persona1 = Persona("persona1", localizacion10, medicina)
persona2 = Persona("persona2", localizacion9, medicina)
persona3 = Persona("persona3", localizacion8, medicina)
persona4 = Persona("persona4", localizacion3, medicina)
persona5 = Persona("persona5", localizacion8, medicina)
persona6 = Persona("persona6", localizacion10, medicina)
persona7 = Persona("persona7", localizacion7, medicina)
persona8 = Persona("persona8", localizacion1, comida)
persona9 = Persona("persona9", localizacion6, medicina)
persona10 = Persona("persona10", localizacion4, medicina)

contenidos = [comida, medicina]

transportador1 = Transportador("transportador1", deposito, 4)

acciones = [
    CogerCaja(dron1, der, caja2, 0, 1),
    CogerCaja(dron2, izq2, caja11, 0, 1),
    Mover(dron1, deposito, localizacion4, 1, 1),
    PonerCajaEnTransportador(dron2, izq2, caja11, transportador1, 1, 1),
    Soltar(dron1, der, caja2, 2, 1),
    CogerTransportador(dron2, izq2, transportador1, 2, 1),
    Mover(dron1, localizacion4, deposito, 3, 1),
    Mover(dron2, deposito, localizacion5, 3, 1),
    CogerCaja(dron1, der, caja3, 4, 1),
    SoltarTransportador(dron2, izq2, transportador1, 4, 1),
    Mover(dron1, deposito, localizacion6, 5, 1),
    SacarCajaDeTransportador(dron2, izq2, caja11, transportador1, 5, 1),
    EntregarCaja(dron1, der, caja3, persona9, 6, 1),
    Soltar(dron2, izq2, caja11, 6, 1),
    Mover(dron1, localizacion6, deposito, 7, 1),
    Mover(dron2, localizacion5, deposito, 7, 1),
    CogerCaja(dron1, der, caja1, 8, 1),
    Mover(dron1, deposito, localizacion1, 9, 1),
    EntregarCaja(dron1, der, caja1, persona8, 10, 1),
    Mover(dron1, localizacion1, deposito, 11, 1),
    CogerCaja(dron1, der, caja4, 12, 1),
    Mover(dron1, deposito, localizacion7, 13, 1),
    EntregarCaja(dron1, der, caja4, persona7, 14, 1),
    Mover(dron1, localizacion7, deposito, 15, 1),
    CogerCaja(dron1, der, caja5, 16, 1),
    Mover(dron1, deposito, localizacion10, 17, 1),
    EntregarCaja(dron1, der, caja5, persona6, 18, 1),
    Mover(dron1, localizacion10, deposito, 19, 1),
    CogerCaja(dron1, der, caja6, 20, 1),
    Mover(dron1, deposito, localizacion8, 21, 1),
    EntregarCaja(dron1, der, caja6, persona5, 22, 1),
    Mover(dron1, localizacion8, deposito, 23, 1),
    CogerCaja(dron1, der, caja7, 24, 1),
    Mover(dron1, deposito, localizacion3, 25, 1),
    EntregarCaja(dron1, der, caja7, persona4, 26, 1),
    Mover(dron1, localizacion3, deposito, 27, 1),
    CogerCaja(dron1, der, caja8, 28, 1),
    Mover(dron1, deposito, localizacion8, 29, 1),
    EntregarCaja(dron1, der, caja8, persona3, 30, 1),
    Mover(dron1, localizacion8, deposito, 31, 1),
    CogerCaja(dron1, der, caja9, 32, 1),
    Mover(dron1, deposito, localizacion9, 33, 1),
    EntregarCaja(dron1, der, caja9, persona2, 34, 1),
    Mover(dron1, localizacion9, deposito, 35, 1),
    CogerCaja(dron1, der, caja10, 36, 1),
    Mover(dron1, deposito, localizacion10, 37, 1),
    EntregarCaja(dron1, der, caja10, persona1, 38, 1),
    Mover(dron1, localizacion10, deposito, 39, 1),
]
drones = [dron1, dron2]
transportadores = [transportador1]
cajas = [caja1, caja2, caja3, caja4, caja5, caja6, caja7, caja8, caja9, caja10, caja11]
personas = [
    persona1,
    persona2,
    persona3,
    persona4,
    persona5,
    persona6,
    persona7,
    persona8,
    persona9,
    persona10,
]

# El problema se resuelve cuando todas las personas tienen lo que necesitan y los
# dos drones han vuelto al depósito.
objetivos = [
    PersonaTieneContenido(persona1, medicina),
    PersonaTieneContenido(persona2, medicina),
    PersonaTieneContenido(persona3, medicina),
    PersonaTieneContenido(persona4, medicina),
    PersonaTieneContenido(persona5, medicina),
    PersonaTieneContenido(persona6, medicina),
    PersonaTieneContenido(persona7, medicina),
    PersonaTieneContenido(persona8, comida),
    PersonaTieneContenido(persona9, medicina),
    PersonaTieneContenido(persona10, medicina),
    DronEnLocalizacion(dron1, deposito),
    DronEnLocalizacion(dron2, deposito),
]

nuevo_mundo = Mundo(
    acciones,
    localizaciones=localizaciones,
    drones=drones,
    cajas=cajas,
    personas=personas,
    contenidos=contenidos,
    transportadores=transportadores,
    objetivos=objetivos,
)

# Para simularlo en la terminal, sin ventana, se cambia la línea siguiente por
# informe = nuevo_mundo.simulacion_texto(). Si la ventana se cierra antes del
# final del plan, el veredicto es "INCOMPLETO".
informe = nuevo_mundo.simulacion_visual()
print(informe.resumen())  # Al cerrar la ventana, se imprime el resumen del informe
