# TFG: Software para la verificación y visualización de resultados de Planificación Automática en dominios de logística de drones utilizando PDDL y Python

## Autor

Iubal Nicolás Camjalli Spiegel

## Requisitos

- Python 3.12.x
- Pygame 2.6 o superior

## Instalación

La biblioteca se puede instalar de dos formas distintas:

### Opción 1: Instalación directa desde GitHub

```bash
pip install git+https://github.com/NicoCam27/tfg-pddl-verificacion-visualizacion.git
```

### Opción 2: Instalación desde una copia local del repositorio

Clona el repositorio:

```bash
git clone https://github.com/NicoCam27/tfg-pddl-verificacion-visualizacion.git
cd tfg-pddl-verificacion-visualizacion
```

Instala la biblioteca:

```bash
pip install .
```

## Uso

Una vez instalada, la biblioteca se importa con:

```python
from simulador_pddl import *
```

Un problema se describe con tres cosas: los **objetos** del dominio, un **plan** (una lista de acciones, cada una con su instante de inicio y su duración, o, en un plan clásico, con el número de paso correspondiente y 1) y los **objetivos** que el plan debe cumplir. `Mundo` comprueba el plan, lo simula y devuelve un veredicto.

Ejemplo básico:

```python
from simulador_pddl import *

# Objetos del dominio
deposito = Localizacion("deposito")
localizacion1 = Localizacion("localizacion1")
localizacion2 = Localizacion("localizacion2")

izq = Brazo("izq")
der = Brazo("der")

dron1 = Dron("dron1", deposito, [izq, der])

comida = Contenido("comida")
medicina = Contenido("medicina")

caja1 = Caja("caja1", deposito, comida)
caja2 = Caja("caja2", deposito, medicina)

persona1 = Persona("persona1", localizacion1, comida)
persona2 = Persona("persona2", localizacion2, medicina)

# Plan: cada acción indica cuándo empieza (inicio_sim) y cuánto dura (duracion_sim)
acciones = [
    CogerCaja(dron1, izq, caja1, inicio_sim=0, duracion_sim=1),
    CogerCaja(dron1, der, caja2, inicio_sim=1, duracion_sim=1),
    Mover(dron1, deposito, localizacion1, inicio_sim=2, duracion_sim=1),
    EntregarCaja(dron1, izq, caja1, persona1, inicio_sim=3, duracion_sim=1),
    Mover(dron1, localizacion1, localizacion2, inicio_sim=4, duracion_sim=1),
    EntregarCaja(dron1, der, caja2, persona2, inicio_sim=5, duracion_sim=1),
    Mover(dron1, localizacion2, deposito, inicio_sim=6, duracion_sim=1),
]

# Objetos del problema: una lista por tipo
localizaciones = [deposito, localizacion1, localizacion2]
drones = [dron1]
cajas = [caja1, caja2]
personas = [persona1, persona2]
contenidos = [comida, medicina]

# Objetivos: lo que debe cumplirse cuando el plan termina
objetivos = [
    PersonaTieneContenido(persona1, comida),
    PersonaTieneContenido(persona2, medicina),
    DronEnLocalizacion(dron1, deposito),
]

nuevo_mundo = Mundo(
    acciones,
    localizaciones=localizaciones,
    drones=drones,
    cajas=cajas,
    personas=personas,
    contenidos=contenidos,
    objetivos=objetivos,
)

# Simula el plan en la terminal y devuelve el informe con el veredicto
informe = nuevo_mundo.simulacion_texto()
```

Al terminar, `simulacion_texto()` muestra el informe con el veredicto:

```text
Veredicto: VÁLIDO
Ejecución: 7/7 acciones terminadas sin errores
Objetivos: 3 de 3 cumplidos
  [OK] la persona persona1 posee una caja con el contenido 'comida'  (cumplido desde t=4.00s)
  [OK] la persona persona2 posee una caja con el contenido 'medicina'  (cumplido desde t=6.00s)
  [OK] el dron dron1 está en la localización deposito  (cumplido desde t=7.00s)
```

Este ejemplo y otros dos están en el directorio `tests/` (`ejemplo_basico.py`, `ejemplo_transportador.py` y `ejemplo_dos_drones_paralelos.py`).

### Objetos

| Clase | Constructor | Significado |
|---|---|---|
| `Localizacion` | `Localizacion(nombre)` | Un lugar. Dos localizaciones con el mismo nombre son la misma. |
| `Brazo` | `Brazo(nombre)` | Un brazo de un dron. Sujeta como máximo una caja, o queda reservado por el transportador que lleva. |
| `Dron` | `Dron(nombre, localizacion, brazos)` | Un dron, con su localización y su lista de brazos. |
| `Caja` | `Caja(nombre, localizacion, contenido)` | Una caja, con su contenido. |
| `Contenido` | `Contenido(nombre)` | Lo que lleva una caja y lo que necesita una persona (por ejemplo `Contenido("comida")`). Dos contenidos con el mismo nombre son el mismo. |
| `Persona` | `Persona(nombre, localizacion, necesidades)` | Una persona, con lo que necesita: un contenido o una lista de contenidos distintos. |
| `Transportador` | `Transportador(nombre, localizacion, capacidad)` | Un transportador en el que caben `capacidad` cajas. Es opcional. |

### Acciones

Cada acción tiene un instante de inicio y una duración, y sus efectos se aplican en dos fases, como en las *durative actions* de PDDL: al empezar (*at start*) y al terminar (*at end*). Después de sus objetos, cada acción recibe `inicio_sim` (instante de inicio) y `duracion_sim` (duración, 1 por defecto). Opcionalmente admite `desc`, una descripción que se muestra al simular y que, si no se indica, se genera automáticamente.

| Acción | Argumentos | Qué hace |
|---|---|---|
| `Mover` | `dron, origen, destino` | El dron va de una localización a otra, con lo que lleve en sus brazos. |
| `CogerCaja` | `dron, brazo, caja` | El dron coge una caja de su localización con un brazo. |
| `EntregarCaja` | `dron, brazo, caja, persona` | El dron entrega la caja a una persona que necesita su contenido. |
| `Soltar` | `dron, brazo, caja` | El dron deja la caja en su localización, sin entregarla. |
| `PonerCajaEnTransportador` | `dron, brazo, caja, transportador` | El dron mete en el transportador la caja que sujeta. |
| `SacarCajaDeTransportador` | `dron, brazo, caja, transportador` | El dron saca una caja del transportador. |
| `CogerTransportador` | `dron, transportador, brazo` | El dron coge el transportador con un brazo, para llevarlo. |
| `SoltarTransportador` | `dron, transportador, brazo` | El dron suelta el transportador que lleva. |
| `MoverTransportador` | `dron, transportador, brazo, origen, destino` | El dron coge el transportador, lo lleva a otra localización y lo suelta. |

Mientras un dron hace un `Mover` o un `MoverTransportador`, no puede hacer ninguna otra acción. El resto de acciones ocupan únicamente su brazo, así que un dron con dos brazos puede, por ejemplo, coger dos cajas al mismo tiempo. Un plan que incumple estas reglas es `NO EJECUTABLE`.

**Planes clásicos.** Un planificador clásico (LAMA, Metric-FF...) devuelve una secuencia de pasos sin tiempos. Se escribe numerando sus pasos desde 0: la acción del paso `i` tiene `inicio_sim=i` y `duracion_sim=1`, el valor por defecto, así que basta con indicar el inicio (por ejemplo, `CogerCaja(dron, brazo, caja, 0)`). Como sus acciones no se solapan, aplicar los efectos en dos fases produce el mismo estado que aplicarlos a la vez, y el veredicto es el mismo que daría el plan clásico.

### Objetivos

| Objetivo | Se cumple cuando |
|---|---|
| `PersonaTieneContenido(persona, contenido)` | La persona posee al menos una caja con ese contenido. |
| `DronEnLocalizacion(dron, localizacion)` | El dron está en esa localización. |
| `TransportadorEnLocalizacion(transportador, localizacion)` | El transportador está en esa localización. |

### Problemas con transportadores

Si el problema tiene transportadores, se pasan en el argumento `transportadores`:

```python
"""Ejemplo básico con un transportador: un dron entrega dos cajas.

El dron mete las dos cajas en un transportador en el depósito, lleva el
transportador hasta cada persona, saca su caja y se la entrega, y vuelve al
depósito. Muestra la simulación en una ventana de pygame e imprime su veredicto al
cerrarla.
"""

from simulador_pddl import *

deposito = Localizacion("deposito")
localizacion1 = Localizacion("localizacion1")
localizacion2 = Localizacion("localizacion2")

localizaciones = [deposito, localizacion1, localizacion2]

izq = Brazo("izq")
der = Brazo("der")

dron1 = Dron("dron1", deposito, [izq, der])

comida = Contenido("comida")
medicina = Contenido("medicina")

caja1 = Caja("caja1", deposito, comida)
caja2 = Caja("caja2", deposito, medicina)

transportador1 = Transportador("transportador1", deposito, 2)

persona1 = Persona("persona1", localizacion1, comida)
persona2 = Persona("persona2", localizacion2, medicina)

acciones = [
    CogerCaja(dron1, izq, caja1, 0, 1),
    PonerCajaEnTransportador(dron1, izq, caja1, transportador1, 1, 1),
    CogerCaja(dron1, der, caja2, 2, 1),
    PonerCajaEnTransportador(dron1, der, caja2, transportador1, 3, 1),
    MoverTransportador(dron1, transportador1, izq, deposito, localizacion1, 4, 1),
    SacarCajaDeTransportador(dron1, izq, caja1, transportador1, 5, 1),
    EntregarCaja(dron1, izq, caja1, persona1, 6, 1),
    MoverTransportador(dron1, transportador1, izq, localizacion1, localizacion2, 7, 1),
    SacarCajaDeTransportador(dron1, izq, caja2, transportador1, 8, 1),
    EntregarCaja(dron1, izq, caja2, persona2, 9, 1),
    Mover(dron1, localizacion2, deposito, 10, 1),
]

drones = [dron1]
cajas = [caja1, caja2]
personas = [persona1, persona2]
contenidos = [comida, medicina]
transportadores = [transportador1]


# El problema se resuelve cuando cada persona tiene lo que necesita y el dron ha
# vuelto al depósito. El transportador se queda donde se sacó la última caja.
objetivos = [
    PersonaTieneContenido(persona1, comida),
    PersonaTieneContenido(persona2, medicina),
    DronEnLocalizacion(dron1, deposito),
    TransportadorEnLocalizacion(transportador1, localizacion2),
]

nuevo_mundo = Mundo(
    acciones,
    localizaciones=localizaciones,
    drones=drones,
    cajas=cajas,
    personas=personas,
    contenidos=contenidos,
    transportadores=transportadores,
    objetivos=objetivos,
)

# Simula el plan en la ventana de pygame y devuelve el informe con el veredicto
informe = nuevo_mundo.simulacion_visual()

print(informe.resumen())  # Una vez se cierra la ventana se imprime el veredicto
```

### Simulación y veredicto

`Mundo` ofrece dos formas de simular el plan. Las dos devuelven un informe (`InformeVerificacion`):

- `simulacion_texto()`: muestra en la terminal el inicio y el final de cada acción y, al terminar, el veredicto.
- `simulacion_visual()`: abre una ventana de Pygame con botones para reproducir, pausar y reiniciar el plan, y un control de velocidad. Devuelve el informe cuando se cierra la ventana.

```python
informe = nuevo_mundo.simulacion_visual()
print(informe.resumen())
```

El informe indica el veredicto en `informe.veredicto`:

| Veredicto | Significado |
|---|---|
| `VÁLIDO` | El plan se ejecuta entero sin errores y cumple todos los objetivos. |
| `NO RESUELVE` | El plan se ejecuta entero sin errores, pero al terminar no se cumple algún objetivo. |
| `EJECUTABLE` | El plan se ejecuta entero sin errores, pero no se han definido objetivos. |
| `INCOMPLETO` | La simulación se detuvo antes de terminar el plan (por ejemplo, al cerrar la ventana). |
| `NO EJECUTABLE` | Una acción no se pudo aplicar: el plan no es ejecutable. |

Además, `informe.es_valido` es `True` solo si el veredicto es `VÁLIDO`, `informe.error` contiene el mensaje de la acción que falló (o `None`) y `informe.resumen()` devuelve el texto completo, con el estado de cada objetivo. Para usar esos datos desde el código (por ejemplo, para comparar planes o en pruebas), el informe también los ofrece como objetos `EstadoObjetivo`, uno por objetivo, en `informe.estados_objetivos`, `informe.objetivos_cumplidos` e `informe.objetivos_no_cumplidos`, con las propiedades `objetivo`, `cumplido`, `logrado_en`, `roto_en` y `explicacion_fallo`.

## Ejecución

Ejecuta cualquier programa de Python que utilice la biblioteca:

```bash
python mi_programa.py
```

Por ejemplo, desde la raíz del repositorio:

```bash
python tests/ejemplo_basico.py
```

## Pruebas

El directorio `tests/regression/` contiene la batería de pruebas de regresión, que conviene ejecutar después de cada cambio en la biblioteca:

```bash
python -m unittest discover -s tests/regression -p "test_*.py"
```

## Tecnologías utilizadas

- Python 3.12.10
- Pygame 2.6.1
- PDDL (Planning Domain Definition Language)
- Git
- GitHub

## Estructura del proyecto

```text
tfg-pddl-verificacion-visualizacion/
├── src/
│   └── simulador_pddl/
│       ├── acciones/       Acciones del dominio (Mover, CogerCaja, EntregarCaja, ...)
│       ├── interfaz/       Botones y control de velocidad de la ventana
│       ├── mundo/          Mundo, el punto de entrada de la biblioteca
│       ├── objetivos/      Objetivos del problema
│       ├── objetos/        Objetos del dominio (Localizacion, Dron, Caja, ...)
│       ├── renderizado/    Dibujo de la simulación con Pygame
│       ├── simulacion/     Motor de simulación y veredicto
│       └── __init__.py
├── tests/
│   ├── regression/         Pruebas de regresión
│   └── ...                 Ejemplos de uso
├── README.md
├── pyproject.toml
└── LICENSE
```

## Licencia

Este proyecto ha sido desarrollado como parte de un Trabajo Fin de Grado (TFG) en Ingeniería Informática.

Se distribuye bajo la licencia MIT: el texto completo está en `LICENSE`.
