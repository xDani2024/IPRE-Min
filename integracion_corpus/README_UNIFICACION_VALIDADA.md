# Unificación bibliográfica validada — ejecución reproducible

## Alcance

Esta versión **sí aplica** las decisiones aprobadas de identidad bibliográfica a las instantáneas locales de OpenAlex, Scopus y WoS. **No cambia el cribado temático**, no reincorpora registros de forma automática y no altera los CSV originales.

Se procesan **dos etapas distintas**:

- **universo**: todos los registros de las tres fuentes, antes de los filtros de selección temática. Es el universo de referencia para deduplicar.
- **base_amplia**: subconjuntos históricos filtrados de cada fuente. Se unifican únicamente los registros presentes en ese nivel; no se incorporan los 105 excluidos de OpenAlex.

Las decisiones humanas se almacenan en `flujo_unificado/decisiones_aprobadas/`. Para reproducir las alertas originales se conserva `historica_ascii`, pero **la unificación validada usa `unicode_v2`**, que preserva cirílico, japonés y coreano. Las decisiones se aplican por `registro_uid`, nunca por el número ordinal de una alerta.

## Requisitos y ejecución en Windows CMD

Desde la carpeta `IPRE-Min-main`, con Python 3.10+ y sin acceso a internet:

```bat
python integracion_corpus/unificacion_validada.py --etapa ambas
python -m unittest discover -s integracion_corpus/pruebas -p "test_*.py"
python -m unittest discover -s flujo_unificado/pruebas -p "test_*.py"
```

Para comprobar que una segunda ejecución es **byte a byte igual** a la primera:

```bat
python integracion_corpus/unificacion_validada.py --etapa ambas --salida integracion_corpus/comprobacion_independiente
python integracion_corpus/verificar_reproduccion.py --referencia integracion_corpus/resultados_validados --nueva integracion_corpus/comprobacion_independiente
```

Si las fuentes, las decisiones o el código cambian, es normal que los hashes cambien; se debe generar un nuevo corte versionado y documentar la diferencia. No ejecute la extracción API para esta prueba: se usan instantáneas congeladas con SHA-256.

## Política de identificación

1. Mantener una fila por registro fuente, con UID `Fuente::ID`, título, año, DOI y hash original.
2. Aplicar primero las **aristas humanas aprobadas**, con comprobación obligatoria de UID en el universo.
3. Bloquear separaciones aprobadas, relaciones editoriales que no son equivalencias y parejas sin dictamen. La restricción también se respeta de forma **transitiva**: si A y C no pueden fusionarse, B no puede crear indirectamente un grupo A–B–C.
4. Aplicar después las propuestas automáticas conservadoras y solo cuando no contradigan decisiones humanas ni unan dos registros de una misma fuente sin autorización.
5. Guardar una fila por publicación consolidada con identificador determinista SHA-256 del **conjunto de UID**. El ID se mantiene entre ejecuciones de las mismas fuentes y reglas, pero puede cambiar legítimamente si se incorporan nuevos registros.
6. Conservar todos los registros en el archivo de procedencia, los DOI/fechas/títulos de cada fuente y sus etiquetas históricas sin homologarlas ni convertirlas en un nuevo cribado.
7. Conservar las separaciones 0111, 0500 y 0529 y la fusión 0534, junto con los seguimientos editoriales no bloqueantes 0467 y 0519. La edición separada de 0182 se respeta.

## Salidas

`integracion_corpus/resultados_validados/{universo,base_amplia}/` contiene:

| Archivo | Uso |
|---|---|
| `01_corpus_unificado_identidad.csv` | Publicaciones unificadas, metadatos por fuente y trazabilidad |
| `02_procedencia_registros.csv` | Relación uno a varios entre publicación y todos los registros fuente |
| `03_bitacora_vinculos.csv` | Cada arista humana y automática aceptada o rechazada |
| `04_restricciones_y_pendientes.csv` | Restricciones activas de no fusionar |
| `05_relaciones_editoriales.csv` | Relaciones entre publicaciones distintas |
| `06_pendientes_bibliograficos.csv` | Alertas sin dictamen (vacío en el corte de cierre) |
| `07_alertas_automaticas_unicode.csv` | Alertas generadas con normalización Unicode v2 |
| `08_resumen_validacion.json` | Totales, huellas SHA-256 de entradas, decisiones, código y salidas |

La capa de identidad bibliográfica está disponible para reproducirse, pero **no debe presentarse como corpus final de estudios incluidos**. Los seguimientos editoriales 0467 y 0519 y las coincidencias automáticas no revisadas son limitaciones explícitas; no se trasladan etiquetas `IN`/`OUT` de una fuente a otra.

## Comparabilidad

El conteo histórico de 15.412 corresponde a la deduplicación **automática y normalización histórica**. El conteo validado puede cambiar por la normalización Unicode y las decisiones humanas. Para reportar diferencias, se requieren el mismo corte de entradas y las huellas verificadas.
