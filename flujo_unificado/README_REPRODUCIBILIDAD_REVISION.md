# Registro reproducible de decisiones bibliográficas IPRE

**Estado:** cierre de revisión manual hasta 9 de noviembre de 2026. Esta versión **NO aplica fusiones**, no reincorpora registros excluidos, no corrige retroactivamente el cribado histórico y no recalcula el corpus final. Las aprobaciones quedan como datos versionados en `decisiones_aprobadas/`.

## Ejecutar en Windows CMD

Desde `IPRE-Min-main`, con Python 3.10 o superior:

```cmd
python flujo_unificado/reproducir_revision_bibliografica.py
```

También puede invocarse a través del flujo principal, **sin ejecutar la integración ni el cribado**:

```cmd
python flujo_unificado/main.py --solo-revision-bibliografica
```

Para ejecutar el flujo original completo y obtener, además, la auditoría humana en una carpeta separada (sin aplicar las fusiones):

```cmd
python flujo_unificado/main.py --auditar-revision-aprobada
```

Para ejecutar las pruebas:

```cmd
python -m unittest discover -s flujo_unificado/pruebas -p "test_*.py"
```

Las salidas se escriben en `flujo_unificado/auditoria_revision_aprobada/` (o en `09_revision_bibliografica_aprobada` bajo la carpeta de salida si utiliza `main.py`). No se modifican los CSV de origen ni las decisiones humanas congeladas.

## Criterios de deduplicación documentados

1. **Identificadores estables:** todas las decisiones se aplican conceptualmente a `OpenAlex::<id>`, `Scopus::<id>` y `WoS::<id>`, no a números de alerta susceptibles de cambiar entre ejecuciones.
2. **Identidad bibliográfica:** DOI idéntico y títulos compatibles favorecen la fusión; DOI diferentes no implican automáticamente ni identidad ni separación. La autoría, revista, volumen, páginas, idioma y fecha editorial ayudan a distinguir variantes.
3. **Años:** conservar íntegramente el año de cada fuente; registrar por separado año del volumen y fecha de publicación en línea. No trasladar fechas verificadas al campo original.
4. **Duplicados de la misma fuente:** solo consolidarlos cuando exista una decisión humana explícita. La fusión automática original es deliberadamente conservadora.
5. **Ediciones y republicaciones:** conservar cada publicación editorial con identificadores propios y, si procede, registrar un vínculo de relación. Los cinco casos de fusión parcial están descritos explícitamente por sus UID en el código (`0112`, `0229`, `0316`, `0384`, `0519`); las separaciones explícitas se exportan en otro archivo.
6. **Coincidencias repetidas entre alertas:** referencias y ampliaciones (`0159`, `0173`, `0308`, `0312`, `0334`, `0397`) se consolidan por UID sin duplicar grupos o fusiones.
7. **Unicode:** 249 alertas `TITULO_VACIO` tienen títulos en alfabetos no latinos válidos. La corrección se registra **sin fusionar** ni asignar inclusión temática.
8. **Procedencia y cribado histórico:** los DOI, años, títulos, resúmenes, fuentes e `IN/OUT` v9 originales se mantienen sin sobrescribir. La identidad bibliográfica no equivale a pertinencia de la tesis.
9. **105 registros de cobertura:** permanecen en el universo OpenAlex, con estado original `exclude` (motivo `sin_foco_operacional_suficiente`). No se reincorporan sin cribado humano; 15 tienen prioridad preliminar y ninguna decisión temática final.
10. **Casos abiertos:** `0111`, `0500`, `0529`, `0534` sin dictamen. Los seguimientos `0467` y `0519` continúan pendientes de verificación editorial; `0182` tiene separación definitiva.

## Versiones del normalizador

`integracion_corpus/normalizacion.py` conserva `normalizar_titulo()` (modo histórico `historica_ascii`) para reproducir las alertas de la primera pasada. Añade `normalizar_titulo_unicode()` (modo `unicode_v2`) que mantiene letras y números de todos los alfabetos. El modo histórico sigue siendo el predeterminado: cambiarlo modifica coincidencias, orden y número de alertas, por lo que **no se deben reutilizar automáticamente IDs de alerta de una ejecución distinta**.

Para una *ejecución exploratoria separada* de la integración con normalización Unicode:

```cmd
python integracion_corpus/main.py --etapa universo --normalizacion-titulos unicode_v2 --salida resultados_exploratorios_unicode
```

**No ejecutar esa prueba como reemplazo del corpus actual sin una validación adicional**; es una ruta futura. Las decisiones manuales aprobadas se reconstruyen directamente por UID y son independientes del ID provisional de cada publicación.

## Salidas de auditoría

| Archivo | Contenido |
|---|---|
| `01_decisiones_bibliograficas.csv` | 791 alertas originales, decisión humana, fundamento, DOI/años e historial v9 |
| `02_aristas_fusion_aprobadas_NO_APLICAR.csv` | Pares de UID autorizados para una futura fusión; hay reiteraciones entre alertas |
| `03_restricciones_no_fusionar.csv` | Pares que deben quedar separados o fuera de fusiones parciales |
| `04_grupos_fusion_aprobados_NO_APLICAR.csv` | Grupos transitivos de decisiones de fusión, sin duplicar referencias anteriores; metadatos de origen en JSON |
| `05_correcciones_unicode_aprobadas.csv` | 249 falsos positivos, título original y versión normalizada Unicode |
| `06_enriquecimientos_editoriales.csv` | Información editorial verificada, sin sobrescribir los campos originales |
| `07_seguimientos_especiales.csv` | Decisiones y pendientes para 0182/0467/0519 |
| `08_cobertura_105_SIN_REINCORPORACION.csv` | Auditoría de procedencia y exclusión de los 105 registros |
| `09_prioritarios_15_PENDIENTES_CRIBADO.csv` | Selección para revisión temática humana futura, sin inclusiones nuevas |
| `10_pendientes_bibliograficos.csv` | Alertas sin dictamen (cero en el corte final) |
| `11_relaciones_no_fusionar.csv` | Vínculos entre publicaciones relacionadas pero distintas |
| `12_resumen_y_huellas.json` | Conteos, limitaciones, hash SHA-256 de entradas y salidas |

La carpeta `decisiones_aprobadas/` contiene la matriz original de 791 decisiones, la bitácora del chat, los seguimientos y la selección de revisión. El archivo `00_manifiesto_entradas_congeladas.json` contiene los SHA-256 de los seis CSV aprobados y de las tres instantáneas originales. Si cualquier archivo cambia, el script detiene la reproducción con un mensaje de error. **Para nuevas descargas de APIs deberá versionarse una nueva matriz de decisiones y volver a validar los UID**, en vez de sustituir silenciosamente los datos.

## Qué no se ha hecho

- No se han aplicado decisiones de deduplicación para recalcular el total de publicaciones únicas.
- No se ha decidido la reincorporación de los 105 registros, incluidos los 15 prioritarios.
- No se ha confirmado la naturaleza editorial de las versiones asociadas a `0467` y `0519`.
- No se han resuelto `0111`, `0500`, `0529` y `0534`.
- No se ha reejecutado un cribado temático multilingüe ni alterado el cribado v9.

Este procedimiento registra evidencia y **prepara restricciones** para aplicar la unificación más adelante. No equiparar el número de alertas aprobadas o aristas de fusión al número de artículos eliminados: existen varias alertas para una misma publicación y fusiones parciales con ediciones independientes.

**Paquete complementario:** el ZIP reproducible incluye las tres instantáneas de universo, la lógica del flujo unificado y los archivos de revisión, pero no reproduce las carpetas completas de todos los análisis v6-v9 ni las entradas históricas de base amplia; para esas etapas deben conservarse los archivos originales del proyecto.
