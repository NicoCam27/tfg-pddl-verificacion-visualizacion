"""ventana: El bucle de la ventana de pygame de la simulación visual."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from simulador_pddl.visualizacion.panel_control import PanelControl
from simulador_pddl.visualizacion.panel_lateral import PanelLateral
from simulador_pddl.visualizacion.renderizador import Renderizador

if TYPE_CHECKING:
    from simulador_pddl.simulacion.simulacion import Simulacion
    from simulador_pddl.visualizacion.panel_control import _ComandoPanel


def _ejecutar_ventana(
    simulacion: Simulacion, ancho: int | None, alto: int | None, titulo: str, fps: int
) -> None:
    """Abre la ventana, ejecuta ``simulacion`` en ella y vuelve al cerrarla.

    Solo la llama ``Mundo.simulacion_visual()``, que ya ha comprobado los
    argumentos. Crea el ``Renderizador``, el ``PanelControl`` y el
    ``PanelLateral``. En cada fotograma, envía cada evento de pygame al
    renderizador (un cambio de tamaño), al panel lateral (su botón) o al panel de
    control (los botones y el deslizador), avanza la simulación el tiempo real
    transcurrido multiplicado por la velocidad del deslizador, y dibuja el mundo y
    los dos paneles. Al terminar, cierra la ventana aunque haya habido una
    excepción.
    """
    renderizador = Renderizador(ancho=ancho, alto=alto, titulo=titulo)
    renderizador._poner_localizaciones(simulacion._localizaciones)

    control = PanelControl(renderizador._ancho, renderizador._alto)
    # El renderizador reserva el alto del panel para no dibujar el mundo debajo.
    renderizador._reservar_panel(control._alto_panel)
    # El panel lateral empieza cerrado, pero su botón ya ocupa la esquina superior
    # derecha del mundo.
    lateral = PanelLateral(renderizador._ancho, renderizador._alto, control._alto_panel)
    renderizador._reservar_panel_lateral(lateral._ancho_ocupado, lateral._ancho_esquina)
    # "Reproducir" se crea activado, pero puede no quedar nada que reproducir
    # (p. ej. si simulacion_texto() ya ejecutó el plan). Se iguala aquí al
    # estado de la simulación para que el primer fotograma ya lo respete.
    control._boton_reproducir._activado = simulacion._puede_reproducir
    reloj = pygame.time.Clock()

    en_curso = True
    try:
        while en_curso:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    en_curso = False
                    break

                # Un cambio de tamaño lo gestiona el renderizador. Después se
                # recolocan los dos paneles, que conservan la velocidad elegida y
                # si el panel lateral está abierto, y el renderizador les reserva
                # su nuevo tamaño, que cambia con el de la ventana.
                if renderizador._gestionar_evento(evento):
                    control._redimensionar(renderizador._ancho, renderizador._alto)
                    renderizador._reservar_panel(control._alto_panel)
                    lateral._redimensionar(
                        renderizador._ancho, renderizador._alto, control._alto_panel
                    )
                    renderizador._reservar_panel_lateral(
                        lateral._ancho_ocupado, lateral._ancho_esquina
                    )
                    continue

                # Al abrir o cerrar el panel lateral, cambia el ancho del mundo.
                if lateral._gestionar_evento(evento):
                    renderizador._reservar_panel_lateral(
                        lateral._ancho_ocupado, lateral._ancho_esquina
                    )
                    continue

                _aplicar_comando(simulacion, control._gestionar_evento(evento))

            # El break anterior solo sale del for: este sale también del while,
            # sin actualizar ni dibujar otro fotograma.
            if not en_curso:
                break

            # tick() espera lo necesario para no pasar de fps y devuelve los
            # milisegundos reales desde el fotograma anterior. Se usa tiempo real
            # para que solo el deslizador acelere o frene la simulación.
            dt = reloj.tick(fps) / 1000.0

            simulacion._velocidad = control._deslizador._valor
            simulacion._actualizar(dt)

            # "Reproducir" se atenúa cuando no hay nada que reproducir (el plan ha
            # terminado o ha fallado una acción), para que se vea sin pulsarlo.
            control._boton_reproducir._activado = simulacion._puede_reproducir

            renderizador._dibujar(simulacion)
            control._dibujar(renderizador._pantalla, simulacion)
            lateral._dibujar(renderizador._pantalla, simulacion)

            pygame.display.flip()
    finally:
        renderizador._cerrar()


def _aplicar_comando(simulacion: Simulacion, comando: _ComandoPanel | None) -> None:
    """Aplica el comando de un botón del panel de control, si lo hay.

    ``"reproducir"`` solo llega si queda algo que reproducir: en otro caso, el
    botón está desactivado.
    """
    if comando == "reproducir":
        simulacion._reproducir()
    elif comando == "pausar":
        simulacion._pausar()
    elif comando == "reiniciar":
        # Es lo mismo que hace Mundo.reiniciar(): si un día hiciera algo más,
        # habría que hacerlo también aquí.
        simulacion._reiniciar()
