"""objetos: Los objetos del dominio de logística con drones.

Un problema se compone de estos objetos:

    Localizacion: un lugar. Dos localizaciones con el mismo nombre son iguales.
    Dron: se mueve entre localizaciones, llevando lo que sujetan sus brazos.
    Brazo: pertenece a un dron. Sujeta una caja o lleva un transportador.
    Caja: tiene un contenido (p. ej. ``"comida"``) que una persona puede necesitar.
    Persona: está en una localización y necesita el contenido de algunas cajas.
    Transportador: guarda cajas y puede ir sujeto por el brazo de un dron.

Una ``Localizacion`` se compara por nombre, mientras que el resto de objetos se
comparan por identidad. ``ObjetoDominio`` es el tipo de cualquiera de ellos.
"""

from simulador_pddl.objetos.brazo import Brazo
from simulador_pddl.objetos.caja import Caja
from simulador_pddl.objetos.dron import Dron
from simulador_pddl.objetos.localizacion import Localizacion
from simulador_pddl.objetos.persona import Persona
from simulador_pddl.objetos.transportador import Transportador

# Cualquier objeto del dominio (lo usan las acciones, los objetivos y la simulación).
type ObjetoDominio = Brazo | Caja | Dron | Localizacion | Persona | Transportador

__all__ = [
    "Brazo",
    "Caja",
    "Dron",
    "Localizacion",
    "ObjetoDominio",
    "Persona",
    "Transportador",
]
