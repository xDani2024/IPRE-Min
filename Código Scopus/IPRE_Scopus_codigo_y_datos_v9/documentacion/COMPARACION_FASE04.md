# Tabla de equivalencias y diferencias — Fase 04 v9

| Etapa | Joaquín — OpenAlex | Réplica Scopus | Diferencia y justificación |
|---|---|---|---|
| Matriz de entrada | 4.735 registros congelados v8; 2.399 TC | 4.614 registros congelados v8; 2.318 TC | Diferentes bases bibliográficas, no deben mezclarse |
| Función `classify()` | Patrones, métricas, relación tarea-resultado y reglas de exclusión | Copia **literal** de la función y expresiones de `22_cerrar_TC.py` | Ninguna en la función. Se comprobaron **2.399/2.399 coincidencias** al ejecutarla sobre los TC de la matriz original de Joaquín |
| Pre-cierre computacional de TC | 79 IN y 2.320 OUT antes de auditorías y precedencias | 81 IN y 2.237 OUT | Los corpus no son iguales; recuentos de **código solamente** |
| Auditorías de IA directas | 118 antiguos TC revisados y una lectura complementaria | 0 auditorías realizadas; se genera planilla de auditoría | Sus auditorías corresponden a artículos OpenAlex concretos y **no se transfieren** |
| Decisiones humanas | 40 decisiones conservadas e integradas cuando corresponde | 0 decisiones humanas integradas | No se inventan juicios ni se heredan dictámenes sobre otros IDs |
| Integración | 419 IN / 4.316 OUT, v9 con auditorías | 390 IN / 4.224 OUT, **pre-cierre no validado** | **No comparables como núcleos finales** |
| Criterio documental OUT | OUT por foco o insuficiencia; no demuestra irrelevancia | Mismas categorías y avisos | Una exclusión documental se mantiene provisional |
| Matriz original | Columnas v8 intactas y columnas v9 añadidas | Columnas v8 intactas y columnas v9 añadidas | Cambia solamente clave a `scopus_id` |
| Integridad | SHA-256, cobertura por ID y trazabilidad | SHA-256, cobertura por ID y trazabilidad | Los SHA provienen de bases diferentes |

**Interpretación:** el resultado v9 de Scopus es una **propuesta computacional**. El único paso restante para una comparación académica de cierres es auditar semánticamente los IN y una muestra de OUT, documentar correcciones, y completar controles documentales de Fase 1. El notebook no automatiza una validación que no se ha efectuado.
