# Guía técnica para revisar extracción, cribado y resultados

## 1 Puntos de entrada y separación de responsabilidades

Los motores archivados son scripts Python, basados en la biblioteca estándar. Se conserva su contenido para no reescribir retrospectivamente la metodología. Los dos primeros scripts contienen diccionarios y funciones de exploración anteriores que no se ejecutan necesariamente desde su bloque `if __name__ == '__main__'`.

| Código | Punto de entrada | Entrada de esta reproducción | Resultado |
|---|---|---|---|
| `01_extraccion_y_filtro/01_extraer_openalex.py` | `extraer()` | API OpenAlex y variable de entorno | Nueva instantánea; no se ejecuta en la reproducción local. |
| `01_extraccion_y_filtro/02_filtrar_y_unificar.py` | `main_integrado()` | Universo reconstruido e historial 4.773 | Filtro amplio 4.735/4.799 e historial conciliado. |
| `02_cribado_v6/codigo/06_screening_multidimensional.py` | Bloque principal | Base amplia conciliada y auditoría 48 | 393 IN, 3.101 OUT, 1.241 dudosos. |
| `03_cribado_v8/entrada/v7/11_resolver_dudosos.py` | Bloque principal | Matriz v6, cola, alertas y auditoría dirigida | 470 IN y 4.265 OUT. |
| `03_cribado_v8/15_aplicar_criterio_calibrado.py` | Bloque principal | Matriz v7 y piloto P20 conservado | 364 IN, 1.972 OUT, 2.399 TC. |
| `04_cierre_v9/22_cerrar_TC.py` | Bloque principal | Matriz v8, auditorías IA y juicios P/H | 419 IN y 4.316 OUT propuestos. |
| `04_cierre_v9/23_verificar_cierre.py` | Bloque principal | Entradas y salidas v9 | Comprobaciones de integridad y cobertura. |
| `05_descriptivos/24_generar_graficos.py` | Ejecución del archivo | Matriz completa v9 | JSON de recuentos y ocho PNG. |
| `05_descriptivos/25_generar_avance.py` | Ejecución del archivo | Recuentos y PNG | Avance Word. |

`00_reproducir_local.py` enlaza los motores y copia en su carpeta de salida las estructuras que esperan las etapas v6–v9. Así no hay que adaptar rutas en los motores archivados ni sobrescribir sus resultados. Una carpeta de salida no vacía produce un error intencional.

## 2 Consulta que origina la cohorte

Endpoint: `https://api.openalex.org/works`

Filtro exacto del código archivado:

```text
title_and_abstract.search.exact:"open pit mining"|"open-pit mining"|"open pit mine"|"open-pit mine"|"surface mining"|"surface mine"|"opencast mining"|"open-cast mining"|"open cut mining"|"open-cut mining",type:article|review,has_abstract:true,is_retracted:false,is_paratext:false
```

La consulta combina expresiones de contexto y filtros técnicos. **No exige DOI, año ni idioma específico.** No incorpora todos los nombres de equipos a esta consulta general; su reconocimiento ocurre después en el filtro local. La selección es una operacionalización del alcance que requiere evaluar omisiones.

Paginación: `per_page=100`, cursor inicial `*`, avance con `meta.next_cursor`. Se utiliza `select` para recuperar los campos:

```text
id,doi,title,publication_year,publication_date,type,language,cited_by_count,abstract_inverted_index,authorships,primary_location,keywords,topics,concepts
```

Se reconstruye `abstract` ordenando posiciones del índice invertido. Los campos de autores, instituciones y conceptos se aplanan en el CSV. Los valores se normalizan en `parse_work()` y otras funciones del motor. ID y DOI son llaves de conciliación; el número de citas es un atributo bibliográfico fechado por la instantánea, no una evaluación operacional.

El nombre `descarga_sin_deduplicar.jsonl` se refiere a filas parseadas antes de deduplicar, **no a la respuesta JSON íntegra de la API**. La extracción original de esta cohorte y su CSV de 9.540 no están disponibles en el paquete.

El código guarda archivos de reanudación, metadatos, consulta, tamaños y hashes. Una interrupción solo se reanuda si conserva ambos archivos temporales. Se rechaza una carpeta que ya contenga resultados finales para evitar mezclar instantáneas.

## 3 Reproducción local de la instantánea disponible

El universo reconstruido de `01_extraccion_y_filtro/datos_reconstruidos/universo_openalex.csv` tiene 9.534 filas con el esquema `RAW_FIELDS`: se unieron incluidos y excluidos archivados de la segunda etapa y se conservaron sus metadatos bibliográficos.

SHA-256 del universo incluido:

```text
ab00259d1d00e93f43b32e27aece05ab279df74fb3e13d112f59983e4ed7de1a
```

`open_pit_extraction_metadata.json` identifica expresamente la reconstrucción y conserva aparte los metadatos reportados por la extracción. No se presenta como archivo original de 9.540.

La corrida de septiembre reportó 9.844 filas, 9.540 únicas y un total API de 9.817. Los seis registros retirados entre 9.540 y 9.534 no pueden identificarse aquí. La diferencia entre total API y filas recogidas tampoco se ha auditado. Estas cantidades se registran separadamente y no se fuerza una explicación sin los archivos faltantes.

Comando de reproducción completa:

```powershell
py -3 00_reproducir_local.py
```

No es necesario correr primero la extracción. El runner ya pasa al filtro `--entrada`, `--historial` y `--salida` con las rutas correspondientes. El modo de entrada es `archivos_nuevos` aunque los datos sean esta instantánea reconstruida; `congelada` es un modo histórico que espera otros archivos no incluidos.

La comprobación completa coteja las cuatro salidas CSV principales del filtro amplio, la matriz v6, tres salidas v7, la matriz v8 y siete salidas v9: **16 comparaciones byte a byte mediante SHA-256**. Fechas de ejecución y hashes de ubicaciones auxiliares de una nueva corrida no se usan como criterio de igualdad. La matriz v8 regenerada coincide con su huella fijada:

```text
66ca3ea1ec0304bcf756de9b10374431c3666ffafc6e120cb92186475f371360
```

La prueba de esta entrega se documenta en `documentacion/Verificacion_cadena_completa.json`. El resultado es una integración reproducible de evidencias congeladas, sin garantía de equivalencia semántica con otra lectura humana o de IA.

## 4 Deduplicación y recuperación del trabajo anterior

`deduplicate()` combina ID, DOI y correspondencias de metadatos. Para resúmenes muy similares usa `difflib.SequenceMatcher` con umbral 0.985 y controles de año/autor. Algunas rutas también exigen semejanza de título >= 0.80. Las condiciones completas y prioridades están en el código; los umbrales no justifican por sí solos tratar dos registros como una misma obra.

Los resúmenes coincidentes con metadatos incompatibles pueden generar alertas en vez de una fusión. Deben examinarse como problemas bibliográficos separados de la pertinencia del estudio. El filtro temático reconoce contexto, procesos, equipos y señales excluyentes; registra el motivo en `auto_screen_reasons`.

La conciliación con `cribado_anterior_4773.csv` primero usa IDs y después correspondencias bibliográficas conservadoras. Se documentan **18 pares de IDs** en `correspondencias_ids_openalex.csv`. No se cuentan ambos identificadores como artículos nuevos. Las etiquetas históricas I/Q/G y sus motivos se heredan como antecedentes provisionales; no se convierten en validación humana.

Las cuatro salidas archivadas utilizadas como referencia son `corpus_general_aceptado.csv`, `excluidos_amplios_con_motivo.csv`, `corpus_unificado_con_historial.csv` y `correspondencias_ids_openalex.csv`.

## 5 Cómo se obtuvo el núcleo operacional

El filtro amplio responde a pertenencia al ámbito general. Las etapas v6–v9 responden a elegibilidad para el núcleo de evaluación operacional. Cada versión agrega columnas o propuestas separadas; la base amplia mantiene todos sus registros.

El criterio calibrado requiere:

- **A:** contexto a cielo abierto y equipo o tarea reconocible.
- **B:** evaluación propia, caracterización, comparación, intervención o modelación del equipo/tarea.
- **C:** un resultado vinculado a esa evaluación: producción, tiempo, esperas, disponibilidad, utilización, consumo, costo, frecuencia/distancia o caudal.

Se admiten resultados modelados y caracterizaciones de partida. Las tareas auxiliares pueden ser elegibles por su propio resultado. No basta una promesa de mejora, un indicador de precisión de un algoritmo, una propiedad material aislada ni una capacidad nominal sin evaluación de la tarea.

El código v9 combina reglas de texto y vínculos entre tarea, indicador y resultado, lecturas dirigidas y precedencia humana. `04_cierre_v9/Cierre_TC_v9_criterios_y_resultados.md` explica las reglas y excepciones; los JSON de auditoría conservan decisiones, motivos y evidencia textual. No hay servicio de IA llamado por estos scripts.

| Origen v8 | IN propuesto v9 | OUT propuesto v9 | Total |
|---|---:|---:|---:|
| IN | 362 | 2 | 364 |
| OUT | 0 | 1.972 | 1.972 |
| TC | 57 | 2.342 | 2.399 |
| Total | 419 | 4.316 | 4.735 |

Los 57 IN nuevos son 56 con evidencia en la ficha y 1 por precedencia humana. Los OUT de los antiguos TC son 616 por foco y 1.726 documentales. Dentro de estos últimos, 1.694 tienen evidencia operacional insuficiente, 22 fuente no fiable y 10 contexto insuficiente.

**Cobertura real de revisión:** barrido computacional de los 2.399 TC; auditoría semántica directa IA de 118 TC y una ficha complementaria H011. Los 57 nuevos IN fueron leídos en título/resumen; no se revisaron individualmente los 2.399 textos completos. Tampoco se auditó nuevamente el conjunto de 362 IN heredados en este cierre. Las auditorías anteriores de 48 fichas v6 y 68 v7 se preservan como entradas, sin presentarlas como nuevas lecturas.

## 6 Registro humano y calibración

Hay 40 IDs humanos: P01–P20 y H001–H020. Se conservan sugerencia previa, motivo, respuesta humana e historia disponible. Los ejercicios tenían sugerencias visibles. No estiman sensibilidad, especificidad ni exactitud del sistema de selección.

P04 y P07 mantienen la reconsideración IN. H003/H015 quedan OUT según su respuesta humana, aunque v8 fuera IN. H013 mantiene IN humano y OUT documental IA en columnas diferentes. H011 mantiene TC en la respuesta humana histórica y recibe una sugerencia IA IN por su evaluación de bombeo; esta lectura no afirma validación del software propuesto.

La unión documentada de desarrollo, calibración y lecturas directas contiene **260 IDs**, dejando **4.475** registros amplios fuera de esa unión. El listado se incluye en `documentacion/IDs_desarrollo_y_calibracion_v9.csv`. Es un marco potencial para diseñar revisión independiente, no una muestra ya validada. De la muestra v8 de 180 quedan 159 fuera de esa exposición documentada; sus pesos anteriores no se trasladan automáticamente a v9.

El diseño futuro debe contrastar IN, OUT por foco y OUT documentales. El control de los 4.799 excluidos amplios es separado y necesario para evaluar omisiones antes del núcleo.

## 7 Campos y resultados para abrir primero

Archivo principal: `04_cierre_v9/salida/Matriz_4735_con_cierre_v9.csv`.

| Campo o archivo | Uso |
|---|---|
| `openalex_id`, `doi`, `title`, `abstract`, `year` | Identidad y ficha bibliográfica congelada. |
| `auto_process_tags`, `auto_equipment_tags`, `auto_focus_tags`, `equipment_title_tags` | Menciones automáticas no excluyentes; deben cotejarse con el diccionario y el texto. |
| Campos v6/v7/v8 | Decisiones y antecedentes conservados. Sus nombres completos están en la cabecera de la matriz. |
| `decision_nucleo_v9_propuesta` | Decisión integrada propuesta del núcleo actual. |
| `origen_v9`, `regla_cierre_v9`, `motivo_cierre_v9` | Procedencia y justificación de la nueva propuesta. |
| `disposicion_documental_v9` | Separa foco y limitación de la evidencia. |
| `decision_solo_IA_v9`, `decision_humana_conservada_v9` | Distinguen sugerencia IA de juicio humano registrado. |
| `IN_propuesto_v9.csv` | 419 candidatos IN. |
| `OUT_propuesto_v9.csv` | 4.316 fuera del núcleo; continúan en la base amplia. |
| `Decisiones_2399_TC_v9.csv` | Motivos y evidencias de los antiguos TC. |

Las figuras se generan de la matriz completa y su subconjunto `decision_nucleo_v9_propuesta == IN`. Las etiquetas heredadas pueden ser incidentales, superponerse o faltar por vocabulario. Cada figura declara su denominador. La serie principal por año cubre 2000–2025 y presenta aparte los años anteriores, 2026 parcial y fechas faltantes.

El campo de citas es un total, no una lista de enlaces a trabajos citados. No se seleccionó `referenced_works`. Las redes de co-citación/acoplamiento requieren enriquecimiento. Autores e instituciones aplanados no preservan toda la estructura necesaria para desambiguación o redes de colaboración.

## 8 Si se decide hacer una extracción nueva

Esta ruta consulta la API y crea otros datos. El código archivado exige `OPENALEX_API_KEY`; la llave no se incluye. La documentación del servicio debe comprobarse antes de modificar la consulta, ya que la API y su cobertura pueden cambiar.

Desde la raíz del paquete, este comando PowerShell pide la llave con entrada oculta y la pasa al proceso hijo, sin guardarla en el código ni imprimirla:

```powershell
py -3 -c "import getpass,os,subprocess,sys; os.environ['OPENALEX_API_KEY']=getpass.getpass('OpenAlex API key: '); subprocess.run([sys.executable,'01_extraccion_y_filtro/01_extraer_openalex.py','--output-dir','nueva_extraccion_YYYYMMDD'],check=True)"
```

Elegir una fecha real y una carpeta nueva. Luego filtrar esa nueva instantánea:

```powershell
py -3 01_extraccion_y_filtro/02_filtrar_y_unificar.py --entrada nueva_extraccion_YYYYMMDD --salida nuevo_filtro_YYYYMMDD
```

La salida se compara por IDs, consulta, fecha y diferencias bibliográficas con la instantánea vigente. No se introduce en los motores v7–v9 fijados a 4.735: una nueva cohorte exige revisar sus entradas, auditorías y huellas, y documentar una versión nueva. Durante esta entrega no se hizo una llamada nueva a OpenAlex, por lo que no se afirma una prueba de extracción en vivo.

## 9 Qué debe auditar la revisión computacional

Revisar cobertura de consulta y sinónimos, normalización del resumen, complejidad de deduplicación, manejo de homónimos y metadatos incompatibles, casos positivos/negativos de cada regla y precedencia de auditorías. Mantener pruebas basadas en comportamiento y evidencia por ID cuando se cambie una regla.

Antes del artículo, completar objeto central, indicador, método, equipo/tarea, etapa de decisión y si el resultado fue observado o modelado. Registrar la versión real de cada herramienta de IA y prompts en las nuevas etapas. Los registros exactos del modelo/prompts anteriores no están completos y no se inventan retrospectivamente.

Cualquier cambio genera otra propuesta y un registro de diferencias, sin reescribir respuestas humanas ni tratar la calibración visible como validación ciega.

## 10 Referencias y fuente técnica

- Donthu et al. (2021), *How to conduct a bibliometric analysis: An overview and guidelines*. DOI: https://doi.org/10.1016/j.jbusres.2021.04.070
- Aria y Cuccurullo (2017), *bibliometrix: An R-tool for comprehensive science mapping analysis*. DOI: https://doi.org/10.1016/j.joi.2017.08.007
- Documentación oficial OpenAlex consultada el 8 de octubre de 2026: https://help.openalex.org/api/searching/, https://help.openalex.org/api/authentication/ y https://help.openalex.org/api/paging/.

Las publicaciones metodológicas fueron adjuntadas al proyecto. Los ejemplos de royalties y minerales críticos orientan técnicas y presentación, pero sus mapas no son resultados de esta cohorte.
