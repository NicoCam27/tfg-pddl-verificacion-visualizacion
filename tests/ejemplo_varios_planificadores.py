"""Dos planes de dos planificadores para el mismo problema, en la terminal.

Un dron tiene que llevar una caja de comida del depósito a ``persona1``, en
``loc1``. Ir directamente del depósito a ``loc1`` dura 4, pero pasar por ``loc2``
dura 1 + 1. El planificador A minimiza el número de acciones y va directo (3
acciones, termina en t=6); el planificador B minimiza la duración del plan y
pasa por ``loc2`` (4 acciones, termina en t=4). Los dos planes son válidos.

El problema se escribe una vez, en ``crear_problema()``, y se llama una vez por
plan: ``Mundo`` cambia los objetos que recibe al ejecutar el plan, así que cada
plan necesita objetos nuevos.
"""

from types import SimpleNamespace

from simulador_pddl import *


def crear_problema():
    """Crea los objetos del problema: cada llamada crea objetos nuevos."""
    p = SimpleNamespace()
    p.deposito = Localizacion("deposito")
    p.loc1 = Localizacion("loc1")
    p.loc2 = Localizacion("loc2")
    p.comida = Contenido("comida")
    p.brazo = Brazo("izquierdo")
    p.dron = Dron("dron1", p.deposito, [p.brazo])
    p.caja = Caja("caja1", p.deposito, p.comida)
    p.persona = Persona("persona1", p.loc1, p.comida)
    return p


def crear_objetivos(p):
    """Crea los objetivos del problema ``p``."""
    return [PersonaTieneContenido(p.persona, p.comida)]


def plan_planificador_a(p):
    """Va directo del depósito a loc1: menos acciones, pero termina en t=6."""
    return [
        CogerCaja(p.dron, p.brazo, p.caja, inicio_sim=0, duracion_sim=1),
        Mover(p.dron, p.deposito, p.loc1, inicio_sim=1, duracion_sim=4),
        EntregarCaja(p.dron, p.brazo, p.caja, p.persona, inicio_sim=5, duracion_sim=1),
    ]


def plan_planificador_b(p):
    """Pasa por loc2: una acción más, pero termina antes, en t=4."""
    return [
        CogerCaja(p.dron, p.brazo, p.caja, inicio_sim=0, duracion_sim=1),
        Mover(p.dron, p.deposito, p.loc2, inicio_sim=1, duracion_sim=1),
        Mover(p.dron, p.loc2, p.loc1, inicio_sim=2, duracion_sim=1),
        EntregarCaja(p.dron, p.brazo, p.caja, p.persona, inicio_sim=3, duracion_sim=1),
    ]


for crear_plan in (plan_planificador_a, plan_planificador_b):
    p = crear_problema()  # Objetos nuevos para cada plan
    mundo = Mundo(
        crear_plan(p),
        localizaciones=[p.deposito, p.loc1, p.loc2],
        drones=[p.dron],
        cajas=[p.caja],
        personas=[p.persona],
        contenidos=[p.comida],
        objetivos=crear_objetivos(p),
    )
    informe = mundo.simulacion_texto()
    print(f"{crear_plan.__name__} - {informe.veredicto}")
