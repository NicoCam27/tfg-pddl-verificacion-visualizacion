"""regression: La batería de pruebas de regresión de ``simulador_pddl``.

Se ejecuta desde la raíz del repositorio después de cada cambio en la
biblioteca, para comprobar que todo sigue funcionando como se espera:

    python -m unittest discover -s tests/regression -p "test_*.py"

Las pruebas cubren:

    - la construcción de objetos, acciones y objetivos, y los errores que se
      lanzan con argumentos incorrectos;
    - cada acción de principio a fin y la semántica ``at start`` / ``at end``,
      con las reglas sobre acciones que se solapan en el tiempo;
    - los planes clásicos y que el veredicto no dependa de ``paso_tiempo``;
    - los veredictos de ``InformeVerificacion`` y el seguimiento de los
      objetivos;
    - ``str()`` y ``repr()`` de los objetos, las acciones, los objetivos y los
      informes, y la descripción automática de las acciones;
    - la simulación visual con pygame, sin pantalla;
    - los planes de planificadores reales, cuando existe el directorio privado
      ``tests/tests_private/real_tests/``.
"""
