# Cambios

## 1.0.0

- Refactor del generador anterior a la librería `sdr_random`.
- Backend opcional RTL-SDR y reproducción de I/Q u8 sin cabecera.
- API para resultados de uno, dos, tres o más dígitos con ceros iniciales.
- SHA-256 y rechazo de nibbles `a..f`; capturas nuevas cuando faltan dígitos.
- Buffer de sobrantes entre llamadas y trazabilidad de posiciones.
- Programa manual `test_generador.py` y entrada compatible `script.py`.
- CSV, hashes, capturas y metadata, incluidos resultados parciales ante error.
- Tests sin hardware y workflow de GitHub Actions para tres sistemas operativos.
- Documentación de instalación, API, límites y publicación en GitHub.

### Cambio respecto al script anterior

Ahora se exige indicar `--frequency-mhz` o `--iq-file`. Se quitó la selección
automática de 100 MHz para evitar confundirla con una frecuencia de ruido válida.
Los nombres de campos internos de metadata y bloques JSON cambiaron; el CSV
mantiene sus columnas. Los dígitos generados desde los mismos bytes y el mismo
tamaño de bloque conservan el algoritmo de la versión anterior.
