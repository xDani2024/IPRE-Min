# 05_descriptivos — WoS (homologación de IPRE_codigo)

Esta carpeta reproduce la etapa descriptiva `05_descriptivos` del proyecto original `IPRE_codigo`: **gráficos + estadísticas + informe Word**, adaptados exclusivamente a las matrices de Web of Science. No modifica el cribado, no usa API y no importa decisiones humanas desde OpenAlex.

## Requisitos

- Python 3.10 o superior.
- Instalar (solo una vez) desde la **carpeta raíz del proyecto**:

```powershell
py -3 -m pip install -r 05_descriptivos/requirements.txt
```

## Generar todo en un paso

Ubicándose en la **carpeta raíz** (junto a `00_ejecutar_cribado_wos.py`):

```powershell
py -3 05_descriptivos/00_generar_descriptivos.py --resultados resultados_cribado_wos_nueva
```

Si usa los resultados incluidos en el ZIP:

```powershell
py -3 05_descriptivos/00_generar_descriptivos.py --resultados resultados_cribado_wos
```

La opción `--resultados` debe ser el nombre exacto de la carpeta de cribado existente (o su ruta absoluta). Los generadores no repiten el cribado: leen la matriz v9 y el manifiesto generado por `00_ejecutar_cribado_wos.py`.

Si prefiere ejecutar los pasos por separado:

```powershell
py -3 05_descriptivos/24_generar_graficos.py --resultados resultados_cribado_wos_nueva
py -3 05_descriptivos/25_generar_avance.py --resultados resultados_cribado_wos_nueva
```

## Archivos generados

- `graficos/01_flujo_del_estudio.png`
- `graficos/02_versiones_del_cribado.png`
- `graficos/03_cierre_de_TC.png`
- `graficos/04_publicaciones_por_ano.png`
- `graficos/05_menciones_de_procesos.png`
- `graficos/06_menciones_de_equipos.png`
- `graficos/07_focos_en_cada_base.png`
- `graficos/08_muestra_pendiente_revision_humana.png`
- `Resultados_descriptivos_amplio_y_v9_WoS.json`
- `informe/Informe_avance_IPRE_WoS_preliminar.docx`

## Diferencia respecto a `IPRE_codigo`

El octavo gráfico del original presenta una **calibración humana ya realizada**. En WoS esa revisión todavía está pendiente. El octavo gráfico de este paquete muestra solamente la **distribución prevista de la muestra de 130 publicaciones** y nunca representa una calibración efectuada.

El informe identifica explícitamente los **168 IN** como *propuestas automáticas v9* y los **917 TC** como *resueltos exclusivamente por reglas*. No señala que los resultados hayan sido validados por personas, ni que se haya consultado texto completo. Los conteos de procesos, equipos y focos son **etiquetas automáticas no excluyentes** y no temas centrales comprobados.

## Reproducibilidad

- El generador comprueba la correspondencia de UID de la matriz con la base amplia original y compara el SHA-256 con `RESUMEN_FLUJO_WOS.json`.
- Al generar un documento a partir de otro directorio de resultados, debe pasar su nombre con `--resultados` en las dos etapas. Esto impide mezclar el informe de una corrida con los gráficos de otra.
- Para guardar los gráficos e informe en otra ubicación del proyecto, use también `--salida ruta_relativa_al_proyecto`.

Los archivos incluidos en el ZIP se generaron con la carpeta `resultados_cribado_wos`, que reproduce los resultados automáticos publicados del proyecto. La muestra humana sigue pendiente.
