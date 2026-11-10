# Cierre reproducible de la unificación bibliográfica — 9 de noviembre de 2026

## Alcance y resultados

Se ejecutó la unificación por **identidad bibliográfica**, sin alterar decisiones históricas de cribado ni cambiar los registros de las tres fuentes. La referencia es una instantánea congelada de OpenAlex, Scopus y Web of Science (WoS). Los conteos son reproducibles **para estas instantáneas**.

| Nivel | Registros originales | Publicaciones unificadas | Reducción por unificación |
|---|---:|---:|---:|
| Universo íntegro (antes de filtros temáticos) | 24.152 | 15.297 | 8.855 |
| Base amplia histórica (después de filtros originales) | 11.587 | 7.422 | 4.165 |

El universo se compone de 9.534 registros OpenAlex, 9.547 Scopus y 5.071 WoS. El reporte guarda por separado el origen de cada registro y su relación con la publicación unificada. Cada publicación incluye los años, DOI, títulos y resúmenes originales de sus componentes, además de un identificador determinista a partir del conjunto de identificadores UID de la fuente.

## Decisiones de cierre aprobadas

- **ALERTA-0111:** conservar separados y vinculados OpenAlex 1985 y Scopus 1986.
- **ALERTA-0500:** conservar separados y vinculados OpenAlex 1982 y Scopus 1983.
- **ALERTA-0529:** conservar separados provisionalmente Scopus 1987 y WoS 1988.
- **ALERTA-0534:** fusionar Scopus 2005 y WoS 2006, conservando ambos años y metadatos fuente.
- **ALERTA-0467:** mantener separados los registros de 2015 y 2025. Sigue pendiente la verificación del tipo editorial de 2025.
- **ALERTA-0519:** fusionar los registros OpenAlex y WoS de 2025, manteniendo separado y vinculado el registro WoS de 2026. Sigue pendiente su comprobación editorial.

Las decisiones se registran por identificadores estables, nunca únicamente por ID ordinal de alerta, en `flujo_unificado/decisiones_aprobadas/07_cierre_unificacion_6_excepciones_aprobadas.csv`. Las restricciones se respetan incluso a través de uniones indirectas.

## Criterios y limitaciones

1. La normalización `unicode_v2` conserva títulos en alfabetos no latinos; se mantiene la opción histórica para reproducir las alertas de origen.
2. La unión manual aprobada se aplica antes de la deduplicación automática y tiene prioridad sobre la heurística. No se fuerza la fusión de registros de una misma fuente sin autorización explícita.
3. Se preservan los metadatos originales y las decisiones históricas `IN/OUT`; la clasificación temática consolidada permanece vacía.
4. La **base amplia** continúa reflejando filtros temáticos aplicados históricamente. Los 105 registros OpenAlex identificados como excluidos en la auditoría de cobertura **no se reincorporan** en ella por este procedimiento.
5. Para hacer un **cribado temático nuevo y exhaustivo** sobre las fuentes actuales, la referencia metodológica apropiada es el **universo unificado de 15.297 publicaciones**, no la base amplia histórica. La base amplia de 7.422 sirve como comparación y para estudiar el filtrado previo.
6. Las alertas 0467 y 0519 siguen abiertas exclusivamente para una aclaración editorial. Se conservan las restricciones conservadoras, por lo que no impiden producir el corpus de identidad bibliográfica de este corte.
7. Las equivalencias automáticas no revisadas una por una siguen siendo limitación metodológica. La deduplicación de este corte es reproducible y auditada, pero no representa validación manual del 100 % de coincidencias automáticas.

## Reproducir en Windows (CMD)

Ejecutar dentro de la carpeta `IPRE-Min-main`:

```bat
python integracion_corpus/unificacion_validada.py --etapa ambas
python -m unittest discover -s integracion_corpus/pruebas -p "test_*.py"
python -m unittest discover -s flujo_unificado/pruebas -p "test_*.py"
python integracion_corpus/unificacion_validada.py --etapa ambas --salida integracion_corpus/comprobacion_independiente
python integracion_corpus/verificar_reproduccion.py --referencia integracion_corpus/resultados_validados --nueva integracion_corpus/comprobacion_independiente
```

Resultado verificado: **18 pruebas de integración + 28 pruebas del flujo = 46 pruebas correctas**; los **16 archivos** en las dos carpetas de resultado coinciden byte a byte (SHA-256).

## Archivos para utilizar en la tesis

- `integracion_corpus/resultados_validados/universo/01_corpus_unificado_identidad.csv`: **15.297 publicaciones**, entrada recomendada del nuevo cribado.
- `integracion_corpus/resultados_validados/universo/02_procedencia_registros.csv`: **24.152 registros originales** vinculados a sus publicaciones consolidadas.
- `integracion_corpus/resultados_validados/base_amplia/01_corpus_unificado_identidad.csv`: **7.422 publicaciones** del subconjunto filtrado histórico.
- `.../03_bitacora_vinculos.csv`: uniones manuales y automáticas, aceptadas y rechazadas.
- `.../04_restricciones_y_pendientes.csv`: pares que no se pueden fusionar por decisión humana.
- `.../05_relaciones_editoriales.csv`: relaciones entre publicaciones distintas.
- `.../08_resumen_validacion.json`: control del número de registros, fuentes, hashes y resultados.

## Independencia del cribado

Los archivos contienen campos de estado temático **sin evaluación en este paso**. Las decisiones temáticas sobre los 15 artículos priorizados y las 90 propuestas adicionales no se han aplicado al corpus. Ese trabajo se retoma una vez seleccionado el protocolo de cribado sobre el universo consolidado.
