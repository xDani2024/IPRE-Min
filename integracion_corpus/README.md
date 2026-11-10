# Integración bibliográfica — OpenAlex, Scopus y Web of Science

Este módulo añade al repositorio un proceso **común y reproducible desde los archivos guardados** para normalizar, vincular y consolidar registros bibliográficos. No sustituye los códigos originales de extracción ni ejecuta llamadas a internet o a las API. Los tres paquetes se mantienen en sus carpetas originales.

## Requisitos y ejecución

Python 3.10 o superior. **No requiere instalar dependencias.** Desde la carpeta principal `IPRE-Min-main`:

```powershell
py -3 integracion_corpus/main.py
```

O desde Linux/macOS:

```bash
python3 integracion_corpus/main.py
```

Se procesan dos niveles por separado:

- `universo`: todos los registros únicos disponibles de las tres fuentes, antes de la selección temática amplia.
- `base_amplia`: registros preseleccionados por los respectivos filtros amplios, **todavía no un corpus final de estudios incluidos**.

Se puede elegir una etapa y una carpeta de salida distinta:

```powershell
py -3 integracion_corpus/main.py --etapa base_amplia --salida integracion_corpus/segunda_ejecucion
```

No ejecutar los scripts de extracción de cada plataforma para reproducir esta consolidación: los archivos base están dentro de las carpetas originales. En una nueva extracción sería necesario actualizar expresamente las entradas y anotar la nueva instantánea.

## Entradas exactas

| Etapa | OpenAlex | Scopus | Web of Science |
|---|---|---|---|
| Universo | `01_extraccion_y_filtro/datos_reconstruidos/universo_openalex.csv` | `01_extraccion_y_filtro/referencia_archivada/universo_scopus_deduplicado.csv` | `entrada_fase01/01_registros_unicos_normalizados.csv` |
| Base amplia | `01_extraccion_y_filtro/referencia_archivada/corpus_general_aceptado.csv` | `01_extraccion_y_filtro/referencia_archivada/corpus_general_aceptado_provisional.csv` | `entrada_fase01/04_base_amplia_provisional.csv` |

Las rutas de cada columna son relativas a su paquete de origen (respectivamente `Código OpenAlex/IPRE_codigo_y_datos_v9/`, `Código Scopus/IPRE_Scopus_codigo_y_datos_v9/` y `Código WoS/IPRE_WoS_cribado_homologado/`). Las rutas completas están explícitas en `fuentes.py`.

Las entradas son instantáneas congeladas: el universo OpenAlex fue reconstruido de 9.534 registros y no representa necesariamente las 9.540 referencias históricas de una descarga anterior. Scopus proviene de la recuperación guardada de sus páginas JSON. En WoS los registros proceden de exportaciones manuales. **El repositorio conserva CSV y manifiestos de esas exportaciones, pero no los 10 archivos XLS originales**, que permanecen en el paquete separado de extracción. Por tanto, esta ejecución reproduce íntegramente la integración **desde los CSV proporcionados**, no una recuperación nueva desde las tres plataformas.

## ¿Qué hace el módulo?

1. Lee cada entrada **sin modificarla**, conserva el ID nativo de la fuente y calcula su huella SHA-256.
2. Normaliza nombres de campos, DOI (prefijos y mayúsculas), títulos (para comparación) y años. Mantiene título, DOI y metadatos originales en los CSV de procedencia y conserva un hash por fila original.
3. Detecta coincidencias entre bases mediante **DOI válido** y títulos compatibles, o mediante **título normalizado y año idénticos** cuando al menos un registro no tiene DOI y no existen DOI contradictorios.
4. Evita fusionar automáticamente DOI distintos para un mismo título-año, DOI asociados a títulos/años incompatibles y dos identificadores distintos de una misma fuente. Estos casos se guardan como alertas para revisión.
5. Produce una publicación provisional por grupo, conserva todos los identificadores de las fuentes, los DOI observados, el resumen seleccionado y sus datos de procedencia. No copia ni redefine categorías temáticas o decisiones humanas entre bases.
6. Entrega una plantilla vacía para la futura clasificación por temática, objetivo, metodología y datos utilizados sobre la **base amplia** consolidada.

**No se aplicó emparejamiento difuso general de títulos.** Esta decisión es conservadora para reducir fusiones incorrectas. Aun así, las coincidencias automáticas deben auditarse antes de presentar un número definitivo de artículos únicos.

## Archivos de salida

En `resultados/universo/` y `resultados/base_amplia/`:

| Archivo | Contenido |
|---|---|
| `01_registros_normalizados.csv` | Una fila por registro fuente, DOI normalizado, etiquetas propias de la fuente y hash original. |
| `02_corpus_consolidado_provisional.csv` | Una fila por publicación vinculada, con identificadores de procedencia, resumen y etiquetas originales en JSON. La columna de etiqueta consolidada permanece en blanco. |
| `03_correspondencias_procedencia.csv` | Tabla de relación 1 a N entre publicación consolidada y registros originales. |
| `04_alertas_revision.csv` | Posibles conflictos de DOI, título, año y varias fichas de una misma fuente. |
| `05_resumen_y_fuentes.json` | Recuentos por fuente, huellas de entradas y limitaciones. |
| `06_huellas_salidas.json` | SHA-256 de los CSV generados para comprobar si se repite exactamente el procesamiento. |
| `07_plantilla_clasificacion_tematica.csv` | Solo para `base_amplia`: campos vacíos para trabajo posterior por paper. |

El archivo `resultados/RESUMEN_INTEGRACION.json` reúne las cifras de ambas etapas.

## Resultados de la instantánea incluida

| Etapa | OpenAlex | Scopus | WoS | Registros de entrada | Publicaciones vinculadas provisionales | Reducción por coincidencias |
|---|---:|---:|---:|---:|---:|---:|
| Universo | 9.534 | 9.547 | 5.071 | 24.152 | 15.412 | 8.740 |
| Base amplia | 4.735 | 4.614 | 2.238 | 11.587 | 7.465 | 4.122 |

Estos valores provienen exclusivamente del tratamiento computacional de los registros incluidos. **No representan el número de estudios seleccionados tras evaluación humana**. Se registraron alertas de revisión que requieren análisis antes de cerrar la deduplicación.

## Cómo se conservan las etiquetas

Las etiquetas de OpenAlex, Scopus y WoS son **metadatos específicos de cada fuente y etapa**. Se mantienen en `01_registros_normalizados.csv` y en `etiquetas_originales_por_fuente_json` del corpus. No se crea una etiqueta común de forma automática. Se recomienda efectuar la clasificación temática definitiva y, si corresponde, la revisión de objetivos, metodologías y datos utilizados sobre los registros consolidados después de validar las coincidencias.

## Reproducibilidad, validación y alcance

- Se usan **solo archivos ya presentes** y se registran sus nombres y huellas SHA-256. Ejecutar nuevamente el módulo con esas mismas entradas produce los mismos CSV.
- En los procesos originales, **OpenAlex incluye juicios humanos históricos** y Scopus y WoS tienen revisiones independientes pendientes. Esta integración no combina ni homologa estados IN/OUT/TC; trabaja con metadatos bibliográficos antes de decidir sobre la clasificación definitiva.
- Las diferencias de fechas de publicación editorial o Early Access no se corrigen automáticamente. Se conservan para revisión bibliográfica.
- El tratamiento conservador deja algunas publicaciones repetidas sin fusionar ante evidencia incompleta o ambigua, mientras otros pares propuestos como equivalentes necesitan revisión. El corpus es por ello **provisional**.
- Para reconstruir desde la extracción original de WoS, se necesitan los XLS de las exportaciones y la documentación completa de búsquedas/filtros. Para extraer nuevamente mediante API, cada proveedor exige su propio procedimiento, credencial y cuota.
- Las huellas verifican identidad de archivos y estabilidad del cómputo, **no calidad científica ni validez de las etiquetas**.

## Pruebas

```powershell
py -3 -m unittest discover -s integracion_corpus/pruebas -v
```

Las pruebas comprueban reglas de DOI y títulos, fusión de casos compatibles, no fusión de DOI contradictorios, diferencias de año y conservación de etiquetas originales.
