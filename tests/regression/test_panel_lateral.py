"""Pruebas del panel lateral de la simulación visual, sin pantalla.

Comprueban el estado del plan que muestra el panel (``"EN CURSO"`` mientras el
plan no ha terminado ni ha fallado ninguna acción, y el veredicto después), su
línea de objetivos y cómo va cada objetivo de la lista, que el botón lo abre y lo
cierra, que abierto deja al mundo solo el ancho que queda, que la rueda del ratón
y la barra desplazan la lista y que se dibuja, abierto y cerrado, en la ventana
más pequeña. Como las de ``test_simulacion_visual.py``, no comprueban la imagen
dibujada, solo posiciones y tamaños.
"""

from __future__ import annotations

import logging
import math
import os
import unittest
from typing import TYPE_CHECKING
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
    DronEnLocalizacion,
    EntregarCaja,
    Localizacion,
    Mover,
    Mundo,
    Persona,
    PersonaTieneContenido,
)
from simulador_pddl.simulacion import InformeVerificacion
from simulador_pddl.visualizacion import PanelControl, PanelLateral, Renderizador
from simulador_pddl.visualizacion.panel_lateral import (
    _clase_objetivo,
    _detalles_objetivo,
    _estado_del_plan,
    _partir_en_lineas,
    _texto_objetivos,
)

if TYPE_CHECKING:
    from simulador_pddl import Objetivo

# Los contenidos de los problemas de este módulo. Un contenido no cambia al
# ejecutar un plan, así que todas las pruebas pueden compartirlos.
COMIDA = Contenido("comida")
CONTENIDOS = (COMIDA,)

TAMANO_VENTANA = (1000, 700)


def crear_mundo(*, objetivos: str = "alcanzables", con_error: bool = False) -> Mundo:
    """Crea un mundo en el que un dron lleva una caja a una persona.

    El dron coge la caja de t=0 a t=1, va del depósito a loc1 de t=1 a t=2 y la
    entrega de t=2 a t=3.

    Args:
        objetivos: ``"alcanzables"`` (la persona recibe la comida), ``"uno sin
            lograr"`` (además, el dron tiene que acabar en el depósito), ``"de
            cada clase"`` (además, el dron tiene que acabar en loc2, adonde nunca
            va) o ``"ninguno"``.
        con_error: Si al final hay un movimiento que sale del depósito, donde el
            dron ya no está, y falla.
    """
    deposito = Localizacion("deposito")
    loc1 = Localizacion("loc1")
    loc2 = Localizacion("loc2")
    brazo = Brazo("brazo")
    dron = Dron("dron1", deposito, [brazo])
    caja = Caja("caja1", deposito, COMIDA)
    persona = Persona("persona1", loc1, COMIDA)

    acciones = [
        CogerCaja(dron, brazo, caja, 0, 1),
        Mover(dron, deposito, loc1, 1, 1),
        EntregarCaja(dron, brazo, caja, persona, 2, 1),
    ]
    if con_error:
        acciones.append(Mover(dron, deposito, loc1, 3, 1))

    lista_objetivos: list[Objetivo] = []
    if objetivos != "ninguno":
        lista_objetivos.append(PersonaTieneContenido(persona, COMIDA))
    if objetivos in ("uno sin lograr", "de cada clase"):
        lista_objetivos.append(DronEnLocalizacion(dron, deposito))
    if objetivos == "de cada clase":
        lista_objetivos.append(DronEnLocalizacion(dron, loc2))

    return Mundo(
        acciones,
        localizaciones=[deposito, loc1, loc2],
        drones=[dron],
        cajas=[caja],
        personas=[persona],
        contenidos=CONTENIDOS,
        objetivos=lista_objetivos,
    )


def raton(tipo_evento: int, posicion: tuple[int, int]) -> pygame.event.Event:
    """Devuelve un evento ``tipo_evento`` del botón izquierdo en ``posicion``."""
    return pygame.event.Event(tipo_evento, pos=posicion, button=pygame.BUTTON_LEFT)


class TestEstadoDelPlan(unittest.TestCase):
    """El estado del plan y la línea de objetivos que muestra el panel."""

    def setUp(self) -> None:
        """Silencia el registro."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_mientras_el_plan_no_ha_terminado_esta_en_curso(self) -> None:
        """Comprueba que el estado es ``"EN CURSO"`` y no ``"INCOMPLETO"``.

        Un objetivo cumplido a mitad del plan aún puede deshacerse, así que el
        veredicto de un plan sin terminar sería siempre ``"INCOMPLETO"``.
        """
        mundo = crear_mundo()
        for instante in (0, 1.5, 2.5):
            with self.subTest(instante=instante):
                informe = mundo.avanzar_hasta(instante)
                self.assertEqual(informe.veredicto, InformeVerificacion.INCOMPLETO)
                self.assertEqual(_estado_del_plan(informe), "EN CURSO")

    def test_al_terminar_el_estado_es_el_veredicto(self) -> None:
        """Comprueba los tres veredictos de un plan que termina sin errores."""
        casos = {
            "alcanzables": InformeVerificacion.VALIDO,
            "uno sin lograr": InformeVerificacion.NO_RESUELVE,
            "ninguno": InformeVerificacion.EJECUTABLE,
        }
        for objetivos, veredicto in casos.items():
            with self.subTest(objetivos=objetivos):
                informe = crear_mundo(objetivos=objetivos).avanzar_hasta(math.inf)
                self.assertEqual(_estado_del_plan(informe), veredicto)

    def test_si_falla_una_accion_el_estado_es_no_ejecutable(self) -> None:
        """Comprueba que el estado es el veredicto en cuanto falla una acción."""
        informe = crear_mundo(con_error=True).avanzar_hasta(math.inf)

        self.assertEqual(_estado_del_plan(informe), InformeVerificacion.NO_EJECUTABLE)

    def test_linea_de_objetivos(self) -> None:
        """Comprueba la línea de objetivos, con y sin objetivos."""
        mundo = crear_mundo(objetivos="uno sin lograr")
        self.assertEqual(
            _texto_objetivos(mundo.verificar()), "Objetivos cumplidos: 1/2"
        )
        self.assertEqual(
            _texto_objetivos(mundo.avanzar_hasta(math.inf)),
            "Objetivos cumplidos: 1/2",
        )
        self.assertEqual(
            _texto_objetivos(crear_mundo(objetivos="ninguno").verificar()),
            "Sin objetivos",
        )


class TestObjetivosDeLaLista(unittest.TestCase):
    """Cómo va cada objetivo de la lista, sus detalles y cómo se parte el texto."""

    def setUp(self) -> None:
        """Silencia el registro."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_clase_de_cada_objetivo(self) -> None:
        """Comprueba las cuatro clases de objetivo a lo largo del plan.

        La persona recibe la comida en t=3. El dron está en el depósito al empezar
        y lo deja en t=2, al terminar el movimiento, y nunca llega a loc2. Un
        objetivo que nunca se ha cumplido solo deja de estar pendiente al terminar
        el plan.
        """
        mundo = crear_mundo(objetivos="de cada clase")
        casos = {
            1.5: ["pendiente", "cumplido", "pendiente"],
            2.5: ["pendiente", "roto", "pendiente"],
            math.inf: ["cumplido", "roto", "no logrado"],
        }
        for instante, clases in casos.items():
            with self.subTest(instante=instante):
                informe = mundo.avanzar_hasta(instante)
                self.assertEqual(
                    [
                        _clase_objetivo(estado, informe)
                        for estado in informe.estados_objetivos
                    ],
                    clases,
                )

    def test_si_falla_una_accion_los_pendientes_no_se_logran(self) -> None:
        """Comprueba que un plan que falla deja sin lograr lo que estaba pendiente."""
        informe = crear_mundo(objetivos="de cada clase", con_error=True).avanzar_hasta(
            math.inf
        )

        self.assertEqual(
            _clase_objetivo(informe.estados_objetivos[2], informe), "no logrado"
        )

    def test_detalles_de_un_objetivo(self) -> None:
        """Comprueba los detalles de un objetivo pendiente, cumplido y roto."""
        mundo = crear_mundo(objetivos="uno sin lograr")
        informe = mundo.avanzar_hasta(2.5)
        estado_persona, estado_dron = informe.estados_objetivos

        self.assertEqual(
            _detalles_objetivo(estado_persona, "pendiente"),
            [
                "Todavía no se ha cumplido",
                "Ahora: la persona persona1 no posee ninguna caja",
            ],
        )
        self.assertEqual(
            _detalles_objetivo(estado_dron, "roto"),
            [
                "Se cumplió en t=0.00s y se rompió en t=2.00s",
                (
                    "Ahora: el dron dron1 está en la localización loc1, no en la "
                    "localización deposito"
                ),
            ],
        )

        informe = mundo.avanzar_hasta(math.inf)
        self.assertEqual(
            _detalles_objetivo(informe.estados_objetivos[0], "cumplido"),
            ["Cumplido desde t=3.00s"],
        )

    def test_partir_en_lineas(self) -> None:
        """Comprueba que el texto se parte por palabras sin pasar del ancho.

        Una palabra que no cabe sola en una línea se acorta con puntos suspensivos.
        """
        pygame.font.init()
        fuente = pygame.font.SysFont(None, 18)
        texto = "la persona persona1 posee una caja con el contenido 'comida'"

        lineas = _partir_en_lineas(fuente, texto, 120)

        self.assertGreater(len(lineas), 1)
        self.assertEqual(" ".join(lineas).split(), texto.split())
        for linea in lineas:
            self.assertLessEqual(fuente.size(linea)[0], 120)

        [acortada] = _partir_en_lineas(fuente, "transportador_muy_largo", 60)
        self.assertTrue(acortada.endswith("..."))
        self.assertLessEqual(fuente.size(acortada)[0], 60)


class TestPanelLateral(unittest.TestCase):
    """El botón del panel, el ancho que ocupa y su dibujo."""

    def setUp(self) -> None:
        """Silencia el registro y crea la ventana, los dos paneles y el mundo."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        self.mundo = crear_mundo()
        self.simulacion = self.mundo._simulacion
        self.renderizador = Renderizador(*TAMANO_VENTANA)
        self.addCleanup(self.renderizador._cerrar)
        self.renderizador._poner_localizaciones(self.simulacion._localizaciones)
        self.control = PanelControl(*TAMANO_VENTANA)
        self.lateral = PanelLateral(*TAMANO_VENTANA, self.control._alto_panel)

    def clic_en(self, lateral: PanelLateral) -> pygame.event.Event:
        """Devuelve un clic izquierdo en el centro del botón de ``lateral``."""
        return raton(pygame.MOUSEBUTTONDOWN, lateral._boton._rectangulo.center)

    def test_el_boton_abre_y_cierra_el_panel(self) -> None:
        """Comprueba que el panel empieza cerrado y que cada clic lo alterna."""
        self.assertFalse(self.lateral._abierto)
        self.assertEqual(self.lateral._ancho_ocupado, 0)
        self.assertGreater(self.lateral._ancho_esquina, 0)

        self.assertTrue(self.lateral._gestionar_evento(self.clic_en(self.lateral)))
        self.assertTrue(self.lateral._abierto)
        self.assertEqual(self.lateral._boton._texto, "Ocultar panel")
        self.assertEqual(self.lateral._ancho_ocupado, self.lateral._rectangulo.width)
        self.assertEqual(self.lateral._ancho_esquina, 0)

        self.assertTrue(self.lateral._gestionar_evento(self.clic_en(self.lateral)))
        self.assertFalse(self.lateral._abierto)
        self.assertEqual(self.lateral._boton._texto, "Mostrar panel")

    def test_otros_eventos_no_cambian_el_panel(self) -> None:
        """Comprueba que solo un clic izquierdo en el botón abre el panel."""
        derecho = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=self.lateral._boton._rectangulo.center,
            button=pygame.BUTTON_RIGHT,
        )
        fuera = raton(pygame.MOUSEBUTTONDOWN, (0, 0))
        for evento in (derecho, fuera):
            with self.subTest(evento=evento):
                self.assertFalse(self.lateral._gestionar_evento(evento))
                self.assertFalse(self.lateral._abierto)

    def test_el_panel_queda_encima_del_panel_de_control(self) -> None:
        """Comprueba que el panel ocupa la derecha, desde arriba hasta los controles."""
        ancho, alto = TAMANO_VENTANA
        rectangulo = self.lateral._rectangulo

        self.assertEqual(rectangulo.right, ancho)
        self.assertEqual(rectangulo.top, 0)
        self.assertEqual(rectangulo.bottom, alto - self.control._alto_panel)

    def test_abierto_el_mundo_no_se_dibuja_debajo(self) -> None:
        """Comprueba que las localizaciones quedan a la izquierda del panel abierto."""
        self.lateral._gestionar_evento(self.clic_en(self.lateral))
        self.renderizador._reservar_panel_lateral(
            self.lateral._ancho_ocupado, self.lateral._ancho_esquina
        )

        radio = self.renderizador._radio_localizacion
        for x, _ in self.renderizador._posiciones_localizaciones.values():
            self.assertLessEqual(x + radio, self.lateral._rectangulo.left)

    def test_conserva_si_esta_abierto_al_redimensionar(self) -> None:
        """Comprueba que el panel sigue abierto y se recoloca en la ventana nueva.

        El panel de control también cambia de alto con la ventana, así que el panel
        lateral recibe ese alto nuevo y tiene que acabar justo encima de él.
        """
        self.lateral._gestionar_evento(self.clic_en(self.lateral))
        ancho, alto = 1400, 850
        self.control._redimensionar(ancho, alto)

        self.lateral._redimensionar(ancho, alto, self.control._alto_panel)

        self.assertTrue(self.lateral._abierto)
        self.assertEqual(self.lateral._rectangulo.right, ancho)
        self.assertEqual(
            self.lateral._rectangulo.bottom, alto - self.control._alto_panel
        )

    def test_se_dibuja_en_la_ventana_mas_pequena(self) -> None:
        """Comprueba que el panel se dibuja abierto y cerrado, con y sin error."""
        ancho, alto = Renderizador.ANCHO_MINIMO, Renderizador.ALTO_MINIMO
        renderizador = Renderizador(ancho, alto)
        self.addCleanup(renderizador._cerrar)
        control = PanelControl(ancho, alto)
        lateral = PanelLateral(ancho, alto, control._alto_panel)

        # El panel cabe en la ventana, y su botón queda dentro de él al abrirlo.
        self.assertTrue(renderizador._pantalla.get_rect().contains(lateral._rectangulo))
        self.assertTrue(lateral._rectangulo.contains(lateral._boton._rectangulo))

        # Dibujar no lanza nada, abierto o cerrado, con un error o sin él.
        for con_error in (False, True):
            mundo = crear_mundo(con_error=con_error)
            mundo.avanzar_hasta(math.inf)
            renderizador._poner_localizaciones(mundo._simulacion._localizaciones)
            for abierto in (False, True):
                with self.subTest(con_error=con_error, abierto=abierto):
                    lateral._abierto = abierto
                    renderizador._reservar_panel_lateral(
                        lateral._ancho_ocupado, lateral._ancho_esquina
                    )
                    renderizador._dibujar(mundo._simulacion)
                    lateral._dibujar(renderizador._pantalla, mundo._simulacion)
                    renderizador._dibujar_ayuda()

    def panel_con_lista_larga(self) -> PanelLateral:
        """Devuelve un panel abierto, en la ventana más pequeña, cuya lista no cabe.

        La lista tiene doce objetivos, y el panel ya se ha dibujado una vez, así que
        conoce la zona de la lista, la de su barra y lo que mide la lista.
        """
        ancho, alto = Renderizador.ANCHO_MINIMO, Renderizador.ALTO_MINIMO
        deposito = Localizacion("deposito")
        personas = [Persona(f"persona{i}", deposito, COMIDA) for i in range(12)]
        mundo = Mundo(
            [],
            localizaciones=[deposito],
            drones=[],
            cajas=[],
            personas=personas,
            contenidos=CONTENIDOS,
            objetivos=[PersonaTieneContenido(persona, COMIDA) for persona in personas],
        )
        renderizador = Renderizador(ancho, alto)
        self.addCleanup(renderizador._cerrar)
        lateral = PanelLateral(ancho, alto, PanelControl(ancho, alto)._alto_panel)
        lateral._gestionar_evento(self.clic_en(lateral))
        lateral._dibujar(renderizador._pantalla, mundo._simulacion)
        self.assertTrue(lateral._lista_desborda)
        return lateral

    def test_la_rueda_desplaza_la_lista(self) -> None:
        """Comprueba que la rueda del ratón desplaza la lista sin salirse de ella.

        La rueda solo desplaza la lista con el panel abierto y el ratón encima de
        ella.
        """
        lateral = self.panel_con_lista_larga()
        maximo = lateral._desplazamiento_maximo

        def rueda(pasos: int, posicion: tuple[int, int]) -> None:
            evento = pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=pasos)
            with mock.patch("pygame.mouse.get_pos", return_value=posicion):
                self.assertFalse(lateral._gestionar_evento(evento))

        dentro = lateral._zona_lista.center
        rueda(-1, dentro)
        self.assertEqual(lateral._desplazamiento, lateral._paso_desplazamiento)
        rueda(-100, dentro)
        self.assertEqual(lateral._desplazamiento, maximo)
        rueda(100, dentro)
        self.assertEqual(lateral._desplazamiento, 0)

        # Fuera de la lista, o con el panel cerrado, la rueda no hace nada.
        rueda(-1, (0, 0))
        self.assertEqual(lateral._desplazamiento, 0)
        lateral._gestionar_evento(self.clic_en(lateral))
        rueda(-1, dentro)
        self.assertEqual(lateral._desplazamiento, 0)

    def test_un_clic_en_la_barra_salta_a_ese_punto(self) -> None:
        """Comprueba que un clic en la barra centra su mando en el punto pulsado.

        Arriba del todo, la lista vuelve a su principio, abajo del todo llega a su
        final, y en medio queda a la mitad.
        """
        lateral = self.panel_con_lista_larga()
        barra = lateral._barra_lista
        maximo = lateral._desplazamiento_maximo
        # El borde de abajo de un pygame.Rect queda fuera de él: el último píxel
        # de la barra está una fila más arriba.
        abajo = (barra.centerx, barra.bottom - 1)

        lateral._gestionar_evento(raton(pygame.MOUSEBUTTONDOWN, abajo))
        self.assertEqual(lateral._desplazamiento, maximo)
        lateral._gestionar_evento(raton(pygame.MOUSEBUTTONUP, abajo))
        lateral._gestionar_evento(raton(pygame.MOUSEBUTTONDOWN, barra.midtop))
        self.assertEqual(lateral._desplazamiento, 0)
        lateral._gestionar_evento(raton(pygame.MOUSEBUTTONUP, barra.midtop))
        lateral._gestionar_evento(raton(pygame.MOUSEBUTTONDOWN, barra.center))
        self.assertAlmostEqual(lateral._desplazamiento, maximo / 2, delta=1)

    def test_arrastrar_la_barra_desplaza_la_lista(self) -> None:
        """Comprueba que la lista sigue al ratón mientras se arrastra la barra.

        Al arrastrar, el ratón puede salirse de la barra: solo cuenta su altura.
        Al soltar el botón, la lista deja de seguirlo.
        """
        lateral = self.panel_con_lista_larga()
        barra = lateral._barra_lista

        lateral._gestionar_evento(raton(pygame.MOUSEBUTTONDOWN, barra.midtop))
        lateral._gestionar_evento(raton(pygame.MOUSEMOTION, (0, barra.bottom)))
        self.assertEqual(lateral._desplazamiento, lateral._desplazamiento_maximo)

        lateral._gestionar_evento(raton(pygame.MOUSEBUTTONUP, (0, barra.bottom)))
        lateral._gestionar_evento(raton(pygame.MOUSEMOTION, barra.midtop))
        self.assertEqual(lateral._desplazamiento, lateral._desplazamiento_maximo)

    def test_si_la_lista_cabe_no_hay_barra(self) -> None:
        """Comprueba que, si la lista cabe, un clic donde iría la barra no hace nada."""
        self.lateral._gestionar_evento(self.clic_en(self.lateral))
        self.lateral._dibujar(self.renderizador._pantalla, self.simulacion)
        self.assertFalse(self.lateral._lista_desborda)

        barra = self.lateral._barra_lista
        self.lateral._gestionar_evento(raton(pygame.MOUSEBUTTONDOWN, barra.center))

        self.assertFalse(self.lateral._arrastrando)
        self.assertEqual(self.lateral._desplazamiento, 0)

    def test_arrastrar_cuando_la_lista_deja_de_desbordar(self) -> None:
        """Comprueba que el arrastre no falla si la lista encoge hasta caber.

        Mientras se arrastra, el plan sigue avanzando, y la lista puede encoger:
        por ejemplo, un objetivo que se cumple pierde su línea de explicación. Aquí
        se simula poniendo su alto a mano.
        """
        lateral = self.panel_con_lista_larga()
        barra = lateral._barra_lista
        lateral._gestionar_evento(raton(pygame.MOUSEBUTTONDOWN, barra.midtop))

        lateral._alto_lista = lateral._zona_lista.height
        lateral._gestionar_evento(raton(pygame.MOUSEMOTION, (0, barra.bottom)))

        self.assertEqual(lateral._desplazamiento, 0)

    def test_repr(self) -> None:
        """Comprueba ``repr()`` del panel lateral."""
        self.assertEqual(repr(self.lateral), "PanelLateral(abierto=False)")


if __name__ == "__main__":
    unittest.main()
