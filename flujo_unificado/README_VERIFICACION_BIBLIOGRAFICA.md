# Verificación bibliográfica automática — actualización v1.3

## Objetivo

Examinar las 791 alertas bibliográficas del corpus consolidado de OpenAlex, Scopus y Web of Science **sin modificar el conjunto de publicaciones existentes**. Se verifican metadatos de artículos y no archivos PDF. Los resultados son **sugerencias técnicas para revisión**, no decisiones humanas confirmadas.

## Ejecución

Desde la carpeta principal `IPRE-Min-main`:

```cmd
python flujo_unificado/verificar_duplicados.py
```

El comando usa, si está presente, `resultados_calibracion_v1_1/02_integracion_y_deduplicacion/01_registros_normalizados.csv`. Si falta el archivo intermedio, lo reconstruye a partir de los tres universos guardados. No ejecuta consultas a API ni borra resultados del corpus.

Como alternativa, la verificación se ejecuta al finalizar `python flujo_unificado/main.py` (si está habilitado el cruce histórico v9).

### Resultados generados

En `flujo_unificado/resultados_calibracion_v1_1/08_verificacion_bibliografica/`:

- `01_diagnostico_por_alerta.csv`: una fila por alerta, evidencia resumida, propuesta y campos en blanco para validación humana.
- `02_evidencia_por_par.csv`: una fila por pareja de registros con títulos, DOI, años, similitudes y fundamento.
- `03_alertas_que_requieren_revision.csv`: alertas que no tienen evidencia suficiente para una conclusión automática.
- `04_resumen_verificacion.json`: conteos, límites metodológicos.
- `05_plantilla_decisiones_humanas.csv`: matriz editable que **no se sobrescribe en ejecuciones posteriores**.
- `06_titulos_no_latinos.csv`: títulos en otros alfabetos incorrectamente clasificados como vacíos por el normalizador anterior.

## Criterios de decisión sugerida

- **MISMA_PUBLICACION**: DOI idéntico y títulos compatibles con años concordantes; o título/año y metadatos adicionales concordantes cuando falta DOI.
- **PUBLICACIONES_DIFERENTES**: DOI distintos, títulos muy discordantes y evidencia de que son publicaciones separadas. Si el título es muy similar pero cambian los DOI, se solicita revisión en vez de separarlas.
- **REQUIERE_REVISION**: DOI contradictorios, discrepancias fuertes de títulos/años, múltiples IDs en una misma fuente, metadatos insuficientes o conjuntos complejos con decisiones incompatibles.

En la cohorte de alertas de v1.2, **no aparecieron parejas con evidencia suficiente para el estado PUBLICACIONES_DIFERENTES**. Eso no significa que todas sean duplicados; las demás permanecen pendientes.

## Precauciones

1. La identificación bibliográfica no equivale a comprobar igualdad exacta de los archivos PDF. Para eso se necesitan los PDF y, por ejemplo, su hash SHA-256.
2. El DOI es un identificador fuerte, pero no excluye errores de indexación. Los DOI distintos podrían corresponder a versiones o metadatos equivocados.
3. Los 15.412 registros únicos del corpus **no se modifican** con estas sugerencias. Tampoco cambian las decisiones de inclusión/exclusión temática.
4. Las alertas de `TITULO_VACIO` fueron generadas por un normalizador latino que eliminaba letras no latinas. Los títulos originales se conservan y deben tratarse como títulos válidos en alfabeto original.
5. Un conjunto de 791 alertas no representa una evaluación exhaustiva de todas las parejas bibliográficas posibles. Las coincidencias nuevas fuera de esas alertas requieren otro análisis.
6. La validación humana y su justificación deben registrarse antes de aplicar cambios al corpus. Guardar una copia de las matrices y el procedimiento de aprobación por el equipo investigador.

## Pruebas

```cmd
python -m unittest discover -s flujo_unificado/pruebas -p "test_verificar_duplicados.py"
```

Incluyen DOI y subtítulos, DOI reutilizado con título discordante, DOI diferentes, año distante, caracteres cirílicos/chinos y duplicación interna.
