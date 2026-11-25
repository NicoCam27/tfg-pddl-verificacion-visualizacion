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
    from simulador_pddl.simulacion.verificacion import EstadoObjetivo

# Un color RGB.
type _Color = tuple[int, int, int]

# Paleta de colores que se usa
_COLOR_FONDO_PANEL = (225, 225, 230)
_COLOR_BORDE_PANEL = (150, 150, 150)
_COLOR_TEXTO = (0, 0, 0)
_COLOR_TEXTO_DETALLE = (80, 80, 85)
_COLOR_TEXTO_ESTADO = (255, 255, 255)
_COLOR_BARRA_LISTA = (200, 200, 205)
_COLOR_MANDO_LISTA = (130, 130, 140)

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

# Cómo va cada objetivo, que se muestra con su color. Un objetivo que todavía no
# se ha cumplido no cuenta como no logrado mientras el plan sigue en curso: está
# pendiente hasta que el plan termina o falla.
_PENDIENTE = "pendiente"
_CUMPLIDO = "cumplido"
_ROTO = "roto"
_NO_LOGRADO = "no logrado"

_COLORES_OBJETIVO: dict[str, _Color] = {
    _PENDIENTE: (150, 150, 155),
    _CUMPLIDO: (30, 140, 60),
    _ROTO: (215, 120, 0),
    _NO_LOGRADO: (200, 30, 30),
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


def _clase_objetivo(estado: EstadoObjetivo, informe: InformeVerificacion) -> str:
    """Devuelve cómo va un objetivo: pendiente, cumplido, roto o no logrado.

    Un objetivo que se cumple está cumplido, y uno que se cumplió y después se
    deshizo está roto, aunque el plan haya terminado. Uno que nunca se ha cumplido
    está pendiente mientras el plan sigue en curso, y no logrado cuando termina o
    falla.
    """
    if estado.cumplido:
        return _CUMPLIDO
    if estado.roto_en is not None:
        return _ROTO
    if _estado_del_plan(informe) == _EN_CURSO:
        return _PENDIENTE
    return _NO_LOGRADO


def _detalles_objetivo(estado: EstadoObjetivo, clase: str) -> list[str]:
    """Devuelve las líneas que se muestran debajo de un objetivo.

    La primera dice cuándo se cumplió o se rompió. Si no se cumple, la segunda dice
    por qué, con lo que pasa ahora en el mundo.
    """
    if clase == _PENDIENTE:
        tiempos = "todavía no se ha cumplido"
    else:
        tiempos = estado._texto_tiempos()
    detalles = [_con_mayuscula(tiempos)]

    if estado.explicacion_fallo is not None:
        detalles.append(f"Ahora: {estado.explicacion_fallo}")
    return detalles


def _con_mayuscula(texto: str) -> str:
    """Devuelve ``texto`` con la primera letra en mayúscula."""
    return texto[:1].upper() + texto[1:]


def _partir_en_lineas(fuente: pygame.font.Font, texto: str, ancho: int) -> list[str]:
    """Parte ``texto`` en líneas de ``ancho`` píxeles como mucho, por palabras.

    Una palabra que no cabe sola en una línea se acorta con ``_truncar()``.
    """
    lineas: list[str] = []
    linea = ""
    for palabra in texto.split():
        candidata = f"{linea} {palabra}" if linea else palabra
        if fuente.size(candidata)[0] <= ancho:
            linea = candidata
            continue
        if linea:
            lineas.append(linea)
        linea = _truncar(fuente, palabra, ancho)
    if linea:
        lineas.append(linea)
    return lineas


class PanelLateral:
    """PanelLateral es el panel plegable del lado derecho de la ventana.

    Un botón en la esquina superior derecha lo abre y lo cierra. Abierto, ocupa una
    franja a la derecha, encima del panel de control, y el renderizador le deja
    ese ancho libre para no dibujar el mundo debajo. Arriba muestra el tiempo
    simulado, el estado del plan, con su color, y cuántos objetivos se cumplen.
    Debajo, la lista de objetivos: cada uno con el color de cómo va, cuándo se
    cumplió o se rompió y, si no se cumple, por qué. Cuando la lista no cabe, se
    desplaza con la rueda del ratón o con la barra de su derecha, que se puede
    pulsar para saltar a un punto o arrastrar.

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

        # Cuántos píxeles se ha desplazado la lista hacia arriba, con la rueda del
        # ratón o con la barra, y si se está arrastrando la barra. Los pone
        # _dibujar_panel(): la zona donde se dibuja la lista, la de su barra y lo
        # que mide la lista entera, que dependen de lo que se dibuja encima.
        self._desplazamiento = 0
        self._arrastrando = False
        self._zona_lista = pygame.Rect(0, 0, 0, 0)
        self._barra_lista = pygame.Rect(0, 0, 0, 0)
        self._alto_lista = 0

        # Los pone _redimensionar(), a partir del tamaño de la ventana.
        self._rectangulo: pygame.Rect
        self._margen: int
        self._paso_desplazamiento: int
        self._ancho_barra: int
        self._fuente_texto: pygame.font.Font
        self._fuente_detalle: pygame.font.Font
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
        self._paso_desplazamiento = int(40 * escala)
        self._ancho_barra = max(6, int(10 * escala))

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
        tamano_fuente_detalle = int(18 * escala)
        tamano_fuente_estado = int(26 * escala)

        self._boton._colocar(
            ancho_ventana - self._margen - ancho_boton,
            self._margen,
            ancho_boton,
            alto_boton,
            tamano_fuente_boton,
        )

        self._fuente_texto = _fuente(tamano_fuente_texto)
        self._fuente_detalle = _fuente(tamano_fuente_detalle)
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

        Con el panel abierto, la rueda del ratón sobre la lista la desplaza, y un
        clic izquierdo en su barra la lleva a ese punto. Si se mantiene pulsado, la
        lista sigue al ratón hasta que se suelta, aunque se salga de la barra.

        Returns:
            ``True`` si el panel se ha abierto o cerrado, que es cuando cambia el
            ancho que ocupa, ``False`` en otro caso.
        """
        if self._boton._pulsado(evento):
            self._abierto = not self._abierto
            self._boton._texto = "Ocultar panel" if self._abierto else "Mostrar panel"
            self._arrastrando = False
            return True

        clic_izquierdo = (
            evento.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)
            and evento.button == pygame.BUTTON_LEFT
        )
        if (
            clic_izquierdo
            and evento.type == pygame.MOUSEBUTTONDOWN
            and self._abierto
            and self._lista_desborda
            and self._barra_lista.collidepoint(evento.pos)
        ):
            self._arrastrando = True
            self._saltar_a(evento.pos[1])
        elif clic_izquierdo and evento.type == pygame.MOUSEBUTTONUP:
            self._arrastrando = False
        elif (
            evento.type == pygame.MOUSEMOTION
            and self._arrastrando
            # Mientras se arrastra, el plan sigue avanzando, y la lista puede
            # encoger hasta caber y quedarse sin barra.
            and self._lista_desborda
        ):
            self._saltar_a(evento.pos[1])
        elif (
            self._abierto
            and evento.type == pygame.MOUSEWHEEL
            and self._zona_lista.collidepoint(pygame.mouse.get_pos())
        ):
            # La rueda hacia arriba da un valor positivo, y sube la lista hacia
            # su principio.
            self._desplazar(-evento.y * self._paso_desplazamiento)
        return False

    def _desplazar(self, pixeles: int) -> None:
        """Desplaza la lista ``pixeles`` hacia arriba, sin salirse de ella."""
        self._desplazamiento = max(
            0, min(self._desplazamiento_maximo, self._desplazamiento + pixeles)
        )

    def _saltar_a(self, y: int) -> None:
        """Desplaza la lista para que el mando de su barra quede centrado en ``y``.

        Solo se llama cuando la lista no cabe en su zona, así que el mando es más
        corto que la barra y tiene recorrido.
        """
        mando = self._mando_lista
        recorrido = self._barra_lista.height - mando.height
        # Dónde quedaría el borde de arriba del mando con su centro en ``y``, como
        # fracción de su recorrido: 0 arriba del todo y 1 abajo del todo.
        fraccion = (y - self._barra_lista.y - mando.height / 2) / recorrido
        # Un clic cerca de un extremo de la barra, o un arrastre fuera de ella, da
        # una fracción menor que 0 o mayor que 1, y se lleva al extremo más cercano.
        fraccion = max(0.0, min(1.0, fraccion))
        # La lista baja la misma fracción de su desplazamiento máximo. Es lo contrario
        # de ``_mando_lista``, que sitúa el mando a partir del desplazamiento.
        self._desplazamiento = round(fraccion * self._desplazamiento_maximo)

    @property
    def _desplazamiento_maximo(self) -> int:
        """Lo que sobra de la lista por debajo de su zona, en píxeles: 0 si cabe."""
        return max(0, self._alto_lista - self._zona_lista.height)

    @property
    def _lista_desborda(self) -> bool:
        """Si la lista no cabe entera en su zona, y por eso tiene barra."""
        return self._desplazamiento_maximo > 0

    @property
    def _mando_lista(self) -> pygame.Rect:
        """El mando de la barra de la lista, en la posición del desplazamiento.

        La parte de la barra que ocupa es la misma que la parte de la lista que se ve:
        si se ve la mitad de la lista, el mando mide la mitad de la barra. Tiene un alto
        mínimo para que se pueda pulsar. Solo tiene sentido cuando la lista no cabe en
        su zona.
        """
        barra = self._barra_lista
        # El mando ocupa de la barra la misma fracción que la zona ocupa de la lista,
        # pero nunca menos de dos anchos de barra. Se multiplica antes de dividir
        # porque, con la división entera, la fracción sola daría 0.
        alto = max(
            self._ancho_barra * 2,
            barra.height * self._zona_lista.height // self._alto_lista,
        )
        # Lo que el mando puede bajar dentro de la barra. Baja la misma fracción de
        # ese recorrido que la lista ha bajado de su desplazamiento máximo.
        recorrido = barra.height - alto
        y = barra.y + recorrido * self._desplazamiento // self._desplazamiento_maximo
        return pygame.Rect(barra.x, y, barra.width, alto)

    def _dibujar(self, pantalla: pygame.Surface, simulacion: Simulacion) -> None:
        """Dibuja el botón y, si el panel está abierto, el panel y su cabecera."""
        if self._abierto:
            self._dibujar_panel(pantalla, simulacion)
        self._boton._dibujar(pantalla)

    def _dibujar_panel(self, pantalla: pygame.Surface, simulacion: Simulacion) -> None:
        """Dibuja el fondo del panel, la cabecera y la lista de objetivos."""
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
        y = self._dibujar_linea(pantalla, _texto_objetivos(informe), x, y, ancho_texto)

        # La lista de objetivos ocupa el resto del panel, salvo una franja a la
        # derecha para su barra. Solo se dibuja dentro de su zona, así que lo que
        # queda fuera al desplazarla no se ve. La franja se reserva siempre, aunque
        # la lista quepa y no haya barra: si dependiera de eso, al aparecer la barra
        # la lista se estrecharía, sus líneas se partirían de otra forma y podría
        # dejar de necesitarla.
        alto_zona = self._rectangulo.bottom - self._margen - y
        separacion = self._margen // 2
        self._zona_lista = pygame.Rect(
            x, y, ancho_texto - self._ancho_barra - separacion, alto_zona
        )
        self._barra_lista = pygame.Rect(
            self._zona_lista.right + separacion, y, self._ancho_barra, alto_zona
        )
        pantalla.set_clip(self._zona_lista)
        y_objetivo = self._zona_lista.y - self._desplazamiento
        for estado in informe.estados_objetivos:
            y_objetivo = self._dibujar_objetivo(
                pantalla, estado, _clase_objetivo(estado, informe), x, y_objetivo
            )
        pantalla.set_clip(None)

        # Lo que mide la lista cambia con la ejecución: si ha encogido, el
        # desplazamiento se ajusta para que no quede espacio vacío abajo.
        self._alto_lista = y_objetivo + self._desplazamiento - self._zona_lista.y
        self._desplazar(0)

        if self._lista_desborda:
            radio = self._ancho_barra // 2
            pygame.draw.rect(
                pantalla, _COLOR_BARRA_LISTA, self._barra_lista, border_radius=radio
            )
            pygame.draw.rect(
                pantalla, _COLOR_MANDO_LISTA, self._mando_lista, border_radius=radio
            )

    def _dibujar_objetivo(
        self,
        pantalla: pygame.Surface,
        estado: EstadoObjetivo,
        clase: str,
        x: int,
        y: int,
    ) -> int:
        """Dibuja un objetivo de la lista y devuelve la ``y`` del siguiente.

        A la izquierda, un cuadrado del color de cómo va. A su derecha, lo que
        exige el objetivo y, debajo, en letra más pequeña, sus detalles.
        """
        lado = self._fuente_texto.get_height()
        pygame.draw.rect(
            pantalla, _COLORES_OBJETIVO[clase], (x, y, lado, lado), border_radius=3
        )

        x_texto = x + lado + self._margen // 2
        ancho = self._zona_lista.right - x_texto
        lineas = [
            (self._fuente_texto, _COLOR_TEXTO, linea)
            for linea in _partir_en_lineas(
                self._fuente_texto, _con_mayuscula(estado.objetivo._describir()), ancho
            )
        ]
        for detalle in _detalles_objetivo(estado, clase):
            lineas += [
                (self._fuente_detalle, _COLOR_TEXTO_DETALLE, linea)
                for linea in _partir_en_lineas(self._fuente_detalle, detalle, ancho)
            ]

        for fuente, color, linea in lineas:
            superficie = fuente.render(linea, True, color)
            pantalla.blit(superficie, (x_texto, y))
            y += superficie.get_height()
        return y + self._margen

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
