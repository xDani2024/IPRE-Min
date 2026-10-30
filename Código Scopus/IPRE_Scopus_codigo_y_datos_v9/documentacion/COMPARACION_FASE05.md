# Equivalencias metodológicas — Fase 05

| Elemento | Joaquín — OpenAlex | Scopus — implementación local | Diferencia y justificación |
|---|---|---|---|
| Entrada | `Matriz_4735_con_cierre_v9.csv` | `Matriz_Scopus_4614_con_pre_cierre_v9.csv` | Fuentes bibliográficas separadas; no heredar juicio humano externo. |
| Subconjunto IN | 419 propuestos v9 | 390 computacionales v9 | Niveles de auditoría diferentes. Scopus no tiene cierre validado. |
| Figura 01 | Universo reconstruido 9.534 → amplio 4.735 → IN 419 | Descarga 10.683 → únicos 9.547 → amplio 4.614 → IN 390 | Incluye 151 registros sin resumen excluidos por control documental de Fase 1. |
| Figura 02 | v6, v7, v8, v9 (4.735) | v6, v7, v8, v9 (4.614) | Igual categorización IN/OUT/TC, conservando diferencias de cada versión. |
| Figura 03 | 2.399 TC: 56 IN evidencia, 1 IN humano, 616 OUT foco y 1.726 OUT documentales | 2.318 TC: 81 IN computacionales, 607 OUT foco y 1.630 OUT documentales | No existe IN por precedencia humana en Scopus. |
| Figura 04 | 2000–2025, otros años por separado | 2000–2025, 2026 y posteriores informados aparte | 2026 es parcial y hay años futuros que son alertas, no exclusiones automáticas. |
| Figuras 05 y 06 | Menciones de procesos/equipos de diccionarios originales | Los mismos campos heredados de Fase 1 | No significa equipo central ni tema primario. |
| Figura 07 | Porcentaje dentro de amplia/núcleo | Igual, N=4.614/N=390 | La suma de porcentajes puede superar 100 %; no son categorías excluyentes. |
| Figura 08 | 40 decisiones humanas históricas (P20/H20) | Tareas de validación por completar: 390 IN y muestra de 120 OUT | No corresponde copiar ni inventar revisiones humanas de OpenAlex. |
| Avance Word | Documento de avance de Joaquín | Informe Word preliminar basado en Scopus | Diferente cohorte y estado de validación, por lo que se reescribe el contenido. |
| Integridad | SHA-256 del corpus archivado y figuras | Verificación SHA-256 de matriz y nuevas salidas | Permite auditar el origen de las cifras. |

**Nota:** ninguna figura reclasifica artículos. La revisión bibliográfica y el análisis de vacíos de investigación deben distinguir mención automatizada, objeto central, etapa de decisión y desempeño realmente evaluado.
