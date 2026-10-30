# Correcciones técnicas y alcance de la entrega

La reproducción local usa únicamente las páginas JSON originales de la cohorte Scopus. Las reglas de elegibilidad se conservan. Las auditorías y decisiones humanas de Joaquín no se transfieren.

## Correcciones técnicas

- Entorno UTF-8 y bitácoras persistentes por etapa.
- Validación de páginas, consultas, acumulados, cursores y cierre de descarga.
- Descripción del estilo real de consulta y fecha editorial fijada por la instantánea.
- Conservación de DOI con punto y coma mediante lista JSON.
- Optimización equivalente de comparaciones de texto, sin cambiar sus umbrales.
- Muestras reproducibles con claves separadas y códigos neutrales.
- Revisión amplia de hasta 240 aceptados y 80 excluidos por motivo, sin atribuir etiquetas históricas I/Q/G inexistentes en esta cohorte.
- Comprobación de matrices v6/v7 mediante sus manifiestos.
- Resumen v7 ampliado y exportación del corpus IN provisional.
- Resúmenes compactos de TC en v9 y nombre de nuevos IN sin conteo fijo.
- Verificador v9 ampliado: cobertura, unicidad, columnas previas, evidencia, particiones y huellas.
- Notebooks con procesos UTF-8 y pasos separados para reanudar comprobaciones.
- Descriptivos basados en el manifiesto de fase 1 y la matriz v9.

## Interpretación de las referencias

Las referencias regeneradas corresponden al código corregido. Su coincidencia demuestra repetibilidad técnica. El registro comparativo por identificador con la entrada recibida documenta cambios de clasificación y agrupación. No implica validación académica de las reglas.

## Trabajos que siguen pendientes

Auditorías semánticas propias de Scopus, revisión humana independiente, comprobación de retractación y paratexto y resolución bibliográfica de grupos con DOI distintos. Los JSON vacíos de auditoría son marcadores informativos que el código no integra. No añadir decisiones allí esperando que se apliquen automáticamente.

Los formularios asistidos v9 muestran sugerencias. El formulario independiente oculta la propuesta y debe entregarse sin su clave. Haber generado formularios no significa que la revisión se haya realizado.

La muestra diagnóstica de 25 registros y la revisión amplia son salidas distintas. En v6, la muestra de dudosos centrales no cubre todos los dudosos. Las tasas de error no pueden extrapolarse sin un diseño y análisis acordes al marco de cada muestra.

La carpeta de revisión bibliográfica recibida se conserva como antecedente y no modifica automáticamente las fusiones ni las decisiones.
