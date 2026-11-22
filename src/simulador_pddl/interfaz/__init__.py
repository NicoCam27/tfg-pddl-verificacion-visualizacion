"""interfaz: Los controles de la simulación visual.

``PanelControl`` es la barra de la parte inferior de la ventana, con los botones
de reproducir, pausar y reiniciar, el deslizador de velocidad y dos líneas de
texto (el recuento de acciones y una línea de estado, con la última acción que
empezó). Importar este paquete importa pygame, así que ``Mundo`` solo importa
el paquete dentro de ``simulacion_visual()``.
"""

from simulador_pddl.interfaz.interfaz import PanelControl

__all__ = ["PanelControl"]
