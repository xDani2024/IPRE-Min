# IPRE — Web of Science — flujo de cribado homologado con IPRE_codigo

**Fecha de corte:** 1 de noviembre de 2026. **Fuente:** Web of Science Core Collection.
**Origen:** 10 exportaciones web manuales incrementales de la Fase 1. Sin API WoS.
**Estado:** cribado computacional preliminar, pendiente de revisión humana y controles documentales.

## Qué contiene

- `entrada_fase01/`: copias sin modificar de los CSV y manifiestos necesarios de `IPRE_WoS_Fase01_LOCAL_COMPLETA(1).zip`. Los `.xls` de las 10 exportaciones permanecen en el paquete original de Fase 1.
- `motores_ipre/`: cuatro scripts **originales**, sin modificar, extraídos de `IPRE_codigo(5).zip`: v6, v7, v8 y clasificador de cierre v9.
- `motor_v8_adaptado.py`: aplicación del motor v8 a la nueva cohorte, con los conteos fijos desactivados y con piloto humano/ajustes históricos de OpenAlex **vacíos**. Las expresiones y reglas de cribado v8 no se modificaron.
- `00_ejecutar_cribado_wos.py`: mapea los campos de WoS, aplica las decisiones de los motores originales y genera archivos v6, v7, v8 y v9. No consulta internet ni API.
- `resultados_cribado_wos/`: matrices, subgrupos y plantillas de revisión. `RESUMEN_FLUJO_WOS.json` documenta recuentos, integridad y SHA-256.

## Reproducción desde cero

Descomprimir el ZIP completo manteniendo carpetas. Requiere Python 3.10 o superior, sin dependencias externas. Ejecutar desde la carpeta principal:

```powershell
py -3 00_ejecutar_cribado_wos.py --salida resultados_cribado_wos_nueva
```

La ejecución puede tomar varios minutos por las expresiones regulares de los motores originales. Se requiere una carpeta de salida nueva o vacía. No sobrescribe las matrices incluidas de referencia.

## Recorrido y cifras comprobadas

| Paso | Base | Resultado computacional |
|---|---:|---|
| Exportación y limpieza WoS | 5.071 UID | 198 sin resumen, 2.635 OUT del filtro amplio, 2.238 base amplia |
| Motor v6 de IPRE_codigo | 2.238 | 92 IN_FUERTE; 124 IN_SECUNDARIO; 690 DUDOSO; 1.332 OUT |
| Motor v7 de IPRE_codigo (solo reglas) | 2.238 | 221 IN; 2.017 OUT |
| Motor v8, mismo criterio, sin piloto humano WoS | 2.238 | 142 IN; 1.179 OUT; 917 TC |
| Clasificador v9, **sin auditorías IA ni dictámenes humanos** | 2.238 | 168 IN; 2.070 OUT **solo computacionales** |

La clasificación v9 aquí **no reproduce** el grado de revisión del cierre OpenAlex. Es una aplicación de las reglas deterministas del cierre a las fichas WoS. El motor v9 de OpenAlex integró además auditorías semánticas IA y decisiones humanas de casos concretos, que **no deben reutilizarse** con los UID WoS. No debe informarse que los 917 TC recibieron lectura semántica o revisión humana.

## Equivalencias de campos

- ID real de fuente: `wos_id`, conservado sin cambios.
- `openalex_id` dentro de las matrices: **alias técnico** con el valor `wos_id` para que los motores del proyecto no fallen. No representa un identificador OpenAlex ni una vinculación entre bases.
- `document_type` se traduce a `type=article|review`; la columna original se mantiene.
- `source_title` se copia a `source`; `language=English` se normaliza a `en` para mantener la misma condición lingüística del motor.
- `auto_screen_status` se conserva como estado previo del filtro amplio, sin usarlo para sustituir los resultados v6.
- `source_files`, `first_discovery_query`, DOI, fecha editorial y fecha de acceso temprano se conservan sin cambiar.

## Pendientes y cautelas metodológicas

1. Realizar una **revisión humana independiente** sobre la muestra ciega v6 (archivo `01_v6/muestra_humana_ciega.csv`), manteniendo separada la clave `01_v6/clave_muestra_NO_ENTREGAR_A_REVISORES.csv`. Se proporciona la plantilla de revisión integral en `04_v9_preliminar/plantilla_revision_humana.csv`.
2. Revisar individualmente los casos TC de v8 y contrastar su disposición documental. OUT por evidencia insuficiente no equivale a irrelevancia definitiva.
3. Verificar las 2 alertas de posible retractación de Fase 1 y los 3 grupos con título/año iguales y UID distintos. No se fusionaron por similitud bibliográfica ni se asignaron resoluciones automáticas definitivas.
4. Conservar los 198 casos sin resumen y 2.635 excluidos del filtro amplio para auditoría y eventual análisis de sensibilidad.
5. Completar, si es posible, el número total original (antes de NOT) de la consulta 05 «surface mining» en el registro documental de la extracción.
6. Antes de integrar con Scopus y OpenAlex, ejecutar deduplicación **entre fuentes** con DOI normalizado y revisión de casos sin DOI, conservando todos los identificadores y la procedencia de las decisiones. No sumar IN entre bases como si fueran publicaciones exclusivas.
7. No confundir el año editorial con la fecha de publicación electrónica o Early Access en análisis temporales.

## Interpretación recomendada

Informar 2.238 **registros WoS candidatos de la base amplia** y 168 **propuestas automáticas de inclusión** tras el recorrido completo de reglas. No presentar las 168 como resultado de revisión humana o número final de estudios incluidos. Para replicar íntegramente el nivel de revisión del v9 OpenAlex se necesitan nuevas auditorías semánticas y dictámenes sobre los registros WoS.

## Integridad

`resultados_cribado_wos/RESUMEN_FLUJO_WOS.json` contiene los SHA-256 de las entradas de Fase 1 y de las matrices de las cuatro etapas. Se comprobó igualdad de los 2.238 UID entre v6, v7, v8 y v9. Las columnas históricas se preservaron y no se importaron juicios humanos ni auditorías IA identificadas con ID OpenAlex.

## Gráficos e informe descriptivo WoS (nueva carpeta 05_descriptivos)

Se incorporó la etapa descriptiva de `IPRE_codigo`, adaptada a WoS. Incluye **ocho gráficos**, un resumen JSON calculado desde las matrices y un **informe Word editable de ocho páginas**. El último gráfico presenta la **muestra humana de v6 pendiente**, no una calibración realizada.

Instalar las dependencias desde la carpeta raíz del proyecto:

```powershell
py -3 -m pip install -r 05_descriptivos/requirements.txt
```

Después del cribado, para usar su propia carpeta de resultados:

```powershell
py -3 05_descriptivos/00_generar_descriptivos.py --resultados resultados_cribado_wos_nueva
```

Para usar los resultados automáticos que ya vienen en el paquete:

```powershell
py -3 05_descriptivos/00_generar_descriptivos.py --resultados resultados_cribado_wos
```

Encontrará las imágenes en `05_descriptivos/graficos/` y el documento en `05_descriptivos/informe/Informe_avance_IPRE_WoS_preliminar.docx`. El procedimiento lee las salidas y no altera los datos de las etapas v6 a v9. Las cifras de v9 siguen siendo **propuestas computacionales**, sujetas a revisión humana. Consulte `05_descriptivos/README.md` para detalles.
