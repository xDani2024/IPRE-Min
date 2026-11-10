# Cribado del corpus unificado: código y resultados del estudio bibliométrico de minería a cielo abierto

Cierre del 10 de noviembre de 2026. Profesor guía: José Joaquín Jara.

Este paquete reproduce, desde cero, el cribado de las **15.297 publicaciones únicas** del corpus unificado OpenAlex + Scopus + WoS.
- Aplica el filtro amplio y las reglas v6–v9 del flujo original OpenAlex, sin modificarlos.
- Agrega un nivel de pertinencia operacional (Nivel 1).
- Cierra con la revisión humana de los casos con información insuficiente y con una muestra de validación.

| Resultado final | Publicaciones |
|---|---:|
| Corpus incluido | **3.851** |
| Excluidas en el filtro amplio | 7.824 |
| Excluidas por pertinencia operacional | 3.608 |
| Excluidas en la revisión humana | 14 |
| Núcleo de desempeño (subconjunto de las incluidas, A+B+C) | **584** |
| Casos pendientes de revisión | 0 |

**Validación.** Muestra ciega de 100 publicaciones (25 por estrato):
- kappa de 0,78 en inclusión y de 0,52 en núcleo;
- acuerdo de inclusión ponderado al corpus de 0,86.

La revisión la hizo la autora con asistencia de un modelo de lenguaje, que propuso una clasificación inicial; cada decisión se verificó y, cuando correspondía, se modificó a mano. Los límites que mostró la validación están en `documentacion/Nota_metodologica_cribado.md`.

## Estructura

```text
IPRE_cribado_unificado_v1/
├── 00_reproducir_local.py              orquesta todas las etapas y coteja cada salida por SHA-256
├── motores_originales/                 5 códigos de IPRE_codigo_y_datos_v9, sin cambios (ORIGEN.md)
├── 01_filtro_amplio/
│   ├── 01_aplicar_filtro_amplio.py     fichas con metadatos de las 3 bases + screen_record() original
│   └── salida_archivada/
├── 02_nucleo_desempeno/
│   ├── 02_aplicar_reglas_v6_a_v9.py    reglas originales v6 → v7 → v8 → v9
│   └── salida_archivada/
├── 03_pertinencia_operacional/
│   ├── 03_proponer_reglas_nivel1.py    reglas de Nivel 1 y grupos de lectura
│   └── salida_archivada/
├── 04_integracion_final/
│   ├── 04_integrar_decisiones.py       reglas + lectura dirigida → corpus cribado
│   ├── 05_generar_cifras_prisma.py
│   ├── 06_verificar_integracion.py     14 comprobaciones de integridad
│   ├── entrada/lectura_dirigida/       decisiones de lectura (entrada congelada)
│   └── salida_archivada/               cribado antes de la revisión humana
├── 05_cierre_revision/
│   ├── 07_preparar_planillas.py        planillas de revisión y muestra ciega (semilla 20261109)
│   ├── 08_aplicar_revision_y_concordancia.py
│   ├── entrada/traducciones_es.json    traducción al español de títulos y resúmenes (IA, apoyo)
│   ├── planillas/                      planillas completadas por la autora + clave de la muestra
│   └── salida_archivada/               ★ CORPUS FINAL (con revisión humana) y concordancia
├── 06_descriptivos/
│   ├── 09_descripcion_bibliometrica.py tablas, redes VOSviewer/Gephi, figuras
│   ├── 10_generar_graficos_informe.py  recuentos y figuras del informe
│   ├── 11_generar_informe.py           informe Word
│   ├── config_descriptivos.json
│   ├── tablas/  redes/  graficos/  graficos_informe/
│   └── Resultados_descriptivos.json  Resultados_informe.json
├── documentacion/
│   ├── Informe_cribado_corpus_unificado_20261110.docx
│   ├── Nota_metodologica_cribado.md
│   ├── Verificacion_cadena_completa.json   comprobante de la última reproducción completa
│   ├── Entorno_verificado.json
│   └── herramientas_lectura/ver_fichas.py
├── GUIA_TECNICA.md  README.md  PROCEDENCIA_DEL_PAQUETE.json  MANIFIESTO_SHA256.json
└── requirements_complementarios.txt
```

## Para empezar

1. Copiar esta carpeta en `IPRE-Min-main/Código Cribado Unificado/`. Las entradas (corpus unificado y universos por base) se leen del propio repositorio y no se duplican.
2. Instalar las dependencias complementarias. Son necesarias para leer las planillas de revisión humana, que definen el corpus final, y para las figuras y el informe.

   ```powershell
   py -3 -m pip install -r requirements_complementarios.txt
   ```

3. Reproducir:

   ```powershell
   py -3 00_reproducir_local.py
   ```

   En Linux/macOS: `python3 00_reproducir_local.py`.

**Al terminar se espera:**

```text
Reproducción completada. INCLUIDOS: 3851 | EXCLUIDOS: 11446 | NÚCLEO IN: 584 | cotejos SHA-256: …
```

**Lo que hace la ejecución**
- No usa internet ni API key; el filtro amplio tarda unos 6 minutos.
- Escribe en `reproduccion_local/` y no toca los archivos archivados. Para otra ejecución: `--salida otra_carpeta`.
- Si el paquete no está dentro de `IPRE-Min-main`, hay que agregar `--proyecto RUTA`.
- Se detiene si cambió una entrada del repositorio o un motor original, o si alguna salida no coincide con su referencia archivada.
- Sin openpyxl corre igual, pero entrega el corpus sin revisión humana y lo advierte.

## Qué se reproduce y qué no

**Se reproduce exactamente:**
- filtro amplio, reglas v6–v9 y reglas de Nivel 1;
- integración, PRISMA y verificación;
- aplicación de la revisión humana y concordancia;
- tablas y redes descriptivas.

**Entradas registradas, no regeneradas:**
- las decisiones de lectura dirigida de título y resumen (`04_integracion_final/entrada/lectura_dirigida/`);
- las planillas completadas (`05_cierre_revision/planillas/`);
- las traducciones.

El código reproduce su integración, no la lectura.

**No se reutiliza nada del flujo anterior:** ni las auditorías IA, ni las decisiones humanas, ni las cifras del piloto.

**Conteos no disponibles:** los de Scopus y WoS previos a su deduplicación interna no están en los archivos de integración y no se estiman.

**Figuras e informe Word:** no se cotejan por huella, porque matplotlib y Word registran metadatos de versión y fecha. Se regeneran con:

```powershell
py -3 06_descriptivos/10_generar_graficos_informe.py
py -3 06_descriptivos/11_generar_informe.py
```

## Qué significan los resultados

- **INCLUIDO (Nivel 1):** estudia procesos, equipos, actividades o decisiones de la operación a cielo abierto, con el rajo como foco central.
  - Geotecnia, vibraciones y agua entran solo con vínculo operacional.
  - Componentes, solo de equipos de la mina.
  - Las plantas quedan fuera.
- **Núcleo IN:** además de estar incluida, la publicación vincula una tarea o un equipo del rajo (A) con una evaluación propia (B) y un resultado operacional (C).
- **EXCLUIDO:** cada exclusión indica su etapa (`filtro_amplio`, `cribado_pertinencia_operacional` o `revision_humana`), un motivo y una justificación.

## Si se modifican las planillas o se calibra

1. Reemplazar las planillas en `05_cierre_revision/planillas/`, o las decisiones en `entrada/lectura_dirigida/`.
2. Ejecutar `00_reproducir_local.py` en una carpeta nueva. El cotejo con lo archivado fallará: eso es lo esperado.
3. Copiar las nuevas salidas a los `salida_archivada/` correspondientes, y las tablas y redes a `06_descriptivos/`.
4. Actualizar `huellas_sha256.json` y regenerar `MANIFIESTO_SHA256.json`.
5. Volver a ejecutar, hasta que todo coincida.

Una calibración debe validarse con una muestra nueva: `07_preparar_planillas.py --semilla OTRA --salida planillas_v2`.

## Siguiente trabajo

1. **Opcional:** calibrar el cribado y reforzar la validación con una submuestra revisada sin IA.
2. Definir de 3 a 5 grupos temáticos emergentes a partir del corpus incluido.
3. Extraer variables del núcleo: equipo (principal o auxiliar), indicador, método y tipo de datos.
4. Contrastar H1–H3. Las hipótesis no se usaron para decidir inclusiones.
