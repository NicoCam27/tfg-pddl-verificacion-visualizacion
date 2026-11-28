from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from simulador_pddl.acciones import Mover, MoverTransportador
from simulador_pddl.objetos import Caja
from simulador_pddl.visualizacion.panel_control import _truncar

if TYPE_CHECKING:
    from simulador_pddl.objetos import Dron, Localizacion, Persona, Transportador
    from simulador_pddl.simulacion.simulacion import Simulacion

# Una línea de la ayuda emergente: un solo texto, o un par (izquierda, derecha)
# que se dibuja en dos columnas.
type _LineaAyuda = str | tuple[str, str | None]

# Dónde se dibuja cada dron y cada transportador, en coordenadas de la ventana.
type _PosicionesDibujo = dict[Dron | Transportador, tuple[float, float]]

# Un color RGB.
# Paleta de colores que se usa
_COLOR_FONDO = (240, 240, 240)
_COLOR_LOCALIZACION = (80, 80, 80)
_COLOR_TEXTO_LOCALIZACION = (255, 255, 255)
_COLOR_CAJA = (200, 135, 0)
_COLOR_CAJA_ENTREGADA = (150, 100, 0)
_COLOR_TRANSPORTADOR = (90, 90, 170)
_COLOR_PERSONA = (40, 160, 80)
_COLOR_PERSONA_NECESIDADES_CUBIERTAS = (25, 100, 50)
_COLOR_DRON = (70, 130, 255)
_COLOR_BORDE_DRON = (20, 60, 150)
_COLOR_TEXTO = (0, 0, 0)
_COLOR_BORDE = (0, 0, 0)
_COLOR_TEXTO_CUENTA = (255, 255, 255)
_COLOR_ERROR = (220, 0, 0)
_COLOR_FONDO_ERROR = (255, 230, 230)
_COLOR_FONDO_AYUDA = (255, 255, 225)
_COLOR_BORDE_AYUDA = (90, 90, 90)
_COLOR_TEXTO_AYUDA = (20, 20, 20)

# Medidas fijas del dibujo, en píxeles
# Grosor del borde de las cajas, las personas y la ayuda emergente.
_GROSOR_BORDE_FINO = 1
# Grosor del borde de los drones, los transportadores y el mensaje de error, y del
# contorno de un transportador sujeto.
_GROSOR_BORDE_GRUESO = 2
_RADIO_ESQUINA_AYUDA = 5
_RADIO_ESQUINA_TRANSPORTADOR = 4
# Contorno que rodea a un transportador mientras un dron lo tiene sujeto: cuántos
# píxeles más ancho y más alto que el transportador es (sobresale la mitad por
# cada lado) y el radio de sus esquinas.
_AUMENTO_CONTORNO_SUJETO = 6
_RADIO_ESQUINA_CONTORNO_SUJETO = 6


class Renderizador:
    """Renderizador dibuja el estado de una ``Simulacion`` en una ventana de pygame.

    Crear un renderizador arranca pygame y abre la ventana, que se puede
    redimensionar. Los argumentos no se comprueban aquí:
    ``Mundo.simulacion_visual()`` los comprueba antes de crear el renderizador.

    ``_ejecutar_ventana()`` (en ``ventana.py``) le da las localizaciones con
    ``_poner_localizaciones()`` y el alto del panel con ``_reservar_panel()``, y
    en cada fotograma le pasa los eventos con ``_gestionar_evento()`` y lo dibuja
    con ``_dibujar()``. Al terminar, ``_cerrar()`` cierra la ventana.

    Args:
        ancho: El ancho de la ventana, en píxeles. Opcional: ``ANCHO_POR_DEFECTO``
            por defecto. Un ancho menor que ``ANCHO_MINIMO`` se sube a
            ``ANCHO_MINIMO``.
        alto: El alto de la ventana, en píxeles. Opcional: ``ALTO_POR_DEFECTO``
            por defecto. Un alto menor que ``ALTO_MINIMO`` se sube a
            ``ALTO_MINIMO``.
        titulo: El título de la ventana. Opcional: ``"Simulación PDDL"`` por
            defecto.
    """

    # El tamaño inicial de la ventana, en píxeles, y también el de diseño: a este
    # tamaño la escala es 1, y todo lo que se dibuja crece o encoge en proporción
    # a él.
    ANCHO_POR_DEFECTO = 1400
    ALTO_POR_DEFECTO = 850
    # Límites de la escala: por debajo el texto ya no se leería, y por encima todo
    # crecería sin necesidad.
    _ESCALA_MINIMA = 0.6
    _ESCALA_MAXIMA = 1.8

    # El tamaño mínimo de la ventana, en píxeles: uno menor se sube a este. Con
    # ANCHO_MINIMO, los controles del panel aún caben y se pueden pulsar (ver
    # PanelControl._redimensionar()).
    ANCHO_MINIMO = 800
    ALTO_MINIMO = 600

    # Espacio inferior reservado para el panel de control, en píxeles, hasta que
    # _reservar_panel() da el que ocupa de verdad.
    _ALTO_PANEL_INICIAL = 110

    # Espacio entre la cuadrícula de localizaciones y los bordes de la zona del
    # mundo, a escala 1, en píxeles.
    _MARGEN_MUNDO = 60

    # El tamaño mínimo de cada figura, en píxeles, para que se vea y quepa su
    # nombre o su número aunque la ventana sea pequeña. Por encima del mínimo, la
    # localización crece con su celda, y las demás figuras, con el radio de la
    # localización.
    _RADIO_MINIMO_LOCALIZACION = 22
    _LADO_MINIMO_CAJA = 22
    _ANCHO_MINIMO_TRANSPORTADOR = 30
    _ALTO_MINIMO_TRANSPORTADOR = 18
    _RADIO_MINIMO_PERSONAS = 14
    _RADIO_MINIMO_DRON = 12
    _LADO_MINIMO_CAJA_SUJETA = 9

    # Distancia mínima, en píxeles, entre una ayuda emergente y el borde de la
    # zona del mundo.
    _MARGEN_AYUDA = 4
    # Mínimos, en píxeles, del relleno de una ayuda emergente, del espacio entre
    # sus líneas y del espacio entre sus dos columnas, para que el texto no quede
    # pegado al borde ni entre sí.
    _RELLENO_MINIMO_AYUDA = 6
    _ESPACIADO_MINIMO_AYUDA = 2
    _SEPARACION_MINIMA_COLUMNAS_AYUDA = 6

    # Tamaño mínimo, en puntos, de la fuente pequeña, para que se lea con la
    # ventana al mínimo.
    _TAMANO_MINIMO_FUENTE_PEQUENA = 18

    def __init__(
        self,
        ancho: int | None = None,
        alto: int | None = None,
        titulo: str = "Simulación PDDL",
    ) -> None:
        pygame.init()

        ancho = self.ANCHO_POR_DEFECTO if ancho is None else ancho
        alto = self.ALTO_POR_DEFECTO if alto is None else alto

        # Las localizaciones se guardan para poder recalcular la cuadrícula en
        # cada cambio de tamaño, sin que quien llama tenga que darlas otra vez.
        self._localizaciones: list[Localizacion] = []
        self._posiciones_localizaciones: dict[Localizacion, tuple[int, int]] = {}
        # Lo pone _calcular_disposicion(), a partir del tamaño de la ventana.
        self._radio_localizacion: int

        # Las pone _crear_fuentes(), a partir del tamaño de la ventana.
        self._fuente: pygame.font.Font
        self._fuente_pequena: pygame.font.Font
        self._fuente_error: pygame.font.Font

        # La ayuda emergente pendiente de dibujar en el fotograma actual: sus
        # líneas y el rectángulo del elemento sobre el que está el ratón, o None
        # si no hay ninguna.
        self._ayuda: tuple[list[_LineaAyuda], pygame.Rect] | None = None

        self._ancho = max(self.ANCHO_MINIMO, ancho)
        self._alto = max(self.ALTO_MINIMO, alto)
        self._alto_panel = self._ALTO_PANEL_INICIAL
        # El ancho que ocupa a la derecha el panel lateral (0 si está cerrado) y
        # el que ocupa su botón sobre el mundo, en la esquina superior derecha.
        # Los da _reservar_panel_lateral().
        self._ancho_panel_lateral = 0
        self._ancho_esquina = 0

        self._pantalla = pygame.display.set_mode(
            (self._ancho, self._alto), pygame.RESIZABLE
        )
        pygame.display.set_caption(titulo)

        self._crear_fuentes()
        self._calcular_disposicion()

    def __repr__(self) -> str:
        return f"Renderizador(ancho={self._ancho!r}, alto={self._alto!r})"

    # ------------------------------------------------------------------
    # Tamaño y disposición
    # ------------------------------------------------------------------

    def _crear_fuentes(self) -> None:
        """Crea las tres fuentes al tamaño que encaja con la ventana actual.

        Cada tamaño, en puntos, es el de la ventana por defecto multiplicado por
        la escala, que va de ``_ESCALA_MINIMA`` a ``_ESCALA_MAXIMA``. Con los
        valores actuales, el tamaño mínimo de cada fuente es:

        * ``_fuente``, para los nombres de las localizaciones: 24 a escala 1, y 14
          como mínimo.
        * ``_fuente_pequena``, para el resto de etiquetas y la ayuda emergente: 20
          a escala 1, y nunca baja de ``_TAMANO_MINIMO_FUENTE_PEQUENA`` (18), para
          que se lea con la ventana al mínimo (800 x 600), donde la cuenta daría 12.
        * ``_fuente_error``, para el mensaje de error: 26 a escala 1, y 15 como
          mínimo.
        """
        escala = self._escala
        self._fuente = pygame.font.SysFont(None, int(24 * escala))
        self._fuente_pequena = pygame.font.SysFont(
            None, max(self._TAMANO_MINIMO_FUENTE_PEQUENA, int(20 * escala))
        )
        self._fuente_error = pygame.font.SysFont(None, int(26 * escala))

    def _poner_localizaciones(self, localizaciones: list[Localizacion]) -> None:
        """Guarda las localizaciones y calcula sus posiciones en la cuadrícula."""
        self._localizaciones = list(localizaciones)
        self._calcular_disposicion()

    def _redimensionar(self, ancho: int, alto: int) -> None:
        """Cambia el tamaño de la ventana y vuelve a colocarlo todo para ese tamaño.

        Solo lo usa ``_gestionar_evento()``, para devolver la ventana al tamaño
        mínimo cuando el usuario la encoge por debajo de él.
        """
        self._ancho = max(self.ANCHO_MINIMO, ancho)
        self._alto = max(self.ALTO_MINIMO, alto)

        self._pantalla = pygame.display.set_mode(
            (self._ancho, self._alto), pygame.RESIZABLE
        )

        self._crear_fuentes()
        self._calcular_disposicion()

    def _reservar_panel(self, alto: int) -> None:
        """Reserva ``alto`` píxeles abajo para el panel y vuelve a colocar el mundo.

        Hay que volver a calcular la disposición porque las posiciones de las
        localizaciones se guardan, no se calculan en cada fotograma.
        """
        self._alto_panel = alto
        self._calcular_disposicion()

    def _reservar_panel_lateral(self, ancho: int, ancho_esquina: int) -> None:
        """Reserva ``ancho`` píxeles a la derecha para el panel lateral.

        ``ancho_esquina`` es el ancho que ocupa su botón sobre el mundo, en la
        esquina superior derecha: el mensaje de error se acorta para no quedar
        debajo. Como ``_reservar_panel()``, vuelve a colocar el mundo.
        """
        self._ancho_panel_lateral = ancho
        self._ancho_esquina = ancho_esquina
        self._calcular_disposicion()

    def _cerrar(self) -> None:
        """Cierra la ventana y apaga pygame."""
        pygame.quit()

    def _gestionar_evento(self, evento: pygame.event.Event) -> bool:
        """Atiende ``evento`` si es un cambio de tamaño de la ventana.

        Returns:
            ``True`` si ``evento`` era un cambio de tamaño y se recalculó la
            disposición, ``False`` para cualquier otro evento.
        """
        if evento.type != pygame.VIDEORESIZE:
            return False

        self._pantalla = pygame.display.get_surface()
        self._ancho, self._alto = self._pantalla.get_size()
        # _redimensionar() (que llama a set_mode) solo se ejecuta cuando el nuevo
        # tamaño queda por debajo del mínimo: en Linux (X11/XWayland) el evento
        # llega mientras el usuario todavía está arrastrando, y llamar a set_mode
        # entraría en conflicto con el gestor de ventanas por el tamaño.
        if self._ancho < self.ANCHO_MINIMO or self._alto < self.ALTO_MINIMO:
            self._redimensionar(evento.w, evento.h)
        else:
            self._crear_fuentes()
            self._calcular_disposicion()
        return True

    def _calcular_disposicion(self) -> None:
        """Coloca las localizaciones en una cuadrícula, en la zona encima del panel.

        También fija ``_radio_localizacion``, del que dependen los tamaños de todo
        lo que se dibuja junto a una localización.
        """
        self._posiciones_localizaciones.clear()

        numero_de_localizaciones = len(self._localizaciones)
        if numero_de_localizaciones == 0:
            # Ocurre al construir el renderizador, antes de _poner_localizaciones().
            # Sin localizaciones no se dibuja nada, así que el radio solo necesita
            # un valor.
            self._radio_localizacion = self._RADIO_MINIMO_LOCALIZACION
            return

        columnas = math.ceil(math.sqrt(numero_de_localizaciones))
        filas = math.ceil(numero_de_localizaciones / columnas)

        margen = int(self._MARGEN_MUNDO * self._escala)

        ancho_celda = (self._ancho_mundo - 2 * margen) / columnas
        alto_celda = (self._alto_mundo - 2 * margen) / filas

        # El radio es un tercio del lado más corto de la celda, para que los
        # círculos no se solapen. Nunca baja del mínimo, para que los nombres se
        # puedan leer. Con la ventana en su tamaño mínimo, a partir de unas 30
        # localizaciones las cajas de una localización se solapan con las personas
        # de la de debajo, y a partir de unas 110 se solapan los propios círculos.
        self._radio_localizacion = int(
            max(self._RADIO_MINIMO_LOCALIZACION, min(ancho_celda, alto_celda) * 0.33)
        )

        for indice, localizacion in enumerate(self._localizaciones):
            fila = indice // columnas
            columna = indice % columnas

            x = margen + columna * ancho_celda + ancho_celda / 2
            y = margen + fila * alto_celda + alto_celda / 2

            self._posiciones_localizaciones[localizacion] = (int(x), int(y))

    # ------------------------------------------------------------------
    # Posiciones de dibujo
    # ------------------------------------------------------------------

    def _obtener_posiciones_dibujo(self, simulacion: Simulacion) -> _PosicionesDibujo:
        """Devuelve dónde dibujar ahora cada dron y cada transportador.

        Un dron que se está moviendo se coloca entre su origen y su destino, y un
        transportador que se lleva se coloca junto a su dron.
        """
        posiciones: _PosicionesDibujo = {}

        for dron in simulacion._drones:
            posiciones[dron] = self._posiciones_localizaciones[dron.localizacion]

        # Interpolación: mientras un dron se mueve, se dibuja entre el origen y el
        # destino, aunque su localización lógica solo cambia cuando termina la
        # acción (``at end``).
        for accion in simulacion._acciones_activas:
            if not isinstance(accion, (Mover, MoverTransportador)):
                continue

            progreso = accion._progreso(simulacion._tiempo_simulacion)
            x0, y0 = self._posiciones_localizaciones[accion.origen]
            x1, y1 = self._posiciones_localizaciones[accion.destino]

            posiciones[accion.dron] = (
                x0 + ((x1 - x0) * progreso),
                y0 + ((y1 - y0) * progreso),
            )

        # Los transportadores se colocan después de los drones, para que un
        # transportador que se lleva pueda usar la posición de su dron. Un
        # transportador sigue al dron que es su propietario: tanto
        # CogerTransportador como MoverTransportador ponen el propietario
        # ``at start``, así que esto también cubre un Mover normal mientras se
        # lleva el transportador.
        for transportador in simulacion._todos_los_transportadores:
            dron_que_lo_sujeta = transportador.propietario_actual

            if dron_que_lo_sujeta is not None:
                x, y = posiciones[dron_que_lo_sujeta]
                # Justo debajo del dron que lo sujeta (0.45 radios más abajo), como
                # si colgara de él.
                posiciones[transportador] = (
                    x,
                    y + int(self._radio_localizacion * 0.45),
                )
            else:
                x, y = self._posiciones_localizaciones[transportador.localizacion]
                # Abajo a la izquierda del centro (0.75 radios a la izquierda y 0.35
                # más abajo), para dejar libre el centro, donde van el nombre de la
                # localización y los drones, y no tapar las cajas, que van abajo.
                posiciones[transportador] = (
                    x - int(self._radio_localizacion * 0.75),
                    y + int(self._radio_localizacion * 0.35),
                )

        return posiciones

    # ------------------------------------------------------------------
    # Consultas del estado de los objetos
    # ------------------------------------------------------------------

    @staticmethod
    def _caja_en_un_brazo(caja: Caja, drones: list[Dron]) -> bool:
        """Si algún brazo de ``drones`` sujeta la caja."""
        return any(brazo.caja is caja for dron in drones for brazo in dron.brazos)

    @staticmethod
    def _cajas_dibujadas_en(transportador: Transportador) -> list[Caja]:
        """Devuelve las cajas que se dibujan dentro del transportador.

        Son las cajas que tiene dentro y las que se están sacando de él. Una
        descarga saca la caja del transportador ``at start``, pero el brazo solo
        la sujeta ``at end``: sin esto, la caja se dibujaría en la localización
        mientras dura la descarga, un sitio al que nunca va.
        """
        return transportador.cajas_dentro + transportador._cajas_salientes

    def _caja_en_transportador(
        self, caja: Caja, transportadores: list[Transportador]
    ) -> bool:
        """Si la caja se dibuja dentro de uno de los ``transportadores``."""
        return any(
            caja in self._cajas_dibujadas_en(transportador)
            for transportador in transportadores
        )

    @staticmethod
    def _esta_entregada(caja: Caja) -> bool:
        """Devuelve si la caja se ha entregado a una persona.

        Lee el estado de la caja, no si tiene propietario: durante ``CogerCaja``
        el dron reclama la caja ``at start`` (estado transportada, propietario
        puesto) pero su brazo solo la sujeta ``at end``, así que mientras dura la
        acción la caja se sigue dibujando en la localización, y no está entregada.
        """
        return caja.estado == Caja.ENTREGADA

    # ------------------------------------------------------------------
    # Ayudas emergentes
    # ------------------------------------------------------------------

    @staticmethod
    def _describir_caja(caja: Caja) -> str:
        """Devuelve la caja como texto para una ayuda, p. ej. ``"caja1 (comida)"``."""
        return f"{caja.nombre} ({caja.contenido})"

    def _dejar_ayuda_pendiente(
        self, lineas: list[_LineaAyuda], rectangulo: pygame.Rect
    ) -> None:
        """Deja pendiente una ayuda si el ratón está en ``rectangulo``.

        Si en el mismo fotograma ya hay una pendiente, la sustituye: el elemento que
        se dibuja después queda encima, así que la ayuda es la del que se ve.
        """
        if not lineas:
            return

        if rectangulo.collidepoint(pygame.mouse.get_pos()):
            self._ayuda = (list(lineas), rectangulo)

    def _dibujar_ayuda(self) -> None:
        """Dibuja la ayuda pendiente a la derecha de su elemento.

        Si no cabe, la pone a la izquierda, y nunca fuera de la zona del mundo. Se
        llama después de dibujar los paneles para que no la tape el botón del panel
        lateral, que está dentro de esa zona.
        """
        if self._ayuda is None:
            return

        lineas, rectangulo = self._ayuda

        # En píxeles: el tamaño a escala 1 multiplicado por la escala, con un
        # mínimo para que el texto no quede pegado al borde ni entre sí.
        relleno = max(self._RELLENO_MINIMO_AYUDA, int(8 * self._escala))
        espaciado = max(self._ESPACIADO_MINIMO_AYUDA, int(3 * self._escala))
        separacion_columnas = max(
            self._SEPARACION_MINIMA_COLUMNAS_AYUDA, int(8 * self._escala)
        )

        # Cada línea es un solo texto o un par (izquierda, derecha). Un par se
        # dibuja en dos columnas alineadas: rellenar con espacios no funcionaría,
        # porque la fuente tiene ancho variable y las cajas no quedarían alineadas
        # en vertical.
        lineas_en_pares = [
            linea if isinstance(linea, tuple) else (linea, None) for linea in lineas
        ]

        # Todas las líneas de la ayuda se tratan como si midieran lo mismo: el alto
        # del texto más alto, de cualquiera de las dos columnas. Si cada línea
        # midiera lo que su propio texto, unas serían más bajas que otras, porque
        # el alto depende de las letras. Por ejemplo, en la ayuda de un
        # transportador solo la primera línea lleva su nombre a la izquierda, y en
        # las demás esa columna está vacía. Las líneas quedarían separadas de forma
        # desigual, y al recortar no se podría saber cuántas caben. También cuenta
        # la línea "… y N líneas más", que se añade si hay que recortar.
        alto_linea = max(
            self._fuente_pequena.size(texto)[1]
            for texto in (
                f"… y {len(lineas_en_pares)} líneas más",
                *(izquierda for izquierda, _ in lineas_en_pares),
                *(derecha for _, derecha in lineas_en_pares if derecha),
            )
        )
        lineas_en_pares = self._recortar_ayuda(
            lineas_en_pares, alto_linea, relleno, espaciado
        )

        superficies_izquierda = [
            self._fuente_pequena.render(izquierda, True, _COLOR_TEXTO_AYUDA)
            for izquierda, _ in lineas_en_pares
        ]
        superficies_derecha = [
            self._fuente_pequena.render(derecha, True, _COLOR_TEXTO_AYUDA)
            if derecha
            else None
            for _, derecha in lineas_en_pares
        ]

        ancho_izquierda = max(
            superficie.get_width() for superficie in superficies_izquierda
        )
        ancho_derecha = max(
            (
                superficie.get_width()
                for superficie in superficies_derecha
                if superficie is not None
            ),
            default=0,
        )

        ancho_contenido = ancho_izquierda
        if ancho_derecha:
            # Solo hay hueco entre columnas si alguna línea tiene columna derecha.
            ancho_contenido += separacion_columnas + ancho_derecha

        ancho = ancho_contenido + relleno * 2
        numero_lineas = len(lineas_en_pares)
        alto = numero_lineas * alto_linea + (numero_lineas - 1) * espaciado
        alto += relleno * 2

        # Anclada junto al elemento, pero nunca fuera de la zona del mundo, para
        # que no pase por encima de los paneles.
        x = rectangulo.right + relleno
        y = rectangulo.top - relleno

        if x + ancho > self._ancho_mundo:
            # A la derecha del elemento no cabe: se pone a su izquierda.
            x = rectangulo.left - ancho - relleno
        x = max(
            self._MARGEN_AYUDA, min(x, self._ancho_mundo - ancho - self._MARGEN_AYUDA)
        )
        y = max(
            self._MARGEN_AYUDA, min(y, self._alto_mundo - alto - self._MARGEN_AYUDA)
        )

        fondo = pygame.Rect(x, y, ancho, alto)

        pygame.draw.rect(
            self._pantalla,
            _COLOR_FONDO_AYUDA,
            fondo,
            border_radius=_RADIO_ESQUINA_AYUDA,
        )
        pygame.draw.rect(
            self._pantalla,
            _COLOR_BORDE_AYUDA,
            fondo,
            _GROSOR_BORDE_FINO,
            border_radius=_RADIO_ESQUINA_AYUDA,
        )

        # Las dos columnas empiezan siempre en la misma x. Solo la y baja en cada
        # línea.
        x_izquierda = x + relleno
        x_derecha = x_izquierda + ancho_izquierda + separacion_columnas
        y_linea = y + relleno
        for superficie_izquierda, superficie_derecha in zip(
            superficies_izquierda, superficies_derecha, strict=True
        ):
            self._pantalla.blit(superficie_izquierda, (x_izquierda, y_linea))

            if superficie_derecha is not None:
                self._pantalla.blit(superficie_derecha, (x_derecha, y_linea))

            y_linea += alto_linea + espaciado

    def _recortar_ayuda(
        self,
        lineas: list[tuple[str, str | None]],
        alto_linea: int,
        relleno: int,
        espaciado: int,
    ) -> list[tuple[str, str | None]]:
        """Devuelve las líneas de una ayuda que caben en el alto del mundo.

        Una ayuda más alta que el mundo no cabría en ningún sitio. Si no caben
        todas, se quedan las primeras y una última que dice cuántas faltan. El mundo
        siempre tiene sitio para varias líneas, porque la ventana tiene un alto
        mínimo y el panel de control y la fuente crecen con ella.
        """
        alto_libre = self._alto_mundo - 2 * self._MARGEN_AYUDA - 2 * relleno + espaciado
        maximo_lineas = alto_libre // (alto_linea + espaciado)
        if len(lineas) <= maximo_lineas:
            return lineas

        ocultas = len(lineas) - (maximo_lineas - 1)
        return [*lineas[: maximo_lineas - 1], (f"… y {ocultas} líneas más", None)]

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------

    def _dibujar(self, simulacion: Simulacion) -> None:
        """Dibuja el estado actual de la simulación, de abajo arriba.

        Primero el mundo (localizaciones, cajas, transportadores, personas y
        drones) y, si una acción ha fallado, el error. La ayuda pendiente no se
        dibuja aquí: ``_dibujar_ayuda()`` la dibuja después de los paneles.
        """
        posiciones = self._obtener_posiciones_dibujo(simulacion)

        drones = simulacion._drones
        cajas = simulacion._cajas
        personas = simulacion._personas
        transportadores = simulacion._todos_los_transportadores

        # Solo una ayuda por fotograma: de los elementos sobre los que está el ratón,
        # se muestra la del último que se dibuja, que queda encima de los demás.
        self._ayuda = None

        self._pantalla.fill(_COLOR_FONDO)

        self._dibujar_localizaciones()
        self._dibujar_cajas(cajas, drones, transportadores)
        self._dibujar_transportadores(transportadores, posiciones)
        self._dibujar_personas(personas)
        self._dibujar_drones(drones, posiciones)

        error = simulacion._error
        if error is not None:
            self._dibujar_error(error)

    def _dibujar_localizaciones(self) -> None:
        """Dibuja cada localización como un círculo con su nombre."""
        for localizacion, (x, y) in self._posiciones_localizaciones.items():
            pygame.draw.circle(
                self._pantalla, _COLOR_LOCALIZACION, (x, y), self._radio_localizacion
            )

            texto = self._fuente.render(
                localizacion.nombre, True, _COLOR_TEXTO_LOCALIZACION
            )
            self._pantalla.blit(texto, texto.get_rect(center=(x, y)))

    def _dibujar_cajas(
        self,
        cajas: list[Caja],
        drones: list[Dron],
        transportadores: list[Transportador],
    ) -> None:
        """Dibuja un cuadrado por localización, con el número de cajas por entregar.

        Las cajas que lleva un dron o que están dentro de un transportador no se
        cuentan: se dibujan con lo que las lleva. Si quedan cajas por entregar, el
        cuadrado tiene el color normal y muestra cuántas son. Si todas las de la
        localización están entregadas, se dibuja con el color de entregada y sin
        número: esas cajas aparecen en la ayuda de la persona que las tiene.
        """
        # El lado del cuadrado: casi la mitad del radio de la localización, con un
        # mínimo para que quepa el número.
        tamano = max(self._LADO_MINIMO_CAJA, int(self._radio_localizacion * 0.45))

        cajas_por_localizacion: dict[Localizacion, list[Caja]] = {}
        for caja in cajas:
            if self._caja_en_un_brazo(caja, drones):
                continue
            if self._caja_en_transportador(caja, transportadores):
                continue
            cajas_por_localizacion.setdefault(caja.localizacion, []).append(caja)

        for localizacion, cajas_aqui in cajas_por_localizacion.items():
            x, y = self._posiciones_localizaciones[localizacion]

            # Pisa un poco el borde inferior del círculo, para que se vea que las
            # cajas son de esa localización.
            rectangulo = pygame.Rect(
                x - tamano // 2,
                y + self._radio_localizacion - tamano // 3,
                tamano,
                tamano,
            )

            por_entregar = [
                caja for caja in cajas_aqui if not self._esta_entregada(caja)
            ]

            color = _COLOR_CAJA if por_entregar else _COLOR_CAJA_ENTREGADA
            pygame.draw.rect(self._pantalla, color, rectangulo)
            pygame.draw.rect(
                self._pantalla, _COLOR_BORDE, rectangulo, _GROSOR_BORDE_FINO
            )

            if por_entregar:
                self._dibujar_cuenta(len(por_entregar), rectangulo)
                self._dejar_ayuda_pendiente(
                    [self._describir_caja(caja) for caja in por_entregar], rectangulo
                )

    def _dibujar_transportadores(
        self, transportadores: list[Transportador], posiciones: _PosicionesDibujo
    ) -> None:
        """Dibuja cada transportador como un rectángulo con su carga, p. ej. ``1/2``.

        Si lo sujeta un dron, lleva además un contorno del color de los drones. Su
        ayuda muestra su nombre y las cajas que lleva dentro.
        """
        # Casi tan ancho como el radio y la mitad de alto, con un mínimo para que
        # quepa la etiqueta.
        ancho = max(
            self._ANCHO_MINIMO_TRANSPORTADOR, int(self._radio_localizacion * 0.9)
        )
        alto = max(self._ALTO_MINIMO_TRANSPORTADOR, int(self._radio_localizacion * 0.5))

        for transportador in transportadores:
            x, y = posiciones[transportador]
            rectangulo = pygame.Rect(
                int(x) - ancho // 2, int(y) - alto // 2, ancho, alto
            )

            pygame.draw.rect(
                self._pantalla,
                _COLOR_TRANSPORTADOR,
                rectangulo,
                border_radius=_RADIO_ESQUINA_TRANSPORTADOR,
            )
            pygame.draw.rect(
                self._pantalla,
                _COLOR_BORDE,
                rectangulo,
                _GROSOR_BORDE_GRUESO,
                border_radius=_RADIO_ESQUINA_TRANSPORTADOR,
            )

            cajas_dibujadas_dentro = self._cajas_dibujadas_en(transportador)

            etiqueta = self._fuente_pequena.render(
                f"{len(cajas_dibujadas_dentro)}/{transportador.capacidad}",
                True,
                _COLOR_TEXTO_CUENTA,
            )
            self._pantalla.blit(etiqueta, etiqueta.get_rect(center=rectangulo.center))

            # Un transportador sujeto lleva un contorno, porque mientras está
            # sujeto no se pueden meter ni sacar cajas.
            if transportador.propietario_actual is not None:
                pygame.draw.rect(
                    self._pantalla,
                    _COLOR_DRON,
                    rectangulo.inflate(
                        _AUMENTO_CONTORNO_SUJETO, _AUMENTO_CONTORNO_SUJETO
                    ),
                    _GROSOR_BORDE_GRUESO,
                    border_radius=_RADIO_ESQUINA_CONTORNO_SUJETO,
                )

            # El nombre en la primera línea y, al lado, una caja por línea, como en
            # la ayuda de las personas.
            lineas: list[_LineaAyuda] = [(transportador.nombre, None)]
            if cajas_dibujadas_dentro:
                lineas = [
                    (
                        transportador.nombre if indice == 0 else "",
                        f"| {self._describir_caja(caja)}",
                    )
                    for indice, caja in enumerate(cajas_dibujadas_dentro)
                ]
            self._dejar_ayuda_pendiente(lineas, rectangulo)

    def _dibujar_personas(self, personas: list[Persona]) -> None:
        """Dibuja un círculo por localización, con el número de personas que hay.

        El círculo es verde oscuro cuando ninguna de esas personas tiene
        necesidades pendientes. Su ayuda enumera las personas y las cajas que posee
        cada una.
        """
        # Algo más de un cuarto del radio de la localización, con un mínimo para
        # que quepa el número.
        radio_personas = max(
            self._RADIO_MINIMO_PERSONAS, int(self._radio_localizacion * 0.28)
        )
        # El centro del círculo queda un poco por encima del borde superior de la
        # localización, así que el círculo de las personas pisa el de la
        # localización.
        separacion_sobre_localizacion = int(5 * self._escala)

        personas_por_localizacion: dict[Localizacion, list[Persona]] = {}
        for persona in personas:
            personas_por_localizacion.setdefault(persona.localizacion, []).append(
                persona
            )

        for localizacion, personas_aqui in personas_por_localizacion.items():
            x, y = self._posiciones_localizaciones[localizacion]
            centro_personas = (
                x,
                y - self._radio_localizacion - separacion_sobre_localizacion,
            )

            necesidades_cubiertas = all(
                not persona.necesidades for persona in personas_aqui
            )

            pygame.draw.circle(
                self._pantalla,
                _COLOR_PERSONA_NECESIDADES_CUBIERTAS
                if necesidades_cubiertas
                else _COLOR_PERSONA,
                centro_personas,
                radio_personas,
            )
            pygame.draw.circle(
                self._pantalla,
                _COLOR_BORDE,
                centro_personas,
                radio_personas,
                _GROSOR_BORDE_FINO,
            )

            rectangulo = pygame.Rect(
                centro_personas[0] - radio_personas,
                centro_personas[1] - radio_personas,
                radio_personas * 2,
                radio_personas * 2,
            )
            self._dibujar_cuenta(len(personas_aqui), rectangulo)

            # Una línea por caja, con el nombre de la persona solo en la primera
            # (ver _dibujar_ayuda()).
            lineas: list[_LineaAyuda] = []
            for persona in personas_aqui:
                cajas_poseidas = persona.posee

                if not cajas_poseidas:
                    lineas.append((persona.nombre, None))
                    continue

                for indice, caja in enumerate(cajas_poseidas):
                    lineas.append(
                        (
                            persona.nombre if indice == 0 else "",
                            f"| {self._describir_caja(caja)}",
                        )
                    )

            self._dejar_ayuda_pendiente(lineas, rectangulo)

    def _dibujar_drones(
        self, drones: list[Dron], posiciones: _PosicionesDibujo
    ) -> None:
        """Dibuja cada dron como un círculo con su nombre y las cajas que lleva."""
        # Algo menos de un tercio del radio de la localización, con un mínimo para
        # que se vea. Cada caja que lleva mide algo menos que ese radio.
        radio_dron = max(self._RADIO_MINIMO_DRON, int(self._radio_localizacion * 0.3))
        tamano_caja = max(self._LADO_MINIMO_CAJA_SUJETA, int(radio_dron * 0.7))
        # Lo que el centro del nombre queda por encima del borde superior del dron.
        separacion_nombre_dron = int(9 * self._escala)

        for dron in drones:
            x, y = posiciones[dron]
            centro_dron = (int(x), int(y))

            pygame.draw.circle(self._pantalla, _COLOR_DRON, centro_dron, radio_dron)
            pygame.draw.circle(
                self._pantalla,
                _COLOR_BORDE_DRON,
                centro_dron,
                radio_dron,
                _GROSOR_BORDE_GRUESO,
            )

            nombre = self._fuente_pequena.render(dron.nombre, True, _COLOR_TEXTO)
            self._pantalla.blit(
                nombre,
                nombre.get_rect(
                    center=(
                        centro_dron[0],
                        centro_dron[1] - radio_dron - separacion_nombre_dron,
                    )
                ),
            )

            # Las cajas que lleva se dibujan debajo de él, una por cada brazo que
            # sujeta una caja.
            numero_de_cajas_sujetas = sum(
                brazo.caja is not None for brazo in dron.brazos
            )
            if not numero_de_cajas_sujetas:
                continue

            # Las cajas que sujeta se dibujan una al lado de otra, separadas 3
            # píxeles. Su borde superior queda 2 píxeles por encima del borde
            # inferior del dron, para que lo pisen un poco, como si colgaran de él.
            espaciado = tamano_caja + 3
            x_inicio = centro_dron[0] - (numero_de_cajas_sujetas - 1) * espaciado // 2

            for indice in range(numero_de_cajas_sujetas):
                rectangulo = pygame.Rect(
                    x_inicio + indice * espaciado - tamano_caja // 2,
                    centro_dron[1] + radio_dron - 2,
                    tamano_caja,
                    tamano_caja,
                )
                pygame.draw.rect(self._pantalla, _COLOR_CAJA, rectangulo)
                pygame.draw.rect(
                    self._pantalla, _COLOR_BORDE, rectangulo, _GROSOR_BORDE_FINO
                )

    def _dibujar_cuenta(self, cuenta: int, rectangulo: pygame.Rect) -> None:
        """Dibuja un número centrado en ``rectangulo``."""
        texto = self._fuente_pequena.render(str(cuenta), True, _COLOR_TEXTO_CUENTA)
        self._pantalla.blit(texto, texto.get_rect(center=rectangulo.center))

    def _dibujar_error(self, error: str) -> None:
        """Dibuja un mensaje de error en la parte superior de la ventana."""
        relleno = int(10 * self._escala)
        # El mensaje puede ser largo: se corta al ancho disponible en lugar de
        # salirse de la zona del mundo. A cada lado deja sitio para el relleno del
        # recuadro, para un margen igual hasta el borde y para el botón del panel
        # lateral, que se dibuja en la esquina superior derecha: como el mensaje
        # va centrado, se descuenta a los dos lados.
        ancho_maximo = self._ancho_mundo - 4 * relleno - 2 * self._ancho_esquina
        mensaje = _truncar(self._fuente_error, f"Error: {error}", ancho_maximo)
        texto = self._fuente_error.render(mensaje, True, _COLOR_ERROR)

        rectangulo = texto.get_rect(centerx=self._ancho_mundo // 2, top=relleno)
        fondo = rectangulo.inflate(relleno * 2, relleno * 2)

        pygame.draw.rect(self._pantalla, _COLOR_FONDO_ERROR, fondo)
        pygame.draw.rect(self._pantalla, _COLOR_ERROR, fondo, _GROSOR_BORDE_GRUESO)
        self._pantalla.blit(texto, rectangulo)

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def _ancho_mundo(self) -> int:
        """El ancho que queda para el mundo, en píxeles, descontado el panel lateral."""
        return self._ancho - self._ancho_panel_lateral

    @property
    def _alto_mundo(self) -> int:
        """El alto que queda para el mundo, en píxeles, descontado el panel."""
        return self._alto - self._alto_panel

    @property
    def _escala(self) -> float:
        """Cuánto escalar los tamaños, respecto al tamaño de ventana por defecto.

        Es el menor de los dos cocientes, el del ancho y el del alto, para que todo
        quepa en las dos direcciones, y se limita entre ``_ESCALA_MINIMA`` y
        ``_ESCALA_MAXIMA``.
        """
        escala_sin_limitar = min(
            self._ancho / self.ANCHO_POR_DEFECTO, self._alto / self.ALTO_POR_DEFECTO
        )
        return max(self._ESCALA_MINIMA, min(self._ESCALA_MAXIMA, escala_sin_limitar))
