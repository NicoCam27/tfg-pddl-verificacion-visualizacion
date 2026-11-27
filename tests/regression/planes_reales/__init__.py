"""Planes reales de planificadores, para problemas escritos para estas pruebas.

Hay dos problemas propios: uno clásico, con un dron de dos brazos que entrega dos
cajas, y uno temporal, con acciones durativas y dos drones que trabajan a la vez.
Sus ficheros PDDL no están en el repositorio. Cada script traduce a la biblioteca
el plan que devolvió un planificador para uno de ellos, cita ese plan tal cual en su
docstring y define ``mundo``, listo para ejecutarse. Los objetos del script son
los del problema. ``test_planes_planificadores_reales.py`` los ejecuta todos y
espera ``"VÁLIDO"``.
"""
