# IPRE-M-DCC

Repositorio de código para la obtención y el procesamiento de datos bibliográficos provenientes de **OpenAlex**, **Scopus** y **Web of Science (WoS)**.

## Objetivo

Analizar la literatura sobre operaciones mineras a cielo abierto, con especial interés en la planificación, asignación y utilización de equipos y actividades auxiliares.

## Alcance del procesamiento

El flujo contempla la obtención y preparación de metadatos, deduplicación, filtrado temático, cribado de publicaciones y generación de resultados descriptivos, gráficos e informes. Se conservan las decisiones y los motivos de clasificación para revisar su evolución.

## Estado del proyecto

- **OpenAlex:** flujo de referencia desarrollado por Joaquín.
- **Scopus:** flujo adaptado y reproducción local comprobada. La validación humana independiente permanece pendiente.
- **Web of Science:** exportación manual y procesamiento local realizados, con cribado automático y resultados descriptivos generados. La revisión humana independiente permanece pendiente y la extracción mediante API continúa en evaluación.

Las cohortes se mantienen separadas y se utilizan criterios de cribado comparables. Las decisiones humanas de una fuente no se trasladan automáticamente a las demás.

## Ejecución y resultados

Las instrucciones de ejecución se encuentran en la documentación de cada paquete.

Scopus utiliza páginas JSON previamente guardadas para su reproducción local. WoS utiliza los archivos exportados manualmente. Estos procesos locales no requieren nuevas consultas a las respectivas API.

Las clasificaciones automáticas son resultados preliminares. La reproducción técnica no equivale a validación académica ni a revisión de texto completo.

## Documentación y datos

Los documentos y archivos asociados al proyecto se encuentran disponibles en [OneDrive](https://uccl0-my.sharepoint.com/:f:/g/personal/dpmunoz7_uc_cl/IgA3vjPfjPjIT4JlB-FXFnTdAfUi-_7iwYc_JCYEWEUt1ko?e=a4DZLa).

## Credenciales

El repositorio no debe contener claves de API ni otros datos de acceso.
