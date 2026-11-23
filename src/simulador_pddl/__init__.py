"""simulador_pddl: Simula, verifica y visualiza planes de logística con drones.

La biblioteca ejecuta sobre los objetos de un problema un plan generado por un
planificador PDDL, clásico (una secuencia de pasos) o temporal (acciones con
inicio y duración), escrito como una lista de acciones de esta biblioteca
(véase ``simulador_pddl.acciones``). Informa de si el plan se puede ejecutar y
de si logra los objetivos del problema, en la terminal o en una ventana de
pygame.

Todo lo que necesita un usuario se puede importar desde aquí:
    Objetos: Localizacion, Dron, Brazo, Caja, Contenido, Persona, Transportador.
    Acciones: Mover, CogerCaja, EntregarCaja, Soltar, CogerTransportador,
        SoltarTransportador, MoverTransportador, PonerCajaEnTransportador,
        SacarCajaDeTransportador.
    Objetivos: PersonaTieneContenido, DronEnLocalizacion,
        TransportadorEnLocalizacion.
    Mundo: ejecuta un plan y devuelve su informe, con el veredicto.
    Informe: InformeVerificacion (lo devuelve ``Mundo``) y EstadoObjetivo (el
        estado de cada objetivo en el informe).
``Accion`` y ``Objetivo`` son las clases base abstractas de las acciones y los
objetivos.

Ejemplo:
    from simulador_pddl import (
        Brazo, Caja, CogerCaja, Contenido, Dron, EntregarCaja, Localizacion,
        Mover, Mundo, Persona, PersonaTieneContenido,
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
    objetivos = [PersonaTieneContenido(persona1, comida)]

    mundo = Mundo(
        acciones,
        localizaciones=[deposito, localizacion1],
        drones=[dron1],
        cajas=[caja1],
        personas=[persona1],
        contenidos=[comida],
        objetivos=objetivos,
    )
    informe = mundo.simulacion_texto()
    print(informe.veredicto)  # VÁLIDO
"""

from simulador_pddl.acciones import (
    Accion,
    CogerCaja,
    CogerTransportador,
    EntregarCaja,
    Mover,
    MoverTransportador,
    PonerCajaEnTransportador,
    SacarCajaDeTransportador,
    Soltar,
    SoltarTransportador,
)
from simulador_pddl.mundo import Mundo
from simulador_pddl.objetivos import (
    DronEnLocalizacion,
    Objetivo,
    PersonaTieneContenido,
    TransportadorEnLocalizacion,
)
from simulador_pddl.objetos import (
    Brazo,
    Caja,
    Contenido,
    Dron,
    Localizacion,
    Persona,
    Transportador,
)
from simulador_pddl.simulacion import EstadoObjetivo, InformeVerificacion

__all__ = [
    "Accion",
    "Brazo",
    "Caja",
    "CogerCaja",
    "CogerTransportador",
    "Contenido",
    "Dron",
    "DronEnLocalizacion",
    "EntregarCaja",
    "EstadoObjetivo",
    "InformeVerificacion",
    "Localizacion",
    "Mover",
    "MoverTransportador",
    "Mundo",
    "Objetivo",
    "Persona",
    "PersonaTieneContenido",
    "PonerCajaEnTransportador",
    "SacarCajaDeTransportador",
    "Soltar",
    "SoltarTransportador",
    "Transportador",
    "TransportadorEnLocalizacion",
]
