# Publicar el proyecto en GitHub

El paquete está preparado para crear un repositorio nuevo; no se ha subido ni
publicado automáticamente. Nombre sugerido: `sdr-random`.

## Desde la web

1. Descomprimir el ZIP y entrar a la carpeta `sdr-random`.
2. En GitHub crear un repositorio nuevo, con la visibilidad que prefieras.
3. No añadir un README ni licencia desde GitHub: ya se incluyen.
4. Subir el contenido de la carpeta, manteniendo la estructura de subcarpetas.
   Comprobar que también se incluya `.github/workflows/tests.yml`.
5. Revisar la pestaña Actions para comprobar los tests de las plataformas elegidas.

## Desde Git

Ejecutar en la carpeta que contiene `pyproject.toml`. Sustituir `TU_USUARIO` por
tu cuenta real y crear primero un repositorio vacío en GitHub:

```bash
git init
git add .
git commit -m "Initial release: SDR library, RTL-SDR backend and tests"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/sdr-random.git
git push -u origin main
```

Revisar `git status` y el contenido a subir antes del commit. `.gitignore` excluye
capturas, entornos y resultados habituales; si usás una carpeta de salida con otro
nombre, excluirla también. No subir capturas ni información local de tus ejecuciones.

## Antes de anunciar la versión

```bash
python -m unittest discover -s tests -v
python -m pip install ".[dev]"
python -m build
```

Validar además con tu receptor físico. Registrar sistema operativo, versión de
Python, `pyrtlsdr`, `librtlsdr`, modelo del receptor y parámetros usados. Una suite
verde sin hardware no prueba la calidad de entropía de la captura.

Se incluyó licencia MIT para el código propio; revisarla antes de publicar.
Las dependencias mantienen sus licencias. El nombre en PyPI no está reservado ni
se ha publicado allí. GitHub y PyPI son publicaciones independientes.

Para una release de GitHub, se puede crear el tag `v1.0.0` después de la validación
física, utilizando el resumen de `CHANGELOG.md` como notas de la versión.
