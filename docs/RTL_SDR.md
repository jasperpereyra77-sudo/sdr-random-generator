# Instalación y compatibilidad RTL-SDR

## Alcance

La captura usa `pyrtlsdr.RtlSdr.read_bytes`, que entrega bytes I/Q u8 mediante
`librtlsdr`. Está destinada a receptores RTL2832U soportados por esa biblioteca.
No es un backend para HackRF, Airspy, SDRplay, dispositivos de audio ni SDR genéricos.

Modelos como RTL-SDR Blog V3/V4 requieren un driver que soporte su revisión; en
particular, seguir las instrucciones del fabricante para V4. La presencia de USB
no garantiza que una instalación antigua de `librtlsdr` reconozca el equipo.

El software no ha sido probado aquí con hardware físico. La compatibilidad real
depende del receptor, biblioteca nativa, controlador USB y sistema operativo.
El rango Python `pyrtlsdr>=0.3.0,<0.6` expresa la dependencia admitida, no una
validación exhaustiva de cada versión intermedia.

## Debian / Ubuntu

```bash
sudo apt update
sudo apt install rtl-sdr librtlsdr0 python3-venv
rtl_test -t
```

Crear y activar el entorno virtual según README e instalar `.[rtl]`. Cerrar
`rtl_test` y cualquier otro programa de SDR antes de iniciar una captura.
Si aparece acceso denegado, revisar las reglas udev incluidas por la distribución.
Si el dispositivo está tomado por un controlador DVB del kernel, seguir la guía
de la distribución para liberar ese receptor; no ejecutar habitualmente Python
como root para resolver el problema.

## Windows

1. Instalar Python de arquitectura compatible con la biblioteca nativa.
2. Seguir la guía del fabricante para instalar WinUSB (normalmente mediante Zadig)
   en la interfaz correspondiente al receptor; verificar cuidadosamente el equipo elegido.
3. Instalar `librtlsdr` y sus dependencias nativas compatibles con el modelo.
   Su ubicación debe ser localizable por Python; revisar la guía de pyrtlsdr y
   el mecanismo de carga de DLL de la versión de Python utilizada.
4. Activar el entorno e instalar `python -m pip install -e ".[rtl]"`.
5. Verificar el equipo con `rtl_test` de la misma distribución del driver.

Instalar únicamente `pyrtlsdr` no instala necesariamente el driver USB ni las DLL.
No mezclar DLL de 32 y 64 bits. No se incluyen drivers en este proyecto.

## macOS

Con Homebrew, instalar `brew install librtlsdr`; después crear el entorno e
instalar `.[rtl]`. Python y librtlsdr deben compartir arquitectura, en particular
en Apple Silicon. Verificar detección con las herramientas del paquete instalado.

## Selección de la fuente de ruido

Revisar el espectro y el ancho de banda del receptor. Elegir una frecuencia
adecuada dentro del rango soportado, evitando portadoras y saturación. Un bloque
descartado es una precaución inicial, no una caracterización de estabilización.
No hay una frecuencia universalmente «vacía». El programa no detecta un canal
libre ni mide la calidad de la entropía.

## Diagnóstico

| Síntoma | Revisar |
| --- | --- |
| No se encuentra `rtlsdr` | Entorno activo e instalación `.[rtl]` |
| No se puede cargar `librtlsdr` | Biblioteca nativa, dependencias y arquitectura |
| Dispositivo no encontrado / ocupado | Driver, índice `--device`, permisos y otros programas abiertos |
| Fallo al establecer frecuencia o ganancia | Valores admitidos por el tuner |
| Captura casi constante / repetida | USB, modo de prueba, driver y señal; no desactivar controles para forzar salida |
| Entrada agotada | Archivo corto o tamaño de bloque distinto al original |

Referencias del fabricante y proyectos upstream:

- https://github.com/pyrtlsdr/pyrtlsdr
- https://pyrtlsdr.readthedocs.io/en/stable/Reference.html
- https://gitea.osmocom.org/sdr/rtl-sdr
- https://www.rtl-sdr.com/rtl-sdr-quick-start-guide/
- https://www.rtl-sdr.com/v4/
