# Flujo unificado del corpus bibliográfico — IPRE

## Objetivo y orden de trabajo

**OpenAlex (API), Scopus (API) y WoS (exportación manual) se obtienen independientemente**, con consultas y filtros de recuperación documentados. Después se efectúan, sobre todos los registros disponibles, **normalización → unificación → deduplicación interbase → cribado común (título y resumen) → revisión humana → clasificación temática**.

Las etiquetas temáticas no se fijan antes de la unificación. Las reglas y decisiones de los cribados anteriores por base (v6-v9) se mantienen intactas como antecedentes para comparar, **pero NO determinan la inclusión en el nuevo corpus**.

### Esquema de pasos

```text
OpenAlex: API ---------┐
Scopus:   API ---------+--> entradas originales conservadas
WoS:     archivos ----┘            |
                       normalización de campos
                                |
                    unificación de las 3 fuentes
                                |
                      deduplicación por DOI y título-año
                       (con alertas para revisión)
                                |
               cribado inicial COMÚN sobre título y abstract
                                |
                         revisión humana (PENDIENTE)
                                |
                  clasificación temática (PENDIENTE)
``` 

## Reproducir con el repositorio entregado

Desde la carpeta `IPRE-Min-main`, ejecute:

```bash
python flujo_unificado/main.py
```

Esto **no requiere internet ni claves**: usa los tres universos archivados antes de sus cribados temáticos individuales. Al final encontrará los resultados en `flujo_unificado/resultados`.

**Entradas por defecto:** OpenAlex `universo_openalex.csv` (9.534), Scopus `universo_scopus_deduplicado.csv` (9.547) y WoS `01_registros_unicos_normalizados.csv` (5.071). Cada fuente ya aplicó algunos controles técnicos y su propia deduplicación, por lo que los 24.152 registros de entrada **no son el total bruto de resultados de búsqueda** ni implican una captura simultánea de las tres bases. Se conservan recuentos y archivos de origen.

## Para utilizar nuevas extracciones (sin ejecutar cribados de cada fuente)

Interfaz común para invocar los extractores existentes, manteniendo internamente sus distintas APIs:

```bash
python flujo_unificado/adquisicion.py --fuente scopus --modo piloto --salida ejecuciones/scopus_2026
python flujo_unificado/adquisicion.py --fuente openalex --modo completo --salida ejecuciones/openalex_2026
python flujo_unificado/adquisicion.py --fuente wos --carpeta-wos exportaciones_wos --salida ejecuciones/wos_2026
```

OpenAlex requiere `OPENALEX_API_KEY`, Scopus requiere `SCOPUS_API_KEY` o ingreso interactivo. El extractor **original OpenAlex no tiene piloto**, por lo que aquí no se simula uno. No se ejecutaron nuevas consultas de red para preparar este paquete. Los extractores siguen usando sus parámetros, consultas y controles originales; la interfaz común solo estandariza cómo invocarlos. Guarde las nuevas consultas, fechas, conteos y criterios en la bitácora.

Tras obtener universos nuevos, ejecutar el procesamiento común con sus rutas (antes de cualquier cribado temático):

```bash
python flujo_unificado/main.py --openalex-csv ejecuciones/openalex_2026/universo_openalex.csv --scopus-csv ejecuciones/scopus_2026/universo_scopus_deduplicado.csv --wos-exportaciones exportaciones_wos --salida ejecuciones/corpus_2026
```

**Nota importante sobre Scopus:** el lanzador común prepara `universo_scopus_deduplicado.csv` directamente desde las páginas guardadas, **sin aplicar cribado temático por fuente**. El modo piloto se rotula como parcial y no reemplaza una extracción completa. Antes de analizar la cohorte, revise el manifiesto de páginas/consultas y complete el ciclo con diez ramas.

WoS también puede ingresar como `--wos-csv ruta/al/universo.csv` si el archivo ya fue normalizado. `--wos-exportaciones` acepta CSV UTF-8, XLSX y XLS; para XLSX se requiere `openpyxl` y para XLS se requiere `xlrd` (instalación con `pip install openpyxl xlrd`). No se importan silenciosamente archivos sin títulos ni se combinan UID repetidos sin revisión. Conservar la fecha de búsqueda, todas las consultas WoS, filtros, lotes exportados, número de resultados y verificaciones de cobertura.

## Estructura de resultados

- `02_integracion_y_deduplicacion/`: matriz normalizada, corpus provisional sin duplicados, correspondencias de ID, alertas, fuentes y huellas SHA-256.
- `03_cribado_comun/`: cribado automático común y subconjuntos de candidatos, pendientes o propuestas de exclusión.
- `04_revision_humana/`: plantilla con **todas** las publicaciones para revisión independiente (nada se elimina automáticamente de forma irreversible).
- `05_clasificacion_posterior/`: plantilla temática, **sin etiquetas definitivas**.
- `06_auditoria/`: resumen completo, parámetros, recuentos, limitaciones y SHA-256 de salidas.

## Precauciones metodológicas

1. **Reproducible desde instantáneas guardadas** no significa idéntica extracción en otra fecha: los catálogos y licencias cambian.
2. **Mismos criterios en el cribado:** el motor solo consulta título, resumen y tipo de documento. No utiliza palabras clave o topics exclusivos de OpenAlex. Los diccionarios proceden del extractor original OpenAlex, pero esta adaptación común aún no ha sido calibrada con revisión humana conjunta; es una primera propuesta.
3. Las coincidencias DOI/título-año son conservadoras y pueden producir **alertas**; revise las alertas antes de publicar cifras finales.
4. Los registros WoS exportados manualmente son válidos para esta integración siempre que exista documentación suficiente de consultas, fechas, filtros, archivos y cobertura. Los diez XLS originales WoS **no estaban incluidos** en el repositorio recibido, por lo que la ejecución de demostración emplea el CSV normalizado de WoS.
5. Las etiquetas temáticas (3–5 grandes grupos, 6–8 temas específicos, objetivo, metodología y datos) deben consensuarse **después** del cribado y la revisión de inclusión, no confundirse con señales automáticas de detección.
6. Los 3 universos tienen filtros documentales propios anteriores (artículo/revisión, acceso a resúmenes, etc.). Si se necesita un conteo PRISMA exacto desde resultados brutos, se deben incorporar también las exportaciones/descargas crudas y sus contadores de origen.

## Pruebas

```bash
python -m unittest discover -s flujo_unificado/pruebas -v
python -m unittest discover -s integracion_corpus/pruebas -v
```

## Actualización del cribado común — v1.1 (noviembre de 2026)

**No utilizar los conteos automáticos como un corpus final ni como estimaciones de
precisión o sensibilidad.** Se ajustaron las reglas tras revisar casos concretos
mal clasificados. Se amplió el reconocimiento de términos como `open-pit mines`,
`drillability` y `auxiliary vehicles`, se separaron las señales de dominio,
proceso/equipo y objetivo, y se introdujo una revisión prioritaria. El cribado
sigue usando **solo título, resumen y tipo de documento** para su decisión.
La procedencia y etiquetas antiguas no determinan la decisión.

Ejecutar desde la carpeta `IPRE-Min-main`:

```cmd
python flujo_unificado/main.py
```

El nuevo destino predeterminado es `flujo_unificado/resultados_calibracion_v1_1`.
**No sustituye** `flujo_unificado/resultados` (la versión anterior), si está
presente. El proceso muestra los conteos y conserva `791` alertas bibliográficas
que aún deben investigarse.

Los cuatro estados son:

- `CANDIDATO`: evidencia automática relativamente fuerte. **No es inclusión confirmada**.
- `REVISION_PRIORITARIA`: evidencia parcial de operación minera. Revisar primero.
- `PENDIENTE_REVISION`: metadatos incompletos o solo contexto minero, sin un
  proceso claramente detectado. Prioridad `MEDIA` o `BAJA` según el motivo.
- `EXCLUSION_PROPUESTA`: poca evidencia de foco operacional o documento
  incompatible con los criterios documentales; **se debe validar antes de excluir**.

Salidas adicionales:

- `03_cribado_comun/05_revision_prioritaria.csv`: cola de revisión.
- `04_revision_humana/02_muestra_validacion.csv`: muestra pseudoaleatoria
  determinista por estado, más cuatro casos centinela conocidos. Completar
  `decision_humana`, `motivo_decision_humana`, `revisor` y `fecha_revision`.
- `06_auditoria/01_cambios_vs_cribado_previo.csv`: comparación por `id_publicacion`
  cuando la matriz anterior está disponible; no es una medida de mejora.
- `06_auditoria/resumen_flujo.json`: conserva versión, recuentos y limitaciones.

Para resumir los acuerdos del equipo sobre la muestra de revisión humana:

```cmd
python flujo_unificado/evaluar_revision_humana.py --muestra flujo_unificado/resultados_calibracion_v1_1/04_revision_humana/02_muestra_validacion.csv
```

Acepta `INCLUIR`, `EXCLUIR` y `DUDOSO`. Los campos vacíos se consideran no
revisados. El programa produce un resumen y alerta de discrepancias claras,
pero **no define automáticamente el criterio de inclusión**, que debe acordarse
con el profesor y ser documentado antes de validar el corpus.

**Aspectos pendientes:** 1) revisar 791 alertas de vinculación bibliográfica,
2) definir criterios explícitos de exclusión/inclusión temática y validar
una muestra por categoría y fuente, 3) revisar artículos no redactados en
inglés con criterios lingüísticos adecuados y 4) pasar a etiquetas temáticas
solo cuando el cribado conjunto esté validado.

## Cruce trazable con las propuestas históricas v9 — v1.2

El repositorio incorpora `flujo_unificado/entrada_historial_v9/`, con tres
instantáneas resumidas (4.735 OpenAlex, 4.614 Scopus y 2.238 WoS) que conservan
los identificadores originales, DOI, título, año, decisión v9 **propuesta** y
cualquier decisión humana histórica expresamente registrada. El archivo
`procedencia.json` documenta la matriz v9 original y su SHA-256. Estos snapshots
se pueden reconstruir desde el repositorio original completo con:

```cmd
python flujo_unificado/preparar_historial_v9.py --zip-origen "IPRE-Min-main.zip"
```

El comando usual genera también `07_cruce_historico_v9`:

```cmd
python flujo_unificado/main.py
```

- `01_cruce_por_registro.csv`: relaciones exactas entre 11.587 registros históricos
  y los identificadores `registro_uid`, con su `id_publicacion` consolidado.
- `02_cruce_por_publicacion.csv`: **una fila por cada una de las 15.412
  publicaciones**. Incluye propuestas v9 por fuente, estado v1.1, posibles
  contradicciones y campos vacíos para revisión humana.
- `03_casos_para_revisar.csv`: propone prioridades, **sin aceptar decisiones automáticamente**.
- `05_resumen_cruce_v9.json`: recuentos, cruces y huellas SHA-256.
- `06_alertas_deduplicacion_para_revisar.csv`: las 791 alertas previas enriquecidas
  con datos bibliográficos y campos para resolverlas manualmente.

La selección histórica `IN` comprende **977 registros pero solo 642 publicaciones
únicas provisionales**. No se debe sumar la cantidad `IN` por base como si fueran
artículos distintos. El historial v9 de Scopus y WoS y la mayoría de los resultados
de OpenAlex **no han sido revisados de manera independiente por personas**.

**La clasificación previa no altera el nuevo cribado común.** Una discrepancia
`IN`/`OUT` entre fuentes es una alerta para revisar el artículo, no una exclusión
ni inclusión definitiva. Para usar nuevos universos completamente distintos, se
puede omitir temporalmente el historial con `--sin-cruce-v9`.

La vinculación y los IDs son **provisionales** mientras existan alertas de
bibliografía y no se hayan acordado las decisiones humanas. Los identificadores
ordinales `IPRE-UNIVERSO-...` se pueden reasignar al actualizar entradas. Para
seguimiento longitudinal de los registros, utilice `registro_uid` y las tablas
de correspondencias, no el número ordinal.

### Corrección de información y límites

- No se reemplazan registros originales ni los resultados históricos.
- Los DOI, título y año de los registros v9 se cotejan con sus entradas actuales
  antes de dar por válido el cruce por ID.
- Cada publicación conserva las fuentes donde aparece y las propuestas v9
  de cada fuente. Se revisarán independientemente las contradicciones.
- Los recuentos representan datos de entrada ya deduplicados dentro de cada fuente,
  no resultados brutos de cada consulta.
- Los archivos XLS originales de WoS no forman parte del paquete, por lo que la
  importación original manual solo es reproducible desde el CSV archivado y la
  documentación de la exportación.
