"""Pruebas de la simulación visual con pygame, sin pantalla.

Usan el controlador de vídeo ``"dummy"`` de SDL, que no necesita ventana. Dibujan
todos los fotogramas de un plan pequeño, comprueban cómo se reparten la ventana y
el panel, manejan la ventana con clics programados y validan los argumentos de
``Mundo.simulacion_visual()``. Son las únicas pruebas que llegan al código de
dibujo, así que un error que solo aparece al dibujar un fotograma (por ejemplo,
llamar a ``Font.render()`` con argumentos por nombre, que pygame no acepta) se
encuentra aquí. No comprueban la imagen dibujada, solo posiciones y tamaños.
"""

import logging
import os
import unittest
from unittest import mock

# Las dos tienen que ponerse antes de que pygame arranque su sistema de vídeo.
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from simulador_pddl import (
    Brazo,
    Caja,
    CogerCaja,
    Contenido,
    Dron,
    EntregarCaja,
    Localizacion,
    Mover,
    MoverTransportador,
    Mundo,
    Persona,
    PersonaTieneContenido,
    PonerCajaEnTransportador,
    SacarCajaDeTransportador,
    Transportador,
)
from simulador_pddl.simulacion import InformeVerificacion
from simulador_pddl.visualizacion import (
    PanelControl,
    PanelLateral,
    Renderizador,
    panel_control,
    renderizador,
)

# Los contenidos de los problemas de este módulo. Un contenido no cambia al
# ejecutar un plan, así que todas las pruebas pueden compartirlos.
COMIDA = Contenido("comida")
MEDICINA = Contenido("medicina")
CONTENIDOS = (COMIDA, MEDICINA)


TAMANO_VENTANA = (1000, 700)


def crear_mundo() -> Mundo:
    """Crea un mundo cuyo plan usa dos brazos, un transportador y dos personas.

    Llega a todos los tipos de dibujo: cajas en una localización, en un brazo, en
    un transportador y entregadas, un transportador en una localización y
    llevado, y un dron moviéndose entre localizaciones.
    """
    deposito = Localizacion("deposito")
    loc1 = Localizacion("loc1")
    loc2 = Localizacion("loc2")
    izquierda = Brazo("izquierda")
    derecha = Brazo("derecha")
    dron = Dron("dron1", deposito, [izquierda, derecha])
    caja1 = Caja("caja1", deposito, COMIDA)
    caja2 = Caja("caja2", deposito, MEDICINA)
    transportador = Transportador("transportador1", deposito, 2)
    persona1 = Persona("persona1", loc1, COMIDA)
    persona2 = Persona("persona2", loc2, [MEDICINA])

    acciones = [
        CogerCaja(dron, izquierda, caja1, 0, 1),
        PonerCajaEnTransportador(dron, izquierda, caja1, transportador, 1, 1),
        CogerCaja(dron, izquierda, caja2, 2, 1),
        MoverTransportador(dron, derecha, transportador, deposito, loc1, 3, 2),
        SacarCajaDeTransportador(dron, derecha, caja1, transportador, 5, 1),
        EntregarCaja(dron, derecha, caja1, persona1, 6, 1),
        Mover(dron, loc1, loc2, 7, 2),
        EntregarCaja(dron, izquierda, caja2, persona2, 9, 1),
    ]
    objetivos = [
        PersonaTieneContenido(persona1, COMIDA),
        PersonaTieneContenido(persona2, MEDICINA),
    ]

    return Mundo(
        acciones,
        localizaciones=[deposito, loc1, loc2],
        drones=[dron],
        cajas=[caja1, caja2],
        personas=[persona1, persona2],
        contenidos=CONTENIDOS,
        transportadores=[transportador],
        objetivos=objetivos,
    )


def evento_raton(tipo_evento: int, posicion: tuple[int, int]) -> pygame.event.Event:
    """Devuelve un evento ``tipo_evento`` del botón izquierdo en ``posicion``."""
    return pygame.event.Event(tipo_evento, pos=posicion, button=pygame.BUTTON_LEFT)


class TestDibujoSinPantalla(unittest.TestCase):
    """El renderizador y el panel dibujan cada fotograma sin lanzar errores."""

    def setUp(self) -> None:
        """Silencia el registro y crea el mundo, el renderizador y el panel."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.mundo = crear_mundo()
        self.simulacion = self.mundo._simulacion
        self.renderizador = Renderizador(*TAMANO_VENTANA)
        self.addCleanup(self.renderizador._cerrar)
        self.renderizador._poner_localizaciones(self.simulacion._localizaciones)
        self.control = PanelControl(self.renderizador._ancho, self.renderizador._alto)

    def dibujar_fotograma(self) -> None:
        """Dibuja una vez la simulación y el panel de control."""
        self.renderizador._dibujar(self.simulacion)
        self.control._dibujar(self.renderizador._pantalla, self.simulacion)

    def test_se_dibujan_todos_los_fotogramas_del_plan(self) -> None:
        """Comprueba que se dibujan todos los fotogramas del plan.

        Al terminar, el veredicto es ``"VÁLIDO"``.
        """
        self.simulacion._reproducir()
        self.dibujar_fotograma()

        while not self.simulacion._terminada:
            self.simulacion._actualizar(0.25)
            self.assertFalse(self.simulacion._tiene_error, self.simulacion._error)
            self.dibujar_fotograma()

        self.assertEqual(
            self.simulacion._crear_informe().veredicto, InformeVerificacion.VALIDO
        )

    def test_caja_que_se_saca_se_dibuja_en_el_transportador(self) -> None:
        """Comprueba que una caja que se saca de un transportador sigue dibujada en él.

        La descarga saca la caja del transportador al empezar y la pone en el brazo
        al terminar. Mientras tanto, la caja tiene que dibujarse en el
        transportador, no en la localización, donde nunca está.
        """
        transportador = self.simulacion._todos_los_transportadores[0]
        caja1 = self.simulacion._cajas[0]
        drones = self.simulacion._drones

        # El SacarCajaDeTransportador de caja1 va de t=5 a t=6.
        self.simulacion._reproducir()
        self.simulacion._actualizar(5.5)
        self.dibujar_fotograma()

        self.assertEqual(transportador.cajas_dentro, [])
        self.assertEqual(self.renderizador._cajas_dibujadas_en(transportador), [caja1])
        self.assertTrue(
            self.renderizador._caja_en_transportador(caja1, [transportador])
        )
        self.assertFalse(self.renderizador._caja_en_un_brazo(caja1, drones))

        # Al final de la descarga la sujeta el brazo, y el transportador no.
        self.simulacion._actualizar(1)
        self.assertEqual(self.renderizador._cajas_dibujadas_en(transportador), [])
        self.assertTrue(self.renderizador._caja_en_un_brazo(caja1, drones))

    def test_las_ayudas_se_dibujan_bajo_el_raton(self) -> None:
        """Comprueba que las ayudas se dibujan cuando el ratón está sobre un elemento.

        La ayuda de un elemento solo se dibuja mientras el ratón está sobre él, así
        que el ratón se mueve por una cuadrícula de puntos que cubre la ventana. Al
        menos un punto tiene que caer sobre un elemento, si no, la prueba no llegaría
        al código de las ayudas.
        """
        ayudas = 0
        for x in range(0, TAMANO_VENTANA[0], 25):
            for y in range(0, TAMANO_VENTANA[1], 25):
                with mock.patch("pygame.mouse.get_pos", return_value=(x, y)):
                    self.dibujar_fotograma()
                ayudas += self.renderizador._ayuda is not None

        self.assertGreater(ayudas, 0)

    def test_una_ayuda_alta_no_queda_debajo_del_panel(self) -> None:
        """Comprueba que una ayuda que no cabe debajo de su elemento sube.

        Veinte personas en una localización de la fila de abajo dan una ayuda de
        veinte líneas, que no cabe entre ellas y el panel de control. La ayuda tiene
        que subir hasta acabar encima del panel, a la distancia del margen.
        """
        localizaciones = [Localizacion(f"loc{i}") for i in range(4)]
        personas = [
            Persona(f"persona{i}", localizaciones[3], COMIDA) for i in range(20)
        ]
        mundo = Mundo(
            [],
            localizaciones=localizaciones,
            drones=[],
            cajas=[],
            personas=personas,
            contenidos=CONTENIDOS,
        )
        ancho, alto = Renderizador.ANCHO_MINIMO, Renderizador.ALTO_MINIMO
        pantalla = Renderizador(ancho, alto)
        self.addCleanup(pantalla._cerrar)
        pantalla._poner_localizaciones(mundo._simulacion._localizaciones)
        pantalla._reservar_panel(PanelControl(ancho, alto)._alto_panel)

        # El ratón recorre la ventana, y se anota el fondo de cada ayuda dibujada.
        fondos: list[pygame.Rect] = []
        for x in range(0, ancho, 20):
            for y in range(0, alto, 20):
                with (
                    mock.patch("pygame.mouse.get_pos", return_value=(x, y)),
                    mock.patch("pygame.draw.rect", wraps=pygame.draw.rect) as rect,
                ):
                    pantalla._dibujar(mundo._simulacion)
                fondos += [
                    pygame.Rect(llamada.args[2])
                    for llamada in rect.call_args_list
                    if llamada.args[1] == renderizador._COLOR_FONDO_AYUDA
                ]

        limite = pantalla._alto_mundo - Renderizador._MARGEN_AYUDA
        self.assertTrue(fondos)
        self.assertLessEqual(max(fondo.bottom for fondo in fondos), limite)
        # Al menos una ayuda ha tenido que subir: si no, la prueba no comprobaría
        # nada.
        self.assertIn(limite, [fondo.bottom for fondo in fondos])

    def test_se_dibuja_el_mensaje_de_error(self) -> None:
        """Comprueba que se dibujan mensajes de error cortos y largos.

        Se llama a ``_dibujar_error()`` directamente porque ``_dibujar()`` solo lo
        llama cuando hay un error, y este mundo no tiene ninguno.
        """
        self.dibujar_fotograma()
        self.renderizador._dibujar_error("corto")
        # Más largo que el ancho de la ventana, así que hay que cortarlo.
        self.renderizador._dibujar_error("un mensaje de error muy largo " * 40)

    def test_la_ventana_y_el_panel_se_pueden_redimensionar(self) -> None:
        """Comprueba que la ventana y el panel se dibujan tras cada cambio de tamaño."""
        for ancho, alto in ((800, 600), (1600, 900), (300, 200)):
            self.renderizador._redimensionar(ancho, alto)
            self.control._redimensionar(
                self.renderizador._ancho, self.renderizador._alto
            )
            self.dibujar_fotograma()

        # Un tamaño menor que el mínimo se sube al mínimo.
        self.assertEqual(self.renderizador._ancho, Renderizador.ANCHO_MINIMO)
        self.assertEqual(self.renderizador._alto, Renderizador.ALTO_MINIMO)

    def test_el_mundo_deja_al_panel_el_espacio_que_ocupa(self) -> None:
        """Comprueba que el mundo termina justo donde empieza el panel.

        El panel escala con la ventana, así que el espacio que ocupa cambia: el
        renderizador tiene que reservar exactamente ese espacio, y todas las
        localizaciones tienen que quedar por encima de él.
        """
        for ancho, alto in ((800, 600), (1400, 850), (1960, 1000), (3000, 1400)):
            with self.subTest(ancho=ancho, alto=alto):
                self.renderizador._redimensionar(ancho, alto)
                self.control._redimensionar(
                    self.renderizador._ancho, self.renderizador._alto
                )
                self.renderizador._reservar_panel(self.control._alto_panel)

                arriba_panel = (
                    self.control._boton_reproducir._rectangulo.y
                    - 2 * self.control._alto_linea_info
                )
                self.assertEqual(self.renderizador._alto_mundo, arriba_panel)

                radio = self.renderizador._radio_localizacion
                for _, y in self.renderizador._posiciones_localizaciones.values():
                    self.assertLessEqual(y + radio, arriba_panel)

                self.dibujar_fotograma()

    def test_los_controles_caben_en_la_ventana_mas_estrecha(self) -> None:
        """Comprueba que los controles se pueden usar con el ancho mínimo de ventana.

        ``PanelControl`` no impone un ancho mínimo a los botones ni al deslizador,
        porque la ventana nunca es más estrecha que ``Renderizador.ANCHO_MINIMO``.
        Si ese mínimo bajara, esta prueba avisaría de que ya no basta: cada etiqueta
        tiene que caber en su botón y cada tramo del deslizador tiene que medir al
        menos 24 píxeles, el tamaño mínimo de un objetivo de clic de WCAG 2.2.
        """
        self.renderizador._redimensionar(1, 1)
        self.control._redimensionar(self.renderizador._ancho, self.renderizador._alto)
        self.assertEqual(self.control._ancho, Renderizador.ANCHO_MINIMO)

        for boton in (
            self.control._boton_reproducir,
            self.control._boton_pausa,
            self.control._boton_reiniciar,
        ):
            with self.subTest(boton=boton._texto):
                ancho_etiqueta = boton._fuente.size(boton._texto)[0]
                ancho_disponible = (
                    boton._rectangulo.width - 2 * panel_control._MARGEN_ETIQUETA_BOTON
                )
                self.assertLessEqual(ancho_etiqueta, ancho_disponible)

        deslizador = self.control._deslizador
        self.assertGreaterEqual(deslizador._ancho_tramo, 24)
        self.assertLessEqual(deslizador._x + deslizador._ancho, self.control._ancho)

        self.dibujar_fotograma()

    def test_repr_de_la_ventana_y_del_panel(self) -> None:
        """Comprueba ``repr()`` del renderizador, el panel, un botón y el deslizador."""
        ancho, alto = TAMANO_VENTANA
        self.assertEqual(
            repr(self.renderizador), f"Renderizador(ancho={ancho}, alto={alto})"
        )
        self.assertEqual(
            repr(self.control), f"PanelControl(ancho={ancho}, alto={alto})"
        )
        self.assertEqual(
            repr(self.control._boton_reproducir), "Boton('Reproducir', activado=True)"
        )
        self.assertEqual(repr(self.control._deslizador), "Deslizador(valor=1)")

    def test_el_panel_atiende_clics_y_arrastres(self) -> None:
        """Comprueba la respuesta del panel a clics en sus botones y su deslizador."""
        comandos = [
            self.control._gestionar_evento(
                evento_raton(pygame.MOUSEBUTTONDOWN, boton._rectangulo.center)
            )
            for boton in (
                self.control._boton_reproducir,
                self.control._boton_pausa,
                self.control._boton_reiniciar,
            )
        ]
        self.assertEqual(comandos, ["reproducir", "pausar", "reiniciar"])

        # Un botón desactivado no responde.
        self.control._boton_reproducir._activado = False
        clic = evento_raton(
            pygame.MOUSEBUTTONDOWN, self.control._boton_reproducir._rectangulo.center
        )
        self.assertIsNone(self.control._gestionar_evento(clic))

        # Pulsar en el extremo derecho de la barra elige la velocidad más rápida.
        deslizador = self.control._deslizador
        y = self.control._boton_pausa._rectangulo.centery
        extremo_derecho = (deslizador._x + deslizador._ancho, y)
        self.control._gestionar_evento(
            evento_raton(pygame.MOUSEBUTTONDOWN, extremo_derecho)
        )
        self.assertEqual(self.control._deslizador._valor, 16)

        # Arrastrar hasta el borde izquierdo elige la más lenta.
        self.control._gestionar_evento(evento_raton(pygame.MOUSEMOTION, (0, y)))
        self.control._gestionar_evento(evento_raton(pygame.MOUSEBUTTONUP, (0, y)))
        self.assertEqual(self.control._deslizador._valor, 0.25)
        self.dibujar_fotograma()

    def test_solo_el_boton_izquierdo_del_raton_cuenta(self) -> None:
        """Comprueba que otros botones del ratón no pulsan ni cambian la velocidad.

        La rueda del ratón también produce eventos ``MOUSEBUTTONDOWN``, con los
        botones 4 y 5, así que sin filtrar el botón del ratón cambiaría la velocidad
        al girarla sobre el deslizador.
        """
        deslizador = self.control._deslizador
        y = self.control._boton_pausa._rectangulo.centery
        extremo_derecho = (deslizador._x + deslizador._ancho, y)
        otros_botones = (
            pygame.BUTTON_MIDDLE,
            pygame.BUTTON_RIGHT,
            pygame.BUTTON_WHEELUP,
            pygame.BUTTON_WHEELDOWN,
        )

        for boton_raton in otros_botones:
            with self.subTest(boton_raton=boton_raton):
                clic_en_boton = pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    pos=self.control._boton_reproducir._rectangulo.center,
                    button=boton_raton,
                )
                self.assertIsNone(self.control._gestionar_evento(clic_en_boton))

                clic_en_barra = pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, pos=extremo_derecho, button=boton_raton
                )
                self.control._gestionar_evento(clic_en_barra)
                self.assertEqual(self.control._deslizador._valor, 1)
                self.assertFalse(self.control._deslizador._arrastrando)

        # Soltar otro botón mientras se arrastra con el izquierdo no termina el
        # arrastre.
        self.control._gestionar_evento(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, pos=extremo_derecho, button=pygame.BUTTON_LEFT
            )
        )
        self.control._gestionar_evento(
            pygame.event.Event(
                pygame.MOUSEBUTTONUP, pos=extremo_derecho, button=pygame.BUTTON_RIGHT
            )
        )
        self.control._gestionar_evento(
            pygame.event.Event(
                pygame.MOUSEMOTION, pos=(0, y), button=pygame.BUTTON_LEFT
            )
        )
        self.assertEqual(self.control._deslizador._valor, 0.25)


class TestSimulacionVisualSinPantalla(unittest.TestCase):
    """``simulacion_visual()`` como la usaría un usuario, con eventos programados."""

    def setUp(self) -> None:
        """Silencia el registro y crea el mundo."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.mundo = crear_mundo()

    def ejecutar_ventana(
        self,
        fotogramas: int,
        eventos_en: dict[int, list[pygame.event.Event]] | None = None,
    ) -> InformeVerificacion:
        """Ejecuta ``simulacion_visual()`` durante un número de fotogramas, sin usuario.

        Se sustituyen los eventos y el reloj de pygame: cada fotograma recibe los
        eventos que se le dan, un evento ``QUIT`` cierra la ventana tras el último
        fotograma, y cada fotograma cuenta como 0.25 segundos simulados, tarde lo
        que tarde de verdad. Así la ejecución es rápida y da el mismo resultado en
        todas las máquinas.

        Args:
            fotogramas: Cuántos fotogramas pasan antes de que se cierre la ventana.
            eventos_en: Los eventos que recibe cada fotograma, con su índice
                (desde 0) como clave. Por defecto, ninguno.

        Returns:
            El ``InformeVerificacion`` que devuelve ``simulacion_visual()`` cuando
            se cierra la ventana.
        """
        eventos_en = eventos_en or {}
        eventos = [eventos_en.get(fotograma, []) for fotograma in range(fotogramas)]
        eventos.append([pygame.event.Event(pygame.QUIT)])
        reloj = mock.Mock()
        reloj.tick.return_value = 250

        with (
            mock.patch("pygame.event.get", side_effect=eventos),
            mock.patch("pygame.time.Clock", return_value=reloj),
        ):
            return self.mundo.simulacion_visual(*TAMANO_VENTANA)

    def test_la_ventana_reserva_para_el_panel_lo_que_ocupa(self) -> None:
        """Comprueba que se reserva el alto del panel al abrir y al redimensionar.

        ``simulacion_visual()`` tiene que avisar al renderizador al crear el panel
        y cada vez que el panel se vuelve a colocar tras un cambio de tamaño.
        """
        pygame.init()
        alto_panel = PanelControl(*TAMANO_VENTANA)._alto_panel
        cambio_tamano = pygame.event.Event(
            pygame.VIDEORESIZE, w=TAMANO_VENTANA[0], h=TAMANO_VENTANA[1]
        )

        with mock.patch.object(
            Renderizador,
            "_reservar_panel",
            autospec=True,
            side_effect=Renderizador._reservar_panel,
        ) as reservar_panel:
            self.ejecutar_ventana(3, {1: [cambio_tamano]})

        self.assertEqual(reservar_panel.call_count, 2)
        for llamada in reservar_panel.call_args_list:
            self.assertEqual(llamada.args[1], alto_panel)

    def test_el_boton_del_panel_lateral_le_reserva_su_ancho(self) -> None:
        """Comprueba que abrir y cerrar el panel lateral cambia el ancho del mundo.

        Al crear la ventana, el panel está cerrado y solo se reserva la esquina de
        su botón. Cada clic en el botón vuelve a avisar al renderizador.
        """
        pygame.init()
        alto_panel = PanelControl(*TAMANO_VENTANA)._alto_panel
        lateral = PanelLateral(*TAMANO_VENTANA, alto_panel)
        clic = evento_raton(pygame.MOUSEBUTTONDOWN, lateral._boton._rectangulo.center)

        with mock.patch.object(
            Renderizador,
            "_reservar_panel_lateral",
            autospec=True,
            side_effect=Renderizador._reservar_panel_lateral,
        ) as reservar_panel_lateral:
            self.ejecutar_ventana(3, {0: [clic], 1: [clic]})

        llamadas = [
            llamada.args[1:] for llamada in reservar_panel_lateral.call_args_list
        ]
        cerrado = (0, lateral._ancho_esquina)
        abierto = (lateral._rectangulo.width, 0)
        self.assertEqual(llamadas, [cerrado, abierto, cerrado])

    def test_al_redimensionar_el_panel_lateral_sigue_abierto(self) -> None:
        """Comprueba que un cambio de tamaño conserva el panel lateral abierto.

        Después del cambio de tamaño, la ventana tiene que volver a reservar el
        ancho del panel abierto, no solo la esquina de su botón. Con el controlador
        ``"dummy"`` la ventana no cambia de tamaño de verdad, como en
        ``test_la_ventana_reserva_para_el_panel_lo_que_ocupa``, pero se recorre el
        mismo código.
        """
        pygame.init()
        alto_panel = PanelControl(*TAMANO_VENTANA)._alto_panel
        lateral = PanelLateral(*TAMANO_VENTANA, alto_panel)
        clic = evento_raton(pygame.MOUSEBUTTONDOWN, lateral._boton._rectangulo.center)
        cambio_tamano = pygame.event.Event(
            pygame.VIDEORESIZE, w=TAMANO_VENTANA[0], h=TAMANO_VENTANA[1]
        )

        with mock.patch.object(
            Renderizador,
            "_reservar_panel_lateral",
            autospec=True,
            side_effect=Renderizador._reservar_panel_lateral,
        ) as reservar_panel_lateral:
            self.ejecutar_ventana(3, {0: [clic], 1: [cambio_tamano]})

        llamadas = [
            llamada.args[1:] for llamada in reservar_panel_lateral.call_args_list
        ]
        cerrado = (0, lateral._ancho_esquina)
        abierto = (lateral._rectangulo.width, 0)
        self.assertEqual(llamadas, [cerrado, abierto, abierto])

    def clic(self, nombre_boton: str) -> pygame.event.Event:
        """Devuelve un clic izquierdo en el centro del botón ``nombre_boton``.

        El panel lo crea la ventana por dentro; se construye otro del mismo tamaño
        solo para saber dónde estará el botón.
        """
        pygame.init()
        boton = getattr(PanelControl(*TAMANO_VENTANA), nombre_boton)
        return evento_raton(pygame.MOUSEBUTTONDOWN, boton._rectangulo.center)

    def test_plan_reproducido_hasta_el_final_es_valido(self) -> None:
        """Comprueba que un plan reproducido hasta el final es ``"VÁLIDO"``."""
        self.mundo._simulacion._reproducir()
        informe = self.ejecutar_ventana(fotogramas=60)
        self.assertEqual(informe.veredicto, informe.VALIDO)

    def test_ventana_cerrada_antes_de_tiempo_es_incompleto(self) -> None:
        """Comprueba que cerrar la ventana antes de tiempo da ``"INCOMPLETO"``."""
        self.mundo._simulacion._reproducir()
        informe = self.ejecutar_ventana(fotogramas=4)
        self.assertEqual(informe.veredicto, informe.INCOMPLETO)

    def test_nada_avanza_hasta_pulsar_reproducir(self) -> None:
        """Comprueba que el plan no avanza antes de pulsar reproducir."""
        informe = self.ejecutar_ventana(fotogramas=60)
        self.assertEqual(informe.veredicto, informe.INCOMPLETO)
        self.assertEqual(self.mundo._simulacion._tiempo_simulacion, 0)

    def test_boton_reproducir_ejecuta_el_plan(self) -> None:
        """Comprueba que pulsar reproducir ejecuta el plan hasta el final."""
        informe = self.ejecutar_ventana(
            fotogramas=60, eventos_en={0: [self.clic("_boton_reproducir")]}
        )
        self.assertEqual(informe.veredicto, informe.VALIDO)

    def test_boton_pausa_detiene_el_plan(self) -> None:
        """Comprueba que pulsar pausa detiene el plan donde estaba."""
        informe = self.ejecutar_ventana(
            fotogramas=60,
            eventos_en={
                0: [self.clic("_boton_reproducir")],
                8: [self.clic("_boton_pausa")],
            },
        )
        self.assertEqual(informe.veredicto, informe.INCOMPLETO)
        # Se ejecutaron los fotogramas 0 a 7, a 0.25 segundos cada uno.
        self.assertEqual(self.mundo._simulacion._tiempo_simulacion, 2.0)

    def test_boton_reiniciar_vuelve_al_principio(self) -> None:
        """Comprueba que pulsar reiniciar vuelve al instante 0, en pausa."""
        self.ejecutar_ventana(
            fotogramas=60,
            eventos_en={
                0: [self.clic("_boton_reproducir")],
                8: [self.clic("_boton_reiniciar")],
            },
        )
        self.assertEqual(self.mundo._simulacion._tiempo_simulacion, 0)
        self.assertFalse(self.mundo._simulacion._reproduciendo)


class TestArgumentosDeEjecucion(unittest.TestCase):
    """Un tipo incorrecto es un ``TypeError``, un valor incorrecto un ``ValueError``."""

    def setUp(self) -> None:
        """Crea el mundo."""
        self.mundo = crear_mundo()

    def test_fps_tiene_que_ser_un_entero(self) -> None:
        """Comprueba que un ``fps`` de tipo incorrecto lanza ``TypeError``."""
        for fps in ("60", 30.0, None, True):
            with self.subTest(fps=fps), self.assertRaises(TypeError):
                self.mundo.simulacion_visual(fps=fps)  # type: ignore[arg-type]

    def test_tamano_de_ventana_tiene_que_ser_un_entero(self) -> None:
        """Comprueba que un ``ancho`` o ``alto`` de tipo incorrecto lanza ``TypeError``.

        ``True`` y ``False`` también se rechazan, aunque ``bool`` sea una subclase
        de ``int``.
        """
        for tamano in ("800", 800.0, True, False):
            for argumento in ("ancho", "alto"):
                with (
                    self.subTest(argumento=argumento, tamano=tamano),
                    self.assertRaises(TypeError),
                ):
                    self.mundo.simulacion_visual(**{argumento: tamano})  # type: ignore[arg-type]

    def test_titulo_tiene_que_ser_una_cadena(self) -> None:
        """Comprueba que un ``titulo`` que no es una cadena lanza ``TypeError``."""
        for titulo in (5, None, b"titulo"):
            with self.subTest(titulo=titulo), self.assertRaises(TypeError):
                self.mundo.simulacion_visual(titulo=titulo)  # type: ignore[arg-type]

    def test_fps_tiene_que_ser_mayor_que_cero(self) -> None:
        """Comprueba que un ``fps`` de 0 o menos lanza ``ValueError``."""
        for fps in (0, -5):
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                self.mundo.simulacion_visual(fps=fps)


if __name__ == "__main__":
    unittest.main()
