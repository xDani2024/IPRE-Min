# Reproducción local del flujo Scopus

Este paquete reproduce la selección computacional desde las páginas JSON guardadas de Scopus. No descarga publicaciones nuevas, no requiere una API key para esta ruta y no vuelve a generar auditorías IA ni decisiones humanas.

## Ejecutar en Windows

Descomprima el ZIP completo en una carpeta nueva. Abra la terminal en la carpeta que contiene `00_reproducir_local.py` y ejecute:

```powershell
py -3 00_reproducir_local.py --salida reproduccion_completa_01
```

Para generar además los ocho gráficos y el documento Word:

```powershell
py -3 -m pip install -r requirements_visuales.txt
py -3 00_reproducir_local.py --salida reproduccion_con_descriptivos_01 --descriptivos
```

Cada corrida debe usar una carpeta vacía o nueva. Los mensajes de cada script se guardan en `bitacoras`. Si falla una etapa, consulte el archivo indicado en el error. La configuración UTF-8 se transmite a todos los procesos.

## Qué se ejecuta

1. Filtro amplio desde `01_extraccion_y_filtro/datos_reconstruidos`.
2. Cribado multidimensional v6.
3. Resolución automática de dudosos v7.
4. Criterio v8 sobre la base amplia completa.
5. Pre-cierre computacional v9 y verificación de integridad.
6. Descriptivos y Word, únicamente con `--descriptivos`.

El resultado final queda en `resultado_v9`. La cadena también conserva las salidas intermedias. `VERIFICACION_REPRODUCCION.json` registra el cotejo de todos los CSV contra las huellas de la versión comprobada. Si cambia el código o difiere un CSV, la ejecución se detiene. No quite estos controles para ocultar diferencias.

## Referencias de reproducción

Las referencias de esta entrega fueron regeneradas para el código corregido. `REFERENCIAS_REPRODUCCION.json` identifica las huellas del código y los CSV esperados. El manifiesto general registra los archivos distribuidos. Las fechas reales de ejecución y las rutas de los JSON pueden variar y no se cotejan byte a byte.

La fecha de corte editorial se obtiene de la última página JSON guardada. Es distinta de la fecha de ejecución. El identificador de instantánea de v8 se conserva para permitir la comparación de sus CSV.

## Relación con el paquete de Joaquín

Se conservan los criterios automáticos de filtrado y clasificación adaptando identificadores y metadatos a Scopus. Las auditorías de OpenAlex y los juicios humanos de Joaquín no se trasladan a esta cohorte. Los archivos JSON vacíos de auditoría son marcadores informativos y el código actual no integra decisiones que se agreguen allí.

La revisión amplia independiente selecciona hasta 240 aceptados y 80 excluidos por motivo, con códigos neutrales y clave reservada. La muestra diagnóstica de fase 1 es otra salida, una selección reproducible de hasta 25 fichas. No equivale a la muestra histórica de Joaquín ni permite estimar una tasa de error global. Las muestras v6/v8 usan códigos neutrales y claves separadas. Los formularios asistidos v9 muestran la propuesta automática. El formulario `Revision_independiente_ciega_v9.csv` la oculta; su clave no debe entregarse a los revisores durante la evaluación.

## Qué significan los resultados

- IN: candidato propuesto según las reglas, pendiente de revisión.
- OUT por foco: se identifica un objeto distinto del alcance operacional.
- OUT documental: la ficha no permite justificar inclusión. No demuestra irrelevancia del artículo completo.
- TC: incertidumbre registrada en v8. La nueva propuesta v9 es binaria, pero conserva las columnas anteriores y los motivos documentales.

No se realiza una nueva lectura de texto completo ni una auditoría IA semántica. Los controles de retractación y paratexto permanecen pendientes. Los grupos fusionados con DOI distintos requieren revisión bibliográfica propia y no se separaron automáticamente.

Las figuras comparan la base amplia con los IN propuestos e indican sus denominadores. Las etiquetas de procesos, equipos y focos son menciones automáticas no excluyentes. No confirman el tema central ni permiten afirmar vacíos de investigación por sí solas.

## Trabajos pendientes

Auditorías propias de Scopus, revisión humana independiente, controles documentales, resolución bibliográfica de fusiones y evaluación metodológica de la selección. Las huellas y la repetibilidad comprueban integridad técnica, no exactitud académica.

La extracción nueva es una ruta distinta mediante `01_extraer_scopus.py`: requiere credenciales propias y puede producir otros conteos. El paquete no contiene claves de acceso.
