from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from simulador_pddl.objetos.caja import Caja
from simulador_pddl.objetos.dron import Dron
from simulador_pddl.objetos.persona import Persona
from simulador_pddl.objetos.transportador import Transportador
from simulador_pddl.simulacion.verificacion import InformeVerificacion
from simulador_pddl.visualizacion.panel_control import (
    Boton,
    PanelControl,
    _fuente,
    _truncar,
)
from simulador_pddl.visualizacion.renderizador import (
    _COLOR_CAJA,
    _COLOR_CAJA_ENTREGADA,
    _COLOR_DRON,
    _COLOR_PERSONA,
    _COLOR_PERSONA_NECESIDADES_CUBIERTAS,
    _COLOR_TRANSPORTADOR,
    Renderizador,
)

if TYPE_CHECKING:
    from simulador_pddl.acciones.accion import Accion
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
_COLOR_PESTANA = (200, 200, 207)
_COLOR_PESTANA_ELEGIDA = (245, 245, 248)
_COLOR_FILA_BAJO_RATON = (240, 240, 245)

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

# Cómo va cada acción del plan, que se muestra con su color. Si falla una acción,
# las que estaban en ejecución ya no van a terminar: quedan interrumpidas.
_SIN_EMPEZAR = "sin empezar"
_EN_EJECUCION = "en ejecución"
_TERMINADA = "terminada"
_INTERRUMPIDA = "interrumpida"
_FALLIDA = "fallida"

_COLORES_ACCION: dict[str, _Color] = {
    _SIN_EMPEZAR: (150, 150, 155),
    _EN_EJECUCION: (50, 100, 200),
    _TERMINADA: (30, 140, 60),
    _INTERRUMPIDA: (215, 120, 0),
    _FALLIDA: (200, 30, 30),
}

# Las pestañas del panel, en el orden en que aparecen. Cada una muestra una lista.
_PESTANA_PLAN = "Plan"
_PESTANA_OBJETIVOS = "Objetivos"
_PESTANA_OBJETOS = "Objetos"
_PESTANAS = (_PESTANA_PLAN, _PESTANA_OBJETIVOS, _PESTANA_OBJETOS)

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


def _clase_accion(accion: Accion, simulacion: Simulacion) -> str:
    """Devuelve cómo va una acción del plan.

    Puede estar sin empezar, en ejecución, terminada, interrumpida o fallida. La
    acción que falló está fallida, tanto si falló al empezar como al terminar.
    Las demás que estaban en ejecución ya no van a terminar, así que quedan
    interrumpidas, y las que no habían empezado siguen sin empezar.
    """
    if accion is simulacion._accion_fallida:
        return _FALLIDA
    if accion.terminada:
        return _TERMINADA
    if accion.iniciada:
        return _INTERRUMPIDA if simulacion._tiene_error else _EN_EJECUCION
    return _SIN_EMPEZAR


def _detalles_accion(accion: Accion, error: str | None) -> list[str]:
    """Devuelve las líneas que se muestran debajo de una acción.

    La primera dice con qué objetos se hace, y la segunda cuándo empieza y
    termina. Si la acción falló, ``error`` es su mensaje, y la tercera lo muestra.
    """
    detalles = [
        ", ".join(objeto.nombre for objeto in accion.objetos.values()),
        f"De t={accion.inicio_sim:.2f}s a t={accion.tiempo_fin:.2f}s",
    ]
    if error is not None:
        detalles.append(f"Falló: {error}")
    return detalles


def _detalles_dron(dron: Dron) -> list[str]:
    """Devuelve las líneas que se muestran debajo de un dron.

    Dónde está y, por cada brazo, lo que sujeta: una caja, un transportador o
    nada.
    """
    detalles = [f"En {dron.localizacion.nombre}"]
    for brazo in dron.brazos:
        if brazo.caja is not None:
            sujeta = Renderizador._describir_caja(brazo.caja)
        elif brazo.transportador is not None:
            sujeta = brazo.transportador.nombre
        else:
            sujeta = "vacío"
        detalles.append(f"Brazo {brazo.nombre}: {sujeta}")
    return detalles


def _detalles_transportador(transportador: Transportador) -> list[str]:
    """Devuelve las líneas que se muestran debajo de un transportador.

    Dónde está, qué dron lo lleva y con qué brazo, y las cajas que tiene dentro,
    con cuántas son de su capacidad.
    """
    if transportador.brazo_actual is None:
        llevado = "No lo lleva ningún dron"
    else:
        llevado = (
            f"Lo lleva {transportador._nombre_propietario()} con el brazo "
            f"{transportador.brazo_actual.nombre}"
        )
    cajas = transportador.cajas_dentro
    nombres_cajas = ", ".join(Renderizador._describir_caja(caja) for caja in cajas)
    return [
        f"En {transportador.localizacion.nombre}",
        llevado,
        f"Cajas ({len(cajas)}/{transportador.capacidad}): {nombres_cajas or 'ninguna'}",
    ]


def _detalles_caja(caja: Caja) -> list[str]:
    """Devuelve las líneas que se muestran debajo de una caja.

    Quién la tiene, que puede ser un dron, un transportador o la persona a la que
    se entregó, o que está disponible, y dónde está.
    """
    propietario = caja.propietario_actual
    if isinstance(propietario, Dron):
        estado = f"La lleva el dron {propietario.nombre}"
    elif isinstance(propietario, Transportador):
        estado = f"Dentro del transportador {propietario.nombre}"
    elif isinstance(propietario, Persona):
        estado = f"Entregada a la persona {propietario.nombre}"
    else:
        estado = "Disponible"
    return [estado, f"En {caja.localizacion.nombre}"]


def _detalles_persona(persona: Persona) -> list[str]:
    """Devuelve las líneas que se muestran debajo de una persona.

    Dónde está, lo que todavía necesita y las cajas que se le han entregado.
    """
    necesidades = ", ".join(necesidad.nombre for necesidad in persona.necesidades)
    cajas = ", ".join(Renderizador._describir_caja(caja) for caja in persona.posee)
    return [
        f"En {persona.localizacion.nombre}",
        f"Necesita: {necesidades}" if necesidades else "No necesita nada",
        f"Tiene: {cajas}" if cajas else "No tiene ninguna caja",
    ]


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
    Debajo, dos pestañas, cada una con una lista. La del plan tiene sus acciones,
    numeradas, cada una con el color de cómo va, sus objetos, cuándo empieza y
    termina y, mientras se ejecuta, una barra con lo que ha avanzado. Al pulsar
    una, la simulación salta a su inicio. La de objetivos tiene cada objetivo con
    el color de cómo va, cuándo se cumplió o se rompió y, si no se cumple, por
    qué. La de objetos tiene los drones, los transportadores, las cajas y las
    personas, agrupados por tipo y con el color que tienen en el mundo, cada uno
    con dónde está y lo que lleva, tiene o necesita. Cuando la lista no cabe, se
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
        self._pestana = _PESTANA_PLAN

        # Cuántos píxeles se ha desplazado la lista hacia arriba, con la rueda del
        # ratón o con la barra, y si se está arrastrando la barra. Los pone
        # _dibujar_panel(): la zona donde se dibuja la lista, la de su barra y lo
        # que mide la lista entera, que dependen de lo que se dibuja encima.
        self._desplazamiento = 0
        self._arrastrando = False
        self._zona_lista = pygame.Rect(0, 0, 0, 0)
        self._barra_lista = pygame.Rect(0, 0, 0, 0)
        self._alto_lista = 0
        # También los pone _dibujar_panel(): dónde está cada pestaña y, con la del
        # plan elegida, dónde está la fila de cada acción, para saber qué se pulsa.
        self._rectangulos_pestanas: dict[str, pygame.Rect] = {}
        self._filas_plan: list[tuple[pygame.Rect, Accion]] = []

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
        return f"PanelLateral(abierto={self._abierto!r}, pestana={self._pestana!r})"

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

        Con el panel abierto, un clic izquierdo en una pestaña muestra su lista, la
        rueda del ratón sobre la lista la desplaza, y un clic izquierdo en su barra
        la lleva a ese punto. Si se mantiene pulsado, la lista sigue al ratón hasta
        que se suelta, aunque se salga de la barra. Un clic en una acción del plan
        no lo atiende este método, sino ``_accion_pulsada()``.

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
        if clic_izquierdo and evento.type == pygame.MOUSEBUTTONDOWN and self._abierto:
            for pestana, rectangulo in self._rectangulos_pestanas.items():
                if rectangulo.collidepoint(evento.pos):
                    self._elegir_pestana(pestana)
                    return False

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

    def _accion_pulsada(self, evento: pygame.event.Event) -> Accion | None:
        """Devuelve la acción de la lista del plan que pulsa ``evento``, o ``None``.

        Solo cuenta un clic izquierdo con el panel abierto y dentro de la zona de la
        lista: una fila que el desplazamiento deja fuera de la zona no se ve, así
        que no se puede pulsar.
        """
        if not (
            self._abierto
            and evento.type == pygame.MOUSEBUTTONDOWN
            and evento.button == pygame.BUTTON_LEFT
            and self._zona_lista.collidepoint(evento.pos)
        ):
            return None
        for fila, accion in self._filas_plan:
            if fila.collidepoint(evento.pos):
                return accion
        return None

    def _elegir_pestana(self, pestana: str) -> None:
        """Muestra la lista de ``pestana``, desde su principio.

        Las filas del plan se olvidan hasta que se vuelva a dibujar su lista, para
        que un clic no elija una acción que ya no se ve.
        """
        self._pestana = pestana
        self._desplazamiento = 0
        self._filas_plan = []

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
        """Dibuja el fondo del panel, la cabecera, las pestañas y la lista elegida."""
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
        # Las pestañas.
        y = self._dibujar_pestanas(pantalla, x, y, ancho_texto)

        # La lista de la pestaña elegida ocupa el resto del panel, salvo una franja a la
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
        y_lista = self._zona_lista.y - self._desplazamiento
        if self._pestana == _PESTANA_PLAN:
            y_lista = self._dibujar_plan(pantalla, simulacion, x, y_lista)
        elif self._pestana == _PESTANA_OBJETIVOS:
            y_lista = self._dibujar_objetivos(pantalla, informe, x, y_lista)
        else:
            y_lista = self._dibujar_objetos(pantalla, simulacion, x, y_lista)
        pantalla.set_clip(None)

        # Lo que mide la lista cambia con la ejecución: si ha encogido, el
        # desplazamiento se ajusta para que no quede espacio vacío abajo.
        self._alto_lista = y_lista + self._desplazamiento - self._zona_lista.y
        self._desplazar(0)

        if self._lista_desborda:
            radio = self._ancho_barra // 2
            pygame.draw.rect(
                pantalla, _COLOR_BARRA_LISTA, self._barra_lista, border_radius=radio
            )
            pygame.draw.rect(
                pantalla, _COLOR_MANDO_LISTA, self._mando_lista, border_radius=radio
            )

    def _dibujar_pestanas(
        self, pantalla: pygame.Surface, x: int, y: int, ancho: int
    ) -> int:
        """Dibuja las pestañas en ``(x, y)`` y devuelve la ``y`` siguiente.

        Se reparten el ``ancho`` a partes iguales. La elegida es más clara y las
        demás, más oscuras. Debajo, una línea las separa de la lista.
        """
        alto = self._fuente_texto.get_height() + self._margen
        for indice, pestana in enumerate(_PESTANAS):
            izquierda = x + ancho * indice // len(_PESTANAS)
            derecha = x + ancho * (indice + 1) // len(_PESTANAS)
            rectangulo = pygame.Rect(izquierda, y, derecha - izquierda, alto)
            self._rectangulos_pestanas[pestana] = rectangulo

            color = (
                _COLOR_PESTANA_ELEGIDA if pestana == self._pestana else _COLOR_PESTANA
            )
            pygame.draw.rect(
                pantalla,
                color,
                rectangulo,
                border_top_left_radius=6,
                border_top_right_radius=6,
            )
            texto = self._fuente_texto.render(
                _truncar(self._fuente_texto, pestana, rectangulo.width),
                True,
                _COLOR_TEXTO,
            )
            pantalla.blit(texto, texto.get_rect(center=rectangulo.center))

        fondo = y + alto
        pygame.draw.line(
            pantalla, _COLOR_BORDE_PANEL, (x, fondo), (x + ancho, fondo), 2
        )
        return fondo + self._margen

    def _dibujar_plan(
        self, pantalla: pygame.Surface, simulacion: Simulacion, x: int, y: int
    ) -> int:
        """Dibuja las acciones del plan desde ``y`` y devuelve la ``y`` siguiente.

        Las acciones van en el orden del plan, numeradas desde 1. Guarda la fila de
        cada una, para saber cuál se pulsa.
        """
        self._filas_plan = []
        for numero, accion in enumerate(simulacion._acciones, start=1):
            clase = _clase_accion(accion, simulacion)
            error = simulacion._error if clase == _FALLIDA else None
            progreso = None
            if clase == _EN_EJECUCION:
                progreso = accion._progreso(simulacion._tiempo_simulacion)
            fila = self._dibujar_fila(
                pantalla,
                _COLORES_ACCION[clase],
                f"{numero}. {type(accion).__name__}",
                _detalles_accion(accion, error),
                x,
                y,
                progreso=progreso,
                pulsable=True,
            )
            self._filas_plan.append((fila, accion))
            y = fila.bottom + self._margen
        return y

    def _dibujar_objetivos(
        self, pantalla: pygame.Surface, informe: InformeVerificacion, x: int, y: int
    ) -> int:
        """Dibuja los objetivos desde ``y`` y devuelve la ``y`` siguiente."""
        for estado in informe.estados_objetivos:
            clase = _clase_objetivo(estado, informe)
            fila = self._dibujar_fila(
                pantalla,
                _COLORES_OBJETIVO[clase],
                _con_mayuscula(estado.objetivo._describir()),
                _detalles_objetivo(estado, clase),
                x,
                y,
            )
            y = fila.bottom + self._margen
        return y

    def _dibujar_objetos(
        self, pantalla: pygame.Surface, simulacion: Simulacion, x: int, y: int
    ) -> int:
        """Dibuja los objetos desde ``y`` y devuelve la ``y`` siguiente.

        Van agrupados por tipo, cada grupo con un título y el número de objetos.
        Un tipo sin objetos no se muestra, como los transportadores en un problema
        que no los tiene. Las cajas entregadas y las personas que ya no necesitan
        nada llevan el color más oscuro que tienen en el mundo.
        """
        grupos = [
            (
                "Drones",
                [
                    (dron.nombre, _COLOR_DRON, _detalles_dron(dron))
                    for dron in simulacion._drones
                ],
            ),
            (
                "Transportadores",
                [
                    (
                        transportador.nombre,
                        _COLOR_TRANSPORTADOR,
                        _detalles_transportador(transportador),
                    )
                    for transportador in simulacion._todos_los_transportadores
                ],
            ),
            (
                "Cajas",
                [
                    (
                        Renderizador._describir_caja(caja),
                        _COLOR_CAJA_ENTREGADA
                        if caja.estado == Caja.ENTREGADA
                        else _COLOR_CAJA,
                        _detalles_caja(caja),
                    )
                    for caja in simulacion._cajas
                ],
            ),
            (
                "Personas",
                [
                    (
                        persona.nombre,
                        _COLOR_PERSONA
                        if persona.necesidades
                        else _COLOR_PERSONA_NECESIDADES_CUBIERTAS,
                        _detalles_persona(persona),
                    )
                    for persona in simulacion._personas
                ],
            ),
        ]
        for titulo, filas in grupos:
            if not filas:
                continue
            y = self._dibujar_linea(
                pantalla, f"{titulo} ({len(filas)})", x, y, self._zona_lista.width
            )
            for nombre, color, detalles in filas:
                fila = self._dibujar_fila(pantalla, color, nombre, detalles, x, y)
                y = fila.bottom + self._margen
        return y

    def _dibujar_fila(
        self,
        pantalla: pygame.Surface,
        color: _Color,
        titulo: str,
        detalles: list[str],
        x: int,
        y: int,
        *,
        progreso: float | None = None,
        pulsable: bool = False,
    ) -> pygame.Rect:
        """Dibuja una fila de una lista en ``(x, y)`` y devuelve lo que ocupa.

        A la izquierda, un cuadrado de ``color``. A su derecha, ``titulo`` y, debajo,
        en letra más pequeña, los ``detalles``. Si se da ``progreso``, de 0 a 1,
        debajo va una barra con esa parte rellena. Si la fila es ``pulsable`` y el
        ratón está encima, se dibuja sobre un fondo más claro, para que se vea que
        se puede pulsar.
        """
        lado = self._fuente_texto.get_height()
        x_texto = x + lado + self._margen // 2
        ancho = self._zona_lista.right - x_texto
        superficies = [
            self._fuente_texto.render(linea, True, _COLOR_TEXTO)
            for linea in _partir_en_lineas(self._fuente_texto, titulo, ancho)
        ]
        for detalle in detalles:
            superficies += [
                self._fuente_detalle.render(linea, True, _COLOR_TEXTO_DETALLE)
                for linea in _partir_en_lineas(self._fuente_detalle, detalle, ancho)
            ]

        # El alto de la fila se conoce antes de dibujarla, para poner debajo el
        # fondo del ratón.
        alto_barra = self._margen // 2
        alto = sum(superficie.get_height() for superficie in superficies)
        if progreso is not None:
            alto += alto_barra + _INTERLINEADO
        fila = pygame.Rect(x, y, self._zona_lista.right - x, alto)

        raton = pygame.mouse.get_pos()
        if (
            pulsable
            and fila.collidepoint(raton)
            and self._zona_lista.collidepoint(raton)
        ):
            pygame.draw.rect(
                pantalla,
                _COLOR_FILA_BAJO_RATON,
                fila.inflate(0, self._margen // 2),
                border_radius=4,
            )

        pygame.draw.rect(pantalla, color, (x, y, lado, lado), border_radius=3)
        for superficie in superficies:
            pantalla.blit(superficie, (x_texto, y))
            y += superficie.get_height()

        if progreso is not None:
            barra = pygame.Rect(x_texto, y + _INTERLINEADO, ancho, alto_barra)
            pygame.draw.rect(pantalla, _COLOR_BARRA_LISTA, barra)
            pygame.draw.rect(
                pantalla,
                color,
                (barra.x, barra.y, int(barra.width * progreso), barra.h),
            )
        return fila

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
