# Cierre documental v9 de los TC

**Resultado:** 2.399 TC con propuesta binaria, 57 IN y 2.342 OUT; cero TC en la columna de propuesta integrada. Núcleo propuesto: 419 IN sobre 4.735 registros. Fecha: 8 de octubre de 2026.

Este paquete conserva v8 y todas sus columnas. El resultado v9 es una propuesta separada; no sustituye automáticamente el corpus original ni constituye validación humana independiente.

## Ejecutar

Extrae el ZIP completo y abre la consola en esta carpeta. Requiere Python 3.9 o superior; no requiere instalaciones adicionales, conexión, ni API key.

Windows PowerShell:

```powershell
py -3 22_cerrar_TC.py
py -3 23_verificar_cierre.py
```

Linux/macOS:

```bash
python3 22_cerrar_TC.py
python3 23_verificar_cierre.py
```

El primer código integra reglas documentales, auditorías IA congeladas y decisiones humanas previas. El segundo verifica cobertura, integridad y trazabilidad. Ambos escriben en `salida/`. La entrada tiene SHA-256 fijado: usar una matriz diferente genera un error intencional para evitar mezclar versiones.

La ejecución reproduce la integración y los conteos a partir del registro de auditorías conservado. **No vuelve a generar las lecturas semánticas IA**, no extrae nuevamente OpenAlex y no es una nueva revisión de texto completo.

## Archivos

- `Cierre_TC_v9_criterios_y_resultados.md`: explicación metodológica, resultados, excepciones y límites.
- `entrada/matriz_completa_4735_v8.csv`: base congelada, intacta.
- `entrada/decisiones_humanas_conservadas.json`: 40 decisiones actuales, con sugerencias y fundamentos previos disponibles.
- `auditoria_directa_IA.json`: 118 lecturas directas de títulos/resúmenes, con decisión, motivo y cita literal.
- `auditoria_complementaria_H011.json`: sugerencia IN para H011, sin modificar su respuesta humana histórica TC.
- `salida/Resumen_por_ID_2399_TC_v9.csv`: vista de consulta de los antiguos TC.
- `salida/Decisiones_2399_TC_v9.csv`: registro detallado de cierre.
- `salida/Matriz_4735_con_cierre_v9.csv`: matriz completa con columnas v8 y nuevas columnas v9.
- `salida/IN_propuesto_v9.csv`: núcleo propuesto de 419 registros.
- `salida/OUT_propuesto_v9.csv`: 4.316 registros fuera del núcleo propuesto; continúan en la base amplia.
- `salida/Resumen_cierre_v9.json`: conteos y cruces humanos.
- `salida/Verificacion_integridad_v9.json` y `Verificacion_reproducibilidad_v9.json`: comprobaciones.
- `MANIFIESTO_SHA256.json`: huellas de los archivos incluidos.

## Interpretar OUT

De los 2.342 antiguos TC propuestos OUT, **1.726 son exclusiones documentales**, por evidencia insuficiente, contexto no acreditado o fuente no fiable; 616 se excluyen por foco. OUT documental significa que la inclusión no pudo justificarse con la ficha congelada, y **no demuestra irrelevancia definitiva**. La incertidumbre de evidencia queda registrada aunque la propuesta sea binaria.

Las 57 propuestas IN nuevas recibieron lectura directa IA del título/resumen. No se leyeron directamente todos los 2.399 artículos ni sus textos completos: se realizó un barrido computacional de todas las fichas y una auditoría semántica de 118 antiguos TC. La revisión humana anterior fue calibración con sugerencias visibles, no una evaluación independiente.
