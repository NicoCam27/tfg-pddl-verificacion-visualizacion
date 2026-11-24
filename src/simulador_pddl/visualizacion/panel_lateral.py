from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from simulador_pddl.simulacion.verificacion import InformeVerificacion
from simulador_pddl.visualizacion.panel_control import (
    Boton,
    PanelControl,
    _fuente,
    _truncar,
)

if TYPE_CHECKING:
    from simulador_pddl.simulacion.simulacion import Simulacion

# Un color RGB.
type _Color = tuple[int, int, int]

# Paleta de colores que se usa
_COLOR_FONDO_PANEL = (225, 225, 230)
_COLOR_BORDE_PANEL = (150, 150, 150)
_COLOR_TEXTO = (0, 0, 0)
_COLOR_TEXTO_ESTADO = (255, 255, 255)

# El estado del plan mientras no ha terminado ni ha fallado ninguna acción. No es
# un veredicto: el de un plan sin terminar sería siempre "INCOMPLETO".
_EN_CURSO = "EN CURSO"

# El color de cada estado del plan. "INCOMPLETO" no aparece en la ventana: mientras
# el plan no ha terminado, el estado es "EN CURSO".
_COLORES_ESTADO: dict[str, _Color] = {
    _EN_CURSO: (110, 110, 120),
    InformeVerificacion.VALIDO: (30, 140, 60),
    InformeVerificacion.NO_RESUELVE: (215, 120, 0),
    InformeVerificacion.EJECUTABLE: (50, 100, 200),
    InformeVerificacion.NO_EJECUTABLE: (200, 30, 30),
}

# Espacio entre las líneas de texto del panel, en píxeles
_INTERLINEADO = 6


def _estado_del_plan(informe: InformeVerificacion) -> str:
    """Devuelve el estado del plan que muestra el panel.

    Es ``"EN CURSO"`` mientras el plan no ha terminado y no ha fallado ninguna
    acción. En otro caso, es el veredicto del informe.
    """
    if informe.ejecutable and not informe.completado:
        return _EN_CURSO
    return informe.veredicto


def _texto_objetivos(informe: InformeVerificacion) -> str:
    """Devuelve cuántos objetivos se cumplen, p. ej. ``"Objetivos cumplidos: 1/2"``."""
    if not informe.tiene_objetivos:
        return "Sin objetivos"
    cumplidos = len(informe.objetivos_cumplidos)
    return f"Objetivos cumplidos: {cumplidos}/{len(informe.estados_objetivos)}"


class PanelLateral:
    """PanelLateral es el panel plegable del lado derecho de la ventana.

    Un botón en la esquina superior derecha lo abre y lo cierra. Abierto, ocupa una
    franja a la derecha, encima del panel de control, y el renderizador le deja
    ese ancho libre para no dibujar el mundo debajo. Arriba muestra el tiempo
    simulado, el estado del plan, con su color, y cuántos objetivos se cumplen.

    Args:
        ancho_ventana: El ancho de la ventana, en píxeles.
        alto_ventana: El alto de la ventana, en píxeles.
        alto_panel_control: El alto del panel de control, en píxeles.
    """

    # El panel mide esta parte del ancho de la ventana, entre un mínimo y un
    # máximo, en píxeles.
    _PROPORCION_ANCHO = 0.3
    _ANCHO_MINIMO = 240
    _ANCHO_MAXIMO = 480

    def __init__(
        self, ancho_ventana: int, alto_ventana: int, alto_panel_control: int
    ) -> None:
        self._abierto = False
        self._boton = Boton("Mostrar panel")

        # Los pone _redimensionar(), a partir del tamaño de la ventana.
        self._rectangulo: pygame.Rect
        self._margen: int
        self._fuente_texto: pygame.font.Font
        self._fuente_estado: pygame.font.Font

        self._redimensionar(ancho_ventana, alto_ventana, alto_panel_control)

    def __repr__(self) -> str:
        return f"PanelLateral(abierto={self._abierto!r})"

    def _redimensionar(
        self, ancho_ventana: int, alto_ventana: int, alto_panel_control: int
    ) -> None:
        """Coloca el panel y su botón para una ventana de ese tamaño.

        Las medidas se escalan con el ancho de la ventana, como las del panel de
        control.
        """
        escala = max(
            PanelControl._ESCALA_MINIMA,
            min(
                PanelControl._ESCALA_MAXIMA,
                ancho_ventana / PanelControl._ANCHO_REFERENCIA,
            ),
        )
        self._margen = int(12 * escala)

        ancho_panel = int(
            max(
                self._ANCHO_MINIMO,
                min(self._ANCHO_MAXIMO, ancho_ventana * self._PROPORCION_ANCHO),
            )
        )
        self._rectangulo = pygame.Rect(
            ancho_ventana - ancho_panel,
            0,
            ancho_panel,
            alto_ventana - alto_panel_control,
        )

        ancho_boton = int(150 * escala)
        alto_boton = int(34 * escala)
        tamano_fuente_boton = int(21 * escala)
        tamano_fuente_texto = int(21 * escala)
        tamano_fuente_estado = int(26 * escala)

        self._boton._colocar(
            ancho_ventana - self._margen - ancho_boton,
            self._margen,
            ancho_boton,
            alto_boton,
            tamano_fuente_boton,
        )

        self._fuente_texto = _fuente(tamano_fuente_texto)
        self._fuente_estado = _fuente(tamano_fuente_estado)

    @property
    def _ancho_ocupado(self) -> int:
        """El ancho que ocupa el panel, en píxeles: 0 si está cerrado."""
        return self._rectangulo.width if self._abierto else 0

    @property
    def _ancho_esquina(self) -> int:
        """El ancho que ocupa el botón sobre el mundo, en píxeles.

        Con el panel cerrado, el botón queda encima del mundo, en la esquina
        superior derecha. Con el panel abierto, queda dentro del panel, así que es 0.
        """
        if self._abierto:
            return 0
        return self._boton._rectangulo.width + 2 * self._margen

    def _gestionar_evento(self, evento: pygame.event.Event) -> bool:
        """Abre o cierra el panel si ``evento`` pulsa su botón.

        Returns:
            ``True`` si el panel se ha abierto o cerrado, ``False`` en otro caso.
        """
        if not self._boton._pulsado(evento):
            return False

        self._abierto = not self._abierto
        self._boton._texto = "Ocultar panel" if self._abierto else "Mostrar panel"
        return True

    def _dibujar(self, pantalla: pygame.Surface, simulacion: Simulacion) -> None:
        """Dibuja el botón y, si el panel está abierto, el panel y su cabecera."""
        if self._abierto:
            self._dibujar_panel(pantalla, simulacion)
        self._boton._dibujar(pantalla)

    def _dibujar_panel(self, pantalla: pygame.Surface, simulacion: Simulacion) -> None:
        """Dibuja el fondo del panel y la cabecera: tiempo, estado y objetivos."""
        pygame.draw.rect(pantalla, _COLOR_FONDO_PANEL, self._rectangulo)
        pygame.draw.line(
            pantalla,
            _COLOR_BORDE_PANEL,
            self._rectangulo.topleft,
            self._rectangulo.bottomleft,
            2,
        )

        informe = simulacion._crear_informe()
        x = self._rectangulo.x + self._margen
        ancho_texto = self._rectangulo.width - 2 * self._margen
        # La altura a la que se dibuja el siguiente elemento: cada uno la baja
        # hasta debajo de sí mismo.
        y = self._boton._rectangulo.bottom + self._margen

        # El tiempo simulado.
        y = self._dibujar_linea(pantalla, simulacion._texto_tiempo(), x, y, ancho_texto)
        # El estado del plan.
        y = self._dibujar_estado(pantalla, _estado_del_plan(informe), x, y, ancho_texto)
        # Cuántos objetivos se cumplen.
        self._dibujar_linea(pantalla, _texto_objetivos(informe), x, y, ancho_texto)

    def _dibujar_estado(
        self, pantalla: pygame.Surface, estado: str, x: int, y: int, ancho: int
    ) -> int:
        """Dibuja ``estado`` en blanco sobre su color y devuelve la ``y`` siguiente.

        El recuadro ocupa todo el ``ancho`` y el texto va centrado dentro.
        """
        texto = self._fuente_estado.render(
            _truncar(self._fuente_estado, estado, ancho - 2 * self._margen),
            True,
            _COLOR_TEXTO_ESTADO,
        )
        fondo = pygame.Rect(x, y, ancho, texto.get_height() + self._margen)
        pygame.draw.rect(pantalla, _COLORES_ESTADO[estado], fondo, border_radius=6)
        pantalla.blit(texto, texto.get_rect(center=fondo.center))
        return fondo.bottom + _INTERLINEADO

    def _dibujar_linea(
        self, pantalla: pygame.Surface, texto: str, x: int, y: int, ancho: int
    ) -> int:
        """Dibuja una línea de texto en ``(x, y)`` y devuelve la ``y`` siguiente."""
        superficie = self._fuente_texto.render(
            _truncar(self._fuente_texto, texto, ancho), True, _COLOR_TEXTO
        )
        pantalla.blit(superficie, (x, y))
        return y + superficie.get_height() + _INTERLINEADO
