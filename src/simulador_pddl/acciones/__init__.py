"""acciones: Las acciones del dominio de logística con drones.

Cada clase es una acción PDDL. Una acción la realiza un dron, empieza en
``inicio_sim`` y dura ``duracion_sim``. Sus efectos se aplican en dos fases,
como en una acción durativa de PDDL: ``at start`` (se comprueban sus condiciones
y se reservan los recursos que usa, si los hay) y ``at end`` (los efectos
finales). Un plan es una lista de acciones, que se pasa a ``Mundo`` junto con
los objetos y los objetivos.

Un plan clásico (una secuencia de pasos sin tiempos) se escribe numerando sus
pasos desde 0: la acción del paso ``i`` tiene ``inicio_sim=i`` y ``duracion_sim=1``.
Como sus acciones no se solapan, aplicar los efectos en dos fases produce el mismo
estado que aplicarlos a la vez, y el veredicto es el del plan clásico.

Acciones disponibles:
    Mover, CogerCaja, EntregarCaja, Soltar,
    CogerTransportador, SoltarTransportador, MoverTransportador,
    PonerCajaEnTransportador, SacarCajaDeTransportador.
``Accion`` es su clase base abstracta.

``desc`` es opcional: si no se da, se genera una descripción a partir de los
objetos y los tiempos de la acción, p. ej.
``CogerCaja(dron=dron1, brazo=izq, caja=caja1, inicio_sim=0, duracion_sim=1)``.

Ejemplo:
    from simulador_pddl import Mundo
    from simulador_pddl.acciones import CogerCaja, EntregarCaja, Mover
    from simulador_pddl.objetos import (
        Brazo, Caja, Contenido, Dron, Localizacion, Persona,
    )

    deposito = Localizacion("deposito")
    localizacion1 = Localizacion("localizacion1")
    comida = Contenido("comida")
    brazo_izquierdo = Brazo("brazo-izquierdo")
    dron1 = Dron("dron1", deposito, [brazo_izquierdo])
    caja1 = Caja("caja1", deposito, comida)
    persona1 = Persona("persona1", localizacion1, comida)

    acciones = [
        CogerCaja(dron1, brazo_izquierdo, caja1, inicio_sim=0, duracion_sim=1),
        Mover(dron1, deposito, localizacion1, inicio_sim=1, duracion_sim=2),
        EntregarCaja(dron1, brazo_izquierdo, caja1, persona1, inicio_sim=3),
    ]

    mundo = Mundo(
        acciones,
        localizaciones=[deposito, localizacion1],
        drones=[dron1],
        cajas=[caja1],
        personas=[persona1],
        contenidos=[comida],
    )
    informe = mundo.simulacion_texto()
"""

from simulador_pddl.acciones.accion import Accion
from simulador_pddl.acciones.coger_caja import CogerCaja
from simulador_pddl.acciones.coger_transportador import CogerTransportador
from simulador_pddl.acciones.entregar_caja import EntregarCaja
from simulador_pddl.acciones.mover import Mover
from simulador_pddl.acciones.mover_transportador import MoverTransportador
from simulador_pddl.acciones.poner_caja_en_transportador import PonerCajaEnTransportador
from simulador_pddl.acciones.sacar_caja_de_transportador import SacarCajaDeTransportador
from simulador_pddl.acciones.soltar import Soltar
from simulador_pddl.acciones.soltar_transportador import SoltarTransportador

__all__ = [
    "Accion",
    "CogerCaja",
    "CogerTransportador",
    "EntregarCaja",
    "Mover",
    "MoverTransportador",
    "PonerCajaEnTransportador",
    "SacarCajaDeTransportador",
    "Soltar",
    "SoltarTransportador",
]
