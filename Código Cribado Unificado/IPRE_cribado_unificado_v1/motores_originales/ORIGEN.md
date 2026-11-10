# Motores originales

Copias **sin modificar** de los códigos del paquete `IPRE_codigo_y_datos_v9` (8-oct-2026). Se conservan con las mismas rutas relativas para que las etapas 1-3 los importen tal como están.

| Archivo | Qué se usa |
|---|---|
| `01_extraccion_y_filtro/02_filtrar_y_unificar.py` | `screen_record()` y sus diccionarios (filtro amplio). |
| `02_cribado_v6/codigo/06_screening_multidimensional.py` | `decide()` y patrones de contexto, tarea y resultado (v6). |
| `03_cribado_v8/entrada/v7/11_resolver_dudosos.py` | `assess()` para los dudosos (v7). |
| `03_cribado_v8/15_aplicar_criterio_calibrado.py` | Reglas del bucle principal v8, sin las ramas que dependen de auditorías IA previas. |
| `04_cierre_v9/22_cerrar_TC.py` | `classify()` y métricas de resultado (v9). |

Las huellas SHA-256 coinciden con `MANIFIESTO_SHA256.json` del paquete original y están registradas en `PROCEDENCIA_DEL_PAQUETE.json`. `00_reproducir_local.py` se detiene si alguna cambia.
