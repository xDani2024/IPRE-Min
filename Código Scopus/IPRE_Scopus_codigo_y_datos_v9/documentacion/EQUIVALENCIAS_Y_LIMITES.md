# Equivalencias y diferencias comprobadas

| Elemento | Joaquín | Scopus reorganizado |
|---|---|---|
| Directorios principales y subdirectorios de etapas | 01, 02, 03, 04, 05 y documentación | Mismos nombres de carpeta y subcarpetas del paquete de referencia. |
| Punto de entrada | `00_reproducir_local.py` | Mismo nombre, una sola cadena y salida nueva por corrida. |
| Extracción | `01_extraer_openalex.py` | `01_extraer_scopus.py`, mantiene proveedor e ID reales. |
| Filtro | `02_filtrar_y_unificar.py` | Mismo punto de entrada, invoca criterios Scopus aportados. |
| Fuente sin red | Universo OpenAlex reconstruido de 9.534 registros | JSON originales Scopus: 10.683 filas y 9.547 únicas. |
| Base amplia | 4.735 | 4.614. |
| Historial anterior | 4.773 registros OpenAlex | No existe equivalente Scopus aportado, no se fabrica ni transfiere. |
| Motor v6 | `06_screening_multidimensional.py` y 48 ajustes por ID | Misma función `decide`, sin los ajustes sobre artículos OpenAlex. |
| Motor v7 | `11_resolver_dudosos.py`, cola histórica y auditorías | Misma función `assess`, cola Scopus de 1.305 DUDOSO, sin herencia de auditorías. |
| Motor v8 | Criterio calibrado y pilotos conservados | Reglas de la versión Scopus aportada, pilotos humanos y auditorías OpenAlex vacíos. |
| Cierre v9 | Reglas, 118 auditorías IA y 40 decisiones humanas | Misma función `classify`, sin juicios sobre artículos distintos. Pre-cierre computacional. |
| Totales v9 | 419 IN / 4.316 OUT | 390 IN / 4.224 OUT, con validación pendiente. |
| Descriptivos | Ocho figuras y avance Word | Ocho figuras y avance Word Scopus, con denominadores y límites propios. |
| Rutas entre etapas | Orquestación y entradas congeladas | Orquestación con salidas recién calculadas. Referencias congeladas se usan para cotejo. |

Las adaptaciones de reglas que ya existían en Scopus se conservan. Esta entrega reorganiza su ejecución y no introduce nuevas decisiones de inclusión ni recalibraciones. Las funciones principales `decide`, `assess` y `classify` se cotejan con el código de Joaquín en `Verificacion_funciones.json`.

Las tablas COMPARACION_FASE01/04/05 conservan la documentación metodológica anterior como referencia. Sus nombres de carpetas y notebooks describen el paquete Scopus original. Las rutas vigentes son las del README y GUIA_TECNICA.

Las auditorías y revisiones pendientes requieren trabajo sobre las publicaciones Scopus. Reproducir el flujo no permite declarar que esas actividades ya ocurrieron.
