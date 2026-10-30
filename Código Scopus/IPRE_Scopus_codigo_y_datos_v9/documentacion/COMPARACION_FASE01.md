# Comparación auditada: Joaquín (OpenAlex) → IPRE Scopus Etapa 01

Fuentes **aportadas por el usuario**: `IPRE_codigo(1).zip`, `IPRE_codigo_y_datos_v9/01_extraccion_y_filtro/01_extraer_openalex.py` (1.395 líneas) y `02_filtrar_y_unificar.py` (1.882 líneas). La comparación se basa **en esos archivos** y no presupone que los resultados finales de Scopus deban igualar OpenAlex.

## Subetapa 01A: extracción y deduplicación

| Paso del nuevo código | Procedimiento de Joaquín | ¿Qué es igual? | ¿Qué cambia y por qué? | Impacto / verificación |
|---|---|---|---|---|
| 1. Preparación | `01_extraer_openalex.py`, líneas 29–70 y punto de entrada `extraer()` 1342–1391 | Flujo API → metadatos → universo antes de cribado, nombre de campos comparable. | Endpoint y credencial Scopus; `requests` en lugar de `urllib` porque son API distintas. | Prueba HTTP de `COMPLETE` + resumen antes de descargar. |
| 2. Diez frases | `01_extraer_openalex.py`, líneas 35–46; `02_filtrar_y_unificar.py`, línea 1568 `FRASES_CONSULTA_ORIGINAL = OPEN_PIT_PHRASES[:10]` | **Exactamente diez términos**, mismo orden y escritura. | API OpenAlex usa una consulta OR; Scopus realiza diez consultas separadas y reúne el universo. | La suma por frase incluye duplicados y debe deduplicarse. |
| 3. Campos consultados | `build_context_filter()` del segundo script, líneas 871–874: `title_and_abstract.search.exact` | Se buscan términos solo en **título y resumen**; no se consulta `KEY` como criterio de búsqueda. | Scopus `TITLE-ABS({frase})`, con llaves de coincidencia exacta. Los motores de búsqueda son diferentes. | No asumir conteos iguales ni que `search.exact` ≡ `{frase}` en todos los casos. Registrar las consultas ejecutadas. |
| 4. Tipos y restricciones | `TECHNICAL_FILTERS`: `type:article\|review`, `has_abstract:true`, `is_retracted:false`, `is_paratext:false` (script 01 líneas 48–53) | `DOCTYPE(ar) OR DOCTYPE(re)`; se requiere un resumen real para pasar el filtro documental. | El resumen se exige después de recuperar registros. `is_retracted` e `is_paratext` quedan como **no verificados**, sin extrapolar un mapeo sin respaldo. | El corpus automático es **provisional** hasta auditar esos controles. |
| 5. Fecha/idioma/DOI | Los filtros originales **no** tienen año, idioma ni DOI obligatorio. | **Se respeta exactamente esa ausencia de restricciones.** | Ninguno, salvo la fecha de acceso a la base. | Las fechas editoriales futuras se marcan, no se eliminan sin acuerdo. |
| 6. Paginación y reanudación | `download_full_records` del script 01 líneas 904–944: cursor, checkpoints y 100 registros por página. | Cursor, páginas continuas, checkpoints, protección contra reanudación con otra configuración. | Scopus soporta `cursor=*`, usa otra estructura JSON, y el tamaño de página se fija en 25 para reducir el riesgo de incompatibilidades. | Los 10 recorridos deben completarse; abortar si falta cursor. |
| 7. Campos y normalización | `parse_work`, script 02 líneas 669–731: ID, DOI, título, resumen, autores, año, keywords, topics y concepts. | Campos equivalentes donde existen, mismo formato general para las funciones de clasificación, no se exige DOI. | `scopus_id` reemplaza `openalex_id`. `dc:description` reemplaza `abstract_inverted_index`. `topics` y `concepts` se mantienen vacíos porque no existe correspondencia demostrada. | Una clasificación puede variar por diferencias en metadatos. |
| 8. Deduplicación | `deduplicate`, script 02 líneas 1084–1286: DOI, ID, título normalizado/compacto, autor+año, similitud de resúmenes. | **Se reutiliza el mismo algoritmo y umbrales** y se conserva `duplicate_count`, ramas y DOI fusionados. | Únicamente se reemplazan etiquetas de `openalex_id` por `scopus_id` (también en nombres auxiliares). | Alertar sobre DOI distintos fusionados por títulos iguales y revisarlos manualmente. |

## Subetapa 01B: filtro amplio

| Paso del nuevo código | Procedimiento de Joaquín | ¿Qué es igual? | ¿Qué cambia y por qué? | Impacto / verificación |
|---|---|---|---|---|
| 9. 21 frases de clasificación | Script 02 líneas 38–60 `OPEN_PIT_PHRASES` contiene **21 frases**; `FRASES_CONSULTA_ORIGINAL` son solo las primeras diez. | Se mantiene el vocabulario ampliado de contexto para el cribado, **sin alterar la búsqueda de diez frases**. | La ampliación ya estaba en Joaquín, no es un cambio nuestro. | No confundir términos de recuperación con términos de relevancia. |
| 10. Vocabularios | `PROCESS_TERMS`, `EQUIPMENT_TERMS`, `FOCUS_TERMS`, `OPERATIONAL_SCOPE_TERMS`, `DIRECT_OPERATIONAL_TERMS`, `EXCLUSION_*`, `FINAL_*`. | Copias **exactas** del script 02, con rangos y SHA256 en `referencias_codigo.json`. | El texto de entrada tiene menos taxonomías automáticas porque Scopus no aporta `topics/concepts` OpenAlex. | Revisar una muestra de aceptados/excluidos por falsos positivos y negativos. |
| 11. Función de cribado | `screen_record`, script 02 líneas 734–856; `screen_records`, 859–868. | **Código de decisiones idéntico**. Incluye título, contexto, señales operativas, exclusiones y el motivo `auto_screen_reasons`. | Ninguno en la función. Cambian solo metadatos disponibles. | Test automatizado compara resultados de ambos módulos sobre la **misma ficha**. |
| 12. Salidas amplias | Script 02 `main_integrado()`, líneas 1779–1790 produce aceptados/rechazados. | Se generan aceptados y `excluidos_amplios_con_motivo.csv`, más matriz y manifiesto SHA256. | Aceptados se denominan `..._provisional` porque retractación/paratexto no están completamente verificados. | No presentar el corpus como final hasta revisión. |
| 13. Historial anterior | Script 02 líneas 1792–1867 concilia IDs OpenAlex del historial de 4.773. | Se conserva la lógica general de trabajar con archivos versionados y su procedencia. | **No se hereda** un juicio I/Q/G desde OpenAlex a Scopus sin una reconciliación documentada y revisión. | Evita trasladar etiquetas del otro corpus como decisiones propias de Scopus. |
| 14. Muestra y reproducibilidad | `muestra_exclusiones_amplias`, `nueva_muestra`, SHA256 por salida, `metadatos_y_flujo.json`. | Se crea muestra humana, alertas, hash por CSV, manifiesto y recuentos. | El muestreo de este primer notebook es deliberadamente **simple y determinista**; no pretende reproducir los cupos históricos I/Q/G usados en Joaquín. | Registrar diferencias de método de muestreo antes de una validación formal. |

## Límite de la equivalencia

**Lo que puede calificarse de idéntico:** los diez términos de recuperación, sin restricción de año/idioma/DOI, y las expresiones/código de los vocabularios y del filtro `screen_record` para una misma ficha ya normalizada.

**Lo que solo es funcionalmente equivalente o aproximado:** el motor de búsqueda, el esquema de tipos documentales, el resumen, el identificador, el enriquecimiento de metadatos, el filtro de retractación/paratexto, la paginación y la deduplicación aplicada a otras fichas bibliográficas.

**Lo que no debe hacerse:** exigir que el universo Scopus replique los 9.540/9.534 o 4.735 registros de OpenAlex, heredar los 419 IN del núcleo v9, afirmar que la tasa de aceptación del piloto representa la población, o usar la no verificación documental como confirmación de ausencia de retractación.

## Validaciones incluidas

`pruebas/test_sin_api.py`:
- Comprueba el **mismo** conjunto de vocabularios del filtro amplio.
- Importa como referencia el código original en modo solo lectura y comprueba que `screen_record()` produce la misma salida para una misma ficha.
- Reproduce deduplicación, conservación de diez consultas, separación piloto/completo y reanudación por cursor con respuestas simuladas.
- Demuestra que una descarga completa **no se presenta como filtro validado** si quedan controles bibliográficos pendientes.

Estos son **tests funcionales locales**, no pruebas de conexión en vivo a Scopus ni validación humana de resultados. La extracción real requiere API Key, acceso autorizado y comprobar que Scopus admite las consultas exactas mediante su API.
