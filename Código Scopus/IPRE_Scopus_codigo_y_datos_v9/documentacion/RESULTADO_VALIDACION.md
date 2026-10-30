# Validación de la entrega

La cadena completa se ejecutó desde las 432 páginas JSON originales de Scopus, sin red ni API key.

- Base amplia: 4.614 publicaciones.
- Pre-cierre v9: 390 IN, 4.224 OUT y 0 TC computacionales.
- 26 CSV regenerados idénticos byte a byte a sus referencias archivadas, mediante SHA-256.
- Las columnas y filas v8 se conservan íntegramente en v9.
- Nueve cotejos de funciones principales con Joaquín superados, comparando AST sin docstrings.
- Todas las subcarpetas del paquete de Joaquín están presentes.
- Ocho gráficos y avance Word regenerados por el ejecutor central.
- No se incorporaron auditorías ni decisiones humanas de OpenAlex.

La revisión humana y los controles documentales indicados en los manifiestos siguen pendientes. El JSON `Verificacion_cadena_completa.json` contiene los hashes de cada cotejo. Las bitácoras de validación se conservan en `documentacion/bitacoras_verificacion/`.
