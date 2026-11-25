"""visualizacion: La ventana de pygame de la simulación visual.

``Renderizador`` dibuja en la ventana las localizaciones, los drones, las cajas,
las personas y los transportadores de una ``Simulacion``, el mensaje de error si
falla una acción y, al pasar el ratón por encima de las cajas, los
transportadores o las personas, una ayuda con sus detalles. ``PanelControl`` es
la barra de la parte inferior de la ventana, con los botones de reproducir,
pausar y reiniciar, el deslizador de velocidad y dos líneas de texto (el
recuento de acciones y una línea de estado, con la última acción que empezó).
``PanelLateral`` es el panel plegable del lado derecho, que se abre con un botón
en la esquina superior derecha y muestra el tiempo simulado, el estado del plan,
cuántos objetivos se cumplen y dos pestañas: las acciones del plan, que se pueden
pulsar para saltar a su inicio, y los objetivos. ``ventana.py`` tiene el bucle
de la ventana, que crea los tres, reparte los eventos, avanza la simulación y
dibuja cada fotograma. Lo llama ``Mundo.simulacion_visual()``.

Importar este paquete importa pygame, así que ``Mundo`` solo importa el paquete
dentro de ``simulacion_visual()``.
"""

from simulador_pddl.visualizacion.panel_control import PanelControl
from simulador_pddl.visualizacion.panel_lateral import PanelLateral
from simulador_pddl.visualizacion.renderizador import Renderizador

__all__ = ["PanelControl", "PanelLateral", "Renderizador"]
