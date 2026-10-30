# Datos y código del estudio bibliométrico de minería a cielo abierto

Avance del 8 de octubre de 2026. Joaquín León, profesor guía José Joaquín Jara.

Este paquete permite entender de dónde vienen los datos, revisar los criterios y reproducir la integración de las versiones conservadas. La base amplia vigente tiene **4.735 registros**. El núcleo operacional **propuesto v9** contiene **419 IN y 4.316 OUT**. Se cerraron los **2.399 antiguos TC** como **57 IN y 2.342 OUT**. OUT se refiere a quedar fuera del núcleo, sin borrar la referencia de la base amplia.

## Para empezar

1. Extraer el ZIP completo, manteniendo las carpetas.
2. Leer `documentacion/Sintesis_IPRE_actualizada_reunion_20261008.pdf` para conocer las preguntas e hipótesis del profesor, el recorrido de los datos, criterios, resultados y tareas pendientes. La copia Word permite editar el avance.
3. Leer `GUIA_TECNICA.md` para conocer la consulta OpenAlex, las entradas y los puntos de ejecución.
4. Reproducir localmente desde la carpeta que contiene este README.

Windows PowerShell, con Python 3.10 o superior:

```powershell
py -3 00_reproducir_local.py
```

Linux/macOS:

```bash
python3 00_reproducir_local.py
```

Esta ruta usa solamente la biblioteca estándar de Python. **No requiere internet, API key ni instalar paquetes.** El filtro amplio hace comparaciones de similitud y puede tardar varios minutos. Los archivos originales se conservan; se escribe en `reproduccion_local/`. Para otra ejecución hay que elegir una carpeta nueva:

```powershell
py -3 00_reproducir_local.py --salida reproduccion_local_2
```

Al finalizar se esperan:

```text
Reproducción completada. IN: 419 | OUT: 4316 | TC: 0
```

El comprobante es `reproduccion_local/VERIFICACION_REPRODUCCION.json` y la matriz de consulta está en `reproduccion_local/resultado_v9/Matriz_4735_con_cierre_v9.csv`. La cadena completa se ejecutó antes de entregar este paquete y superó **16 comparaciones SHA-256 de salidas estables**. Su comprobante se incluye en `documentacion/Verificacion_cadena_completa.json`.

## Qué hay en cada carpeta

| Ruta | Contenido y función |
|---|---|
| `00_reproducir_local.py` | Orquesta filtro amplio, v6, v7, v8, cierre v9 y verificaciones en una carpeta nueva. |
| `01_extraccion_y_filtro/` | Los dos códigos originales separados: extracción OpenAlex y filtrado/conciliación; universo reconstruido, historial anterior y referencia vigente. |
| `02_cribado_v6/` | Motor multidimensional, auditoría dirigida de 48 fichas y matriz archivada. |
| `03_cribado_v8/` | Resolución v7 de 1.241 dudosos, sus auditorías y calibración P20; aplicación del criterio v8. |
| `04_cierre_v9/` | Matriz v8 congelada, 40 decisiones humanas conservadas, auditorías IA, criterios, código, verificaciones y salidas v9. |
| `05_descriptivos/` | Ocho figuras, sus recuentos y códigos para generar figuras y avance Word. |
| `documentacion/` | Avance PDF/Word, evidencia de reproducción y listado de exposición documentada al desarrollo/calibración. |
| `PROCEDENCIA_DEL_PAQUETE.json` | Origen de códigos, tamaños y límites de recuperación. |
| `MANIFIESTO_SHA256.json` | Integridad de los archivos incluidos. |

Los dos códigos de extracción y filtro se conservan sin cambiar su contenido. Contienen funciones de exploraciones anteriores; sus puntos de ejecución vigentes son `extraer()` y `main_integrado()`. La guía distingue las funciones utilizadas de las que no se invocan en esta corrida.

## Qué se reproduce y qué no

La ejecución original reportó **9.844 filas descargadas y 9.540 únicas**. El archivo de 9.540 y la respuesta JSON original de esa descarga no están en los materiales recuperados. Reconstruimos un universo de **9.534** uniendo los **4.735 incluidos y 4.799 excluidos** de la segunda etapa. El filtro reproduce exactamente las cuatro salidas CSV principales desde ese punto de partida. No podemos identificar aquí los seis registros retirados entre ambas deduplicaciones.

Las auditorías IA y los juicios humanos son **entradas congeladas**. Ejecutar los códigos reproduce reglas e integración de esos juicios, sin hacer nuevas llamadas a IA, sin releer artículos completos y sin consultar OpenAlex. Una descarga nueva es otra ruta: necesita una llave propia según el código archivado y crea una instantánea cuyos conteos pueden cambiar.

El historial de 4.773 se conserva para recuperar trabajo previo. Los 9.611 y 4.773 históricos no se presentan como escalones de la corrida vigente. El modo histórico `--fuente congelada` de `02_filtrar_y_unificar.py` espera otros archivos y **no es el modo de ejecución de este paquete**.

## Qué significan los resultados

- **IN:** candidato elegible para el núcleo operacional según esta propuesta.
- **OUT por foco:** la ficha se aleja del objeto operacional definido.
- **OUT documental:** la ficha no permite justificar inclusión. Puede requerir texto completo; no demuestra irrelevancia definitiva.
- **TC:** caso que requería revisión adicional, habitualmente de texto completo, por incertidumbre de la ficha. La nueva columna v9 no tiene TC; los TC y motivos históricos se conservan.

El piloto P20 y el lote H20 fueron calibraciones con sugerencias visibles. No constituyen validación independiente. H011 conserva su respuesta humana histórica TC, aunque la nueva sugerencia IA sea IN. H013 permanece IN por precedencia humana y mantiene aparte la discrepancia con IA. P04/P07 conservan su reconsideración humana IN.

Las figuras identifican si trabajan sobre 4.735 o sobre 419. Las etiquetas de equipo, proceso y foco son menciones automáticas no excluyentes, heredadas del filtro amplio. No confirman por sí solas el tema central ni prueban vacíos de investigación.

## Figuras y documento opcionales

No son dependencias del cribado. Para regenerarlos:

```powershell
py -3 -m pip install -r requirements_visuales.txt
py -3 05_descriptivos/24_generar_graficos.py
py -3 05_descriptivos/25_generar_avance.py
```

El segundo código produce Word. Para exportarlo a PDF puede utilizarse Word o LibreOffice. El PDF incluido ya está exportado y revisado.

## Siguiente trabajo del equipo

Precisar alcance e indicadores; auditar vocabulario, deduplicación y datos; diseñar revisión humana independiente con criterios v9 y control de exclusiones amplias; completar indicadores por estudio y depurar términos para los análisis bibliométricos. Las redes de co-citación/acoplamiento necesitan referencias enlazadas que esta extracción no conservó. El avance propone una distribución de tareas, sin asumir compromisos de la nueva colaboradora.

El paquete no incluye claves de acceso. Es un registro reproducible del desarrollo de la selección, no una afirmación de exactitud validada. El informe usa nombres de etapas y la expresión última revisión; las carpetas y campos conservan sus identificadores técnicos para permitir la reproducción. `documentacion/Orientaciones_profesor_20260902.md` registra la procedencia de las preguntas e hipótesis.
