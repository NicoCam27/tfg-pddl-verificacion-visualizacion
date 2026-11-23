from simulador_pddl.objetos.utilidades_objetos import validar_nombre


class Contenido:
    """Contenido representa un contenido en el dominio de logística con drones.

    Un contenido es lo que lleva una caja y lo que necesita una persona, p. ej.
    comida o medicina. Solo tiene un nombre, y dos contenidos con el mismo
    nombre son el mismo contenido.

    Args:
        nombre: El nombre del contenido en el dominio.
    """

    def __init__(self, nombre: str) -> None:
        validar_nombre(nombre)

        self._nombre = nombre

    def __repr__(self) -> str:
        return f"Contenido({self._nombre!r})"

    def __str__(self) -> str:
        """Devuelve solo el nombre, no la forma ``Clase(...)`` del resto de objetos.

        Un contenido se identifica por su nombre, así que se lee con
        naturalidad en los mensajes.
        """
        return self._nombre

    def __eq__(self, otro: object) -> bool:
        """Devuelve si ``otro`` es un contenido con el mismo nombre."""
        return isinstance(otro, Contenido) and self._nombre == otro._nombre

    def __hash__(self) -> int:
        return hash(self._nombre)

    @property
    def nombre(self) -> str:
        """El nombre del contenido.

        Es de solo lectura porque ``__hash__()`` depende de él: renombrar un
        contenido que está en un conjunto, o que es clave de un diccionario,
        haría imposible encontrarlo.
        """
        return self._nombre
