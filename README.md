# SDR Random

Generador **experimental** de números decimales desde capturas de ruido I/Q de un
RTL-SDR. Aplica SHA-256, descarta los nibbles hexadecimales `a..f` y agrupa los
dígitos `0..9` en cadenas del ancho solicitado.

Incluye una librería Python reutilizable, un programa de prueba, reproducción de
archivos I/Q y auditoría de cada ejecución. No utiliza números aleatorios del
sistema operativo, reloj ni contadores como entradas al hash.

## Qué significa «uno, dos o tres dígitos»

| Opción | Salida | Ejemplos ilustrativos |
| --- | --- | --- |
| `-1` | `0` a `9` | `0`, `5`, `9` |
| `-2` | `00` a `99` | `03`, `47`, `90` |
| `-3` | `000` a `999` | `007`, `428`, `901` |
| `-80` | Cadenas de 80 dígitos | Se combinan varios hashes si hace falta |

Se conservan ceros iniciales. Se admiten repeticiones entre resultados: no es un
sorteo sin reposición. `-N` debe ir primero; `--digitos N` puede ir en cualquier posición.

## Requisitos e instalación

- Python **3.10 o posterior**.
- Para captura en vivo: receptor RTL-SDR compatible con `librtlsdr`, biblioteca
  nativa, controlador USB y `pyrtlsdr`.
- Para reproducir archivos y ejecutar los tests: no hace falta un SDR ni `pyrtlsdr`.

Desde la carpeta del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[rtl]"
```

En PowerShell, activar con `.\.venv\Scripts\Activate.ps1`; se puede usar `py`
en lugar de `python3` para crear el entorno. Para trabajar sin hardware:

```bash
python -m pip install -e .
```

La opción `[rtl]` instala la interfaz Python; el driver USB y `librtlsdr` se
instalan por separado. Consultar [compatibilidad RTL-SDR](docs/RTL_SDR.md).

## Programa de prueba

Ejemplo de sintaxis con **100 MHz**; cambiar esa frecuencia por una que hayas
verificado en tu ubicación. 100 MHz pertenece a la banda de radiodifusión FM y
no se considera un canal de ruido recomendado. La frecuencia se exige
explícitamente; el programa no busca canales libres.

```bash
python test_generador.py -1 --cantidad 20 --frequency-mhz 100
python test_generador.py -2 --cantidad 20 --frequency-mhz 100
python test_generador.py -3 --cantidad 20 --frequency-mhz 100
```

También funcionan `python script.py`, `python -m sdr_random` y el comando
instalado `sdr-random`, con las mismas opciones:

```bash
sdr-random --digitos 3 --cantidad 100 --frequency-mhz 100 --gain auto
python -m sdr_random -80 --cantidad 5 --frequency-mhz 100
python test_generador.py -2 --cantidad 100 --iq-file captura.iq
```

`--cantidad` cuenta resultados completos, no dígitos ni bloques. Si no se indica,
genera un resultado. Para guardar el texto, redirigir stdout:

```bash
python test_generador.py -3 --cantidad 100 --frequency-mhz 100 > numeros.txt
```

Los números se imprimen de a uno por línea; mensajes y errores van a stderr.

### Opciones

| Opción | Predeterminado | Descripción |
| --- | --- | --- |
| `-N` / `--digitos N` | `1` | Ancho positivo; usar una sola forma |
| `--cantidad N` | `1` | Cantidad positiva de resultados |
| `--frequency-mhz F` | Sin valor | Frecuencia de captura; excluye `--iq-file` |
| `--iq-file ARCHIVO` | Sin valor | I/Q u8 intercalado, sin cabecera; excluye frecuencia |
| `--device N` | `0` | Índice USB del receptor |
| `--sample-rate HZ` | `2048000` | Tasa solicitada, sujeta al hardware |
| `--gain auto` / `--gain DB` | `auto` | Ganancia soportada por el receptor |
| `--bloque-bytes N` | `65536` | Tamaño positivo múltiplo de 512 |
| `--salida CARPETA` | Nombre con fecha UTC | Carpeta nueva para todos los registros |

Hay que elegir exactamente una fuente: `--frequency-mhz` o `--iq-file`.
Las opciones de hardware no se aplican a la reproducción.

## Usar como librería

```python
from sdr_random import RTLSDRSource, SDRRandom

# Frecuencia ilustrativa: elegir una apropiada después de revisar el espectro.
with RTLSDRSource(frequency_hz=100_000_000, gain="auto") as source:
    generator = SDRRandom(source)
    print(generator.number(digits=1))       # str: "0" ... "9"
    print(generator.number(digits=2))       # str: "00" ... "99"
    for value in generator.numbers(count=10, digits=3):
        print(value)
```

El generador conserva los dígitos sobrantes entre llamadas. Si se pide más de
lo que aporta un hash, lee **otro bloque de la fuente** y concatena los dígitos
aceptados de su hash. No vuelve a hashear el mismo bloque para estirar la salida.

Reproducción sin hardware:

```python
from sdr_random import IQFileSource, SDRRandom

with IQFileSource("captura.iq") as source:
    generator = SDRRandom(source, block_bytes=65536)
    values = list(generator.numbers(count=10, digits=3))
```

Para integraciones y trazabilidad: [API pública](docs/API.md).

## Procedimiento y corrección de sesgo

1. Configura el RTL-SDR con el modo de prueba del hardware desactivado.
2. Descarta un bloque inicial después de configurarlo; en archivos no descarta nada.
3. Lee bloques I/Q nuevos. Detiene la ejecución si faltan bytes, hay menos de
   cuatro valores distintos en el bloque o su hash ya apareció en esta instancia.
4. Calcula `SHA-256(bytes_del_bloque)` y recorre sus 64 caracteres hexadecimales.
5. Acepta `0..9`, descarta `a..f` y conserva el orden.
6. Concatena los dígitos aceptados y forma grupos de N, cruzando bloques si hace falta.

Aplicar `% 10` a valores `0..15` duplicaría las posibilidades de los resultados
`0..5`. El rechazo evita ese sesgo de conversión: **si los nibbles de entrada son
uniformes**, cada dígito aceptado tiene probabilidad `1/10`. Si además son
independientes, cada cadena de N dígitos tiene probabilidad `10^-N`.

Un SHA-256 aporta 64 nibbles y, bajo ese modelo, unos **40 dígitos aceptados en
promedio**. No hay que confundir esa cantidad con una medición de entropía.

### Alcance y limitaciones

Este proyecto no certifica entropía ni implementa una fuente validada según
NIST SP 800-90B. SHA-256 no crea entropía y un canal aparentemente vacío puede
contener señales, interferencia o muestras predecibles. Los controles incluidos
son heurísticas de fallos: un patrón periódico de muchos valores puede pasarlos.
No hay escaneo automático del espectro, estimación de minentropía, pruebas RCT/APT
calibradas ni garantía de independencia entre bloques.

Reprocesar las mismas capturas con igual tamaño de bloque reproduce exactamente
la salida. El control de duplicados se limita a una instancia y no compara con
ejecuciones anteriores. No usar esta versión como fuente única para claves,
contraseñas ni sorteos que requieran certificación. Las capturas guardadas
permiten reconstruir todos los números: no publicar capturas de resultados secretos.

La memoria del control de duplicados crece con los bloques procesados. La librería
no guarda I/Q por defecto; el programa de prueba sí, por lo que el disco crece con
la captura. No es una instancia compartible entre hilos y su fuente debe ser finita
o capaz de entregar bloques nuevos. La llamada nativa USB es síncrona, sin timeout
adicional gestionado por esta librería.

## Auditoría y reproducción

Cada ejecución del programa de prueba crea:

```text
resultados_sdr_FECHA/
  numeros.csv
  metadata.json
  bloques.jsonl
  capturas/
    bloque_000001.iq
    bloque_000002.iq
```

- `numeros.csv`: texto de cada resultado y bloque/posición hexadecimal inicial y
  final, ambos inclusivos; posiciones `0..63`.
- `metadata.json`: fuente, ajustes leídos del receptor, versión, estado, cantidades
  y frecuencias observadas de los dígitos emitidos.
- `bloques.jsonl`: hash, dígitos aceptados, rechazos y ruta de cada captura.
- `capturas/*.iq`: bytes usados como entrada al hash; excluyen el bloque inicial descartado.

En Excel, importar `numero_texto` como **texto** para mantener los ceros.
Una carpeta existente nunca se sobrescribe. Ante error se conservan los registros
parciales; el estado se actualiza cuando Python puede ejecutar la limpieza.
Códigos de salida: `0` completo, `1` error, `2` argumentos inválidos, `130` interrupción.
Una pérdida de energía o terminación forzada puede dejar metadata sin actualizar.

Para reproducir una ejecución, concatenar sus capturas en orden y mantener el
mismo `--bloque-bytes`, ancho y cantidad. Crear `replay.iq` con Python:

```python
from pathlib import Path

captures = Path("resultados_sdr_FECHA/capturas")
with open("replay.iq", "wb") as output:
    for path in sorted(captures.glob("bloque_*.iq")):
        output.write(path.read_bytes())
```

```bash
python test_generador.py -3 --cantidad 100 --iq-file replay.iq --salida reproduccion
```

Si se solicita más salida de la disponible, termina con error; nunca vuelve al
inicio del archivo ni cambia silenciosamente a una fuente del sistema operativo.

## Pruebas y publicación

```bash
python -m unittest discover -s tests -v
python -m pip install ".[dev]"
python -m build
```

Hay 15 pruebas automáticas sin hardware, incluidas pruebas de integración CLI y
del adaptador USB con un dispositivo simulado. Se verificaron localmente; no se
ha validado un receptor físico en este entorno. El workflow de GitHub ejecutará
la suite y el empaquetado en Linux, Windows y macOS con Python 3.10, 3.12 y 3.14;
eso verifica software, no compatibilidad física de todos los receptores.

Ver [guía para subir a GitHub](docs/PUBLICAR_GITHUB.md) y [cambios](CHANGELOG.md).

## Licencia y referencias

El código propio se distribuye bajo [MIT](LICENSE). Los drivers y dependencias
conservan sus respectivas licencias; no se incluyen sus binarios.

- [pyrtlsdr: proyecto oficial](https://github.com/pyrtlsdr/pyrtlsdr).
- [API oficial de pyrtlsdr](https://pyrtlsdr.readthedocs.io/en/stable/Reference.html).
- [RTL-SDR de Osmocom](https://gitea.osmocom.org/sdr/rtl-sdr).
