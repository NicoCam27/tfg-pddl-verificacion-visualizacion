"""Simulación: valida un plan y dirige su ejecución a lo largo del tiempo.

Una ``Simulacion`` se construye a partir de las acciones del plan, los objetos
del problema y, si los hay, sus objetivos. Al construirse comprueba que cada
acción y cada objetivo solo se refieren a objetos declarados, que los drones,
las cajas, las personas y los transportadores están en localizaciones
declaradas, que las cajas y las personas solo usan contenidos declarados, que
ningún brazo pertenece a dos drones, que no hay dos objetos con el mismo nombre,
que ninguna acción ha empezado ya en otra simulación y que ningún objetivo es
imposible de lograr desde el estado inicial. Que ningún dron se mueva mientras
hace otra cosa, ni un brazo haga dos cosas a la vez, se comprueba al ejecutar,
cuando empieza cada acción.

Después, ``_avanzar_hasta()`` aplica en orden temporal los efectos ``at start`` y
``at end`` de cada acción hasta un instante dado (``_actualizar()`` lo usa para
avanzar paso a paso), y ``_crear_informe()`` devuelve el informe con el veredicto
(ver ``InformeVerificacion``). Un plan clásico, sin tiempos, se simula igual: sus
pasos se numeran desde 0, y el paso ``i`` es una acción con ``inicio_sim=i`` y
``duracion_sim=1``. ``_reiniciar()`` vuelve al estado capturado cuando se
construyó la simulación.

``Mundo`` es el punto de entrada público y la única clase que crea una
``Simulacion``: ``Mundo.simulacion_texto()`` ejecuta el plan en una terminal,
``Mundo.simulacion_visual()`` lo ejecuta en una ventana de pygame, donde el
``Renderizador`` lo dibuja y el ``PanelControl`` muestra sus controles, y
``Mundo.avanzar_hasta()`` lo ejecuta solo hasta un instante, sin imprimir nada.
Como el usuario solo utiliza ``Mundo``, nunca una ``Simulacion``, todos los
miembros de ``Simulacion`` salvo el constructor son privados.
"""

from __future__ import annotations

import copy
import logging
import sys
from typing import TYPE_CHECKING, assert_never

from simulador_pddl.acciones import Accion, Mover, MoverTransportador
from simulador_pddl.objetivos import Objetivo
from simulador_pddl.objetos import (
    Brazo,
    Caja,
    Contenido,
    Dron,
    Localizacion,
    Persona,
    Transportador,
)
from simulador_pddl.objetos.utilidades_objetos import (
    con_articulo,
    con_preposicion_a,
    tipo_con_articulo_indefinido,
    tipo_en_plural,
)
from simulador_pddl.simulacion.instantanea import InstantaneaMundo
from simulador_pddl.simulacion.verificacion import EstadoObjetivo, InformeVerificacion

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from simulador_pddl.objetivos.objetivo import ObjetoReferenciado
    from simulador_pddl.objetos import ObjetoDominio


def _lista_tipada[T](
    lista_recibida: object,
    tipo_esperado: type[T],
    nombre_argumento: str,
    *,
    admite_none: bool = False,
) -> list[T]:
    """Comprueba que ``lista_recibida`` es una lista o tupla de ``tipo_esperado``.

    Devuelve sus elementos en una lista nueva, para que la simulación no cambie si
    el usuario modifica después su lista. ``nombre_argumento`` es el argumento de
    ``Mundo`` del que viene la lista, y aparece en el mensaje de error.

    Si ``admite_none`` es verdadero, el mensaje dice "una lista, una tupla o None"
    en lugar de "una lista o una tupla", porque ese argumento de ``Mundo`` también
    acepta ``None``, como ``transportadores`` y ``objetivos``. ``None`` nunca llega
    a esta función: ``Simulacion`` lo trata antes de llamarla.

    Raises:
        TypeError: Si ``lista_recibida`` no es una lista o una tupla, o contiene algo
            que no es un objeto ``tipo_esperado``.
    """
    if not isinstance(lista_recibida, (list, tuple)):
        valores_validos = (
            "una lista, una tupla o None" if admite_none else "una lista o una tupla"
        )
        msg_lista = (
            f"'{nombre_argumento}' debe ser {valores_validos}, "
            f"se recibió {lista_recibida!r}"
        )
        raise TypeError(msg_lista)

    for elemento in lista_recibida:
        if not isinstance(elemento, tipo_esperado):
            msg_tipo_elemento = (
                f"'{nombre_argumento}' solo puede contener objetos "
                f"{tipo_esperado.__name__}, se recibió {elemento!r}"
            )
            raise TypeError(msg_tipo_elemento)

    return list(lista_recibida)


class Simulacion:
    """Simulacion valida un plan y lo ejecuta a lo largo del tiempo simulado.

    Al construirla se comprueban el plan y los objetivos (ver el docstring del
    módulo) y se captura el estado del mundo, para que ``_reiniciar()`` pueda
    volver a él. Una simulación empieza en pausa, en el instante 0.

    Todos los argumentos menos ``acciones`` se pasan por nombre. Cada uno es una
    lista o una tupla, salvo ``transportadores`` y ``objetivos``, que también
    pueden ser ``None``.

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
    """

    # Acciones que ocupan el dron entero: mientras se mueve no puede hacer nada
    # más. El resto (coger o soltar una caja o un transportador, entregar una caja,
    # y meter o sacar una caja de un transportador) solo ocupan un brazo, así que
    # dos brazos distintos pueden trabajar a la vez.
    _TIPOS_ACCION_DRON_ENTERO = (Mover, MoverTransportador)

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
        self._localizaciones = _lista_tipada(
            localizaciones, Localizacion, "localizaciones"
        )
        self._drones = _lista_tipada(drones, Dron, "drones")
        self._cajas = _lista_tipada(cajas, Caja, "cajas")
        self._personas = _lista_tipada(personas, Persona, "personas")
        self._contenidos = _lista_tipada(contenidos, Contenido, "contenidos")

        # Los transportadores son opcionales: un problema sin ellos es válido, no
        # un error. Sin una lista de transportadores esto es None.
        # _todos_los_transportadores da [] para recorrerlos.
        self._transportadores = (
            _lista_tipada(
                transportadores, Transportador, "transportadores", admite_none=True
            )
            if transportadores is not None
            else None
        )
        self._exigir_referencias_declaradas()
        self._exigir_brazos_no_compartidos()
        self._exigir_nombres_no_repetidos()

        # acciones se anota como Sequence para que el comprobador de tipos acepte
        # una lista de un solo tipo de acción (list[CogerCaja]): list[Accion] la
        # rechazaría. mypy no deja pasar una clase abstracta como type[T], por si
        # se instancia, pero _lista_tipada() solo la usa en isinstance().
        self._acciones = _lista_tipada(acciones, Accion, "acciones")  # type: ignore[type-abstract]
        for accion in self._acciones:
            self._exigir_objetos_declarados(accion)
            self._exigir_accion_sin_empezar(accion)

        # Una lista vacía si no se dieron objetivos.
        self._objetivos = self._validar_objetivos(objetivos)
        self._estados_objetivos = [
            EstadoObjetivo(objetivo) for objetivo in self._objetivos
        ]

        # _reiniciar() vuelve al estado del momento en que se construyó esta
        # Simulacion, no al del momento en que se crearon los objetos.
        self._instantanea_inicial = InstantaneaMundo._capturar(
            self._drones, self._cajas, self._personas, self._todos_los_transportadores
        )

        # El tiempo simulado actual, en segundos.
        self._tiempo_simulacion = 0.0
        # Cuántos segundos simulados pasan por cada segundo que se da a _actualizar().
        self._velocidad = 1.0
        # Si _actualizar() avanza la simulación.
        self._reproduciendo = False
        # Las acciones que han empezado y todavía no han terminado.
        self._acciones_activas: list[Accion] = []
        # La línea de estado del panel de la simulación visual (PanelControl): la
        # descripción de la última acción que empezó, o "Simulación preparada" si
        # todavía no ha empezado ninguna ("Simulación reiniciada" después de un
        # reinicio).
        self._texto_estado = "Simulación preparada"
        # El mensaje de error de la acción que falló y la propia acción, o None si
        # ninguna falló. El panel lateral de la simulación visual marca esa acción.
        self._error: str | None = None
        self._accion_fallida: Accion | None = None

        # Funciones opcionales que se llaman con cada acción justo después de que
        # empiece o termine, si no son None. Solo _simulacion_texto() les da valor,
        # para imprimir en la terminal una línea por cada acción que empieza o
        # termina. Así _actualizar() no imprime nada por su cuenta, y la simulación
        # visual ejecuta el mismo código sin escribir en la terminal.
        self._al_iniciar_accion: Callable[[Accion], None] | None = None
        self._al_terminar_accion: Callable[[Accion], None] | None = None

        # Estado inicial de los objetivos: alguno puede cumplirse ya al inicio
        # (un dron que empieza en el depósito, por ejemplo).
        self._evaluar_objetivos()

    def __repr__(self) -> str:
        return (
            f"Simulacion(acciones={len(self._acciones)}, "
            f"objetivos={len(self._objetivos)}, "
            f"tiempo_simulacion={self._tiempo_simulacion!r})"
        )

    def __str__(self) -> str:
        return f"Simulacion({self._texto_tiempo()}, {self._texto_recuento_acciones()})"

    # ------------------------------------------------------------------
    # Validación al construir
    # ------------------------------------------------------------------

    @staticmethod
    def _exigir_dentro(objeto: ObjetoDominio, coleccion: Sequence[object]) -> None:
        """Lanza ``ValueError`` si ``objeto`` no está en ``coleccion``."""
        if objeto not in coleccion:
            msg_no_mencionado = (
                f"{con_articulo(objeto)} no aparece en la lista de "
                f"{tipo_en_plural(objeto)} dada"
            )
            raise ValueError(msg_no_mencionado)

    def _exigir_lista_de_transportadores(self, accion: Accion) -> None:
        """Lanza ``ValueError`` si el problema no tiene lista de transportadores."""
        if self._transportadores is None:
            msg_sin_transportadores = (
                f"la acción {type(accion).__name__} no se puede realizar "
                "si no se dan transportadores"
            )
            raise ValueError(msg_sin_transportadores)

    def _exigir_objetos_declarados(self, accion: Accion) -> None:
        """Lanza ``ValueError`` si la acción usa un objeto que no se declaró.

        También si usa un transportador y el problema no tiene lista de
        transportadores.
        """
        # El brazo no se comprueba: no hay lista de brazos, y cada acción ya exige
        # al construirse que su brazo sea de su dron.
        objetos = accion.objetos.values()
        if any(isinstance(objeto, Transportador) for objeto in objetos):
            self._exigir_lista_de_transportadores(accion)
        for objeto in objetos:
            if not isinstance(objeto, Brazo):
                self._exigir_dentro(objeto, self._lista_declarada(objeto))

    @staticmethod
    def _exigir_accion_sin_empezar(accion: Accion) -> None:
        """Lanza ``ValueError`` si ``accion`` ya empezó en otro mundo.

        Una acción guarda si ha empezado y si ha terminado. Si otro mundo la dejó
        empezada, en este no estaría ni en curso ni pendiente, así que nunca
        terminaría y el plan no llegaría a acabar. Si la dejó terminada, contaría
        como terminada sin haberse ejecutado aquí. Una acción que falló al empezar
        se acepta: ``iniciada`` solo se activa cuando sus efectos ``at start``
        se aplican sin error, así que sigue como una acción nueva y en este mundo
        empieza con normalidad.
        """
        if accion.iniciada:
            msg_accion_ya_empezada = (
                f"la acción {accion.desc!r} ya empezó en otro mundo: cada mundo "
                "necesita acciones nuevas"
            )
            raise ValueError(msg_accion_ya_empezada)

    def _exigir_referencias_declaradas(self) -> None:
        """Lanza ``ValueError`` si un objeto del problema usa algo que no se declaró.

        Cada dron, caja, persona y transportador tiene que estar en una
        localización declarada, y cada caja y cada necesidad tienen que usar un
        contenido declarado. Una localización o un contenido mal escritos (p. ej.
        ``"deposto"`` por ``"deposito"``) harían que el plan pareciera incorrecto,
        o dejarían un objeto que la ventana no puede dibujar, así que se rechazan
        al construir.
        """
        objetos: list[Dron | Caja | Persona | Transportador] = [
            *self._drones,
            *self._cajas,
            *self._personas,
            *self._todos_los_transportadores,
        ]
        for objeto in objetos:
            if objeto.localizacion not in self._localizaciones:
                msg_localizacion_objeto = (
                    f"{con_articulo(objeto)} está en "
                    f"{con_articulo(objeto.localizacion)}, que no aparece en la "
                    f"lista de {tipo_en_plural(objeto.localizacion)} dada"
                )
                raise ValueError(msg_localizacion_objeto)

        for caja in self._cajas:
            if caja.contenido not in self._contenidos:
                msg_contenido_caja = (
                    f"{con_articulo(caja)} tiene {con_articulo(caja.contenido)}, "
                    "que no aparece en la lista de "
                    f"{tipo_en_plural(caja.contenido)} dada"
                )
                raise ValueError(msg_contenido_caja)

        for persona in self._personas:
            for necesidad in persona.necesidades:
                if necesidad not in self._contenidos:
                    msg_necesidad_persona = (
                        f"{con_articulo(persona)} necesita "
                        f"{con_articulo(necesidad)}, que no aparece en la lista de "
                        f"{tipo_en_plural(necesidad)} dada"
                    )
                    raise ValueError(msg_necesidad_persona)

    def _exigir_brazos_no_compartidos(self) -> None:
        """Lanza ``ValueError`` si un brazo pertenece a más de un dron.

        En el dominio, cada brazo es de un solo dron. Dos drones con el mismo
        objeto ``Brazo`` verían el mismo contenido, y la comprobación de
        solapamientos, que agrupa las acciones por dron, no los detendría: un
        plan incorrecto podría resultar ejecutable sin ningún error.
        """
        duenos: dict[Brazo, Dron] = {}
        for dron in self._drones:
            for brazo in dron.brazos:
                otro = duenos.setdefault(brazo, dron)
                if otro is not dron:
                    msg_brazo_compartido = (
                        f"el brazo {brazo.nombre} no puede pertenecer a más de un "
                        f"dron, pertenece {con_preposicion_a(con_articulo(otro))} y "
                        f"{con_preposicion_a(con_articulo(dron))}"
                    )
                    raise ValueError(msg_brazo_compartido)

    def _exigir_nombres_no_repetidos(self) -> None:
        """Lanza ``ValueError`` si dos objetos del problema tienen el mismo nombre.

        En PDDL, todos los objetos de un problema comparten un único espacio de
        nombres: el nombre identifica al objeto, sea del tipo que sea. Por eso se
        rechazan dos objetos con el mismo nombre, del mismo tipo o de tipos
        distintos, y también un mismo objeto repetido en una lista. Los brazos
        cuentan como los demás objetos, porque en PDDL lo son.
        """
        listas: list[Sequence[ObjetoDominio]] = [
            self._localizaciones,
            self._drones,
            [brazo for dron in self._drones for brazo in dron.brazos],
            self._cajas,
            self._personas,
            self._contenidos,
            self._todos_los_transportadores,
        ]
        objetos_por_nombre: dict[str, ObjetoDominio] = {}
        for lista in listas:
            for objeto in lista:
                otro = objetos_por_nombre.get(objeto.nombre)
                if otro is None:
                    objetos_por_nombre[objeto.nombre] = objeto
                    continue
                if otro is objeto:
                    msg_nombre_repetido = (
                        f"{con_articulo(objeto)} aparece más de una vez en la lista "
                        f"de {tipo_en_plural(objeto)} dada"
                    )
                elif type(otro) is type(objeto):
                    msg_nombre_repetido = (
                        f"hay más de {tipo_con_articulo_indefinido(objeto)} con el "
                        f"nombre {objeto.nombre}"
                    )
                else:
                    msg_nombre_repetido = (
                        f"{con_articulo(otro)} y {con_articulo(objeto)} tienen el "
                        f"mismo nombre"
                    )
                raise ValueError(msg_nombre_repetido)

    def _lista_declarada(
        self,
        objeto: Caja | Contenido | Dron | Localizacion | Persona | Transportador,
    ) -> Sequence[object]:
        """Devuelve la lista de objetos del tipo de ``objeto`` que se dio."""
        if isinstance(objeto, Caja):
            return self._cajas
        if isinstance(objeto, Contenido):
            return self._contenidos
        if isinstance(objeto, Dron):
            return self._drones
        if isinstance(objeto, Localizacion):
            return self._localizaciones
        if isinstance(objeto, Persona):
            return self._personas
        if isinstance(objeto, Transportador):
            return self._todos_los_transportadores
        # Si se añade un tipo de objeto, mypy avisa aquí hasta que tenga su rama.
        assert_never(objeto)

    def _validar_objetivos(
        self, objetivos: Sequence[Objetivo] | None
    ) -> list[Objetivo]:
        """Comprueba los objetivos y los devuelve en una lista nueva.

        Si ``objetivos`` es ``None``, la lista está vacía.

        Raises:
            TypeError: Si ``objetivos`` no es una lista, una tupla o ``None``, o
                contiene algo que no es un objetivo.
            ValueError: Si un objetivo se refiere a un objeto que no se declaró, o
                ningún plan puede lograrlo desde el estado inicial.
        """
        if objetivos is None:
            return []

        # Objetivo es abstracta, como Accion en __init__().
        lista_objetivos = _lista_tipada(
            objetivos,
            Objetivo,  # type: ignore[type-abstract]
            "objetivos",
            admite_none=True,
        )
        for objetivo in lista_objetivos:
            # Un objetivo sobre un objeto no declarado nunca se podría lograr, así
            # que se rechaza al construir en lugar de dar el plan por no válido.
            # También se rechaza un objetivo que ningún plan puede lograr desde el
            # estado inicial (p. ej. que una persona posea un contenido que no
            # necesita): eso lo comprueba _validar_alcanzable().
            for referenciado in objetivo._objetos_referenciados():
                self._exigir_declarado(referenciado, objetivo)
            objetivo._validar_alcanzable()

        return lista_objetivos

    def _exigir_declarado(
        self, referenciado: ObjetoReferenciado, objetivo: Objetivo
    ) -> None:
        """Lanza ``ValueError`` si ``referenciado`` no se declaró.

        ``referenciado`` es uno de los objetos a los que se refiere ``objetivo``.
        También lanza el error si es un transportador y el problema no tiene lista
        de transportadores.
        """
        if isinstance(referenciado, Transportador) and self._transportadores is None:
            msg_sin_transportadores = (
                f"el objetivo {objetivo._describir()!r} se refiere a un "
                "transportador, pero no se dan transportadores"
            )
            raise ValueError(msg_sin_transportadores)

        if referenciado not in self._lista_declarada(referenciado):
            msg_objeto_no_mencionado = (
                f"el objetivo {objetivo._describir()!r} se refiere "
                f"{con_preposicion_a(con_articulo(referenciado))}, que no aparece "
                f"en la lista de {tipo_en_plural(referenciado)} dada"
            )
            raise ValueError(msg_objeto_no_mencionado)

    # ------------------------------------------------------------------
    # Ejecución paso a paso
    # ------------------------------------------------------------------

    def _actualizar(self, dt: float) -> None:
        """Avanza el tiempo simulado ``dt * _velocidad`` segundos como máximo.

        Cada acción empieza y termina en su instante exacto, en orden temporal,
        así que el resultado no depende del tamaño de ``dt``. Cuando termina el
        plan, el reloj se detiene en el instante del último suceso y la
        simulación se pone en pausa. No hace nada mientras está en pausa o
        después de que una acción haya fallado.
        """
        if not self._reproduciendo:
            return
        self._avanzar_hasta(self._tiempo_simulacion + dt * self._velocidad)

    def _avanzar_hasta(self, tiempo_objetivo: float) -> None:
        """Aplica en orden temporal los sucesos del plan hasta ``tiempo_objetivo``.

        Se aplican todos los sucesos de ``tiempo_objetivo``, así que una acción que
        empieza en ese instante queda recién empezada. Si el plan termina antes,
        el reloj se detiene en el instante de su último suceso y la simulación se
        pone en pausa. Si falla una acción, se detiene en ella. No hace nada
        después de que una acción haya fallado.

        Lo llaman ``_actualizar()``, que antes comprueba que la simulación no está
        en pausa, y ``Mundo.avanzar_hasta()`` y ``_saltar_a_accion()`` de la
        ventana, que avanzan aunque lo esté. Por eso este método no mira la pausa.
        """
        if self._tiene_error:
            return

        # Un tic puede abarcar varios sucesos del plan (el inicio o el final de
        # una acción): con un paso_tiempo grande, con el multiplicador de
        # velocidad, o con planes cuyos instantes están a milisegundos (sgplan40
        # deja 0.01 entre acciones, optic-clp encadena acciones a 0.001). Si el
        # tic se aplicara de una vez, una acción que empieza y termina dentro de
        # él no terminaría hasta el tic siguiente, y otra que empezara más tarde
        # en el mismo tic no vería sus efectos: el veredicto dependería del tamaño
        # del paso. Por eso el tiempo avanza de suceso en suceso, en orden
        # temporal y no en el orden en que se escribió el plan. tiempo_objetivo
        # solo decide hasta dónde llega esta llamada, no el orden de los efectos.
        while True:
            tiempo_suceso = self._tiempo_siguiente_suceso(tiempo_objetivo)
            if tiempo_suceso is None:
                break

            # Las acciones, _al_iniciar_accion/_al_terminar_accion y el
            # seguimiento de los objetivos ven el instante exacto del suceso, no el
            # final del tic.
            self._tiempo_simulacion = tiempo_suceso
            self._aplicar_suceso(tiempo_suceso)

            if self._tiene_error:
                return

        # Si el plan ha terminado, el reloj se queda en el instante de su último
        # suceso y no avanza hasta el final del tic, que no tiene por qué ser un
        # instante del plan: depende de paso_tiempo y del redondeo de las sumas.
        if self._terminada:
            self._reproduciendo = False
            return

        self._tiempo_simulacion = tiempo_objetivo

    def _tiempo_siguiente_suceso(self, limite: float) -> float | None:
        """Devuelve el primer instante, no posterior a ``limite``, con un suceso.

        Un suceso es el final de una acción en curso o el inicio de una pendiente.
        Devuelve ``None`` si no queda ninguno hasta ``limite``.
        """
        instantes_de_sucesos = [accion.tiempo_fin for accion in self._acciones_activas]
        instantes_de_sucesos += [
            accion.inicio_sim for accion in self._acciones if not accion.iniciada
        ]
        return min(
            (instante for instante in instantes_de_sucesos if instante <= limite),
            default=None,
        )

    def _aplicar_suceso(self, tiempo_suceso: float) -> None:
        """Termina e inicia las acciones que acaban o empiezan en ``tiempo_suceso``.

        En el mismo instante, los finales se procesan antes que los inicios. En
        un plan encadenado normal, una acción que termina en T y otra que empieza
        en T son un relevo, no una carrera: el ``_iniciar_*()`` de la segunda (sus
        efectos ``at start``) tiene que encontrar ya aplicados los efectos del
        ``_terminar_*()`` de la primera (p. ej. que el brazo ya sujeta la caja antes
        de comprobar que la puede soltar). Procesar antes los inicios convertiría
        cada relevo de este tipo en un falso error, y que dos acciones consecutivas
        compartan instante es lo más habitual en los planes que generan
        planificadores como LAMA u OPTIC.

        Los empates se resuelven por el orden de la lista: los finales en el orden
        en que empezaron las acciones, los inicios en el orden del plan. Dos
        acciones en el mismo instante son realmente simultáneas, y el plan no dice
        nada más para deshacer el empate. Ningún inicio libera algo que otro inicio
        necesite: solo comprueban condiciones o reservan algo. Si dos compiten por
        lo mismo, uno falla en cualquier orden, así que este empate no cambia el
        veredicto.
        """
        pendientes_de_terminar = [
            accion
            for accion in self._acciones_activas
            if accion.tiempo_fin <= tiempo_suceso
        ]

        for accion in pendientes_de_terminar:
            self._terminar_accion(accion)
            if self._tiene_error:
                return

        pendientes_de_iniciar = [
            accion
            for accion in self._acciones
            if not accion.iniciada and accion.inicio_sim <= tiempo_suceso
        ]

        for accion in pendientes_de_iniciar:
            self._iniciar_accion(accion)
            if self._tiene_error:
                return

    def _error_de_solapamiento(self, accion: Accion) -> str | None:
        """Devuelve el error si ``accion`` choca con una acción en curso, o ``None``.

        El recurso que no se puede compartir es el brazo, no el dron: un dron con
        dos brazos puede coger dos cajas a la vez, y los planificadores que
        paralelizan (lpg-td) lo hacen. Lo que sí ocupa el dron entero es moverse,
        porque se lleva consigo todo lo que sujeta. Una acción que termina en el
        mismo instante en que empieza ``accion`` ya no está en curso, porque los
        finales se procesan antes que los inicios.
        """
        for activa in self._acciones_activas:
            if activa.dron is not accion.dron:
                continue

            if isinstance(activa, self._TIPOS_ACCION_DRON_ENTERO) or isinstance(
                accion, self._TIPOS_ACCION_DRON_ENTERO
            ):
                return (
                    f"el dron {accion.dron.nombre} no puede empezar {accion.desc!r} "
                    f"en t={accion.inicio_sim} antes de terminar {activa.desc!r} "
                    f"en t={activa.tiempo_fin}"
                )

            # Ninguna de las dos es un movimiento, así que las dos tienen brazo.
            brazo = accion.objetos["brazo"]
            if activa.objetos["brazo"] is brazo:
                return (
                    f"el brazo {brazo.nombre} del dron {accion.dron.nombre} no "
                    f"puede empezar {accion.desc!r} en t={accion.inicio_sim} "
                    f"antes de terminar {activa.desc!r} en t={activa.tiempo_fin}"
                )

        return None

    def _iniciar_accion(self, accion: Accion) -> None:
        """Aplica los efectos ``at start`` de ``accion``.

        Si choca con una acción en curso del mismo dron o del mismo brazo, o si
        sus efectos fallan, detiene la simulación con el mensaje de error.
        """
        error = self._error_de_solapamiento(accion)
        if error is None:
            error = accion._iniciar_ejecucion()

        if error is not None:
            self._poner_error(error, accion)
            return

        self._acciones_activas.append(accion)
        self._texto_estado = accion.desc

        # Los objetivos se comprueban después de cada suceso, también de los
        # inicios, para que los instantes anotados no dependan de qué efectos
        # aplica una acción ``at start``.
        self._evaluar_objetivos()

        if self._al_iniciar_accion is not None:
            self._al_iniciar_accion(accion)

    def _terminar_accion(self, accion: Accion) -> None:
        """Aplica los efectos ``at end`` de ``accion``.

        Si fallan, detiene la simulación con el mensaje de error de la acción.
        """
        error = accion._terminar_ejecucion()

        if error is not None:
            self._poner_error(error, accion)
            return

        self._acciones_activas.remove(accion)

        # Los efectos ``at end`` ya se han aplicado, así que este es el momento de
        # comprobar si un objetivo se acaba de lograr o de romper.
        self._evaluar_objetivos()

        if self._al_terminar_accion is not None:
            self._al_terminar_accion(accion)

    def _evaluar_objetivos(self) -> None:
        """Anota si cada objetivo se cumple en el instante actual.

        Se llama al construir y al reiniciar la simulación y después de cada
        suceso, no solo cuando termina el plan: así se distingue un objetivo que
        nunca se cumplió de uno que se cumplió y que después el plan deshizo.
        """
        for estado_objetivo in self._estados_objetivos:
            estado_objetivo._observar(
                cumplido=estado_objetivo.objetivo._se_cumple(),
                tiempo_simulacion=self._tiempo_simulacion,
            )

    def _poner_error(self, mensaje: str, accion: Accion) -> None:
        """Detiene la simulación con el mensaje de error de ``accion``.

        Las acciones en curso ya no van a terminar, así que se quitan de
        ``_acciones_activas``: así el ``Renderizador`` deja de dibujar a mitad de
        camino un dron cuyo movimiento no terminó.
        """
        self._error = mensaje
        self._accion_fallida = accion
        self._reproduciendo = False
        self._acciones_activas.clear()

    def _reproducir(self) -> None:
        """Deja que ``_actualizar()`` avance la simulación."""
        self._reproduciendo = True

    def _pausar(self) -> None:
        """Impide que ``_actualizar()`` avance la simulación."""
        self._reproduciendo = False

    def _reiniciar(self) -> None:
        """Vuelve al instante 0 y al estado del mundo al construir la simulación.

        También olvida lo que pasó en la ejecución: qué acciones empezaron o
        terminaron, el error, si lo hubo, y cuándo se cumplió cada objetivo.
        """
        # La velocidad no se toca: la elige quien mira la simulación visual, con el
        # deslizador, y solo cambia lo rápido que se ve el plan, no lo que pasa en él.
        self._reproduciendo = False
        self._tiempo_simulacion = 0.0
        self._acciones_activas.clear()
        self._error = None
        self._accion_fallida = None
        self._texto_estado = "Simulación reiniciada"

        for accion in self._acciones:
            accion._reiniciar()

        self._instantanea_inicial._restaurar()

        for estado_objetivo in self._estados_objetivos:
            estado_objetivo._reiniciar()

        # El mundo se ha restaurado, así que los objetivos vuelven a empezar desde
        # su estado inicial, no desde el que quedó al final de la ejecución.
        self._evaluar_objetivos()

    # ------------------------------------------------------------------
    # Veredicto
    # ------------------------------------------------------------------

    def _crear_informe(self) -> InformeVerificacion:
        """Devuelve el informe de la ejecución en su estado actual.

        El informe dice si el plan es ejecutable hasta ahora y si resuelve el
        problema. Los objetivos no se evalúan de nuevo, porque su estado ya
        corresponde al del mundo: se evalúan tras el inicio y el final de cada
        acción, los únicos momentos en que el mundo cambia. Antes de que el plan
        termine, el veredicto es ``"INCOMPLETO"``
        (``InformeVerificacion.INCOMPLETO``), salvo que ya haya fallado una
        acción: solo una ejecución terminada puede decir si el plan es válido.
        """
        return InformeVerificacion(
            ejecutable=not self._tiene_error,
            completado=self._terminada,
            error=self._error,
            accion_fallida=self._accion_fallida,
            # Después de un error el reloj ya no avanza, así que sigue en el
            # instante del suceso que falló. No se deduce de la acción (si había
            # empezado), porque eso cambia al reiniciar, y el informe no.
            fallo_en=self._tiempo_simulacion if self._tiene_error else None,
            # Copias, no los estados de la propia simulación: _reiniciar() y las
            # actualizaciones posteriores los cambian, y un informe tiene que
            # conservar el veredicto con el que se creó.
            estados_objetivos=[copy.copy(estado) for estado in self._estados_objetivos],
            acciones_totales=len(self._acciones),
            acciones_terminadas=sum(accion.terminada for accion in self._acciones),
        )

    # ------------------------------------------------------------------
    # Uso en terminal, sin pygame
    # ------------------------------------------------------------------

    def _simulacion_texto(self, paso_tiempo: float) -> InformeVerificacion:
        """Ejecuta el plan en la terminal, imprimiendo cada inicio y final.

        Si una acción falla, imprime también una línea ``NO INICIA`` o ``NO
        TERMINA`` con ella, en el instante en que falló, antes del error.

        Args:
            paso_tiempo: Los segundos simulados que avanza la simulación en cada
                actualización, mayor que 0. El veredicto no depende de él.

        Returns:
            El ``InformeVerificacion`` de la ejecución. La ejecución siempre llega
            al final del plan o se detiene en la primera acción que falla, así que
            el veredicto nunca es ``"INCOMPLETO"``: ``informe.ejecutable`` dice si
            se aplicaron todas las acciones, e ``informe.es_valido`` si, además,
            se cumplen todos los objetivos al final (un plan sin objetivos es
            ``"EJECUTABLE"``, nunca ``"VÁLIDO"``).

        Solo lo llama ``Mundo.simulacion_texto()``, que antes comprueba
        ``paso_tiempo``. Por eso este método no lo comprueba.
        """
        # Los drones narran mediante logging, no con print(), para que la
        # biblioteca no diga nada cuando la usa otro código. _simulacion_texto()
        # es para la terminal, así que activa esa narración. basicConfig no hace
        # nada si quien llama ya ha configurado logging.
        logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

        # Solo durante esta ejecución: al terminar vuelven a None, para que una
        # simulación visual posterior no imprima nada en la terminal.
        self._al_iniciar_accion = lambda accion: print(
            f"[t={self._tiempo_simulacion:6.2f}s] INICIA  {accion.desc}"
        )
        self._al_terminar_accion = lambda accion: print(
            f"[t={self._tiempo_simulacion:6.2f}s] TERMINA {accion.desc}"
        )

        try:
            print(f"Simulación preparada: {len(self._acciones)} acciones")

            # Cada actualización tiene que avanzar exactamente paso_tiempo, aunque
            # una simulación visual anterior haya dejado otra velocidad.
            self._velocidad = 1.0
            self._reproducir()

            while not self._terminada and not self._tiene_error:
                self._actualizar(paso_tiempo)

            if self._accion_fallida is not None:
                # La acción que falla no se narra como INICIA ni como TERMINA,
                # porque esas líneas solo se imprimen cuando el suceso se aplica.
                # Se narra aquí, en el instante en que falló: si había empezado,
                # lo que no pudo hacer es terminar.
                fase = "NO TERMINA" if self._accion_fallida.iniciada else "NO INICIA"
                print(
                    f"[t={self._tiempo_simulacion:6.2f}s] {fase} "
                    f"{self._accion_fallida.desc}"
                )
                print(f"\nError en la simulación: {self._error}")
            else:
                print(f"\nEjecución terminada en t={self._tiempo_simulacion:.2f}s")

            informe = self._crear_informe()

            print()
            print(informe.resumen())

            return informe
        finally:
            self._al_iniciar_accion = None
            self._al_terminar_accion = None

    # ------------------------------------------------------------------
    # Texto que se muestra
    # ------------------------------------------------------------------

    def _texto_recuento_acciones(self) -> str:
        """Devuelve cuántas acciones están pendientes, en curso y terminadas.

        Si ha fallado una acción, ninguna sigue en curso: las que habían empezado
        y no han terminado quedan interrumpidas, y la que falló se cuenta aparte,
        tanto si falló al empezar como al terminar. Así las cuentas siempre suman
        el total del plan.
        """
        # La acción que falló no cuenta como pendiente ni como empezada.
        otras = [
            accion for accion in self._acciones if accion is not self._accion_fallida
        ]
        pendientes = sum(not accion.iniciada for accion in otras)
        empezadas = sum(accion._en_curso for accion in otras)
        terminadas = sum(accion.terminada for accion in self._acciones)

        if self._accion_fallida is None:
            empezadas_y_fallida = f"En curso: {empezadas}"
        else:
            empezadas_y_fallida = f"Interrumpidas: {empezadas} | Fallida: 1"
        return (
            f"Pendientes: {pendientes} | "
            f"{empezadas_y_fallida} | "
            f"Terminadas: {terminadas}/{len(self._acciones)}"
        )

    def _texto_tiempo(self) -> str:
        """Devuelve el tiempo simulado actual, como texto."""
        return f"Tiempo: {self._tiempo_simulacion:.2f} s"

    # ------------------------------------------------------------------
    # Consultas del estado
    # ------------------------------------------------------------------

    @property
    def _terminada(self) -> bool:
        """Si han terminado todas las acciones del plan."""
        return all(accion.terminada for accion in self._acciones)

    @property
    def _puede_reproducir(self) -> bool:
        """Si pulsar reproducir haría algo.

        El panel de control lo usa para atenuar el botón de reproducir.
        """
        return not self._tiene_error and not self._terminada

    @property
    def _tiene_error(self) -> bool:
        """Si ha fallado una acción."""
        return self._error is not None

    @property
    def _todos_los_transportadores(self) -> list[Transportador]:
        """Los transportadores como lista, vacía cuando el problema no tiene ninguno.

        ``self._transportadores`` se queda en ``None`` en un problema sin
        transportadores porque la validación necesita distinguir "no se
        declararon transportadores" de "se declaró una lista vacía". Esta
        propiedad sirve para recorrer los transportadores sin tener que
        distinguir esos casos.
        """
        return self._transportadores if self._transportadores is not None else []
