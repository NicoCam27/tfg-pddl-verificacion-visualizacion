"""mundo: El punto de entrada de la biblioteca.

``Mundo`` recibe un plan, los objetos de un problema y sus objetivos. Al
construirlo comprueba lo que se puede comprobar sin ejecutar el plan, y lanza
una excepción si algo falla. Después ejecuta el plan en la terminal
(``simulacion_texto()``) o en una ventana de pygame (``simulacion_visual()``).
Los dos métodos devuelven el informe del plan (``InformeVerificacion``), con su
veredicto; un fallo durante la ejecución no lanza ninguna excepción, sino que
queda en el informe. ``verificar()`` devuelve el informe del punto al que haya
llegado la ejecución, sin ejecutar nada más, y ``reiniciar()`` vuelve al
instante 0, con los objetos como estaban al construir el mundo. Solo se importa
pygame cuando se pide una simulación visual.
"""

from simulador_pddl.mundo.mundo import Mundo

__all__ = ["Mundo"]
