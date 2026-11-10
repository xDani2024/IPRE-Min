# Cribado del corpus unificado IPRE: nota metodológica

Cierre del 10 de noviembre de 2026. Complementa `README.md` y `GUIA_TECNICA.md`.

## Flujo aplicado (15.297 publicaciones únicas)

| Etapa | Evaluadas | Siguen | Excluidas |
|---|---|---|---|
| 1. Filtro amplio original (`screen_record`, sin modificar) | 15.297 | 7.473 | 7.824 |
| 2. Pertinencia operacional (Nivel 1, reglas + lectura dirigida) | 7.473 | 3.865 | 3.608 |
| 3. Revisión humana de 86 casos con información insuficiente | 86 | 72 | 14 |
| **Corpus final** | | **3.851 incluidas** | **11.446** |
| Núcleo de desempeño (A+B+C, subconjunto de las incluidas) | 3.851 | **584 IN** | 3.267 fuera del núcleo |

**Cómo se lee el resultado**
- **Decisión final:** es la del Nivel 1, corregida por la revisión humana. El núcleo es una columna (`decision_cribado_desempeno`) y un subconjunto; no excluye del corpus.
- **Hipótesis:** H1–H3 no se usaron como criterio de inclusión ni de exclusión.
- **Trazabilidad:** toda publicación tiene decisión, etapa, motivo, justificación y procedencia. Las columnas originales del corpus unificado se conservan sin cambios.

## Réplica del código original

- **Filtro amplio:** la función original se importó sin cambios. Cada publicación entra con una ficha armada así:
  - título unificado, o el alternativo latino en 2 casos con título no latino;
  - resumen unificado, o recuperado de otra base (38 casos);
  - unión de las palabras clave y topics de las tres bases;
  - concepts, que solo existen en OpenAlex.
- **Núcleo:** se reprodujeron las reglas v6, v7, v8 y v9. La réplica coincidió con lo archivado en:
  - v6: 4.735 de 4.735;
  - v8, en las reglas que no dependen de auditorías: 4.604 de 4.604;
  - v9: 2.280 de 2.281.
- **Decisiones previas:** no se reutilizaron (auditorías IA I02/I03/O05, decisiones humanas, cifras del piloto).

## Diferencias entre el código y los criterios documentados

1. El filtro amplio usa *concepts*, que solo existen en OpenAlex. Eso cambia 8 decisiones.
2. El requisito de resumen no se aplicó como exclusión: 215 publicaciones sin resumen se evaluaron con título, palabras clave y tipo.
3. La regex de contexto de v6 no reconoce «open-cut»; esos casos se resolvieron por lectura.
4. El código de la auditoría del 28-oct no está en el paquete; sus criterios se aplicaron en la lectura dirigida.
5. El Nivel 1 aplica las decisiones de alcance acordadas:
   - geotecnia, vibraciones y agua, solo con vínculo operacional;
   - componentes, solo de equipos de la mina;
   - plantas fuera;
   - contexto a cielo abierto central;
   - los procesos auxiliares no se excluyen por ser auxiliares.
6. Se reconstruyó la alerta de resumen compartido (53 casos entre las aceptadas).

## Procedencia de las decisiones (7.473 aceptadas)

| Procedencia | Incluidas | Excluidas |
|---|---:|---:|
| Regla confirmada por lectura de título | 1.997 | 2.926 |
| Lectura dirigida de título y resumen | 1.782 | 682 |
| Revisión humana | 72 | 14 |

**Control de omisiones del núcleo:** se leyeron 378 incluidas que tenían términos de desempeño en el título y estaban fuera del núcleo; 121 pasaron a IN.

## Revisión humana y validación

**Revisión de casos.** La autora revisó los 86 casos marcados: 36 sin resumen, 30 con resumen compartido y 20 con texto solo en otro idioma. Resultado: 14 excluidos, 12 al núcleo y 60 incluidos fuera del núcleo.

**Muestra de validación.** Muestra ciega de 100 publicaciones, 25 por estrato, con semilla 20261109.

| Estrato | Acuerdo en inclusión (IC 95 %) | Acuerdo en núcleo (IC 95 %) |
|---|---|---|
| E1 Excluidas en el filtro amplio | 0,84 (0,65–0,94) | — |
| E2 Excluidas por pertinencia | 1,00 (0,87–1,00) | — |
| E3 Incluidas fuera del núcleo | 0,72 (0,52–0,86) | 0,72 (0,49–0,88) |
| E4 Incluidas en el núcleo | 1,00 (0,87–1,00) | 0,80 (0,61–0,91) |

- **Kappa de Cohen:** 0,78 en inclusión (acuerdo sustancial) y 0,52 en núcleo (moderado).
- **Acuerdo de inclusión ponderado al corpus:** 0,86.

**Cómo se hizo la revisión.** Ambas planillas las revisó la autora con asistencia de un modelo de lenguaje, que propuso una clasificación inicial; ella verificó y modificó cada decisión. Como la asistencia y el cribado provienen de herramientas similares, la concordancia puede estar sobrestimada. Una submuestra revisada sin asistencia, por ejemplo por el profesor guía, permitiría medir el acuerdo entre revisores humanos.

## Límites que mostró la validación

1. **Recall del filtro amplio original.** En E1, 4 de 25 serían incluibles. Extrapolado, son unas 1.250 publicaciones (intervalo aproximado de 500 a 2.700).
   - Los cuatro casos fueron excluidos por «sin foco operacional suficiente»: tratan ventilación del rajo, explotación con dozer y tronadura, mapa geológico de gestión y largo de la línea de trabajo.
   - El vocabulario que falta en los diccionarios es sobre todo de procesos auxiliares y planificación, lo que podría sesgar el análisis hacia confirmar H3.
   - Hay 1.955 publicaciones excluidas solo por «sin foco» que nombran el cielo abierto en el título. Son el conjunto natural para una auditoría de recall.
2. **Precisión del núcleo.** En E4, 5 de 25 no cumplen A+B+C: el resumen anuncia beneficios o discute un problema, pero no informa un resultado de la tarea. Cuatro venían de la regla v8 confirmada por lectura. Aplicar la regla estricta de v9 no los separa bien, así que corregirlos exige releerlos con un criterio C explícito.
3. **Nivel 1 en las incluidas fuera del núcleo.** Hubo errores de lectura (estudio subterráneo, CFD de emisiones, levantamiento geológico, cancha de homogeneización) y dos desacuerdos de criterio todavía sin resolver:
   - estudios que solo miden precisión (volumen de la pila tronada, fragmentación): ¿se excluyen en el Nivel 1 o quedan incluidos con núcleo OUT, como se acordó?
   - modelos de planificación cuyo resultado es el VPN o un parámetro de diseño: ¿núcleo IN, o OUT como en el código original (regla O07)?
4. La lectura se hizo sobre título y resumen, no sobre texto completo.
5. Los conteos de Scopus y WoS previos a su deduplicación interna no están en los archivos de integración.

## Calibración opcional

Si se decide calibrar:
- auditar el recall del filtro amplio, como paso agregado y documentado;
- releer el núcleo con un criterio C escrito y estricto;
- resolver los dos desacuerdos de criterio.

Después se debe validar con una **muestra nueva**, porque la actual ya se usó para diagnosticar.
