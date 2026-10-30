# Guía técnica

## Flujo central

`00_reproducir_local.py` pasa explícitamente cada salida recién generada a la etapa siguiente. No usa las matrices archivadas para sustituir cálculos. Esas matrices se utilizan solo para el cotejo SHA-256.

| Orden | Script | Entrada de reproducción | Salida de reproducción |
|---|---|---|---|
| 1 | `01_extraccion_y_filtro/02_filtrar_y_unificar.py` | Páginas JSON y configuración guardadas | `filtro_amplio/` |
| 2 | `02_cribado_v6/codigo/06_screening_multidimensional.py` | `filtro_amplio/` | `motores/v6/codigo/salida/` |
| 3 | `03_cribado_v8/entrada/v7/11_resolver_dudosos.py` | CSV v6 regenerado | `motores/v8/entrada/v7/salida/` |
| 4 | `03_cribado_v8/15_aplicar_criterio_calibrado.py` | CSV v6 y v7 regenerados | `motores/v8/salida/` |
| 5 | `04_cierre_v9/22_cerrar_TC.py` | Matriz y resumen v8 regenerados | `motores/v9/salida/` |
| 6 | `04_cierre_v9/23_verificar_cierre.py` | Matriz v8 y salidas v9 regeneradas | Verificación de integridad |
| 7 | Copia final | Salidas v9 verificadas | `resultado_v9/` |
| Opcional | `05_descriptivos/25_generar_avance.py` | Matriz y manifiesto v9 regenerados | `05_descriptivos/` |

Todas estas carpetas están bajo `--salida`. Cada script de cálculo admite `--entrada` y `--salida`. El de v8 también admite `--entrada-v6`. Las rutas relativas de esos argumentos se interpretan respecto de la terminal. Las rutas predeterminadas se resuelven respecto del paquete, no del directorio actual.

## Nueva extracción

Instale `requests` y use:

```powershell
py -3 -m pip install requests
py -3 01_extraccion_y_filtro/01_extraer_scopus.py --modo PILOTO --salida descarga_nueva
```

La clave se solicita en memoria o se toma de `SCOPUS_API_KEY`. Se conserva `ELSEVIER_INSTTOKEN` cuando está disponible. Para extracción completa, elija explícitamente `--modo COMPLETO`. El motor escribe `fase1_completo/` o `fase1_piloto/` dentro de la salida y puede reanudar una descarga compatible. No se efectuó una consulta nueva a Scopus durante esta reorganización.

El filtro admite después `--entrada descarga_nueva/fase1_completo --salida filtro_nuevo`. No mezcle esa instantánea con las etapas congeladas sin revisar la cohorte.

## Entorno

Python 3.10 o posterior. Biblioteca estándar para la reproducción 01–04. `requests` para descargar. `matplotlib` y `python-docx` para los descriptivos opcionales. El import de `requests` se trasladó al método HTTP para no exigirlo en la reproducción sin red.

## Integridad

`MANIFIESTO_SHA256.json` enumera los archivos distribuidos. `documentacion/Verificacion_cadena_completa.json` contiene los cotejos de la ejecución verificada. Las salidas CSV se comparan por sus bytes, no solo por sus recuentos. Las figuras se regeneran y verifican por número de archivos y sus manifiestos, sin exigir identidad binaria de PNG o Word entre versiones de bibliotecas.

El programa se detiene ante una salida ocupada, archivos de entrada faltantes, manifiestos incompatibles, diferencias de cohorte o discrepancias de resultados. Las bitácoras conservan los mensajes de cada etapa.
