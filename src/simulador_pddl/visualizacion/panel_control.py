from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import pygame

if TYPE_CHECKING:
    from simulador_pddl.simulacion.simulacion import Simulacion

# Lo que devuelve PanelControl._gestionar_evento() cuando se pulsa un botón.
type _ComandoPanel = Literal["reproducir", "pausar", "reiniciar"]

# Paleta de colores que se usa
_COLOR_TEXTO = (0, 0, 0)
_COLOR_BOTON = (180, 180, 180)
_COLOR_BOTON_DESACTIVADO = (120, 120, 120)
_COLOR_BORDE_BOTON = (0, 0, 0)
_COLOR_BARRA_DESLIZADOR = (50, 50, 50)
_COLOR_MARCA_DESLIZADOR = (110, 110, 110)
_COLOR_MANDO_DESLIZADOR = (70, 130, 255)

# Medidas del botón, en píxeles
_RADIO_ESQUINA_BOTON = 8
_GROSOR_BORDE_BOTON = 2
# Espacio entre la etiqueta y cada lado del botón.
_MARGEN_ETIQUETA_BOTON = 4

# Medidas del deslizador, en píxeles
_GROSOR_BARRA_DESLIZADOR = 4
_GROSOR_MARCA_DESLIZADOR = 1
# Espacio entre el mando y la etiqueta de velocidad.
_SEPARACION_ETIQUETA_DESLIZADOR = 6

# Espacio entre las dos líneas de texto del panel, en píxeles.
_INTERLINEADO_PANEL = 4


def _truncar(fuente: pygame.font.Font, texto: str, ancho_maximo: int) -> str:
    """Devuelve ``texto`` ajustado a ``ancho_maximo`` píxeles de ancho.

    Si es más ancho, se acorta y termina en ``"..."``. Se usa para las etiquetas
    de los botones, para las dos líneas de información del panel (el recuento de
    acciones y la línea de estado) y para el mensaje de error que dibuja el
    ``Renderizador``, que pueden no caber en la ventana.
    """
    if fuente.size(texto)[0] <= ancho_maximo:
        return texto

    while texto and fuente.size(texto + "...")[0] > ancho_maximo:
        texto = texto[:-1]

    return texto + "..."


class Boton:
    """Boton es un botón del panel de control que se puede pulsar.

    Se crea sin posición ni tamaño: ``_colocar()`` se los da antes de dibujarlo.

    Args:
        texto: La etiqueta del botón.
    """

    def __init__(self, texto: str) -> None:
        self._activado = True
        self._texto = texto

        # Los pone _colocar(), a partir del tamaño de la ventana.
        self._rectangulo: pygame.Rect
        self._fuente: pygame.font.Font

    def __repr__(self) -> str:
        return f"Boton({self._texto!r}, activado={self._activado!r})"

    def _colocar(
        self, x: int, y: int, ancho: int, alto: int, tamano_fuente: int
    ) -> None:
        """Da al botón su posición, su tamaño y el tamaño de su etiqueta, en píxeles.

        ``x`` e ``y`` son su esquina superior izquierda, en coordenadas de la ventana.
        """
        self._rectangulo = pygame.Rect(x, y, ancho, alto)
        self._fuente = pygame.font.SysFont(None, tamano_fuente)

    def _dibujar(self, pantalla: pygame.Surface) -> None:
        """Dibuja el botón en ``pantalla``, más oscuro si está desactivado."""
        color = _COLOR_BOTON if self._activado else _COLOR_BOTON_DESACTIVADO

        # Relleno
        pygame.draw.rect(
            pantalla, color, self._rectangulo, border_radius=_RADIO_ESQUINA_BOTON
        )
        # Borde
        pygame.draw.rect(
            pantalla,
            _COLOR_BORDE_BOTON,
            self._rectangulo,
            _GROSOR_BORDE_BOTON,
            border_radius=_RADIO_ESQUINA_BOTON,
        )

        ancho_etiqueta = self._rectangulo.width - 2 * _MARGEN_ETIQUETA_BOTON
        etiqueta = _truncar(self._fuente, self._texto, ancho_etiqueta)
        texto = self._fuente.render(etiqueta, True, _COLOR_TEXTO)

        # Etiqueta, centrada en el botón
        pantalla.blit(texto, texto.get_rect(center=self._rectangulo.center))

    def _pulsado(self, evento: pygame.event.Event) -> bool:
        """Devuelve si ``evento`` es un clic izquierdo dentro del botón.

        Un botón desactivado nunca cuenta como pulsado, así que devuelve ``False``.
        """
        if not self._activado:
            return False

        return (
            evento.type == pygame.MOUSEBUTTONDOWN
            and evento.button == pygame.BUTTON_LEFT
            and self._rectangulo.collidepoint(evento.pos)
        )


class Deslizador:
    """Deslizador es la barra con la que el usuario elige la velocidad de reproducción.

    Ofrece siete velocidades fijas, de 0.25x a 16x, y cada una es el doble de la
    anterior. Empieza en 1x.

    Se crea sin posición ni tamaño: ``_colocar()`` se los da antes de dibujarlo.
    """

    # Las velocidades que se pueden elegir, de la más lenta a la más rápida.
    _VELOCIDADES: tuple[float, ...] = (0.25, 0.5, 1, 2, 4, 8, 16)

    def __init__(self) -> None:
        self._arrastrando = False
        self._indice = self._VELOCIDADES.index(1)  # Empieza en 1x

        # Los pone _colocar(), a partir del tamaño de la ventana.
        self._x: int
        self._y: int
        self._ancho: int
        self._radio: int
        self._fuente: pygame.font.Font

    def __repr__(self) -> str:
        return f"Deslizador(valor={self._valor!r})"

    def _colocar(
        self, x: int, y: int, ancho: int, tamano_fuente: int, radio: int
    ) -> None:
        """Da al deslizador su posición, su longitud, su fuente y el radio del mando.

        ``x`` es el extremo izquierdo de la barra e ``y`` la altura a la que se
        dibuja, en coordenadas de la ventana. ``ancho`` y ``radio`` se expresan en
        píxeles.
        """
        self._x = x
        self._y = y
        self._ancho = ancho
        self._fuente = pygame.font.SysFont(None, tamano_fuente)
        self._radio = radio

    def _dibujar(self, pantalla: pygame.Surface) -> None:
        """Dibuja la barra, una marca por cada velocidad, el mando y la etiqueta."""
        pygame.draw.line(
            pantalla,
            _COLOR_BARRA_DESLIZADOR,
            (self._x, self._y),
            (self._x + self._ancho, self._y),
            _GROSOR_BARRA_DESLIZADOR,
        )

        ancho_tramo = self._ancho_tramo

        # Una marca por velocidad disponible, para que se vea dónde encaja el mando.
        # Cada marca mide lo mismo que el radio del mando, centrada en la barra.
        for indice in range(len(self._VELOCIDADES)):
            x_marca = int(self._x + indice * ancho_tramo)
            pygame.draw.line(
                pantalla,
                _COLOR_MARCA_DESLIZADOR,
                (x_marca, self._y - self._radio // 2),
                (x_marca, self._y + self._radio // 2),
                _GROSOR_MARCA_DESLIZADOR,
            )

        x_mando = self._x + self._indice * ancho_tramo

        # Mando
        pygame.draw.circle(
            pantalla, _COLOR_MANDO_DESLIZADOR, (int(x_mando), self._y), self._radio
        )

        texto = self._fuente.render(f"Velocidad: {self._valor}x", True, _COLOR_TEXTO)

        # Etiqueta con la velocidad
        pantalla.blit(
            texto, (self._x, self._y + self._radio + _SEPARACION_ETIQUETA_DESLIZADOR)
        )

    def _gestionar_evento(self, evento: pygame.event.Event) -> None:
        """Lleva el mando a la velocidad más cercana al pulsar o arrastrar."""
        clic_izquierdo = (
            evento.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)
            and evento.button == pygame.BUTTON_LEFT
        )

        if clic_izquierdo and evento.type == pygame.MOUSEBUTTONDOWN:
            # Un clic en cualquier punto de la barra mueve el mando hasta allí, así
            # que no hace falta acertar en él. La zona de clic deja un margen de un
            # radio del mando alrededor de la barra, para que el mando entero se pueda
            # pulsar, incluso en las puntas.
            x_raton, y_raton = evento.pos
            desplazamiento_y = y_raton - self._y

            limite_izquierdo_zona_clic = self._x - self._radio
            limite_derecho_zona_clic = self._x + self._ancho + self._radio
            en_zona_clic = (
                limite_izquierdo_zona_clic <= x_raton <= limite_derecho_zona_clic
                and abs(desplazamiento_y) <= self._radio
            )

            if en_zona_clic:
                self._arrastrando = True
                self._indice = self._indice_mas_cercano(x_raton)

        elif clic_izquierdo and evento.type == pygame.MOUSEBUTTONUP:
            self._arrastrando = False

        elif evento.type == pygame.MOUSEMOTION and self._arrastrando:
            # Al arrastrar ya no hace falta estar en la zona de clic: el índice solo
            # depende de la posición x del ratón, aunque se aleje de la barra.
            x_raton, _ = evento.pos
            self._indice = self._indice_mas_cercano(x_raton)

    def _indice_mas_cercano(self, x_raton: int) -> int:
        """Devuelve el índice de la velocidad más cercana a ``x_raton``.

        Si ``x_raton`` queda fuera de la barra, cuenta como el extremo más próximo,
        es decir, la velocidad más lenta o la más rápida. Ocurre al pulsar en el margen
        de la zona de clic y al arrastrar el ratón más allá de la barra.
        """
        x = min(max(x_raton, self._x), self._x + self._ancho)
        return round((x - self._x) / self._ancho_tramo)

    @property
    def _ancho_tramo(self) -> float:
        """La distancia en píxeles entre dos velocidades consecutivas de la barra."""
        return self._ancho / (len(self._VELOCIDADES) - 1)

    @property
    def _valor(self) -> float:
        """La velocidad elegida, p. ej. ``2`` para el doble de la velocidad normal."""
        return self._VELOCIDADES[self._indice]


class PanelControl:
    """PanelControl es la barra de controles de la parte inferior de la ventana.

    Tiene los botones de reproducir, pausar y reiniciar, el deslizador de
    velocidad y dos líneas de texto: el recuento de acciones y una línea de
    estado, con la última acción que empezó.

    Args:
        ancho_ventana: El ancho de la ventana, en píxeles.
        alto_ventana: El alto de la ventana, en píxeles.
    """

    # El ancho de la ventana por defecto: con él, el panel se dibuja a su tamaño de
    # diseño (escala 1). Debe coincidir con Renderizador.ANCHO_POR_DEFECTO.
    _ANCHO_REFERENCIA = 1400
    # Límites de la escala, para que el panel se pueda usar en ventanas estrechas y
    # no crezca sin límite en ventanas muy anchas.
    _ESCALA_MINIMA = 0.7
    _ESCALA_MAXIMA = 1.4

    def __init__(self, ancho_ventana: int, alto_ventana: int) -> None:
        # Los controles se crean sin posición ni tamaño: _redimensionar() los coloca.
        self._boton_reproducir = Boton("Reproducir")
        self._boton_pausa = Boton("Pausa")
        self._boton_reiniciar = Boton("Reiniciar")

        self._deslizador = Deslizador()

        # Los pone _redimensionar(), a partir del tamaño de la ventana.
        self._ancho: int
        self._alto: int
        self._fuente_info: pygame.font.Font
        self._margen_info: int
        self._alto_linea_info: int
        self._alto_panel: int

        self._redimensionar(ancho_ventana, alto_ventana)

    def __repr__(self) -> str:
        return f"PanelControl(ancho={self._ancho!r}, alto={self._alto!r})"

    def _redimensionar(self, ancho_ventana: int, alto_ventana: int) -> None:
        """Coloca los controles y las líneas de texto para una ventana de ese tamaño.

        Lo llama ``__init__()`` y, después, ``_ejecutar_ventana()`` cada vez que
        cambia el tamaño de la ventana. Las medidas se escalan con el ancho de la
        ventana. Los botones miden su ancho de diseño escalado, y el deslizador
        ocupa el resto del ancho.

        La ventana mide al menos ``Renderizador.ANCHO_MINIMO`` de ancho, así que
        los controles no necesitan un ancho mínimo propio: incluso con ese ancho,
        la etiqueta más larga cabe en su botón y cada tramo del deslizador mide más
        de 24 píxeles, el tamaño mínimo de un objetivo de clic que recomienda
        WCAG 2.2.
        """
        self._ancho = ancho_ventana
        self._alto = alto_ventana

        # La escala es el ancho de la ventana respecto al de referencia (1 con la
        # ventana por defecto).
        escala = max(
            self._ESCALA_MINIMA,
            min(self._ESCALA_MAXIMA, self._ancho / self._ANCHO_REFERENCIA),
        )

        # Cada medida es su valor de diseño (a escala 1) multiplicado por la escala.
        # Todas están en píxeles salvo los tamaños de fuente: el texto dibujado es más
        # bajo, y su alto real lo da get_height() (por eso se usa en _alto_linea_info).
        margen_lateral = int(20 * escala)
        separacion_botones = int(12 * escala)
        ancho_boton = int(140 * escala)
        alto_boton = int(40 * escala)
        tamano_fuente_botones = int(23 * escala)
        # Del borde superior de los botones al borde inferior de la ventana.
        alto_franja_botones = int(62 * escala)
        separacion_botones_deslizador = int(34 * escala)
        tamano_fuente_deslizador = int(20 * escala)
        radio_mando = int(10 * escala)
        tamano_fuente_info = int(21 * escala)

        # Botones: los tres seguidos, desde el margen izquierdo, a la misma altura.
        y_botones = self._alto - alto_franja_botones

        x_reproducir = margen_lateral
        x_pausa = x_reproducir + ancho_boton + separacion_botones
        x_reiniciar = x_pausa + ancho_boton + separacion_botones

        for boton, x_boton in (
            (self._boton_reproducir, x_reproducir),
            (self._boton_pausa, x_pausa),
            (self._boton_reiniciar, x_reiniciar),
        ):
            boton._colocar(
                x_boton, y_botones, ancho_boton, alto_boton, tamano_fuente_botones
            )

        # Deslizador: ocupa lo que queda a la derecha de los botones, hasta el margen
        # derecho, con la barra a media altura de los botones.
        x_deslizador = x_reiniciar + ancho_boton + separacion_botones_deslizador
        ancho_deslizador = self._ancho - x_deslizador - margen_lateral
        y_deslizador = y_botones + alto_boton // 2

        self._deslizador._colocar(
            x_deslizador,
            y_deslizador,
            ancho_deslizador,
            tamano_fuente=tamano_fuente_deslizador,
            radio=radio_mando,
        )

        # Líneas de texto: _dibujar() las pone justo encima de los botones, con el
        # mismo margen izquierdo.
        self._fuente_info = pygame.font.SysFont(None, tamano_fuente_info)
        self._margen_info = margen_lateral
        self._alto_linea_info = self._fuente_info.get_height() + _INTERLINEADO_PANEL

        # El alto del panel, desde el borde inferior de la ventana: los botones y
        # las dos líneas de texto que tienen encima. El renderizador lo reserva para
        # no dibujar el mundo debajo.
        self._alto_panel = alto_franja_botones + 2 * self._alto_linea_info

    def _dibujar(self, pantalla: pygame.Surface, simulacion: Simulacion) -> None:
        """Dibuja los controles, el recuento de acciones y la línea de estado."""
        # Cada control se dibuja a sí mismo, en el sitio que le dio _colocar().
        self._boton_reproducir._dibujar(pantalla)
        self._boton_pausa._dibujar(pantalla)
        self._boton_reiniciar._dibujar(pantalla)
        self._deslizador._dibujar(pantalla)

        # Dos líneas de texto justo encima de los botones: arriba el recuento de
        # acciones y, debajo, la línea de estado. Si no caben entre los dos márgenes
        # laterales, se cortan con "...".
        ancho_texto = self._ancho - 2 * self._margen_info
        y_botones = self._boton_reproducir._rectangulo.y

        lineas = (
            (
                simulacion._texto_recuento_acciones(),
                y_botones - 2 * self._alto_linea_info,
            ),
            (simulacion._texto_estado, y_botones - self._alto_linea_info),
        )
        for texto, y_linea in lineas:
            linea = self._fuente_info.render(
                _truncar(self._fuente_info, texto, ancho_texto), True, _COLOR_TEXTO
            )
            pantalla.blit(linea, (self._margen_info, y_linea))

    def _gestionar_evento(self, evento: pygame.event.Event) -> _ComandoPanel | None:
        """Gestiona ``evento`` y devuelve el comando del botón pulsado, si lo hay.

        El deslizador cambia la velocidad por su cuenta, y ``_ejecutar_ventana()``
        lee en cada fotograma la velocidad elegida. Los botones, en cambio, no
        actúan sobre la simulación: solo dicen qué se ha pulsado, y
        ``_aplicar_comando()`` lo aplica.

        Returns:
            ``"reproducir"``, ``"pausar"`` o ``"reiniciar"`` si ``evento`` pulsa ese
            botón, o ``None`` en cualquier otro caso.
        """
        # El deslizador recibe todos los eventos, porque un arrastre sigue aunque el
        # ratón salga de la barra.
        self._deslizador._gestionar_evento(evento)

        # Los botones no se solapan, así que un clic solo puede caer en uno de ellos:
        # basta con devolver el primero que se haya pulsado.
        if self._boton_reproducir._pulsado(evento):
            return "reproducir"

        if self._boton_pausa._pulsado(evento):
            return "pausar"

        if self._boton_reiniciar._pulsado(evento):
            return "reiniciar"

        return None
