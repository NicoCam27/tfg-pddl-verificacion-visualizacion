"""Pruebas del panel lateral de la simulación visual, sin pantalla.

Comprueban el estado del plan que muestra el panel (``"EN CURSO"`` mientras el
plan no ha terminado ni ha fallado ninguna acción, y el veredicto después), su
línea de objetivos, cómo va cada acción del plan y cada objetivo, lo que se dice
de cada objeto, que pulsar una acción salta a su inicio, que el botón abre y
cierra el panel, que abierto deja al mundo solo el ancho que queda, que las
pestañas cambian la lista, que la rueda del ratón y la barra la desplazan y que se
dibuja, abierto y cerrado, en la ventana más pequeña. Como las de
``test_simulacion_visual.py``, no comprueban la imagen dibujada, solo posiciones y
tamaños.
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
    CogerTransportador,
    Contenido,
    Dron,
    DronEnLocalizacion,
    EntregarCaja,
    Localizacion,
    Mover,
    Mundo,
    Persona,
    PersonaTieneContenido,
    PonerCajaEnTransportador,
    Transportador,
)
from simulador_pddl.simulacion import InformeVerificacion
from simulador_pddl.visualizacion import PanelControl, PanelLateral, Renderizador
from simulador_pddl.visualizacion.panel_lateral import (
    _clase_accion,
    _clase_objetivo,
    _detalles_accion,
    _detalles_caja,
    _detalles_dron,
    _detalles_objetivo,
    _detalles_persona,
    _detalles_transportador,
    _estado_del_plan,
    _partir_en_lineas,
    _texto_objetivos,
)
from simulador_pddl.visualizacion.ventana import _saltar_a_accion

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


def crear_mundo_con_dos_brazos() -> Mundo:
    """Crea un mundo cuyo plan falla mientras otra acción está en ejecución.

    Con el brazo izquierdo, el dron coge una caja de t=0 a t=2. Con el derecho,
    que está vacío, intenta entregar otra caja en t=1, y falla al empezar. El
    movimiento de t=3 ya no llega a empezar.
    """
    deposito = Localizacion("deposito")
    loc1 = Localizacion("loc1")
    izquierdo = Brazo("izquierdo")
    derecho = Brazo("derecho")
    dron = Dron("dron1", deposito, [izquierdo, derecho])
    caja1 = Caja("caja1", deposito, COMIDA)
    caja2 = Caja("caja2", deposito, COMIDA)
    persona = Persona("persona1", deposito, COMIDA)

    return Mundo(
        [
            CogerCaja(dron, izquierdo, caja1, 0, 2),
            EntregarCaja(dron, derecho, caja2, persona, 1, 1),
            Mover(dron, deposito, loc1, 3, 1),
        ],
        localizaciones=[deposito, loc1],
        drones=[dron],
        cajas=[caja1, caja2],
        personas=[persona],
        contenidos=CONTENIDOS,
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


class TestAccionesDelPlan(unittest.TestCase):
    """Cómo va cada acción de la lista del plan y sus detalles."""

    def setUp(self) -> None:
        """Silencia el registro."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_clase_de_cada_accion(self) -> None:
        """Comprueba cómo va cada acción a lo largo de un plan sin errores."""
        mundo = crear_mundo()
        simulacion = mundo._simulacion
        casos = {
            0: ["en ejecución", "sin empezar", "sin empezar"],
            1.5: ["terminada", "en ejecución", "sin empezar"],
            math.inf: ["terminada", "terminada", "terminada"],
        }
        for instante, clases in casos.items():
            with self.subTest(instante=instante):
                mundo.avanzar_hasta(instante)
                self.assertEqual(
                    [
                        _clase_accion(accion, simulacion)
                        for accion in simulacion._acciones
                    ],
                    clases,
                )

    def test_si_falla_una_accion_las_que_se_ejecutaban_se_interrumpen(self) -> None:
        """Comprueba la acción que falla, la interrumpida y la que no empieza.

        Al reiniciar, ninguna acción queda marcada como fallida.
        """
        mundo = crear_mundo_con_dos_brazos()
        simulacion = mundo._simulacion

        mundo.avanzar_hasta(math.inf)
        self.assertEqual(
            [_clase_accion(accion, simulacion) for accion in simulacion._acciones],
            ["interrumpida", "fallida", "sin empezar"],
        )

        mundo.reiniciar()
        self.assertEqual(
            [_clase_accion(accion, simulacion) for accion in simulacion._acciones],
            ["sin empezar", "sin empezar", "sin empezar"],
        )

    def test_el_recuento_del_panel_de_control_cuadra_con_la_lista(self) -> None:
        """Comprueba que el recuento de acciones dice lo mismo que la lista del plan.

        Mientras el plan se ejecuta, cuenta las acciones pendientes, en curso y
        terminadas. Si falla una acción, ya no hay ninguna en curso: cuenta las
        interrumpidas y la que falló.
        """
        mundo = crear_mundo()
        mundo.avanzar_hasta(1.5)
        self.assertEqual(
            mundo._simulacion._texto_recuento_acciones(),
            "Pendientes: 1 | En curso: 1 | Terminadas: 1/3",
        )

        mundo = crear_mundo_con_dos_brazos()
        mundo.avanzar_hasta(math.inf)
        self.assertEqual(
            mundo._simulacion._texto_recuento_acciones(),
            "Pendientes: 1 | Interrumpidas: 1 | Fallida: 1 | Terminadas: 0/3",
        )

    def test_detalles_de_una_accion(self) -> None:
        """Comprueba los detalles de una acción, y los de la que falló."""
        mundo = crear_mundo(con_error=True)
        simulacion = mundo._simulacion
        mundo.avanzar_hasta(math.inf)
        coger, *_, mover = simulacion._acciones

        self.assertEqual(
            _detalles_accion(coger, None),
            ["dron1, brazo, caja1", "De t=0.00s a t=1.00s"],
        )
        self.assertEqual(
            _detalles_accion(mover, simulacion._error),
            [
                "dron1, deposito, loc1",
                "De t=3.00s a t=4.00s",
                (
                    "Falló: el dron dron1 no está en la localización deposito, está "
                    "en la localización loc1"
                ),
            ],
        )


class TestSaltarAUnaAccion(unittest.TestCase):
    """Pulsar una acción de la lista lleva la simulación a su inicio, en pausa."""

    def setUp(self) -> None:
        """Silencia el registro."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_salta_a_una_accion_anterior(self) -> None:
        """Comprueba que la acción queda recién empezada, con lo anterior aplicado."""
        mundo = crear_mundo()
        simulacion = mundo._simulacion
        coger, mover, entregar = simulacion._acciones
        mundo.avanzar_hasta(math.inf)

        _saltar_a_accion(simulacion, mover)

        self.assertEqual(simulacion._tiempo_simulacion, mover.inicio_sim)
        self.assertTrue(coger.terminada)
        self.assertTrue(mover.iniciada)
        self.assertFalse(mover.terminada)
        self.assertFalse(entregar.iniciada)

    def test_salta_a_una_accion_posterior_y_queda_en_pausa(self) -> None:
        """Comprueba que se salta también hacia delante, y que se pausa."""
        mundo = crear_mundo()
        simulacion = mundo._simulacion
        entregar = simulacion._acciones[2]
        simulacion._reproducir()

        _saltar_a_accion(simulacion, entregar)

        self.assertEqual(simulacion._tiempo_simulacion, entregar.inicio_sim)
        self.assertTrue(entregar.iniciada)
        self.assertFalse(simulacion._reproduciendo)

    def test_si_falla_una_accion_anterior_se_detiene_en_ella(self) -> None:
        """Comprueba que el salto se para en el error, y que otro salto lo deshace."""
        mundo = crear_mundo_con_dos_brazos()
        simulacion = mundo._simulacion
        coger, entregar, mover = simulacion._acciones

        _saltar_a_accion(simulacion, mover)
        self.assertEqual(simulacion._tiempo_simulacion, entregar.inicio_sim)
        self.assertIs(simulacion._accion_fallida, entregar)
        self.assertFalse(mover.iniciada)

        _saltar_a_accion(simulacion, coger)
        self.assertEqual(simulacion._tiempo_simulacion, 0)
        self.assertFalse(simulacion._tiene_error)
        self.assertTrue(coger.iniciada)


class TestObjetosDeLaLista(unittest.TestCase):
    """Lo que dice de cada objeto la lista de objetos."""

    def setUp(self) -> None:
        """Silencia el registro."""
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_detalles_de_un_dron_y_de_una_caja(self) -> None:
        """Comprueba el dron y la caja antes, durante y después de llevarla.

        Mientras el dron coge la caja, la caja ya es suya, pero no está en el brazo
        hasta que la acción termina.
        """
        mundo = crear_mundo()
        simulacion = mundo._simulacion
        [dron] = simulacion._drones
        [caja] = simulacion._cajas
        self.assertEqual(_detalles_dron(dron), ["En deposito", "Brazo brazo: vacío"])
        self.assertEqual(_detalles_caja(caja), ["Disponible", "En deposito"])

        casos = {
            0.5: (
                ["En deposito", "Brazo brazo: vacío"],
                ["La lleva el dron dron1", "En deposito"],
            ),
            1.5: (
                ["En deposito", "Brazo brazo: caja1 (comida)"],
                ["La lleva el dron dron1", "En deposito"],
            ),
            math.inf: (
                ["En loc1", "Brazo brazo: vacío"],
                ["Entregada a la persona persona1", "En loc1"],
            ),
        }
        for instante, (detalles_dron, detalles_caja) in casos.items():
            with self.subTest(instante=instante):
                mundo.avanzar_hasta(instante)
                self.assertEqual(_detalles_dron(dron), detalles_dron)
                self.assertEqual(_detalles_caja(caja), detalles_caja)

    def test_detalles_de_una_persona(self) -> None:
        """Comprueba la persona antes y después de recibir la caja."""
        mundo = crear_mundo()
        [persona] = mundo._simulacion._personas

        self.assertEqual(
            _detalles_persona(persona),
            ["En loc1", "Necesita: comida", "No tiene ninguna caja"],
        )
        mundo.avanzar_hasta(math.inf)
        self.assertEqual(
            _detalles_persona(persona),
            ["En loc1", "No necesita nada", "Tiene: caja1 (comida)"],
        )

    def test_detalles_de_un_transportador(self) -> None:
        """Comprueba el transportador vacío y con una caja, llevado por un dron.

        El brazo del dron que lo lleva lo nombra, y la caja dice que está dentro.
        """
        deposito = Localizacion("deposito")
        brazo = Brazo("brazo")
        dron = Dron("dron1", deposito, [brazo])
        caja = Caja("caja1", deposito, COMIDA)
        transportador = Transportador("transportador1", deposito, 2)
        mundo = Mundo(
            [
                CogerCaja(dron, brazo, caja, 0, 1),
                PonerCajaEnTransportador(dron, brazo, caja, transportador, 1, 1),
                CogerTransportador(dron, brazo, transportador, 2, 1),
            ],
            localizaciones=[deposito],
            drones=[dron],
            cajas=[caja],
            personas=[],
            contenidos=CONTENIDOS,
            transportadores=[transportador],
        )

        self.assertEqual(
            _detalles_transportador(transportador),
            ["En deposito", "No lo lleva ningún dron", "Cajas (0/2): ninguna"],
        )
        mundo.avanzar_hasta(math.inf)
        self.assertEqual(
            _detalles_transportador(transportador),
            [
                "En deposito",
                "Lo lleva dron1 con el brazo brazo",
                "Cajas (1/2): caja1 (comida)",
            ],
        )
        self.assertEqual(
            _detalles_dron(dron), ["En deposito", "Brazo brazo: transportador1"]
        )
        self.assertEqual(
            _detalles_caja(caja),
            ["Dentro del transportador transportador1", "En deposito"],
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
        """Comprueba que el panel se dibuja abierto y cerrado, con y sin error.

        Abierto, se dibuja con cada pestaña.
        """
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
            for abierto, pestana in (
                (False, "Plan"),
                (True, "Plan"),
                (True, "Objetivos"),
                (True, "Objetos"),
            ):
                with self.subTest(
                    con_error=con_error, abierto=abierto, pestana=pestana
                ):
                    lateral._abierto = abierto
                    lateral._pestana = pestana
                    renderizador._reservar_panel_lateral(
                        lateral._ancho_ocupado, lateral._ancho_esquina
                    )
                    renderizador._dibujar(mundo._simulacion)
                    lateral._dibujar(renderizador._pantalla, mundo._simulacion)
                    renderizador._dibujar_ayuda()

    def panel_con_lista_larga(self, pestana: str = "Objetivos") -> PanelLateral:
        """Devuelve un panel abierto, en la ventana más pequeña, cuya lista no cabe.

        Las dos listas tienen doce filas: el dron va y viene doce veces, y hay doce
        personas que necesitan comida. El panel se abre, se pulsa ``pestana`` y se
        dibuja, así que conoce la zona de la lista, la de su barra, lo que mide la
        lista y, en la pestaña del plan, dónde está cada acción.
        """
        ancho, alto = Renderizador.ANCHO_MINIMO, Renderizador.ALTO_MINIMO
        deposito = Localizacion("deposito")
        loc1 = Localizacion("loc1")
        dron = Dron("dron1", deposito, [])
        idas = [(deposito, loc1), (loc1, deposito)] * 6
        personas = [Persona(f"persona{i}", deposito, COMIDA) for i in range(12)]
        self.mundo_largo = Mundo(
            [
                Mover(dron, origen, destino, i, 1)
                for i, (origen, destino) in enumerate(idas)
            ],
            localizaciones=[deposito, loc1],
            drones=[dron],
            cajas=[],
            personas=personas,
            contenidos=CONTENIDOS,
            objetivos=[PersonaTieneContenido(persona, COMIDA) for persona in personas],
        )
        renderizador = Renderizador(ancho, alto)
        self.addCleanup(renderizador._cerrar)
        lateral = PanelLateral(ancho, alto, PanelControl(ancho, alto)._alto_panel)
        lateral._gestionar_evento(self.clic_en(lateral))
        # Las pestañas se colocan al dibujar el panel.
        lateral._dibujar(renderizador._pantalla, self.mundo_largo._simulacion)
        pulsar = lateral._rectangulos_pestanas[pestana].center
        lateral._gestionar_evento(raton(pygame.MOUSEBUTTONDOWN, pulsar))
        lateral._dibujar(renderizador._pantalla, self.mundo_largo._simulacion)
        self.assertTrue(lateral._lista_desborda)
        return lateral

    def test_empieza_en_el_plan_y_las_pestanas_cambian_la_lista(self) -> None:
        """Comprueba que se empieza en la pestaña del plan y que se puede cambiar.

        Con la pestaña de objetivos, no queda ninguna fila del plan que pulsar.
        """
        self.lateral._gestionar_evento(self.clic_en(self.lateral))
        self.lateral._dibujar(self.renderizador._pantalla, self.simulacion)
        self.assertEqual(self.lateral._pestana, "Plan")
        self.assertEqual(
            [accion for _, accion in self.lateral._filas_plan],
            self.simulacion._acciones,
        )

        objetivos = self.lateral._rectangulos_pestanas["Objetivos"].center
        self.assertFalse(
            self.lateral._gestionar_evento(raton(pygame.MOUSEBUTTONDOWN, objetivos))
        )
        self.lateral._dibujar(self.renderizador._pantalla, self.simulacion)
        self.assertEqual(self.lateral._pestana, "Objetivos")
        self.assertEqual(self.lateral._filas_plan, [])

        plan = self.lateral._rectangulos_pestanas["Plan"].center
        self.lateral._gestionar_evento(raton(pygame.MOUSEBUTTONDOWN, plan))
        self.assertEqual(self.lateral._pestana, "Plan")

    def test_la_pestana_de_objetos_los_agrupa_por_tipo(self) -> None:
        """Comprueba los títulos de los grupos de la lista de objetos.

        Un tipo sin objetos no tiene grupo: este problema no tiene transportadores.
        """
        self.lateral._gestionar_evento(self.clic_en(self.lateral))
        self.lateral._dibujar(self.renderizador._pantalla, self.simulacion)
        objetos = self.lateral._rectangulos_pestanas["Objetos"].center
        self.lateral._gestionar_evento(raton(pygame.MOUSEBUTTONDOWN, objetos))

        with mock.patch.object(
            PanelLateral,
            "_dibujar_linea",
            autospec=True,
            side_effect=PanelLateral._dibujar_linea,
        ) as dibujar_linea:
            self.lateral._dibujar(self.renderizador._pantalla, self.simulacion)

        # Las dos primeras líneas son las de la cabecera: el tiempo y los objetivos.
        titulos = [llamada.args[2] for llamada in dibujar_linea.call_args_list][2:]
        self.assertEqual(titulos, ["Drones (1)", "Cajas (1)", "Personas (1)"])

    def test_cambiar_de_pestana_vuelve_al_principio_de_la_lista(self) -> None:
        """Comprueba que la lista de la otra pestaña se ve desde su principio."""
        lateral = self.panel_con_lista_larga()
        lateral._desplazar(lateral._desplazamiento_maximo)
        self.assertGreater(lateral._desplazamiento, 0)

        plan = lateral._rectangulos_pestanas["Plan"].center
        lateral._gestionar_evento(raton(pygame.MOUSEBUTTONDOWN, plan))

        self.assertEqual(lateral._desplazamiento, 0)

    def test_un_clic_en_una_accion_la_devuelve(self) -> None:
        """Comprueba qué acción del plan pulsa cada clic.

        Solo cuenta un clic izquierdo en una fila, con el panel abierto y la
        pestaña del plan elegida.
        """
        self.lateral._gestionar_evento(self.clic_en(self.lateral))
        self.lateral._dibujar(self.renderizador._pantalla, self.simulacion)
        fila, accion = self.lateral._filas_plan[1]
        derecho = pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, pos=fila.center, button=pygame.BUTTON_RIGHT
        )

        self.assertIs(
            self.lateral._accion_pulsada(raton(pygame.MOUSEBUTTONDOWN, fila.center)),
            accion,
        )
        self.assertIsNone(self.lateral._accion_pulsada(derecho))
        self.assertIsNone(self.lateral._accion_pulsada(self.clic_en(self.lateral)))

        objetivos = self.lateral._rectangulos_pestanas["Objetivos"].center
        self.lateral._gestionar_evento(raton(pygame.MOUSEBUTTONDOWN, objetivos))
        self.assertIsNone(
            self.lateral._accion_pulsada(raton(pygame.MOUSEBUTTONDOWN, fila.center))
        )

        self.lateral._gestionar_evento(self.clic_en(self.lateral))
        self.assertIsNone(
            self.lateral._accion_pulsada(raton(pygame.MOUSEBUTTONDOWN, fila.center))
        )

    def test_una_accion_fuera_de_la_zona_no_se_puede_pulsar(self) -> None:
        """Comprueba que no se pulsa una fila que el desplazamiento ha subido.

        La fila sigue ahí, encima de la zona de la lista, pero no se ve.
        """
        lateral = self.panel_con_lista_larga("Plan")
        lateral._desplazar(lateral._desplazamiento_maximo)
        lateral._dibujar(self.renderizador._pantalla, self.mundo_largo._simulacion)
        encima = (lateral._zona_lista.centerx, lateral._zona_lista.top - 1)
        self.assertTrue(
            any(fila.collidepoint(encima) for fila, _ in lateral._filas_plan)
        )

        self.assertIsNone(
            lateral._accion_pulsada(raton(pygame.MOUSEBUTTONDOWN, encima))
        )

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
        self.assertEqual(
            repr(self.lateral), "PanelLateral(abierto=False, pestana='Plan')"
        )


if __name__ == "__main__":
    unittest.main()
