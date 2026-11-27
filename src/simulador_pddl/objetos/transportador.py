from __future__ import annotations

from typing import TYPE_CHECKING

from simulador_pddl.objetos.utilidades_objetos import (
    validar_capacidad,
    validar_objeto_localizacion,
)
from simulador_pddl.tipos_basicos import validar_cadena

if TYPE_CHECKING:
    from simulador_pddl.objetos.brazo import Brazo
    from simulador_pddl.objetos.caja import Caja
    from simulador_pddl.objetos.dron import Dron
    from simulador_pddl.objetos.localizacion import Localizacion


class Transportador:
    """Transportador representa un transportador en el dominio de logística con drones.

    Un transportador puede estar suelto en una localización o sujeto por el brazo
    de un dron (``propietario_actual`` es el dron y ``brazo_actual``, el brazo).
    Se mueve con el dron que lo lleva, así que siempre tiene una localización.
    Se compara por identidad, así que las acciones y los objetivos tienen que
    usar este mismo objeto, no otro creado con el mismo nombre.

    Args:
        nombre: El nombre del transportador en el dominio.
        localizacion: La localización donde empieza el transportador.
        capacidad: El número de cajas que caben dentro de este transportador.
    """

    def __init__(self, nombre: str, localizacion: Localizacion, capacidad: int) -> None:
        validar_cadena(nombre, "nombre")
        validar_objeto_localizacion(localizacion)
        validar_capacidad(capacidad)

        self._nombre = nombre
        self._localizacion = localizacion
        self._capacidad = capacidad
        self._cajas_dentro: list[Caja] = []
        # Cajas cuyo PonerCajaEnTransportador ha empezado y no ha terminado: cada
        # una tiene ya un hueco reservado, y el transportador no se puede coger
        # mientras haya alguna.
        self._cajas_entrantes: list[Caja] = []
        # Cajas cuyo SacarCajaDeTransportador ha empezado y no ha terminado: ya
        # no están dentro del transportador, pero siguen ocupando su hueco hasta
        # que termina la descarga, y el transportador no se puede coger mientras
        # haya alguna.
        self._cajas_salientes: list[Caja] = []
        self._propietario_actual: Dron | None = None
        self._brazo_actual: Brazo | None = None

    def __repr__(self) -> str:
        return f"Transportador({self._nombre!r})"

    def __str__(self) -> str:
        cajas_dentro = [caja.nombre for caja in self._cajas_dentro]
        brazo_actual = (
            self._brazo_actual.nombre if self._brazo_actual is not None else None
        )
        return (
            f"Transportador(nombre={self._nombre}, localizacion={self._localizacion}, "
            f"capacidad={self._capacidad}, cajas_dentro={cajas_dentro}, "
            f"propietario_actual={self._nombre_propietario()}, "
            f"brazo_actual={brazo_actual})"
        )

    # ------------------------------------------------------------------
    # Cajas dentro
    # ------------------------------------------------------------------

    def _reservar_hueco(self, caja: Caja) -> None:
        """Guarda un hueco para una caja cuya carga ha empezado.

        Tiene que quedar un hueco libre:
        ``Dron._iniciar_poner_caja_en_transportador()`` lo comprueba antes de
        llamarlo.
        """
        self._cajas_entrantes.append(caja)

    def _anadir_caja(self, caja: Caja) -> None:
        """Mete en el transportador una caja cuyo hueco estaba reservado.

        La caja usa el hueco que obtuvo al empezar su carga (``_reservar_hueco()``),
        así que siempre hay sitio para ella. El hueco tiene que estar reservado:
        la simulación solo termina una carga cuyo inicio tuvo éxito.
        """
        self._cajas_entrantes.remove(caja)
        self._cajas_dentro.append(caja)

    def _quitar_caja(self, caja: Caja) -> None:
        """Saca una caja del transportador, que no puede estar sujeto por un dron.

        La caja tiene que estar dentro y ningún dron puede estar sujetando el
        transportador: ``Dron._iniciar_sacar_caja_de_transportador()``, el único
        que lo llama, comprueba las dos cosas antes.
        """
        self._cajas_dentro.remove(caja)

    def _anadir_caja_saliente(self, caja: Caja) -> None:
        """Anota que una descarga que ha empezado está sacando una caja."""
        self._cajas_salientes.append(caja)

    def _quitar_caja_saliente(self, caja: Caja) -> None:
        """Anota que la descarga de una caja ha terminado.

        La descarga tiene que estar anotada (``_anadir_caja_saliente()``): la
        simulación solo termina una descarga cuyo inicio tuvo éxito.
        """
        self._cajas_salientes.remove(caja)

    # ------------------------------------------------------------------
    # Sujetar el transportador
    # ------------------------------------------------------------------

    def _exigir_no_sujeto(self, intento: str) -> None:
        """Lanza ``ValueError`` si un dron sujeta el transportador.

        Args:
            intento: Lo que no se puede hacer con un transportador sujeto, como
                comienzo del mensaje de error, p. ej.
                ``"el transportador transportador1 no se puede coger"``.
        """
        propietario = self._propietario_actual
        brazo = self._brazo_actual
        # El propietario y el brazo siempre se ponen a la vez (_coger(), _soltar()),
        # así que o los dos son None o ninguno lo es. Se sale si cualquiera lo es
        # para que mypy sepa que ninguno es None al construir el mensaje.
        if propietario is None or brazo is None:
            return

        msg_transportador_sujeto = (
            f"{intento}, lo sujeta el dron {propietario.nombre} "
            f"con el brazo {brazo.nombre}"
        )
        raise ValueError(msg_transportador_sujeto)

    def _exigir_sujeto_con(self, brazo: Brazo, intento: str) -> None:
        """Lanza ``ValueError`` si ``brazo`` no es el brazo que sujeta el transportador.

        Args:
            brazo: El brazo que tiene que estar sujetando el transportador.
            intento: Lo que no se puede hacer con otro brazo, como comienzo del
                mensaje de error, p. ej. ``"el dron dron1 no puede soltar el
                transportador transportador1 con el brazo izquierdo"``.
        """
        if self._brazo_actual is brazo:
            return

        if self._brazo_actual is None:
            quien_lo_sujeta = "ningún brazo lo sujeta"
        else:
            quien_lo_sujeta = f"está sujeto con el brazo {self._brazo_actual.nombre}"
        msg_brazo_transportador = f"{intento}, {quien_lo_sujeta}"
        raise ValueError(msg_brazo_transportador)

    def _exigir_sin_carga_ni_descarga_en_curso(self, intento: str) -> None:
        """Lanza ``ValueError`` si se está metiendo o sacando una caja de él.

        Args:
            intento: Lo que no se puede hacer mientras tanto, como comienzo del
                mensaje de error, p. ej.
                ``"el transportador transportador1 no se puede coger"``.
        """
        # Un transportador no se puede coger mientras se mete una caja en él: la
        # carga terminaría con el transportador en otro sitio.
        if self._cajas_entrantes:
            msg_transportador_cargando = (
                f"{intento}, se está metiendo en él la caja "
                f"{self._cajas_entrantes[0].nombre}"
            )
            raise ValueError(msg_transportador_cargando)
        # Lo mismo mientras se saca una caja de él: el transportador tiene que
        # quedarse en la localización durante toda la descarga.
        if self._cajas_salientes:
            msg_transportador_descargando = (
                f"{intento}, se está sacando de él la caja "
                f"{self._cajas_salientes[0].nombre}"
            )
            raise ValueError(msg_transportador_descargando)

    def _coger(self, dron: Dron, brazo: Brazo) -> None:
        """Reclama el transportador para un dron que lo sujeta con ``brazo``.

        Aquí no se comprueba nada: quien llama comprueba que ningún dron sujeta
        el transportador y que no se está metiendo ni sacando ninguna caja de él.
        """
        self._propietario_actual = dron
        self._brazo_actual = brazo

    def _soltar(self) -> None:
        """Libera el transportador: ya no lo sujeta ningún dron ni ningún brazo.

        Aquí no se comprueba nada: solo puede llamarlo el dron que sujeta el
        transportador.
        """
        self._propietario_actual = None
        self._brazo_actual = None

    def _nombre_propietario(self) -> str | None:
        """Devuelve el nombre del propietario actual, o ``None`` si no lo hay."""
        return (
            self._propietario_actual.nombre
            if self._propietario_actual is not None
            else None
        )

    # ------------------------------------------------------------------
    # Movimiento
    # ------------------------------------------------------------------

    def _mover(self, destino: Localizacion) -> None:
        """Cambia la localización del transportador y de las cajas que lleva dentro.

        Aquí no se comprueba nada. El transportador solo se mueve con el dron
        que lo sujeta, y el dron se mueve antes, así que ya está en ``destino``.
        """
        self._localizacion = destino
        for caja in self._cajas_dentro:
            caja._mover(destino)

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def nombre(self) -> str:
        """El nombre del transportador."""
        return self._nombre

    @property
    def localizacion(self) -> Localizacion:
        """La localización donde está ahora el transportador."""
        return self._localizacion

    @property
    def capacidad(self) -> int:
        """El número de cajas que caben en el transportador."""
        return self._capacidad

    @property
    def cajas_dentro(self) -> list[Caja]:
        """Las cajas dentro del transportador, como copia de la lista interna.

        Una caja que se está sacando ya no está en la lista, aunque sigue ocupando
        su hueco hasta que termina la descarga.
        """
        return list(self._cajas_dentro)

    @property
    def propietario_actual(self) -> Dron | None:
        """El dron que sujeta el transportador, o ``None`` si nadie lo sujeta."""
        return self._propietario_actual

    @property
    def brazo_actual(self) -> Brazo | None:
        """El brazo que sujeta el transportador, o ``None`` si nadie lo sujeta."""
        return self._brazo_actual

    @property
    def _numero_de_cajas_dentro(self) -> int:
        """Cuántas cajas hay dentro del transportador."""
        return len(self._cajas_dentro)

    @property
    def _tiene_hueco_libre(self) -> bool:
        """Si cabe una caja más, contando las que se están metiendo o sacando."""
        return (
            len(self._cajas_dentro)
            + len(self._cajas_entrantes)
            + len(self._cajas_salientes)
            < self._capacidad
        )
