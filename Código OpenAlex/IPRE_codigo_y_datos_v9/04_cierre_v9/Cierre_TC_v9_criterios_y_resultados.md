# Cierre documental v9: criterios, resultados y trazabilidad

**Proyecto:** núcleo de desempeño operacional de equipos y tareas de minería a cielo abierto. **Corte de esta etapa:** 8 de octubre de 2026. **Versión:** `v9_cierre_binario_documental_20261008_1`.

## Resultado de la etapa

Se asignó una propuesta IN/OUT a los **2.399 registros TC de v8**, sin retirar registros de la base amplia. La columna `decision_nucleo_v9_propuesta` no contiene TC. Esto cierra la disposición documental de esta versión; no elimina la incertidumbre científica de fuentes insuficientes ni convierte el cribado en una revisión de texto completo.

| Estado de los antiguos TC | Registros | Sustento |
|---|---:|---|
| IN con evidencia operacional en la ficha | 56 | Título/resumen y lectura directa IA |
| IN por precedencia del juicio humano previo | 1 | H013; propuesta IA discrepante conservada |
| OUT por foco | 616 | Reglas documentales y auditorías directas identifican otro foco |
| OUT documental | 1.726 | No se justifica inclusión con evidencia congelada disponible |
| TC en la propuesta v9 | 0 | Cobertura comprobada por ID |
| **Total** | **2.399** | **Un único resultado propuesto por registro** |

Los OUT documentales se desglosan en **1.694 por evidencia operacional insuficiente**, **22 por fuente no fiable** y **10 por contexto no acreditado**. Los primeros 1.694 suman dos familias de reglas equivalentes, computacionales y de auditoría directa. Estas exclusiones son decisiones conservadoras de esta versión, no pruebas de ausencia de desempeño operacional en el artículo completo.

## Cómo cambia la base propuesta

| Propuesta v8 | IN v9 | OUT v9 | Total |
|---|---:|---:|---:|
| IN | 362 | 2 | 364 |
| OUT | 0 | 1.972 | 1.972 |
| TC | 57 | 2.342 | 2.399 |
| **Total v9** | **419** | **4.316** | **4.735** |

Las dos propuestas v8 IN que pasan a OUT en la nueva columna corresponden a **H003 y H015**, por sus decisiones humanas OUT ya recibidas. No son nuevas exclusiones automáticas. Todas las columnas originales v8 permanecen intactas, incluido su IN histórico. Fuera de esas integraciones humanas y los antiguos TC, no se cambió la propuesta de los demás registros.

La base amplia continúa teniendo 4.735 registros. Los gráficos descriptivos anteriores calculados sobre esa base siguen representando los 4.735, y no los 419 IN de v9. Este cierre no recalcula esos gráficos ni convierte su denominador en el del núcleo.

## Criterio de elegibilidad aplicado

La inclusión propuesta por IA exige evidencia positiva conjunta de:

1. **Contexto:** evaluación pertinente a minería a cielo abierto, superficial o cantera. Una mención superficial en antecedentes de un estudio subterráneo no basta.
2. **Tarea/equipo:** actividad operacional reconocible, principal o auxiliar; por ejemplo, carguío, acarreo, excavación, perforación, tronadura, transporte por correa, mantenimiento de caminos, riego o desagüe.
3. **Evaluación y resultado propios:** productividad/producción, tiempos y esperas, disponibilidad/utilización del equipo, consumo energético o de combustible, costo de tarea, distancia/frecuencia, carga transportada o caudal/tiempo de bombeo vinculados a la evaluación del estudio.

Se aceptan caracterizaciones de la operación existente, comparaciones analíticas y resultados de simulación. No se exige demostrar una mejora ni medir siempre en terreno; sí se distingue una evaluación realizada de un beneficio deseado. Los resultados modelados no se presentan como mejoras implementadas en campo.

Las tareas auxiliares son elegibles por su propio desempeño, sin obligarlas a demostrar además producción de mineral. La cifra nominal de una bomba/camión, una variable de entrada o una meta de producción no son por sí mismas resultados de evaluación. Una descripción de sensores que miden caudal tampoco equivale a un resultado reportado de bombeo.

El desempeño de un componente puede sustentar IN cuando se vincula explícitamente con disponibilidad, tiempo, producción, consumo o costo del equipo/tarea. Resistencia de soldadura, desgaste de una pieza o precisión de un predictor sin ese vínculo no bastan. Una revisión de literatura puede conservarse como referencia en la base amplia, pero no como evaluación primaria de este núcleo.

## Qué se hizo realmente

Se utilizó la matriz congelada v8 de 4.735 registros como única fuente bibliográfica nueva para este cierre. Se procesaron computacionalmente los títulos/resúmenes de **todos los 2.399 TC**, conservando los textos y las etiquetas previas. El código usa reglas explícitas, no un score oculto: contexto, relación tarea-indicador, evidencia de evaluación/resultados, exclusiones por foco y disposición documental de cierre.

Se realizó además una **lectura semántica directa por IA de 118 antiguos TC**, seleccionados por las inclusiones candidatas y por riesgo de omisión en exclusiones. Se verificaron todas las 57 nuevas propuestas IN, incluidos estudios recuperados del barrido y el caso humano H013. La revisión de exclusiones priorizó títulos de desempeño y registros antes incluidos en v7; no fue una muestra probabilística. H011 recibió una lectura complementaria fuera de los antiguos TC. El total de fichas con lectura directa nueva es **119**, de las cuales 118 pertenecen al grupo de 2.399.

No se obtuvo texto completo nuevo, no se verificaron externamente los resultados numéricos y no se añadieron respuestas humanas. El resto de los TC se cerró mediante reglas y criterio conservador documental, sin afirmar una lectura semántica individual de esos artículos. Las categorías de foco generadas por reglas son propuestas auditables, no una certificación de ausencia de resultados operacionales.

Las reglas y auditorías se ajustaron durante esta etapa; el protocolo v9 es una decisión metodológica posterior a v8. No debe describirse en un paper como criterio preregistrado o aplicado desde la extracción inicial. El archivo de auditoría conserva los motivos y citas finales, no un historial completo de todos los borradores internos.

Las lecturas IA proceden del asistente Codex de esta sesión. No se utilizó una API externa ni se conserva un identificador exacto de versión del modelo que permita repetir la generación semántica. Por eso se preservan sus adjudicaciones como entrada congelada para reproducir la integración.

## Decisiones humanas conservadas y excepciones

Se preservaron las **40 decisiones humanas actuales** y los motivos, sugerencias visibles y fundamentos previos disponibles en su registro. P04 y P07 conservan la reconsideración IN. Los juicios humanos previos IN/OUT tienen prioridad en la nueva propuesta integrada.

| Ficha | Juicio humano conservado | Nueva disposición propuesta | Explicación |
|---|---|---|---|
| H013 — W2380999572 | IN | IN | La ficha solo afirma beneficio económico general; IA propone OUT documental, pero prevalece el IN humano y se conserva la discrepancia. |
| H003 — W864986546 | OUT | OUT | Se integra la exclusión humana por foco ambiental; el IN computacional v8 sigue visible. |
| H015 — W4408093925 | OUT | OUT | Se integra la exclusión humana por falta de desempeño operacional directo; se conserva el IN v8. |
| H011 — W2031061065 | TC histórico | IN sugerido por IA | El desagüe existente reporta volumen anual bombeado y agua retirada por tonelada. Se incluye por caracterización operacional de partida; no se afirma que el sistema informático nuevo esté validado. |

En H011 se conserva **TC como respuesta humana histórica**. Su nueva sugerencia IA es binaria IN y su propuesta integrada sigue siendo IN, como ya proponía v8. Esto no atribuye al usuario una confirmación humana nueva. Por tanto, cero pendientes de propuesta no significa cero TC en el archivo histórico de respuestas humanas.

Esta calibración mostró sugerencias de IA; sus acuerdos no son exactitud, sensibilidad o especificidad del sistema. No se usa el grupo de 118 auditorías como validación independiente ni para extrapolar una tasa de error a toda la base.

## Registro por ID y reproducibilidad

Cada antiguo TC tiene ID OpenAlex, título/resumen original, DOI disponible, versiones previas, propuesta nueva, regla, motivo, fragmento textual, origen computacional o lectura directa, tipo de disposición documental, juicio humano disponible y señal de consulta de texto completo. Para H013 se conservan separadamente la propuesta IA OUT y la propuesta integrada IN.

Los códigos `22_cerrar_TC.py` y `23_verificar_cierre.py` se ejecutan sin red, sin API key y sin dependencias externas. Reproducen las propuestas integrando las auditorías semánticas conservadas; no generan esas auditorías nuevamente. La entrada congelada tiene SHA-256:

`66ca3ea1ec0304bcf756de9b10374431c3666ffafc6e120cb92186475f371360`

Se verificaron cobertura exacta de 2.399 IDs, unicidad de los 4.735, ausencia de TC en la propuesta, motivos/evidencias no vacíos, citas de auditoría presentes en las fuentes, preservación de todas las columnas v8 y de las 40 decisiones humanas, y lectura directa para cada nuevo IN. Una ejecución en carpeta independiente reprodujo los siete archivos de salida byte a byte. La matriz v8 original permanece intacta.

## Cómo describir esta etapa en la publicación

> Sobre la matriz congelada se efectuó un cierre documental asistido de 2.399 registros previamente indeterminados. Se aplicaron reglas reproducibles sobre títulos y resúmenes y un criterio conservador de inclusión basado en evidencia positiva de desempeño operacional; las exclusiones por evidencia insuficiente se registraron separadamente de las exclusiones por foco. Se auditó directamente con IA un subconjunto dirigido de 118 fichas, incluidas todas las nuevas inclusiones, y se conservaron con precedencia los juicios humanos binarios de la calibración previa con sugerencias visibles. La propuesta integrada contiene 419 registros y ninguna decisión indeterminada, sin que ello constituya validación humana independiente o revisión de texto completo.

La frase identifica el procedimiento realizado y su alcance. No permite afirmar que los 2.399 artículos fueron leídos íntegramente ni que los 4.316 OUT del núcleo carecen definitivamente de pertinencia. Si se evalúa posteriormente la calidad del cribado, deberá incluirse la posibilidad de omisiones entre OUT documentales; el cierre binario actual no aporta esa estimación.
