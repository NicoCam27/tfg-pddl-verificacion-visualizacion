"""Pruebas del panel lateral de la simulación visual, sin pantalla.

Comprueban el estado del plan que muestra el panel (``"EN CURSO"`` mientras el
plan no ha terminado ni ha fallado ninguna acción, y el veredicto después) y su
línea de objetivos, que el botón lo abre y lo cierra, que abierto deja al mundo
solo el ancho que queda y que se dibuja, abierto y cerrado, en la ventana más
pequeña. Como las de ``test_simulacion_visual.py``, no comprueban la imagen
dibujada, solo posiciones y tamaños.
"""

from __future__ import annotations

import logging
import math
import os
import unittest
from typing import TYPE_CHECKING

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
    _estado_del_plan,
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
            lograr"`` (además, el dron tiene que acabar en el depósito) o
            ``"ninguno"``.
        con_error: Si al final hay un movimiento que sale del depósito, donde el
            dron ya no está, y falla.
    """
    deposito = Localizacion("deposito")
    loc1 = Localizacion("loc1")
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
    if objetivos == "uno sin lograr":
        lista_objetivos.append(DronEnLocalizacion(dron, deposito))

    return Mundo(
        acciones,
        localizaciones=[deposito, loc1],
        drones=[dron],
        cajas=[caja],
        personas=[persona],
        contenidos=CONTENIDOS,
        objetivos=lista_objetivos,
    )


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

    def clic(self, boton: int = pygame.BUTTON_LEFT) -> pygame.event.Event:
        """Devuelve un clic con ``boton`` en el centro del botón del panel."""
        return pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            pos=self.lateral._boton._rectangulo.center,
            button=boton,
        )

    def test_el_boton_abre_y_cierra_el_panel(self) -> None:
        """Comprueba que el panel empieza cerrado y que cada clic lo alterna."""
        self.assertFalse(self.lateral._abierto)
        self.assertEqual(self.lateral._ancho_ocupado, 0)
        self.assertGreater(self.lateral._ancho_esquina, 0)

        self.assertTrue(self.lateral._gestionar_evento(self.clic()))
        self.assertTrue(self.lateral._abierto)
        self.assertEqual(self.lateral._boton._texto, "Ocultar panel")
        self.assertEqual(self.lateral._ancho_ocupado, self.lateral._rectangulo.width)
        self.assertEqual(self.lateral._ancho_esquina, 0)

        self.assertTrue(self.lateral._gestionar_evento(self.clic()))
        self.assertFalse(self.lateral._abierto)
        self.assertEqual(self.lateral._boton._texto, "Mostrar panel")

    def test_otros_eventos_no_cambian_el_panel(self) -> None:
        """Comprueba que solo un clic izquierdo en el botón abre el panel."""
        fuera = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, pos=(0, 0), button=pygame.BUTTON_LEFT
        )
        for evento in (self.clic(pygame.BUTTON_RIGHT), fuera):
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
        self.lateral._gestionar_evento(self.clic())
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
        self.lateral._gestionar_evento(self.clic())
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

    def test_repr(self) -> None:
        """Comprueba ``repr()`` del panel lateral."""
        self.assertEqual(repr(self.lateral), "PanelLateral(abierto=False)")


if __name__ == "__main__":
    unittest.main()
