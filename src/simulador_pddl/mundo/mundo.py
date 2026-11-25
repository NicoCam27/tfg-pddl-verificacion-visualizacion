from __future__ import annotations

from typing import TYPE_CHECKING

from simulador_pddl.simulacion.simulacion import Simulacion

if TYPE_CHECKING:
    from collections.abc import Sequence

    from simulador_pddl.acciones import Accion
    from simulador_pddl.objetivos import Objetivo
    from simulador_pddl.objetos import (
        Caja,
        Contenido,
        Dron,
        Localizacion,
        Persona,
        Transportador,
    )
    from simulador_pddl.simulacion import InformeVerificacion


class Mundo:
    """Mundo es el punto de entrada de la biblioteca: ejecuta y verifica un plan.

    Un mundo se construye a partir de un plan y del problema que el plan debería
    resolver. Al construirlo solo se comprueba lo que se ve sin ejecutar el plan:
    que cada acción y cada objetivo usen objetos declarados, que los drones, las
    cajas, las personas y los transportadores estén en localizaciones declaradas,
    que las cajas y las personas usen contenidos declarados, que ningún brazo
    pertenezca a dos drones, que no haya dos objetos con el mismo nombre y que
    ningún objetivo sea imposible de lograr. Si algo falla, se lanza una
    excepción. Lo demás se comprueba al ejecutarlo con
    ``simulacion_texto()`` o ``simulacion_visual()``: si cada acción se puede
    aplicar en el estado de ese momento (por ejemplo, si dos drones intentan coger
    la misma caja a la vez, uno de los dos falla), si ningún dron se mueve mientras
    hace otra cosa, si ningún brazo hace dos cosas a la vez y si se logran los
    objetivos. Un fallo en ese momento no lanza ninguna excepción: la ejecución se
    detiene en la acción que falla, y el ``InformeVerificacion`` que devuelven da el
    veredicto ``"NO EJECUTABLE"`` y el mensaje de ese fallo.

    El plan se ejecuta sobre los objetos que recibe el mundo, no sobre copias: al
    ejecutarlo, los objetos cambian (los drones se mueven, las cajas se entregan,
    las personas dejan de necesitar lo que reciben) y después se pueden consultar
    para ver cómo ha quedado el problema. Las acciones también guardan si han
    empezado y terminado. Por eso un mundo parte del estado en que estén sus
    objetos al construirlo: si otro mundo ya los usó, parte del estado en que ese
    otro los dejó. Para comprobar varios planes sobre el mismo problema, hay que
    crear los objetos y las acciones de nuevo para cada plan, p. ej. con una
    función que construya el problema. ``reiniciar()`` devuelve los objetos al
    estado en que estaban al construir este mundo.

    Todos los argumentos menos ``acciones`` se pasan por nombre, para que cada
    lista diga lo que contiene. Cada lista puede ser una lista o una tupla.

    Args:
        acciones: Las acciones del plan.
        localizaciones: Las localizaciones del problema.
        drones: Los drones del problema.
        cajas: Las cajas del problema.
        personas: Las personas del problema.
        contenidos: Los contenidos del problema: los de las cajas, las
            necesidades de las personas y los de los objetivos.
        transportadores: Los transportadores del problema. Opcional: ``None``
            (por defecto) significa que el problema no tiene transportadores, así
            que se rechaza un plan que use alguno.
        objetivos: Los objetivos que tiene que lograr el plan. Opcional: ``None``
            (por defecto) o una lista vacía significan que no hay objetivos, así que
            el plan puede resultar ejecutable, pero nunca válido.

    Raises:
        TypeError: Si un argumento no es una lista o una tupla (salvo ``None`` en
            ``transportadores`` y ``objetivos``) o contiene algo que no es del
            tipo esperado, o si un objetivo se refiere a algo que no es un objeto
            del dominio.
        ValueError: Si una acción o un objetivo usa un objeto que no está en su
            lista (o un transportador, si no se dan transportadores), si una caja o
            una persona usa un contenido que no está en ``contenidos``, si un dron,
            una caja, una persona o un transportador está en una localización que no
            está en ``localizaciones``, si un brazo pertenece a dos drones, si dos
            objetos tienen el mismo nombre o si ningún plan puede lograr un
            objetivo.

    Example:
        mundo = Mundo(
            acciones,
            localizaciones=[deposito, localizacion1],
            drones=[dron],
            cajas=[caja],
            personas=[persona],
            contenidos=[comida],
            objetivos=objetivos,
        )
        informe = mundo.simulacion_texto()
        print(informe.veredicto)
    """

    def __init__(
        self,
        acciones: Sequence[Accion],
        *,
        localizaciones: Sequence[Localizacion],
        drones: Sequence[Dron],
        cajas: Sequence[Caja],
        personas: Sequence[Persona],
        contenidos: Sequence[Contenido],
        transportadores: Sequence[Transportador] | None = None,
        objetivos: Sequence[Objetivo] | None = None,
    ) -> None:
        # Mundo es solo la fachada pública: Simulacion comprueba el plan y lo
        # ejecuta. Las excepciones de la sección Raises salen de esa comprobación.
        self._simulacion = Simulacion(
            acciones,
            localizaciones=localizaciones,
            drones=drones,
            cajas=cajas,
            personas=personas,
            contenidos=contenidos,
            transportadores=transportadores,
            objetivos=objetivos,
        )

    def __repr__(self) -> str:
        return (
            f"Mundo(acciones={len(self._simulacion._acciones)}, "
            f"objetivos={len(self._simulacion._objetivos)})"
        )

    # ------------------------------------------------------------------
    # Uso en terminal, sin pygame
    # ------------------------------------------------------------------

    def simulacion_texto(self, paso_tiempo: float = 0.1) -> InformeVerificacion:
        """Ejecuta el plan en la terminal y devuelve su informe.

        Imprime cada inicio y final de acción, lo que narra cada dron y, al
        terminar, el resumen del informe. Si falla una acción, la nombra antes del
        error. La ejecución llega al final del plan o se detiene en la primera
        acción que falla, así que el veredicto nunca es ``"INCOMPLETO"``.

        La ejecución sigue desde donde esté la simulación: una segunda llamada no
        vuelve a ejecutar el plan, solo da otra vez su informe. Para ejecutarlo de
        nuevo desde el principio, hay que llamar antes a ``reiniciar()``.

        Args:
            paso_tiempo: Los segundos simulados que avanza la simulación en cada
                actualización. Opcional: 0.1 por defecto. El veredicto no depende
                de él.

        Returns:
            El ``InformeVerificacion`` de la ejecución.

        Raises:
            TypeError: Si ``paso_tiempo`` no es un int o un float.
            ValueError: Si ``paso_tiempo`` no es mayor que 0.
        """
        return self._simulacion._simulacion_texto(paso_tiempo)

    def verificar(self) -> InformeVerificacion:
        """Devuelve el informe del plan en el estado actual, sin ejecutar nada.

        Juzga el punto al que haya llegado la ejecución, p. ej. después de
        ``simulacion_texto()`` o de cerrar ``simulacion_visual()``. Mientras el
        plan no haya terminado, el veredicto es ``"INCOMPLETO"``, o
        ``"NO EJECUTABLE"`` si ya ha fallado una acción. Por eso un mundo recién
        construido da ``"INCOMPLETO"``: para comprobar un plan, primero hay que
        ejecutarlo. La única excepción es un plan vacío, que ya está terminado
        desde el principio y se juzga sobre el estado inicial.

        Returns:
            El ``InformeVerificacion`` del estado actual.
        """
        return self._simulacion._crear_informe()

    def avanzar_hasta(self, instante: float) -> InformeVerificacion:
        """Ejecuta el plan hasta ``instante``, sin imprimir nada, y devuelve el informe.

        ``instante`` es un tiempo del plan, como ``inicio_sim``, y la ejecución sigue
        desde el estado actual. Se aplican todos los sucesos de ese instante (los
        finales antes que los inicios), así que
        ``mundo.avanzar_hasta(accion.inicio_sim)`` deja el mundo con ``accion``
        recién empezada. Después se puede seguir con otro ``avanzar_hasta()``
        posterior, con ``simulacion_texto()`` o con ``simulacion_visual()``.

        La ejecución se detiene antes de ``instante`` si el plan termina o falla una
        acción. Para ejecutar el plan entero sin saber cuándo termina, basta con
        ``math.inf``.

        Args:
            instante: El instante del plan hasta el que se ejecuta, en segundos.

        Returns:
            El ``InformeVerificacion`` de ese punto, como el de ``verificar()``.
            Si ha fallado una acción, el veredicto es ``"NO EJECUTABLE"``, con el
            mensaje en ``error``. Si no, es ``"INCOMPLETO"`` mientras el plan no ha
            terminado, y el veredicto final (``"VÁLIDO"``, ``"NO RESUELVE"`` o
            ``"EJECUTABLE"``) cuando termina.

        Raises:
            TypeError: Si ``instante`` no es un int o un float.
            ValueError: Si ``instante`` es negativo o NaN, o anterior al tiempo
                actual de la simulación (para volver atrás, hay que llamar antes a
                ``reiniciar()``).
        """
        # bool es una subclase de int, así que True y False se rechazan expresamente.
        if isinstance(instante, bool) or not isinstance(instante, (int, float)):
            msg_tipo_instante = (
                f"'instante' debe ser un int o un float, se recibió {instante!r}"
            )
            raise TypeError(msg_tipo_instante)
        # La comparación es falsa con NaN, así que también lo rechaza.
        if not instante >= 0:
            msg_rango_instante = (
                f"'instante' debe ser mayor o igual que 0, se recibió {instante!r}"
            )
            raise ValueError(msg_rango_instante)
        tiempo_actual = self._simulacion._tiempo_simulacion
        if instante < tiempo_actual:
            msg_instante_pasado = (
                f"el instante {instante!r} es anterior al tiempo actual de la "
                f"simulación, {tiempo_actual!r}: para volver atrás, hay que "
                "llamar antes a reiniciar()"
            )
            raise ValueError(msg_instante_pasado)

        self._simulacion._avanzar_hasta(instante)
        return self._simulacion._crear_informe()

    def reiniciar(self) -> None:
        """Vuelve al instante 0, con los objetos como estaban al construir el mundo.

        También olvida lo que pasó en la ejecución: qué acciones empezaron o
        terminaron, el error, si lo hubo, y cuándo se cumplió cada objetivo. Así
        el plan se puede volver a ejecutar desde el principio con
        ``simulacion_texto()`` o ``simulacion_visual()``. Un informe devuelto
        antes conserva el resultado de su ejecución.
        """
        self._simulacion._reiniciar()

    # ------------------------------------------------------------------
    # Simulación visual
    # ------------------------------------------------------------------

    def simulacion_visual(
        self,
        ancho: int | None = None,
        alto: int | None = None,
        titulo: str = "Simulación PDDL",
        fps: int = 60,
    ) -> InformeVerificacion:
        """Ejecuta el plan en una ventana de pygame y devuelve su informe.

        La ventana, que se puede redimensionar, tiene botones para reproducir,
        pausar y reiniciar el plan, y un deslizador para la velocidad: a 1x, un
        segundo simulado dura un segundo real. Si una acción falla, la ejecución
        se detiene y la ventana sigue abierta mostrando el error. El método
        vuelve cuando se cierra la ventana.

        La ventana muestra la simulación tal como esté: un mundo recién
        construido o reiniciado se abre en pausa, y el plan avanza al pulsar
        "Reproducir". Si el plan ya se ha ejecutado, p. ej. con
        ``simulacion_texto()``, se abre terminado, o detenido en la acción que
        falló, y "Reiniciar" lo vuelve a poner al principio.

        Args:
            ancho: El ancho de la ventana, en píxeles. Opcional: ``None`` (por
                defecto) usa el ancho por defecto de ``Renderizador``. Un ancho
                menor que ``Renderizador.ANCHO_MINIMO`` se sube a ese mínimo.
            alto: El alto de la ventana, en píxeles. Opcional: ``None`` (por
                defecto) usa el alto por defecto de ``Renderizador``. Un alto
                menor que ``Renderizador.ALTO_MINIMO`` se sube a ese mínimo.
            titulo: El título de la ventana. Opcional: ``"Simulación PDDL"`` por
                defecto.
            fps: Los fotogramas que se dibujan por segundo. Opcional: 60 por
                defecto.

        Returns:
            El ``InformeVerificacion`` del plan en el momento en que se cierra la
            ventana. Si para entonces el plan no había terminado, su veredicto es
            ``"INCOMPLETO"`` (``InformeVerificacion.INCOMPLETO``).

        Raises:
            TypeError: Si ``ancho`` o ``alto`` no es un entero o ``None``,
                ``titulo`` no es una cadena o ``fps`` no es un entero.
            ValueError: Si ``fps`` no es mayor que 0.
        """
        # Los argumentos se comprueban antes de arrancar pygame: si alguno es
        # incorrecto, se lanza el error sin llegar a abrir la ventana.
        self._validar_argumentos_ventana(ancho, alto, titulo, fps)

        # Se importa aquí, no al nivel del módulo, para que usar Mundo solo para
        # verificar o para simular en texto no necesite pygame.
        from simulador_pddl.visualizacion.ventana import _ejecutar_ventana

        _ejecutar_ventana(self._simulacion, ancho, alto, titulo, fps)
        return self._simulacion._crear_informe()

    @staticmethod
    def _validar_argumentos_ventana(
        ancho: object, alto: object, titulo: object, fps: object
    ) -> None:
        """Lanza un error si un argumento de ``simulacion_visual()`` es incorrecto.

        Raises:
            TypeError: Si ``ancho`` o ``alto`` no es un entero o ``None``,
                ``titulo`` no es una cadena o ``fps`` no es un entero.
            ValueError: Si ``fps`` no es mayor que 0.
        """
        # bool es una subclase de int, así que True y False se rechazan expresamente.
        # Un tamaño menor que el mínimo no es un error: Renderizador lo sube al
        # mínimo.
        for nombre_tamano, tamano in (("ancho", ancho), ("alto", alto)):
            if tamano is not None and (
                isinstance(tamano, bool) or not isinstance(tamano, int)
            ):
                msg_tipo_tamano = (
                    f"'{nombre_tamano}' debe ser un entero o None, "
                    f"se recibió {tamano!r}"
                )
                raise TypeError(msg_tipo_tamano)

        if not isinstance(titulo, str):
            msg_tipo_titulo = f"'titulo' debe ser una cadena, se recibió {titulo!r}"
            raise TypeError(msg_tipo_titulo)

        if isinstance(fps, bool) or not isinstance(fps, int):
            msg_tipo_fps = f"'fps' debe ser un entero, se recibió {fps!r}"
            raise TypeError(msg_tipo_fps)
        if fps < 1:
            msg_rango_fps = f"'fps' debe ser mayor que 0, se recibió {fps!r}"
            raise ValueError(msg_rango_fps)
