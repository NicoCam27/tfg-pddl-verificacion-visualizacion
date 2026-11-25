"""Resultado de verificar un plan: si se pudo ejecutar, y si resolvió el problema.

Son dos preguntas distintas, y este módulo las mantiene separadas. Un plan es
ejecutable si ninguna de sus acciones falla, y eso solo se sabe al llegar a su
final. Resuelve el problema si además su estado final cumple todos los
objetivos. Así, un plan vacío nunca falla, pero solo resuelve el problema si
los objetivos ya se cumplen al inicio.

Las dos respuestas dan uno de cinco veredictos: ``"NO EJECUTABLE"`` si falla
una acción, ``"INCOMPLETO"`` si la ejecución se detiene antes del final sin que
falle ninguna (p. ej. porque se cierra la ventana de una simulación visual),
``"EJECUTABLE"`` si termina sin objetivos que comprobar, ``"NO RESUELVE"`` si
termina sin cumplirlos todos, y ``"VÁLIDO"`` si los cumple.

``InformeVerificacion`` es el informe de una ejecución, con su veredicto, y
``EstadoObjetivo`` anota cómo le fue a cada objetivo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulador_pddl.acciones import Accion
    from simulador_pddl.objetivos import Objetivo


class EstadoObjetivo:
    """EstadoObjetivo anota cómo le fue a un objetivo a lo largo de una ejecución.

    ``logrado_en`` y ``roto_en`` describen el último periodo en el que se cumplió
    el objetivo. Juntos distinguen un objetivo que nunca se cumplió de uno que se
    cumplió y que después el plan deshizo, dos defectos muy distintos. Si el
    objetivo se cumple, se rompe y se vuelve a cumplir, solo se guarda el último
    periodo, para que el informe nunca dé a entender que el objetivo se cumplió
    durante un hueco en el que no se cumplía.

    Args:
        objetivo: El objetivo que se sigue.
    """

    def __init__(self, objetivo: Objetivo) -> None:
        self._objetivo = objetivo
        self._cumplido = False
        self._logrado_en: float | None = None
        self._roto_en: float | None = None
        self._explicacion_fallo: str | None = None

    def __repr__(self) -> str:
        return f"EstadoObjetivo({self._objetivo!r}, cumplido={self._cumplido!r})"

    def __str__(self) -> str:
        marca = "OK" if self._cumplido else "--"
        return f"[{marca}] {self._objetivo._describir()}"

    def _observar(self, *, cumplido: bool, tiempo_simulacion: float) -> None:
        """Anota si el objetivo se cumple en ``tiempo_simulacion``."""
        if cumplido and not self._cumplido:
            # Ahora empieza un nuevo periodo en el que se cumple el objetivo.
            self._logrado_en = tiempo_simulacion
            self._roto_en = None
        elif not cumplido and self._cumplido:
            # Ahora termina ese periodo: el plan ha deshecho el objetivo.
            self._roto_en = tiempo_simulacion

        self._cumplido = cumplido
        self._explicacion_fallo = None if cumplido else self._objetivo._explicar_fallo()

    def _reiniciar(self) -> None:
        """Vuelve al estado inicial, como si el objetivo no se hubiera observado."""
        self._cumplido = False
        self._logrado_en = None
        self._roto_en = None
        self._explicacion_fallo = None

    def _texto_tiempos(self) -> str:
        """Devuelve, como texto, cuándo se logró y cuándo se rompió el objetivo."""
        if self._cumplido:
            # Mientras se cumple, _logrado_en nunca es None: _observar() lo pone al
            # empezar cada periodo en que se cumple el objetivo.
            return f"cumplido desde t={self._logrado_en:.2f}s"

        # Si no se cumple, los dos tiempos son None (nunca se cumplió) o los dos
        # tienen valor (se cumplió y después se rompió).
        if self._roto_en is not None:
            return (
                f"se cumplió en t={self._logrado_en:.2f}s "
                f"y se rompió en t={self._roto_en:.2f}s"
            )

        return "nunca se cumplió"

    @property
    def objetivo(self) -> Objetivo:
        """El objetivo que se sigue."""
        return self._objetivo

    @property
    def cumplido(self) -> bool:
        """Si el objetivo se cumplía la última vez que se observó."""
        return self._cumplido

    @property
    def logrado_en(self) -> float | None:
        """Cuándo empezó a cumplirse el objetivo, o ``None`` si nunca se cumplió.

        Es el inicio del último periodo en que se cumplió, en segundos de
        simulación.
        """
        return self._logrado_en

    @property
    def roto_en(self) -> float | None:
        """Cuándo dejó de cumplirse el objetivo, o ``None``.

        Es el final del último periodo en que se cumplió, en segundos de
        simulación. Es ``None`` si el objetivo se cumple ahora o si nunca se cumplió.
        """
        return self._roto_en

    @property
    def explicacion_fallo(self) -> str | None:
        """Por qué no se cumple el objetivo, o ``None`` mientras se cumpla.

        Cada vez que se observa el objetivo y no se cumple,
        ``Objetivo._explicar_fallo()`` escribe la explicación, que se guarda como
        texto. Así, un informe muestra la explicación del momento en que se creó el
        informe, aunque después la simulación siga avanzando o se reinicie.
        """
        return self._explicacion_fallo


class InformeVerificacion:
    """InformeVerificacion es el informe de la ejecución de un plan, con su veredicto.

    ``veredicto`` es uno de cinco textos, que se muestran al usuario. Cada texto
    tiene una constante de la clase, indicada entre paréntesis, para que el código
    compare con la constante y no con el texto. Las condiciones se comprueban en
    este orden, y el veredicto es el de la primera que se cumple:

    * ``"NO EJECUTABLE"`` (``NO_EJECUTABLE``): falló una acción.
    * ``"INCOMPLETO"`` (``INCOMPLETO``): no falló ninguna acción, pero la
      ejecución se detuvo antes del final del plan (p. ej. porque se cerró la
      ventana de una simulación visual), así que las acciones restantes y el
      estado final no llegaron a comprobarse.
    * ``"EJECUTABLE"`` (``EJECUTABLE``): el plan entero se ejecutó sin errores,
      pero el problema no tiene objetivos, así que no había nada más que comprobar.
    * ``"NO RESUELVE"`` (``NO_RESUELVE``): el plan entero se ejecutó, pero algún
      objetivo no se cumple.
    * ``"VÁLIDO"`` (``VALIDO``): el plan entero se ejecutó y se cumplen todos los
      objetivos.

    Todos los argumentos se pasan por nombre, y se pueden leer después mediante
    una propiedad de solo lectura con el mismo nombre: un informe no se puede
    cambiar una vez creado.

    Args:
        ejecutable: Si no ha fallado ninguna acción.
        completado: Si han terminado todas las acciones del plan.
        error: El mensaje de error de la acción que falló, o ``None`` si no falló
            ninguna.
        accion_fallida: La acción que falló, la misma que se dio en el plan, o
            ``None`` si no falló ninguna.
        fallo_en: El instante en que falló la acción, o ``None`` si no falló
            ninguna.
        estados_objetivos: El estado de cada objetivo, en el orden en que se
            dieron los objetivos.
        acciones_totales: El número de acciones del plan.
        acciones_terminadas: El número de acciones que terminaron.
    """

    VALIDO = "VÁLIDO"
    NO_RESUELVE = "NO RESUELVE"
    NO_EJECUTABLE = "NO EJECUTABLE"
    INCOMPLETO = "INCOMPLETO"
    EJECUTABLE = "EJECUTABLE"

    def __init__(
        self,
        *,
        ejecutable: bool,
        completado: bool,
        error: str | None,
        accion_fallida: Accion | None,
        fallo_en: float | None,
        estados_objetivos: list[EstadoObjetivo],
        acciones_totales: int,
        acciones_terminadas: int,
    ) -> None:
        self._ejecutable = ejecutable
        self._completado = completado
        self._error = error
        self._accion_fallida = accion_fallida
        self._fallo_en = fallo_en
        # Simulacion ya pasa una lista nueva con copias de sus estados, para que el
        # informe no cambie cuando la simulación avance o se reinicie, así que aquí
        # no hace falta copiarla.
        self._estados_objetivos = estados_objetivos
        self._acciones_totales = acciones_totales
        self._acciones_terminadas = acciones_terminadas

    def __repr__(self) -> str:
        return f"InformeVerificacion(veredicto={self.veredicto!r})"

    def __str__(self) -> str:
        return self.resumen()

    # ------------------------------------------------------------------
    # Texto que se muestra
    # ------------------------------------------------------------------

    def resumen(self) -> str:
        """Devuelve el veredicto y sus motivos, como texto de varias líneas."""
        lineas = [f"Veredicto: {self.veredicto}"]

        if self._error is not None:
            lineas.append(f"Ejecución: interrumpida -> {self._error}")
        else:
            lineas.append(
                f"Ejecución: {self._acciones_terminadas}/{self._acciones_totales} "
                "acciones terminadas sin errores"
            )
            if not self._completado:
                lineas.append(
                    "Aviso: el plan no llegó a terminar, así que las acciones "
                    "pendientes y el estado final no se han comprobado"
                )

        if not self.tiene_objetivos:
            lineas.append("Objetivos: no se han definido")
            if self.veredicto == self.EJECUTABLE:
                lineas.append(
                    "Aviso: solo se ha comprobado que el plan se ejecuta "
                    "entero sin errores"
                )
            return "\n".join(lineas)

        lineas.append(
            f"Objetivos: {len(self.objetivos_cumplidos)} de "
            f"{len(self._estados_objetivos)} cumplidos"
        )

        for estado_objetivo in self._estados_objetivos:
            lineas.append(f"  {estado_objetivo}  ({estado_objetivo._texto_tiempos()})")
            if estado_objetivo.explicacion_fallo is not None:
                # La explicación lleva delante siete espacios, el ancho de "  [--] " al
                # principio de la línea del objetivo, para que quede justo debajo de su
                # descripción.
                lineas.append(f"       {estado_objetivo.explicacion_fallo}")

        return "\n".join(lineas)

    # ------------------------------------------------------------------
    # Valores de la ejecución
    # ------------------------------------------------------------------

    @property
    def ejecutable(self) -> bool:
        """Si no ha fallado ninguna acción."""
        return self._ejecutable

    @property
    def completado(self) -> bool:
        """Si han terminado todas las acciones del plan."""
        return self._completado

    @property
    def error(self) -> str | None:
        """El mensaje de error de la acción que falló, o ``None`` si ninguna falló."""
        return self._error

    @property
    def accion_fallida(self) -> Accion | None:
        """La acción que falló, o ``None`` si ninguna falló.

        Es la misma acción que se dio en el plan, no una copia, así que se puede
        buscar en la lista de acciones, p. ej. con ``acciones.index()``. El mensaje
        de ``error`` dice por qué falló.
        """
        return self._accion_fallida

    @property
    def fallo_en(self) -> float | None:
        """El instante en que falló la acción, o ``None`` si ninguna falló.

        Es el ``inicio_sim`` de la acción si no pudo empezar, o su ``tiempo_fin``
        si no pudo terminar. Como una acción siempre dura más de 0, los dos
        instantes son distintos, así que comparándolos se sabe en cuál falló.
        """
        return self._fallo_en

    @property
    def estados_objetivos(self) -> list[EstadoObjetivo]:
        """El estado de cada objetivo, en el orden en que se dieron los objetivos.

        Devuelve una copia de la lista, así que añadirle o quitarle estados no
        cambia el informe.
        """
        return list(self._estados_objetivos)

    @property
    def acciones_totales(self) -> int:
        """El número de acciones del plan."""
        return self._acciones_totales

    @property
    def acciones_terminadas(self) -> int:
        """El número de acciones que terminaron."""
        return self._acciones_terminadas

    # ------------------------------------------------------------------
    # Objetivos y veredicto
    # ------------------------------------------------------------------

    @property
    def tiene_objetivos(self) -> bool:
        """Si el problema recibió algún objetivo."""
        return len(self._estados_objetivos) > 0

    @property
    def objetivos_no_cumplidos(self) -> list[EstadoObjetivo]:
        """El estado de cada objetivo que no se cumplía al crear el informe."""
        return [estado for estado in self._estados_objetivos if not estado.cumplido]

    @property
    def objetivos_cumplidos(self) -> list[EstadoObjetivo]:
        """El estado de cada objetivo que se cumplía al crear el informe."""
        return [estado for estado in self._estados_objetivos if estado.cumplido]

    @property
    def todos_cumplidos(self) -> bool:
        """Si se cumplen todos los objetivos. También es cierto si no hay ninguno."""
        return not self.objetivos_no_cumplidos

    @property
    def veredicto(self) -> str:
        """El veredicto de la ejecución: una de las cinco constantes de la clase."""
        if not self._ejecutable:
            return self.NO_EJECUTABLE
        # Aquí ya no ha fallado ninguna acción, de modo que un plan sin terminar se
        # detuvo antes de tiempo, p. ej. porque se cerró la ventana. Esto se mira
        # antes que los objetivos: las acciones que quedan no se llegaron a
        # intentar, y un objetivo cumplido a mitad del plan aún podía deshacerse.
        if not self._completado:
            return self.INCOMPLETO
        # Sin objetivos el plan no puede llamarse válido, solo ejecutable:
        # "VÁLIDO" se reserva para los planes que logran los objetivos que recibieron.
        if not self.tiene_objetivos:
            return self.EJECUTABLE
        if not self.todos_cumplidos:
            return self.NO_RESUELVE
        return self.VALIDO

    @property
    def es_valido(self) -> bool:
        """Si el plan entero se ejecutó sin errores y logró sus objetivos.

        Un plan sin objetivos nunca es válido: si se ejecuta entero, su veredicto
        es ``"EJECUTABLE"``.
        """
        return self.veredicto == self.VALIDO
