# Protocolo de lectura del corpus incluido

Esta es la última etapa de la revisión bibliométrica: leer cada publicación del corpus incluido (3.851) y registrar en detalle su objetivo, metodologías, datos, indicadores, resultados y proceso. Con esa información se arma después el mapa de brechas por proceso.

Esta etapa responde a lo acordado en la reunión de noviembre:

- Primero se clasifica cada publicación de forma individual. Las agrupaciones se hacen después, a partir de lo leído.
- La lectura cubre las 3.851 publicaciones incluidas, no solo el núcleo.
- El análisis se organiza por proceso y actividad, no por equipo.
- Una publicación puede tener más de una metodología y más de un tipo de dato. Por eso, los totales de esas columnas pueden sumar más que el número de publicaciones.
- Cada agrupación incluye siempre una categoría «Otros», para no forzar clasificaciones.

## Reparto

El notebook `13_reparto_y_consolidacion.ipynb` divide el corpus entre los dos revisores y equilibra los grupos según núcleo y proceso candidato.

- **Proceso candidato:** se calcula con el diccionario de procesos del código v8. Solo sirve para repartir de forma pareja y nunca reemplaza la lectura.
- **Muestra común:** un 5 % del corpus lo leen ambos revisores, por separado y sin ver la lectura del otro. Esa muestra permite medir el acuerdo entre revisores.
- **Lotes:** cada revisor recibe sus publicaciones ordenadas en lotes de 50, con el núcleo primero.

## Qué se registra por publicación

| Columna | Qué escribir | Ejemplo |
| --- | --- | --- |
| `proceso` | El proceso principal que estudia la publicación. Se elige de la lista. | `acarreo` |
| `procesos_secundarios` | Otros procesos que también aborda, separados por `;`. | `carguio_excavacion` |
| `problema` | El tipo de problema. Se elige de la lista. | `asignacion_despacho` |
| `objetivo` | 1 o 2 oraciones, de hasta 50 palabras, con qué busca, qué problema aborda y en qué contexto (equipo, proceso, tipo de mina o mineral). | Resolver la asignación camión-pala con camiones de distinta capacidad y múltiples rutas, considerando incertidumbre en el rendimiento de palas y chancador |
| `metodologias` | Cada método con su detalle, separados por `;`: tipo de modelo o algoritmo, qué optimiza, software y cómo se valida. | `optimización robusta por escenarios en dos fases; programación entera binaria; comparación con la asignación actual de la mina` |
| `datos` | Tipo, fuente, tamaño o período y lugar, separados por `;`. | `datos operacionales de una mina de cobre (palas, chancador, flota heterogénea)` |
| `indicadores` | Lo que mide como desempeño o resultado, separado por `;`. Si no mide nada, `no aplica`. | `producción de palas (t/turno); costo operacional (USD/t)` |
| `resultados` | El hallazgo principal en 1 o 2 oraciones, con cifras si las informa. | La producción sube a 6.719–12.500 t/turno según la estrategia y el costo baja a 0,81–1,18 USD/t |
| `observacion` | Lo que no calza en las columnas anteriores o la razón de una duda. | `transporte ferroviario de rajo` |

La ficha tiene que ser lo bastante detallada para no volver a leer el resumen al agrupar. Si el resumen no entrega algún dato, se escribe `no informado`, sin completarlo con supuestos. La hoja «Ejemplos» de la planilla muestra el nivel de detalle esperado.

Al completar las columnas, hay que tener en cuenta lo siguiente:

- **Metodologías específicas:** escribir «MILP», «algoritmo genético» o «simulación de eventos discretos», no solo «optimización» o «simulación». La agrupación por familias se hace después.
- **Revisiones de literatura:** registrarlas como metodología `revisión de literatura` y como dato `literatura`.
- **Publicaciones sin resumen:** completar lo que permitan el título y las palabras clave, y anotar `sin resumen` en `observacion`. No se excluyen.
- **Proceso `otro`:** si la publicación trata un proceso que no está en la lista, elegir `otro` y escribir en `observacion` `otro: <nombre del proceso>`.
- **Proceso `mina_general`:** se usa para toda la mina sin un proceso unitario, como límite de rajo, secuenciamiento, programación de largo plazo o una evaluación energética o económica global.

### Listas

**Procesos:** `perforacion`, `tronadura`, `carguio_excavacion`, `acarreo`, `transporte_continuo`, `riego_control_polvo`, `caminos`, `abastecimiento`, `desague`, `mantenimiento_equipos`, `mina_general`, `otro`.

**Problemas:** `diseno`, `planificacion`, `asignacion_despacho`, `ejecucion_operacion`, `mantenimiento_confiabilidad`, `reemplazo_ciclo_vida`, `ambiente_seguridad`, `automatizacion_control`, `otro`.

Las dos listas vienen de los diccionarios del código v8. Solo se agregaron `mina_general` y `otro`, porque el corpus incluye planificación de toda la mina, y esa planificación no corresponde a un proceso unitario.

### Criterios de decisión

Estos criterios se acordaron después de probar el lote L002:

- **`diseno` o `ejecucion_operacion`.**
  - `diseno`: la publicación evalúa una alternativa antes de implementarla, por ejemplo diseñar, dimensionar, seleccionar o comparar tecnologías o sistemas. Va aquí aunque estime la productividad que tendría la alternativa, como al evaluar un sistema de trolley o mineros de superficie para una mina.
  - `ejecucion_operacion`: la publicación mide o mejora el desempeño de una operación que ya existe, como los tiempos de ciclo medidos o la productividad de la flota actual.
- **Dudas entre dos tipos de problema.** Se elige el más cercano según las definiciones y se anota la otra opción en `observacion` como `alternativa: <código>`. Ese formato permite contarlas al consolidar.
- **Proceso `otro`.** En `observacion` se escribe siempre `otro: <nombre del proceso>`, por ejemplo `otro: botaderos de estéril`. Por ahora no se crean códigos nuevos. Después de la calibración, con unos cinco lotes por revisor, se revisa la hoja «Resumen_otro» y se decide qué procesos tienen frecuencia suficiente para un código propio. Los candidatos vistos hasta ahora son botaderos de estéril, transporte no camión (ferroviario o por cable), minería highwall y relleno post-minería.
- **Evaluación global de la mina.** Una auditoría energética o una evaluación económica de toda la mina va en `mina_general`.
- **Posible fuera de alcance.** Si la publicación no trata operaciones a cielo abierto, por ejemplo un método subterráneo, el cierre o la rehabilitación, se clasifica igual y se anota `revisar alcance` en `observacion`. Esas publicaciones se revisan juntas al consolidar.
- **Datos no informados.** No se agregan datos que el resumen no entrega, como el país, el mineral o el tamaño. Se escribe `no informado`.
- **Varias observaciones.** Se separan con `;`. Si no hay ninguna, el campo queda vacío.

## Lectura asistida por IA

La lectura se hace con la IA que cada uno use, sea ChatGPT, Claude u otra, sin API. El procedimiento es el mismo para ambos y está en la sección 5 del notebook:

1. `exportar_lote('Joaquin', 3)` crea `ia_lotes/Joaquin_L003.txt`, con las instrucciones, la lista de códigos, dos ejemplos y las publicaciones pendientes del lote.
2. Se pega el texto completo en una conversación nueva de la IA, y la IA responde con un bloque JSON.
3. La respuesta se guarda en `respuestas_ia/Joaquin/` con el nombre del lote: `L003.txt` si se pegó el texto, o `L003.json` si la IA entregó un archivo.
4. `importar_respuestas('Joaquin', 'ChatGPT')` valida los códigos y escribe las lecturas en la planilla como `IA sin revisar`. El Excel tiene que estar cerrado mientras se importa. Si la IA dejó publicaciones sin responder, el notebook lo avisa y basta con exportar de nuevo el mismo lote.
5. El revisor revisa cada fila en Excel y cambia `fuente_lectura` a `IA revisada`.

Para que la lectura sea comparable entre revisores hay que cuidar cuatro cosas:

- **Una conversación nueva por lote.** En conversaciones largas, la IA arrastra criterios de los lotes anteriores.
- **La misma IA para ambos, de preferencia.** La herramienta usada queda anotada en `respuestas_ia/registro_importaciones.csv`.
- **La muestra común se lee sin IA.** El notebook no la exporta. Así, el acuerdo mide a los revisores y no al modelo.
- **Revisión por columna.** Revisar todas las filas en `proceso` y `problema`, porque de ahí salen los conteos. Comprobar que `metodologias` y `datos` sean concretos y no inventados.

La columna `fuente_lectura` indica cómo se hizo cada fila: `manual`, `IA revisada` o `IA sin revisar`. Las primeras publicaciones del núcleo ya vienen leídas con IA, marcadas como `IA sin revisar`, y quien las reciba debe verificarlas.

## Consolidación

Cuando ambas planillas están completas, la segunda parte del notebook hace lo siguiente:

1. Valida los campos obligatorios y los códigos.
2. Calcula el acuerdo entre revisores en la muestra común: porcentaje de acuerdo y kappa de Cohen, para el proceso y el problema.
3. Deja las discrepancias en una hoja para resolverlas juntos.
4. Genera el Excel unificado, con una fila por publicación, conteos por proceso, metodologías y datos.
5. Calcula cuántas temáticas corresponde agrupar en cada proceso, con la regla acordada:

| Publicaciones del proceso | Temáticas |
| --- | --- |
| Más de 1.000 | 12 |
| De 500 a 1.000 | 10 |
| De 200 a 499 | 8 |
| De 100 a 199 | 6 |
| Menos de 100 | 5 |

En cada proceso se agrega siempre la categoría «Otros». Las metodologías y los datos se agrupan después por temática, entre 3 y 5 categorías más «Otros», con su N.
