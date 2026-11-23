from simulador_pddl import *

# Objetos del dominio
deposito = Localizacion("deposito")
localizacion1 = Localizacion("localizacion1")
localizacion2 = Localizacion("localizacion2")

izq = Brazo("izq")
der = Brazo("der")

dron1 = Dron("dron1", deposito, [izq, der])

comida = Contenido("comida")
medicina = Contenido("medicina")

caja1 = Caja("caja1", deposito, comida)
caja2 = Caja("caja2", deposito, medicina)

persona1 = Persona("persona1", localizacion1, comida)
persona2 = Persona("persona2", localizacion2, medicina)

# Plan: cada acción indica cuándo empieza (inicio_sim) y cuánto dura (duracion_sim)
acciones = [
    CogerCaja(dron1, izq, caja1, inicio_sim=0, duracion_sim=1),
    CogerCaja(dron1, der, caja2, inicio_sim=1, duracion_sim=1),
    Mover(dron1, deposito, localizacion1, inicio_sim=2, duracion_sim=1),
    EntregarCaja(dron1, izq, caja1, persona1, inicio_sim=3, duracion_sim=1),
    Mover(dron1, localizacion1, localizacion2, inicio_sim=4, duracion_sim=1),
    EntregarCaja(dron1, der, caja2, persona2, inicio_sim=5, duracion_sim=1),
    Mover(dron1, localizacion2, deposito, inicio_sim=6, duracion_sim=1),
]

# Objetos del problema: una lista por tipo
localizaciones = [deposito, localizacion1, localizacion2]
drones = [dron1]
cajas = [caja1, caja2]
personas = [persona1, persona2]
contenidos = [comida, medicina]

# Objetivos: lo que debe cumplirse cuando el plan termina
objetivos = [
    PersonaTieneContenido(persona1, comida),
    PersonaTieneContenido(persona2, medicina),
    DronEnLocalizacion(dron1, deposito),
]

nuevo_mundo = Mundo(
    acciones,
    localizaciones=localizaciones,
    drones=drones,
    cajas=cajas,
    personas=personas,
    contenidos=contenidos,
    objetivos=objetivos,
)

# Simula el plan en la terminal y devuelve el informe con el veredicto
informe = nuevo_mundo.simulacion_texto()
