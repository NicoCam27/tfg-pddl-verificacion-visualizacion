"""Pruebas de que el resultado de una simulación no depende de ``paso_tiempo``.

Los inicios y los finales de las acciones se aplican de instante en instante,
en orden temporal, sea cual sea el tamaño del paso con el que avanza la
simulación. Cada prueba ejecuta el mismo plan con varios pasos, desde uno más
pequeño que cualquier acción hasta uno más largo que el plan entero, y comprueba
que el veredicto, el error, el instante en que se logra un objetivo y el
instante en que termina la ejecución son siempre los mismos.
"""

import contextlib
import io
import unittest

from simulador_pddl.acciones import (
    CogerCaja,
    EntregarCaja,
    Mover,
    PonerCajaEnTransportador,
    SacarCajaDeTransportador,
)
from simulador_pddl.mundo import Mundo
from simulador_pddl.objetivos import PersonaTieneContenido
from simulador_pddl.objetos import (
    Brazo,
    Caja,
    Contenido,
    Dron,
    Localizacion,
    Persona,
    Transportador,
)
from simulador_pddl.simulacion import InformeVerificacion

# Los contenidos de los problemas de este módulo. Un contenido no cambia al
# ejecutar un plan, así que todas las pruebas pueden compartirlos.
COMIDA = Contenido("comida")
CONTENIDOS = (COMIDA,)


# Desde pasos más pequeños que cualquier acción hasta uno que cubre el plan entero.
PASOS_TIEMPO = (0.001, 0.01, 0.1, 1, 10)


def ejecutar_plan(mundo: Mundo, paso_tiempo: float) -> InformeVerificacion:
    """Ejecuta el plan en modo texto, sin imprimir, y devuelve su informe."""
    with contextlib.redirect_stdout(io.StringIO()):
        return mundo.simulacion_texto(paso_tiempo)


# Cada ejecución necesita objetos nuevos: la simulación trabaja sobre las mismas
# instancias, así que reutilizarlos haría que cada ejecución empezara donde
# terminó la anterior.
def crear_cadena_corta() -> Mundo:
    """Crea un plan de acciones cortas, cada una justo después de la anterior.

    Algunos planificadores reales producen planes con esta forma: cada acción dura
    0.005 y la siguiente empieza 0.01 después, así que un paso de 0.1 abarca
    varias.
    """
    deposito = Localizacion("deposito")
    localizacion1 = Localizacion("localizacion1")
    brazo = Brazo("brazo")
    dron = Dron("dron1", deposito, [brazo])
    caja = Caja("caja1", deposito, COMIDA)
    persona = Persona("persona1", localizacion1, COMIDA)

    acciones = [
        CogerCaja(
            dron=dron, brazo=brazo, caja=caja, inicio_sim=0.01, duracion_sim=0.005
        ),
        Mover(
            dron=dron,
            origen=deposito,
            destino=localizacion1,
            inicio_sim=0.02,
            duracion_sim=0.005,
        ),
        EntregarCaja(
            dron=dron,
            brazo=brazo,
            caja=caja,
            persona=persona,
            inicio_sim=0.03,
            duracion_sim=0.005,
        ),
        Mover(
            dron=dron,
            origen=localizacion1,
            destino=deposito,
            inicio_sim=0.04,
            duracion_sim=0.005,
        ),
    ]
    objetivos = [PersonaTieneContenido(persona, COMIDA)]

    return Mundo(
        acciones,
        localizaciones=[deposito, localizacion1],
        drones=[dron],
        cajas=[caja],
        personas=[persona],
        contenidos=CONTENIDOS,
        objetivos=objetivos,
    )


def crear_mover_largo() -> Mundo:
    """Crea un plan de un solo ``Mover`` que empieza en t=0 y termina en t=7.

    Con un paso de 0.1, el último tic acaba en t=7.1: por el redondeo, setenta
    sumas se quedan justo por debajo de 7 y hace falta una más.
    """
    deposito = Localizacion("deposito")
    localizacion1 = Localizacion("localizacion1")
    dron = Dron("dron1", deposito, [Brazo("brazo")])

    acciones = [
        Mover(
            dron=dron,
            origen=deposito,
            destino=localizacion1,
            inicio_sim=0,
            duracion_sim=7,
        ),
    ]

    return Mundo(
        acciones,
        localizaciones=[deposito, localizacion1],
        drones=[dron],
        cajas=[],
        personas=[],
        contenidos=[],
    )


def crear_carrera_por_transportador() -> Mundo:
    """Crea un plan en el que una caja se saca de un transportador demasiado pronto.

    ``dron1`` mete ``caja1`` en el transportador entre t=0.25 y t=0.35, y
    ``dron2`` intenta sacarla en t=0.32, cuando todavía no está dentro. Con un
    paso de 0.1 los dos instantes caen en el mismo tic (0.3, 0.4].
    """
    deposito = Localizacion("deposito")
    brazo1 = Brazo("brazo1")
    brazo2 = Brazo("brazo2")
    dron1 = Dron("dron1", deposito, [brazo1])
    dron2 = Dron("dron2", deposito, [brazo2])
    caja = Caja("caja1", deposito, COMIDA)
    transportador = Transportador("transportador1", deposito, 4)

    acciones = [
        CogerCaja(dron=dron1, brazo=brazo1, caja=caja, inicio_sim=0, duracion_sim=0.05),
        PonerCajaEnTransportador(
            dron=dron1,
            brazo=brazo1,
            caja=caja,
            transportador=transportador,
            inicio_sim=0.25,
            duracion_sim=0.1,
        ),
        SacarCajaDeTransportador(
            dron=dron2,
            brazo=brazo2,
            caja=caja,
            transportador=transportador,
            inicio_sim=0.32,
            duracion_sim=0.05,
        ),
    ]

    return Mundo(
        acciones,
        localizaciones=[deposito],
        drones=[dron1, dron2],
        cajas=[caja],
        personas=[],
        contenidos=CONTENIDOS,
        transportadores=[transportador],
    )


class TestVeredictoNoDependeDelPaso(unittest.TestCase):
    """El veredicto y los instantes de la ejecución son iguales con cualquier paso."""

    def test_acciones_cortas_encadenadas_son_validas_con_cualquier_paso(self) -> None:
        """Comprueba que una cadena de acciones cortas es válida con cada paso.

        Cada acción necesita que se haya aplicado el final de la anterior, aunque
        las dos caigan en el mismo tic.
        """
        for paso_tiempo in PASOS_TIEMPO:
            with self.subTest(paso_tiempo=paso_tiempo):
                informe = ejecutar_plan(crear_cadena_corta(), paso_tiempo)

                self.assertEqual(
                    informe.veredicto, InformeVerificacion.VALIDO, informe.error
                )

    def test_inicio_antes_de_un_final_del_mismo_tic_no_ve_su_efecto(self) -> None:
        """Comprueba que un inicio no ve un final que llega más tarde en su tic.

        ``SacarCajaDeTransportador`` empieza en t=0.32 y ``PonerCajaEnTransportador``
        termina en t=0.35. Con un paso de 0.1 los dos caen en el mismo tic, pero el
        inicio sigue llegando antes: la caja todavía no está en el transportador,
        así que el plan es ``"NO EJECUTABLE"`` con cualquier paso.
        """
        for paso_tiempo in PASOS_TIEMPO:
            with self.subTest(paso_tiempo=paso_tiempo):
                informe = ejecutar_plan(crear_carrera_por_transportador(), paso_tiempo)

                self.assertEqual(informe.veredicto, InformeVerificacion.NO_EJECUTABLE)
                self.assertEqual(
                    informe.error,
                    "la caja caja1 no se puede sacar del transportador "
                    "transportador1, el dron dron1 todavía la está metiendo",
                )

    def test_instante_en_que_se_logra_un_objetivo_no_depende_del_paso(self) -> None:
        """Comprueba que un objetivo se logra en el mismo instante con cualquier paso.

        Los objetivos se anotan en el instante exacto del suceso que los logra, no
        al final del tic en el que cae.
        """
        tiempos_logrados = set()
        for paso_tiempo in PASOS_TIEMPO:
            informe = ejecutar_plan(crear_cadena_corta(), paso_tiempo)
            tiempos_logrados.add(informe.estados_objetivos[0].logrado_en)

        self.assertEqual(len(tiempos_logrados), 1, tiempos_logrados)

    def test_la_ejecucion_termina_en_el_ultimo_suceso_con_cualquier_paso(self) -> None:
        """Comprueba que la ejecución termina en el final del plan con cada paso.

        El reloj se queda en el instante del último suceso, no en el final del
        último tic, y es el instante que imprime ``simulacion_texto()``.
        """
        for paso_tiempo in PASOS_TIEMPO:
            with self.subTest(paso_tiempo=paso_tiempo):
                mundo = crear_mover_largo()
                salida = io.StringIO()
                with contextlib.redirect_stdout(salida):
                    mundo.simulacion_texto(paso_tiempo)

                self.assertEqual(mundo._simulacion._tiempo_simulacion, 7)
                self.assertIn("Ejecución terminada en t=7.00s", salida.getvalue())


if __name__ == "__main__":
    unittest.main()
