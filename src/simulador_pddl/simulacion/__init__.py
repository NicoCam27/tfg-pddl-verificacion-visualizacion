"""simulacion: El motor que ejecuta y verifica un plan.

``Mundo`` es el punto de entrada público de la biblioteca. Cada ejecución
devuelve un ``InformeVerificacion``, y los dos tipos que se exportan aquí son
los que el usuario puede leer, pero no cambiar:

    InformeVerificacion: el informe de una ejecución, con su veredicto
        (``informe.veredicto``).
    EstadoObjetivo: cuándo se logró y cuándo se rompió cada objetivo durante la
        ejecución (``informe.estados_objetivos``).

Por debajo, ``Mundo`` usa ``Simulacion`` (``simulacion.simulacion``), que valida
un plan y aplica sus acciones a lo largo del tiempo. ``Simulacion`` usa a su vez
``InstantaneaMundo`` (``simulacion.instantanea``), que captura el estado del
mundo al construir la simulación para que ``Mundo.reiniciar()`` pueda volver a
él. El usuario nunca utiliza ninguno de los dos, así que no se exportan.
"""

from simulador_pddl.simulacion.verificacion import EstadoObjetivo, InformeVerificacion

__all__ = [
    "EstadoObjetivo",
    "InformeVerificacion",
]
