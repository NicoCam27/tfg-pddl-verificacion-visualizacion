from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from simulador_pddl.objetos.caja import Caja
from simulador_pddl.objetos.persona import Persona
from simulador_pddl.objetos.transportador import Transportador
from simulador_pddl.objetos.utilidades_objetos import (
    con_articulo,
    con_preposicion_a,
    describir_cantidad,
    describir_necesidades,
    validar_lista_brazos,
    validar_nombre,
    validar_objeto_localizacion,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from simulador_pddl.objetos.brazo import Brazo
    from simulador_pddl.objetos.localizacion import Localizacion

registrador = logging.getLogger(__name__)

# Los objetos que están en una localización.
type _Localizable = Caja | Transportador | Dron | Persona


def _exigir_misma_localizacion(primero: _Localizable, segundo: _Localizable) -> None:
    """Lanza ``ValueError`` si los dos objetos no están en la misma localización."""
    if primero.localizacion != segundo.localizacion:
        msg_localizacion = (
            f"{con_articulo(primero)} está en la localización {primero.localizacion} "
            f"pero {con_articulo(segundo)} está en la localización "
            f"{segundo.localizacion}"
        )
        raise ValueError(msg_localizacion)


class Dron:
    """Dron representa un dron en el dominio de logística con drones.

    Un dron se mueve entre localizaciones y, con sus brazos, coge y suelta cajas
    y transportadores, mete cajas en un transportador y las saca, y entrega cajas
    a personas. Al moverse se lleva todo lo que sujetan sus brazos.

    Args:
        nombre: El nombre del dron en el dominio.
        localizacion: La localización donde empieza el dron.
        brazos: Los brazos del dron, como una lista o una tupla, sin repetir
            ninguno. Cada brazo tiene que pertenecer solo a este dron. Puede estar
            vacía: un dron sin brazos solo puede moverse.
    """

    def __init__(
        self, nombre: str, localizacion: Localizacion, brazos: Sequence[Brazo]
    ) -> None:
        validar_nombre(nombre)
        validar_objeto_localizacion(localizacion)
        validar_lista_brazos(brazos)

        # El dron guarda su propia lista, para que los cambios posteriores en la
        # lista de quien llama no le afecten.
        self._brazos = list(brazos)
        self._nombre = nombre
        self._localizacion = localizacion

    def __repr__(self) -> str:
        return f"Dron({self._nombre!r})"

    def __str__(self) -> str:
        brazos_info = ""
        for brazo in self._brazos:
            brazos_info += f"  - {brazo}\n"
        return (
            f"Dron(nombre={self._nombre}, localizacion={self._localizacion}, "
            f"brazos=\n{brazos_info})"
        )

    # ------------------------------------------------------------------
    # Movimiento
    # ------------------------------------------------------------------

    def _mover(self, destino: Localizacion) -> None:
        """Cambia la localización del dron y de todo lo que lleva.

        Las cajas que sujetan sus brazos y los transportadores que lleva se
        mueven con él. Lo llama el ``_terminar_ejecucion()`` de ``Mover`` y de
        ``MoverTransportador``, porque el movimiento es un efecto ``at end``.

        No comprueba nada, porque el movimiento ya es válido cuando se llama:
        ``Mover`` y ``MoverTransportador`` rechazan un origen igual al destino al
        construirse y comprueban que el dron está en el origen cuando empiezan
        (``_exigir_en()``), y ``Simulacion`` rechaza al construirse cualquier otra
        acción del dron que se solape con el movimiento. Así, todo lo que se
        comprobó al construir y en ``_iniciar_ejecucion()`` sigue siendo cierto
        cuando ``_terminar_ejecucion()`` llama a este método.
        """
        origen = self._localizacion

        numero_de_cajas_sujetas = 0
        numero_de_transportadores_sujetos = 0

        self._localizacion = destino

        for brazo in self._brazos:
            if brazo.contenido is not None:
                brazo.contenido._mover(destino)
                numero_de_cajas_sujetas += 1

            if brazo.reservado_por is not None:
                # El transportador mueve las cajas que lleva dentro, el mensaje
                # solo cuenta lo que llevan los brazos.
                brazo.reservado_por._mover(destino)
                numero_de_transportadores_sujetos += 1

        registrador.info(
            "El dron %s se ha movido de %s a %s%s",
            self._nombre,
            origen,
            self._localizacion,
            self._describir_sujetos(
                numero_de_cajas_sujetas, numero_de_transportadores_sujetos
            ),
        )

    @staticmethod
    def _describir_sujetos(
        numero_de_cajas_sujetas: int, numero_de_transportadores_sujetos: int
    ) -> str:
        """Devuelve el final del mensaje de movimiento que dice qué lleva el dron.

        Args:
            numero_de_cajas_sujetas: Número de cajas que sujetan los brazos del dron.
            numero_de_transportadores_sujetos: Número de transportadores que lleva
                el dron.

        Returns:
            Un texto como ``" con 2 cajas y 1 transportador"``, que empieza por un
            espacio, o una cadena vacía si el dron no lleva nada.
        """
        partes = []
        if numero_de_cajas_sujetas:
            partes.append(describir_cantidad(numero_de_cajas_sujetas, Caja))
        if numero_de_transportadores_sujetos:
            partes.append(
                describir_cantidad(numero_de_transportadores_sujetos, Transportador)
            )

        if not partes:
            return ""
        return f" con {' y '.join(partes)}"

    def _exigir_en(self, localizacion: Localizacion) -> None:
        """Lanza ``ValueError`` si el dron no está en ``localizacion``.

        Lo llama el ``_iniciar_ejecucion()`` de ``Mover`` y de
        ``MoverTransportador``, porque el origen es una condición ``at start``.
        """
        if self._localizacion != localizacion:
            msg_localizacion_dron = (
                f"el dron {self._nombre} no está en la localización {localizacion}, "
                f"está en la localización {self._localizacion}"
            )
            raise ValueError(msg_localizacion_dron)

    # ------------------------------------------------------------------
    # Transportadores: coger y soltar
    # ------------------------------------------------------------------

    def _exigir_propietario_transportador(
        self, transportador: Transportador, intento: str
    ) -> None:
        """Lanza ``ValueError`` si este dron no es el que sujeta el transportador.

        Args:
            transportador: El transportador que tiene que sujetar el dron.
            intento: Lo que el dron no puede hacer con un transportador que no
                sujeta, para el mensaje de error, p. ej. ``"soltar"``.
        """
        propietario = transportador.propietario_actual
        if propietario is not self:
            quien_lo_sujeta = (
                "ningún dron lo sujeta"
                if propietario is None
                else f"lo sujeta el dron {propietario.nombre}"
            )
            msg_propietario_transportador = (
                f"el dron {self._nombre} no puede {intento} el transportador "
                f"{transportador.nombre}, {quien_lo_sujeta}"
            )
            raise ValueError(msg_propietario_transportador)

    def _iniciar_coger_transportador(
        self, transportador: Transportador, brazo: Brazo
    ) -> None:
        """Reclama el transportador para este dron, para que ningún otro lo coja.

        El brazo tiene que estar libre, ningún dron puede sujetar ya el
        transportador, no se puede estar metiendo ni sacando ninguna caja de él,
        y tiene que estar en la localización del dron. Todavía no reserva el
        brazo: eso se hace al final, en ``_terminar_coger_transportador()``.
        """
        brazo._exigir_libre()

        intento = f"el transportador {transportador.nombre} no se puede coger"
        transportador._exigir_no_sujeto(intento)
        transportador._exigir_sin_carga_ni_descarga_en_curso(intento)

        _exigir_misma_localizacion(self, transportador)

        transportador._coger(self, brazo)

        registrador.info(
            "El dron %s ha empezado a coger el transportador %s con el brazo %s",
            self._nombre,
            transportador.nombre,
            brazo.nombre,
        )

    def _terminar_coger_transportador(
        self, transportador: Transportador, brazo: Brazo
    ) -> None:
        """Reserva el brazo para el transportador: ahora el dron lo lleva.

        No comprueba que el dron sujeta el transportador, porque sigue siendo
        así desde ``_iniciar_coger_transportador()``: este dron solo podría
        soltarlo con este mismo brazo, que está ocupado por la acción, y otro
        dron no puede soltar un transportador que no sujeta. Tampoco comprueba
        que el brazo sigue libre: ``Simulacion`` no deja que otra acción del dron
        use el mismo brazo mientras tanto.
        """
        brazo._poner_reservado_por(transportador)

        registrador.info(
            "El dron %s ha cogido el transportador %s con el brazo %s",
            self._nombre,
            transportador.nombre,
            brazo.nombre,
        )

    def _iniciar_soltar_transportador(
        self, transportador: Transportador, brazo: Brazo
    ) -> None:
        """Comprueba que el dron puede soltar el transportador que sujeta con el brazo.

        Todavía no cambia nada: el dron lo sigue sujetando hasta el final.
        """
        # Solo el dron que sujeta el transportador puede soltarlo.
        self._exigir_propietario_transportador(transportador, "soltar")

        # Solo el brazo que sujeta el transportador puede soltarlo.
        transportador._exigir_sujeto_con(
            brazo,
            f"el dron {self._nombre} no puede soltar el transportador "
            f"{transportador.nombre} con el brazo {brazo.nombre}",
        )

        brazo._exigir_sin_caja()

        registrador.info(
            "El dron %s ha empezado a soltar el transportador %s, "
            "que sujeta con el brazo %s",
            self._nombre,
            transportador.nombre,
            brazo.nombre,
        )

    def _terminar_soltar_transportador(
        self, transportador: Transportador, brazo: Brazo
    ) -> None:
        """Suelta el transportador: ni el dron ni su brazo lo sujetan ya.

        Desde este momento cualquier dron puede cogerlo, y se pueden meter o
        sacar cajas de él. No comprueba nada, porque lo que comprobó
        ``_iniciar_soltar_transportador()`` sigue siendo cierto: el
        transportador solo se suelta aquí, este dron solo podría soltarlo con
        este mismo brazo, que está ocupado por la acción, y otro dron no puede
        soltar un transportador que no sujeta.
        """
        brazo._quitar_reservado_por()
        transportador._soltar()

        registrador.info(
            "El dron %s ha soltado el transportador %s, que sujetaba con el brazo %s",
            self._nombre,
            transportador.nombre,
            brazo.nombre,
        )

    # ------------------------------------------------------------------
    # Cajas: coger, entregar y soltar
    # ------------------------------------------------------------------

    def _iniciar_coger_caja(self, brazo: Brazo, caja: Caja) -> None:
        """Reclama la caja para este dron, para que nadie más la pueda coger.

        La caja tiene que estar disponible y en la localización del dron, y el
        brazo tiene que estar libre. Todavía no pone la caja en el brazo: eso se
        hace al final, en ``_terminar_coger_caja()``.
        """
        _exigir_misma_localizacion(self, caja)

        brazo._exigir_libre()

        # Si la caja ya es de este dron, el mensaje de _asignar_a() ("pertenece
        # al dron dron1") parecería decir que no puede coger su propia caja.
        if caja.propietario_actual is self:
            brazo_que_la_sujeta = next(
                (otro for otro in self._brazos if otro.contenido is caja), None
            )
            que_hace_con_ella = (
                f"ya la sujeta con el brazo {brazo_que_la_sujeta.nombre}"
                if brazo_que_la_sujeta is not None
                else "ya la está cogiendo o sacando de un transportador con otro brazo"
            )
            msg_caja_ya_del_dron = (
                f"el dron {self._nombre} no puede coger la caja {caja.nombre}, "
                f"{que_hace_con_ella}"
            )
            raise ValueError(msg_caja_ya_del_dron)

        # El dron reclama la caja si está disponible, en el caso contrario fallo.
        caja._asignar_a(self)

        registrador.info(
            "El dron %s ha empezado a coger la caja %s con el brazo %s",
            self._nombre,
            caja.nombre,
            brazo.nombre,
        )

    def _terminar_coger_caja(self, brazo: Brazo, caja: Caja) -> None:
        """Pone la caja en el brazo: ya la ha cogido.

        No comprueba que la caja sigue siendo del dron, porque nada puede
        cambiarlo desde ``_iniciar_coger_caja()``: ya no está disponible, así que
        nadie más puede cogerla, y para soltarla, entregarla o meterla en un
        transportador un brazo tiene que sujetarla. Tampoco comprueba que el
        brazo sigue vacío: ``Simulacion`` no deja que otra acción del dron use el
        mismo brazo mientras tanto.
        """
        brazo._poner_contenido(caja)

        registrador.info(
            "La caja %s está ahora en el brazo %s del dron %s",
            caja.nombre,
            brazo.nombre,
            self._nombre,
        )

    def _exigir_propietario_caja(self, caja: Caja) -> None:
        """Lanza ``ValueError`` si este dron no es el propietario de la caja."""
        if caja.propietario_actual is not self:
            msg_propietario_caja = (
                f"la caja {caja.nombre} no pertenece al dron {self._nombre}, "
                f"pertenece {con_preposicion_a(caja._describir_propietario())}"
            )
            raise ValueError(msg_propietario_caja)

    def _exigir_necesidad_persona(self, persona: Persona, caja: Caja) -> None:
        """Lanza ``ValueError`` si la persona no necesita el contenido de la caja."""
        if caja.contenido not in persona.necesidades:
            msg_necesidad_persona = (
                f"la caja {caja.nombre} no se puede entregar a la persona "
                f"{persona.nombre}: tiene '{caja.contenido}', y la persona "
                f"{describir_necesidades(persona.necesidades)}"
            )
            raise ValueError(msg_necesidad_persona)

    def _iniciar_entregar_caja(
        self, brazo: Brazo, caja: Caja, persona: Persona
    ) -> None:
        """Comprueba que la caja se puede entregar a la persona.

        El dron y la persona tienen que estar en la misma localización, la
        persona tiene que necesitar el contenido de la caja, y el brazo tiene que
        sujetar la caja. Todavía no cambia nada: la caja sigue en el brazo, y se
        entrega a la persona al final.
        """
        _exigir_misma_localizacion(self, persona)

        self._exigir_necesidad_persona(persona, caja)

        brazo._exigir_sujetando(caja)

        self._exigir_propietario_caja(caja)

        registrador.info(
            "El dron %s ha empezado a entregar la caja %s del brazo %s a la persona %s",
            self._nombre,
            caja.nombre,
            brazo.nombre,
            persona.nombre,
        )

    def _terminar_entregar_caja(
        self, brazo: Brazo, caja: Caja, persona: Persona
    ) -> None:
        """Entrega la caja a la persona y libera el brazo.

        Si la persona dejó de necesitar el contenido entre el inicio y el final
        (terminó antes otra entrega del mismo contenido), se informa como un
        error, y la caja se queda en el brazo. Lo demás que comprobó
        ``_iniciar_entregar_caja()`` sigue siendo cierto: la caja no puede salir
        del brazo, que está ocupado por la acción, y el dron no se puede mover
        mientras tanto.
        """
        # Se comprueba otra vez antes de cambiar nada, para que una entrega que
        # no puede terminar deje la caja en el brazo, no medio entregada.
        self._exigir_necesidad_persona(persona, caja)

        caja._liberar_de(self)
        persona._anadir_caja_poseida(caja)
        brazo._quitar_contenido()

        registrador.info(
            "La caja %s ha salido del brazo %s del dron %s "
            "y se ha entregado a la persona %s",
            caja.nombre,
            brazo.nombre,
            self._nombre,
            persona.nombre,
        )

    def _iniciar_soltar(self, brazo: Brazo, caja: Caja) -> None:
        """Comprueba que el dron puede soltar la caja que sujeta con el brazo.

        Todavía no cambia nada: la caja sigue en el brazo hasta el final.
        """
        brazo._exigir_sujetando(caja)

        self._exigir_propietario_caja(caja)

        registrador.info(
            "El dron %s ha empezado a soltar la caja %s del brazo %s",
            self._nombre,
            caja.nombre,
            brazo.nombre,
        )

    def _terminar_soltar(self, brazo: Brazo, caja: Caja) -> None:
        """Suelta la caja, sin entregarla a una persona.

        El brazo queda vacío y la caja se queda en la localización del dron,
        disponible otra vez para que cualquier dron la coja. No comprueba nada,
        porque lo que comprobó ``_iniciar_soltar()`` sigue siendo cierto: la caja
        no puede salir del brazo, que está ocupado por la acción.
        """
        caja._liberar_de(self)
        brazo._quitar_contenido()

        registrador.info(
            "La caja %s se ha soltado del brazo %s del dron %s en la localización %s",
            caja.nombre,
            brazo.nombre,
            self._nombre,
            self._localizacion,
        )

    # ------------------------------------------------------------------
    # Cajas en un transportador: poner y sacar
    # ------------------------------------------------------------------

    def _iniciar_poner_caja_en_transportador(
        self, brazo: Brazo, caja: Caja, transportador: Transportador
    ) -> None:
        """Reserva un hueco del transportador para la caja que sujeta el brazo.

        El dron y el transportador tienen que estar en la misma localización,
        ningún dron puede estar sujetando el transportador, el brazo tiene que
        sujetar la caja, y el transportador tiene que tener un hueco libre. La
        caja sigue en el brazo hasta el final. Desde este momento el hueco está
        reservado y el transportador no se puede coger.
        """
        _exigir_misma_localizacion(self, transportador)

        transportador._exigir_no_sujeto(
            f"la caja {caja.nombre} no se puede meter en el transportador "
            f"{transportador.nombre}"
        )

        brazo._exigir_sujetando(caja)

        if not transportador._tiene_hueco_libre:
            msg_capacidad_maxima_transportador = (
                f"el transportador {transportador.nombre} ha llegado a su capacidad "
                f"máxima de {transportador.capacidad}, contando las cajas que se están "
                "metiendo en él"
            )
            raise ValueError(msg_capacidad_maxima_transportador)

        self._exigir_propietario_caja(caja)

        transportador._reservar_hueco(caja)

        registrador.info(
            "El dron %s ha empezado a meter la caja %s del brazo %s "
            "en el transportador %s",
            self._nombre,
            caja.nombre,
            brazo.nombre,
            transportador.nombre,
        )

    def _terminar_poner_caja_en_transportador(
        self, brazo: Brazo, caja: Caja, transportador: Transportador
    ) -> None:
        """Pasa la caja del brazo al transportador.

        No comprueba nada, porque lo que comprobó
        ``_iniciar_poner_caja_en_transportador()`` sigue siendo cierto. El hueco
        se reservó al inicio, y desde entonces el transportador no se ha podido
        coger, así que sigue en la localización del dron y tiene sitio para la
        caja. La caja sigue en el brazo, que está ocupado por la acción, y el dron
        no se puede mover mientras tanto.
        """
        transportador._anadir_caja(caja)
        caja._liberar_de(self)
        brazo._quitar_contenido()
        caja._asignar_a(transportador)

        registrador.info(
            "La caja %s se ha metido en el transportador %s, que ahora tiene dentro %s",
            caja.nombre,
            transportador.nombre,
            describir_cantidad(transportador._numero_de_cajas_dentro, Caja),
        )

    def _iniciar_sacar_caja_de_transportador(
        self, brazo: Brazo, caja: Caja, transportador: Transportador
    ) -> None:
        """Saca la caja del transportador: este dron es su propietario desde el inicio.

        El dron y el transportador tienen que estar en la misma localización, la
        caja tiene que estar dentro del transportador y no se puede estar sacando
        ya (otro dron, o el otro brazo de este), ningún dron puede estar
        sujetando el transportador, y el brazo tiene que estar libre. El
        transportador no se puede coger hasta que termine la descarga.
        """
        _exigir_misma_localizacion(self, transportador)

        # Una carga no mete la caja en cajas_dentro hasta que termina, y una
        # descarga la quita en cuanto empieza. Así que si hay una carga o otra
        # descarga de esta caja en curso, la comprobación de abajo solo diría
        # "no está en el transportador". Estas comprobaciones indican por qué.
        # El dron de esa otra acción es el propietario de la caja, así que el mensaje
        # puede nombrarlo.
        if caja in transportador._cajas_entrantes:
            msg_caja_entrando_transportador = (
                f"la caja {caja.nombre} no se puede sacar del transportador "
                f"{transportador.nombre}, {caja._describir_propietario()} todavía "
                "la está metiendo"
            )
            raise ValueError(msg_caja_entrando_transportador)

        if caja in transportador._cajas_salientes:
            msg_caja_ya_saliendo_transportador = (
                f"la caja {caja.nombre} no se puede sacar del transportador "
                f"{transportador.nombre}, {caja._describir_propietario()} ya la está "
                "sacando"
            )
            raise ValueError(msg_caja_ya_saliendo_transportador)

        if caja not in transportador.cajas_dentro:
            msg_caja_no_en_transportador = (
                f"la caja {caja.nombre} no está en el transportador "
                f"{transportador.nombre}"
            )
            raise ValueError(msg_caja_no_en_transportador)

        transportador._exigir_no_sujeto(
            f"la caja {caja.nombre} no se puede sacar del transportador "
            f"{transportador.nombre}"
        )

        brazo._exigir_libre()

        caja._liberar_de(transportador)
        caja._asignar_a(self)
        transportador._quitar_caja(caja)
        transportador._anadir_caja_saliente(caja)

        registrador.info(
            "El dron %s ha empezado a sacar la caja %s del transportador %s "
            "con el brazo %s",
            self._nombre,
            caja.nombre,
            transportador.nombre,
            brazo.nombre,
        )

    def _terminar_sacar_caja_de_transportador(
        self, brazo: Brazo, caja: Caja, transportador: Transportador
    ) -> None:
        """Pone la caja en el brazo: la descarga ha terminado.

        Desde ahora esta descarga ya no impide coger el transportador. No
        comprueba que la caja sigue siendo del dron, por lo mismo que
        ``_terminar_coger_caja()``: nadie puede cogerla ni sacarla otra vez, y
        ningún brazo la sujeta. Tampoco comprueba que el brazo sigue libre:
        ``Simulacion`` no deja que otra acción del dron use el mismo brazo
        mientras tanto.
        """
        brazo._poner_contenido(caja)
        transportador._quitar_caja_saliente(caja)

        registrador.info(
            "La caja %s está ahora en el brazo %s del dron %s, "
            "y el transportador %s tiene dentro %s",
            caja.nombre,
            brazo.nombre,
            self._nombre,
            transportador.nombre,
            describir_cantidad(transportador._numero_de_cajas_dentro, Caja),
        )

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def nombre(self) -> str:
        """El nombre del dron."""
        return self._nombre

    @property
    def localizacion(self) -> Localizacion:
        """La localización donde está ahora el dron."""
        return self._localizacion

    @property
    def brazos(self) -> list[Brazo]:
        """Los brazos del dron, como copia de la lista interna."""
        return list(self._brazos)
