# Guía técnica del cribado del corpus unificado

## 1 Puntos de entrada y separación de responsabilidades

Los scripts del cribado usan la biblioteca estándar de Python. Las excepciones son `07`/`08`, que necesitan openpyxl, y las figuras de `09` y `10`, que necesitan matplotlib, y el informe de `11`, que necesita python-docx. Cada script se puede ejecutar por separado:
- sus rutas por defecto apuntan a las carpetas vecinas de este paquete;
- `--help` muestra los argumentos;
- `00_reproducir_local.py` los encadena con rutas explícitas hacia una carpeta nueva.

| Código | Entrada | Resultado |
|---|---|---|
| `01_filtro_amplio/01_aplicar_filtro_amplio.py` | Corpus unificado, procedencia (24.152 registros), universo OpenAlex (concepts) y `screen_record()` original | 7.473 aceptadas y 7.824 excluidas; sensibilidad sin concepts. |
| `02_nucleo_desempeno/02_aplicar_reglas_v6_a_v9.py` | Aceptadas y motores v6, v7, v8 y v9 | Decisión por regla de cada versión, con evidencia y alerta de resumen compartido. |
| `03_pertinencia_operacional/03_proponer_reglas_nivel1.py` | Aceptadas, reglas del núcleo y diccionarios originales | Código de regla de Nivel 1 (propuesta IN/OUT o grupo de lectura). |
| `04_integracion_final/04_integrar_decisiones.py` | Etapas 1–3 y `entrada/lectura_dirigida/` | Archivos 01–05. |
| `04_integracion_final/05_generar_cifras_prisma.py` | Procedencia, `08_resumen_validacion.json` y 01 | `06_prisma.json`. |
| `04_integracion_final/06_verificar_integracion.py` | Corpus unificado, 01–06 y archivos de lectura | `Verificacion_integridad.json` (14 comprobaciones). |
| `05_cierre_revision/07_preparar_planillas.py` | 01, resúmenes de la etapa 1 y `entrada/traducciones_es.json` (traducción al español con IA, entrada congelada) | Planillas 01 y 02 y la clave 03 (semilla 20261109). No sobrescribe planillas existentes. |
| `05_cierre_revision/08_aplicar_revision_y_concordancia.py` | 01 y planillas completadas | Concordancia y **corpus final** (01–05). El orquestador vuelve a aplicar `05` y `06` sobre esta salida. |
| `06_descriptivos/09_descripcion_bibliometrica.py` | 02 (cerrado si existe) y universos por base | Tablas, redes, figuras y `Resultados_descriptivos.json`. |
| `06_descriptivos/10_generar_graficos_informe.py` | Salidas archivadas del cribado y tablas de 09 | `Resultados_informe.json` y ocho figuras en `graficos_informe/` (matplotlib). |
| `06_descriptivos/11_generar_informe.py` | `Resultados_informe.json` y `graficos_informe/` | Informe Word en `documentacion/` (python-docx). |

Las rutas de los universos por base se leen de `integracion_corpus/resultados_validados/universo/08_resumen_validacion.json`. Así, el cribado usa exactamente las instantáneas de la integración.

## 2 Adaptaciones del flujo original al corpus unificado

Solo se adaptó lo que exige la estructura distinta de los datos. Las reglas no se cambiaron.

**Fichas (etapa 1)**
- Título: el unificado. Si no está en alfabeto latino, se usa el alternativo latino de otra base (2 casos).
- Resumen: el unificado o el recuperado de otra base (38).
- Palabras clave y topics: la unión de las tres bases.
- Concepts: solo de OpenAlex.
- Tipo: `review` si alguna base lo marca así.
- Idioma: `en` si alguna base lo indica.

**Concepts**
- El filtro amplio los usa, pero solo existen en OpenAlex.
- La columna `sensibilidad_sin_concepts` muestra que cambian 8 decisiones.

**Alerta de resumen compartido**
- v6 dependía de un archivo de alertas que no existe para esta cohorte.
- Se reconstruyó la misma alerta: un resumen idéntico en publicaciones con similitud de título menor que 0,80.

**v8**
- Se reproduce el bucle principal.
- Se omiten las ramas I02, I03 y O05, porque dependen de auditorías IA previas indexadas por ID OpenAlex de otra cohorte.

**Nivel 1**
- Es un nivel agregado, no presente en el flujo original. Aplica las decisiones de alcance acordadas: vínculo operacional, componentes, plantas, contexto central, revisiones, idioma y procesos auxiliares.
- Usa los diccionarios de los motores, más marcadores de vínculo operacional tomados de las métricas de v7/v8/v9.

## 3 Decisiones de lectura dirigida

Los archivos de `04_integracion_final/entrada/lectura_dirigida/` son entradas congeladas. Cada línea tiene la forma:

```text
<índice> <decisión> <código> <motivo breve>
#DEFAULT <decisión> <código> <motivo>      (decisión para los índices no listados)
```

**Cómo se interpreta el índice**
- Es la posición, en base 0, dentro del grupo ordenado por `id_publicacion`.
- `n1_L00.txt` usa claves `v8:i` / `v9:i` sobre los candidatos al núcleo.
- `nucleo_rescate.txt` se refiere a la lista de `nucleo_rescate_candidatos.txt`.

**Grupos de archivos**

| Archivo | Grupo |
|---|---|
| `n1_<código>.txt` | Grupo de Nivel 1 con ese código de regla (p. ej. `N1_O03`). |
| `nucleo_v8.txt` | Excepciones OUT a los IN por regla v8. |
| `nucleo_v9.txt` | Lectura de los TC que la regla v9 propone IN. |
| `nucleo_rescate.txt` | Lectura de 378 incluidas con términos de desempeño, para controlar omisiones. 121 pasan a IN. |

**Códigos de decisión**
- Nivel 1:
  - `I` (incluida). Lleva un código interno de motivo de lectura (p. ej. `EQUIPO`, `PLAN`), que no se exporta: no es una etiqueta temática.
  - `O` (excluida) con un código `F_*`.
- Núcleo: `NI_A` (IN), `NO_D` (documental), `NO_F` (foco), `NO_M` (métrica de modelo), `NO_C` (componente), `NO_V` (mina o proyecto), `NO_R` (revisión) o `NO_U` (subterráneo).

**Códigos de exclusión por pertinencia**

| Código | Motivo |
|---|---|
| `F_GEO` | Geotecnia o estabilidad sin vínculo operacional explícito. |
| `F_AMB` | Ambiental, hídrico, emisiones, cierre o recuperación, sin vínculo con la operación. |
| `F_VIB` | Efectos de tronadura (vibración, onda aérea, proyecciones) sin vínculo operacional. |
| `F_CTX` | Contexto distinto del rajo (subterráneo, otra industria). |
| `F_ECO` | Economía agregada, social, legal, política o educación. |
| `F_GEOL` | Geología, exploración o recursos. |
| `F_TELE` | Cartografía o teledetección sin objeto operacional. |
| `F_SEG` | Seguridad ocupacional general. |
| `F_SALUD` | Salud o exposición de trabajadores. |
| `F_PROC` | Procesamiento o planta. |
| `F_COMP` | Componente o material sin equipo de la mina. |
| `F_DOC` | Sin estudio propio (editorial, reseña, retractación). |
| `F_OTRO` | No trata la operación del rajo. |

`documentacion/herramientas_lectura/ver_fichas.py` imprime las fichas de cada grupo en el mismo orden que los índices, usando la carpeta de una reproducción.

## 4 Columnas del cribado

`01_corpus_completo_cribado.csv` conserva **todas las columnas originales sin cambios** y agrega:

| Columna | Contenido |
|---|---|
| `titulo_usado_en_cribado`, `resumen_usado_en_cribado_origen` | Qué título y resumen se evaluaron, cuando difieren de los unificados. |
| `decision_filtro_amplio`, `motivo_filtro_amplio` | Etapa 1. |
| `decision_pertinencia_nivel1` | INCLUIDO, EXCLUIDO o NO_EVALUADO. |
| `decision_cribado_desempeno`, `regla_cribado_desempeno`, `justificacion_cribado_desempeno` | Núcleo A+B+C. |
| `decision_final`, `etapa_exclusion`, `motivo_exclusion`, `justificacion` | Decisión operativa. |
| `procedencia_decision` | `regla_filtro_amplio_original`, `regla_confirmada_por_lectura_de_titulo`, `lectura_dirigida_titulo_resumen` o `revision_humana`. |
| `revision_de_literatura`, `limitacion_informacion`, `requiere_revision_humana` | Marcas de información. |

No se agregan etiquetas temáticas.

## 5 Muestra de validación y concordancia

**Diseño de la muestra**
- Cuatro estratos de 25 publicaciones: excluidas en el filtro amplio, excluidas por pertinencia, incluidas fuera del núcleo e incluidas en el núcleo.
- Se excluyen los 86 casos de revisión humana.
- El orden es aleatorio, con semilla fija.

**Cálculos de `08`**
- Acuerdo por estrato, con intervalo de Wilson.
- Kappa de Cohen.
- Acuerdo ponderado por el tamaño de cada estrato.
- Falsos excluidos y falsos incluidos, extrapolados a cada estrato.

Con 25 casos por estrato los intervalos son amplios. Para más precisión, `--n-por-estrato` permite ampliar la muestra, en una carpeta nueva.

**Resultado del cierre (10-nov-2026)**
- Kappa: 0,78 en inclusión y 0,52 en núcleo.
- Acuerdo ponderado de inclusión: 0,86.
- Acuerdo por estrato: E1 0,84; E2 1,00; E3 0,72; E4 0,80 en núcleo.
- La revisión la hizo la autora con asistencia de un modelo de lenguaje que propuso una clasificación inicial, que ella verificó y modificó caso a caso. Se reporta así porque puede sobrestimar la concordancia.
- El detalle está en `05_cierre_revision/salida_archivada/concordancia_muestra_validacion.json`.

**Columnas que agregó la revisora**
- Las planillas completadas incluyen columnas propias: `A_tarea_rajo`, `B_evaluacion_propia`, `C_resultado_operacional`, `confianza_evidencia`, `base_de_clasificacion`, `criterio_metodologico` y una hoja `Resumen_revision`.
- `08` las conserva, pero solo lee `decision_revisor`, `nucleo_revisor` y `motivo_o_comentario_revisor`.

## 6 Determinismo e integridad

- Los únicos pasos aleatorios usan semilla fija.
- Todas las lecturas y escrituras usan UTF-8.
- Las salidas CSV/JSON no incluyen rutas ni fechas de ejecución.
- `00_reproducir_local.py` se detiene si cambia una entrada o un motor, o si una salida no coincide con su referencia.
- Las planillas `.xlsx` no se cotejan por huella, porque openpyxl registra la fecha de creación. Se coteja su clave CSV.
- `MANIFIESTO_SHA256.json` cubre todos los archivos del paquete, excepto el propio manifiesto y las carpetas de reproducción.

**Salidas archivadas**
- Cada `salida_archivada/huellas_sha256.json` lista las huellas de referencia. Los archivos grandes que son subconjuntos de otros se archivan solo por su huella.
- El corpus final completo está en `05_cierre_revision/salida_archivada/01_corpus_completo_cribado.csv`.
- El corpus anterior a la revisión humana (etapa 4) se archiva solo por su huella.
- Las tablas y redes de `06_descriptivos/` corresponden al corpus final.
