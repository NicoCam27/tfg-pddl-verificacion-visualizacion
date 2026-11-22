"""renderizado: El dibujo de la simulación visual.

``Renderizador`` dibuja en una ventana de pygame las localizaciones, los drones,
las cajas, las personas y los transportadores de una ``Simulacion``, el mensaje
de error si falla una acción y, al pasar el ratón por encima de las cajas, los
transportadores o las personas, una ayuda con sus detalles. Importar este
paquete importa pygame, así que ``Mundo`` solo importa el paquete dentro de
``simulacion_visual()``.
"""

from simulador_pddl.renderizado.renderizador import Renderizador

__all__ = ["Renderizador"]
