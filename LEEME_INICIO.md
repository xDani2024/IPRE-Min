# IPRE-Min — unificación bibliográfica reproducible (2026-11-09)

**Punto de entrada recomendado:** `integracion_corpus/README_UNIFICACION_VALIDADA.md`.

Desde `IPRE-Min-main`, ejecutar:

```bat
python integracion_corpus/unificacion_validada.py --etapa ambas
python -m unittest discover -s integracion_corpus/pruebas -p "test_*.py"
python -m unittest discover -s flujo_unificado/pruebas -p "test_*.py"
```

Esta operación **sí aplica fusiones y restricciones de identidad bibliográfica** sobre las instantáneas originales de OpenAlex, Scopus y WoS y produce `integracion_corpus/resultados_validados/`. La auditoría de 791 alertas, sus decisiones y las fechas originales permanecen reproducibles desde `flujo_unificado/`.

**No realiza cribado temático**, no reincorpora automáticamente los 105 registros excluidos por el filtro original y no resuelve forzosamente las alertas bibliográficas 0111, 0500, 0529, 0534 ni los seguimientos 0467 y 0519.

El comando anterior `python flujo_unificado/main.py --solo-revision-bibliografica` únicamente reproduce la auditoría y **no aplica** la unificación; úselo para verificar decisiones, no para crear el corpus consolidado.
