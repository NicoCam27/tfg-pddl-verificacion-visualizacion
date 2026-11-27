"""mundo: El punto de entrada de la biblioteca.

``Mundo`` recibe un plan, los objetos de un problema y sus objetivos. Al
construirlo comprueba que el plan y el problema están bien formados (ver
``Mundo``), y lanza una excepción si no lo están, antes de ejecutar nada.
Después ejecuta el plan en la terminal (``simulacion_texto()``) o en una ventana
de pygame (``simulacion_visual()``). Los dos métodos devuelven el informe del
plan (``InformeVerificacion``), con su veredicto. Un fallo durante la ejecución
no lanza ninguna excepción, sino que queda en el informe. ``avanzar_hasta()``
ejecuta el plan solo hasta un instante dado y devuelve el informe de ese punto,
``verificar()`` devuelve el informe del punto al que haya llegado la ejecución,
sin ejecutar nada más, y ``reiniciar()`` vuelve al instante 0, con los objetos
como estaban al construir el mundo. Solo se importa pygame cuando se pide una
simulación visual.
"""

from simulador_pddl.mundo.mundo import Mundo

__all__ = ["Mundo"]
