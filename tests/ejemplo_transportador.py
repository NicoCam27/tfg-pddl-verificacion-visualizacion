"""Ejemplo básico con un transportador: un dron entrega dos cajas.

El dron mete las dos cajas en un transportador en el depósito, lleva el
transportador hasta cada persona, saca su caja y se la entrega, y vuelve al
depósito. Muestra la simulación en una ventana de pygame e imprime su veredicto al
cerrarla.
"""

from simulador_pddl import *

deposito = Localizacion("deposito")
localizacion1 = Localizacion("localizacion1")
localizacion2 = Localizacion("localizacion2")

localizaciones = [deposito, localizacion1, localizacion2]

izq = Brazo("izq")
der = Brazo("der")

dron1 = Dron("dron1", deposito, [izq, der])

comida = Contenido("comida")
medicina = Contenido("medicina")

caja1 = Caja("caja1", deposito, comida)
caja2 = Caja("caja2", deposito, medicina)

transportador1 = Transportador("transportador1", deposito, 2)

persona1 = Persona("persona1", localizacion1, comida)
persona2 = Persona("persona2", localizacion2, medicina)

acciones = [
    CogerCaja(dron1, izq, caja1, 0, 1),
    PonerCajaEnTransportador(dron1, izq, caja1, transportador1, 1, 1),
    CogerCaja(dron1, der, caja2, 2, 1),
    PonerCajaEnTransportador(dron1, der, caja2, transportador1, 3, 1),
    MoverTransportador(dron1, transportador1, izq, deposito, localizacion1, 4, 1),
    SacarCajaDeTransportador(dron1, izq, caja1, transportador1, 5, 1),
    EntregarCaja(dron1, izq, caja1, persona1, 6, 1),
    MoverTransportador(dron1, transportador1, izq, localizacion1, localizacion2, 7, 1),
    SacarCajaDeTransportador(dron1, izq, caja2, transportador1, 8, 1),
    EntregarCaja(dron1, izq, caja2, persona2, 9, 1),
    Mover(dron1, localizacion2, deposito, 10, 1),
]

drones = [dron1]
cajas = [caja1, caja2]
personas = [persona1, persona2]
contenidos = [comida, medicina]
transportadores = [transportador1]


# El problema se resuelve cuando cada persona tiene lo que necesita y el dron ha
# vuelto al depósito. El transportador se queda donde se sacó la última caja.
objetivos = [
    PersonaTieneContenido(persona1, comida),
    PersonaTieneContenido(persona2, medicina),
    DronEnLocalizacion(dron1, deposito),
    TransportadorEnLocalizacion(transportador1, localizacion2),
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

# Simula el plan en la ventana de pygame y devuelve el informe con el veredicto
informe = nuevo_mundo.simulacion_visual()

print(informe.resumen())  # Una vez se cierra la ventana se imprime el veredicto
