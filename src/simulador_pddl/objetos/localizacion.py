from simulador_pddl.tipos_basicos import validar_cadena


class Localizacion:
    """Localizacion representa una localización en el dominio de logística con drones.

    Una localización solo tiene un nombre, y dos localizaciones con el mismo
    nombre son la misma localización.

    Args:
        nombre: El nombre de la localización en el dominio.
    """

    def __init__(self, nombre: str) -> None:
        validar_cadena(nombre, "nombre")

        self._nombre = nombre

    def __repr__(self) -> str:
        return f"Localizacion({self._nombre!r})"

    def __str__(self) -> str:
        """Devuelve solo el nombre, no la forma ``Clase(...)`` del resto de objetos.

        Una localización se identifica por su nombre, así que se lee con
        naturalidad en los mensajes.
        """
        return self._nombre

    def __eq__(self, otro: object) -> bool:
        """Devuelve si ``otro`` es una localización con el mismo nombre."""
        return isinstance(otro, Localizacion) and self._nombre == otro._nombre

    def __hash__(self) -> int:
        return hash(self._nombre)

    @property
    def nombre(self) -> str:
        """El nombre de la localización.

        Es de solo lectura porque ``__hash__()`` depende de él: renombrar una
        localización que está en un conjunto, o que es clave de un diccionario,
        haría imposible encontrarla.
        """
        return self._nombre
