# IPRE-M-DCC

Repositorio de código para la extracción y el procesamiento de datos bibliográficos provenientes de **OpenAlex** y **Scopus**, con futura incorporación de **Web of Science (WoS)**.

## Objetivo

Analizar la literatura sobre operaciones mineras a cielo abierto, con especial interés en la planificación, asignación y utilización de equipos y actividades auxiliares.

## Alcance del procesamiento

El flujo contempla la extracción de metadatos, deduplicación, filtrado temático, cribado de publicaciones y generación de resultados descriptivos. Se conservan las decisiones y los motivos de clasificación para revisar su evolución.

## Estado del proyecto

- **OpenAlex:** flujo de referencia desarrollado por Joaquín.
- **Scopus:** flujo adaptado y reproducción local comprobada. La validación humana independiente permanece pendiente.
- **Web of Science:** pruebas de conexión realizadas. La extracción de registros completos con resúmenes permanece pendiente por restricciones de acceso o cuota.

Las cohortes se mantienen separadas. Las decisiones humanas de OpenAlex no se trasladan automáticamente a Scopus.

## Ejecución y resultados

Las instrucciones específicas de ejecución se encuentran en la documentación de cada paquete.

La reproducción local de Scopus utiliza páginas JSON previamente guardadas y no requiere una API key. Una nueva extracción requiere credenciales propias y puede generar conteos diferentes.

Las clasificaciones automáticas son propuestas preliminares. La reproducción técnica no equivale a validación académica ni a revisión de texto completo.

## Documentación y datos

Los documentos y archivos asociados al proyecto se encuentran disponibles en [OneDrive](https://uccl0-my.sharepoint.com/:f:/g/personal/dpmunoz7_uc_cl/IgA3vjPfjPjIT4JlB-FXFnTdAfUi-_7iwYc_JCYEWEUt1ko?e=a4DZLa).

## Credenciales

El repositorio no debe contener claves de API ni otros datos de acceso.
