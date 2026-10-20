# API pública

Importar desde `sdr_random`. El núcleo no importa `pyrtlsdr` hasta que se crea
una fuente RTL-SDR, permitiendo utilizar archivos sin dependencias externas.

## SDRRandom(source, block_bytes=65536, on_block=None)

`source` implementa `read(size) -> bytes`; debe entregar el tamaño exacto o lanzar
una excepción. `block_bytes` debe ser un entero positivo múltiplo de 512. La fuente
pertenece al llamador: el generador no la abre ni la cierra.

| Método / atributo | Resultado |
| --- | --- |
| `number(digits=1)` | `str` del ancho pedido, con ceros iniciales |
| `numbers(count, digits=1)` | Iterador; las lecturas ocurren al consumirlo |
| `number_record(digits=1)` | `Number` con texto y procedencia |
| `blocks` | Cantidad de bloques completos que pasaron los controles |

`count` y `digits` deben ser enteros positivos; booleanos no se aceptan. Las
peticiones de ancho arbitrario están sujetas a memoria y tiempo disponibles.

`Number` es una dataclass inmutable con `text`, `start_block`, `start_hex`,
`end_block`, `end_hex`. Bloques desde 1; posiciones hexadecimales desde 0 hasta 63,
ambas inclusivas. Un número puede cruzar varios bloques.

`on_block(block)` recibe un `Block` inmutable por cada nueva captura aceptada,
antes de entregar sus dígitos. Contiene `index`, `raw`, `sha256`, `accepted`.
Sirve para auditoría propia; no se escriben archivos automáticamente en la API.
Una excepción de la fuente o del callback deja la instancia detenida. No se
entregan números incompletos ni se permite continuar con otra captura después
de ese fallo. Crear una instancia nueva para reiniciar.

## Fuentes

`RTLSDRSource(frequency_hz, sample_rate=2048000, gain='auto', device_index=0,
block_bytes=65536)` configura el receptor, desactiva su modo de prueba y descarta
un bloque inicial. Frecuencia y sample rate positivos y finitos; ganancia válida
para el dispositivo. El último parámetro determina el tamaño del bloque inicial
descartado; el generador elige por separado su tamaño de lectura.
`settings` expone frecuencia, tasa y ganancia informadas por el receptor.

`IQFileSource(path)` lee un archivo u8 I/Q intercalado sin cabecera; no lo repite.
Ambas fuentes admiten `with`, `read(size)` y `close()`.

`SourceError(RuntimeError)` identifica lecturas incompletas, errores de lectura
USB y fallos de los controles básicos. La carga de drivers ausentes también se
convierte a `SourceError`; otros errores de configuración de la dependencia
pueden propagarse. Parámetros inválidos propios lanzan `ValueError`; errores de
archivos y callbacks pueden mantener su tipo original.

`decimal_digits(digest: bytes) -> str` filtra los nibbles del digest; acepta bytes
de cualquier longitud, aunque el generador utiliza SHA-256.

## Semántica de reproducibilidad

La secuencia depende de los bytes y de cómo se dividen en bloques. Se conservan
sobrantes entre llamadas incluso si cambia el ancho. La misma concatenación de
peticiones de dígitos consume el mismo flujo decimal. Crear un generador nuevo
reinicia el control de duplicados y descarta los sobrantes del anterior.

No hay mezcla con una segunda fuente, expansión de un hash mediante contadores
ni selección de una frecuencia predeterminada. Un hash con cero dígitos aceptados
hace que se lea otro bloque; una fuente infinita que nunca produzca dígitos
aceptados podría mantener ocupada la llamada.
