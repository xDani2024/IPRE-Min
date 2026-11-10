"""Muestreo trazable y comparaciones del cribado, sin etiquetas humanas fingidas."""
from __future__ import annotations
import csv
import hashlib
from collections import Counter
from pathlib import Path

CASOS_CENTINELA = {
    'IPRE-UNIVERSO-009763': 'vehiculos_auxiliares_rutas',
    'IPRE-UNIVERSO-003333': 'perforacion_drillability',
    'IPRE-UNIVERSO-007128': 'perforacion_productividad',
    'IPRE-UNIVERSO-000256': 'feria_industrial_no_estudio',
}
CUOTAS = {'CANDIDATO':40,'EXCLUSION_PROPUESTA':60,'REVISION_PRIORITARIA':50,'PENDIENTE_REVISION':30}


def leer(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def muestra_estratificada(registros):
    """Muestra determinista, no aleatoria a cada ejecución.

    Conserva ejemplos de fallo identificados, pero NO infiere respuesta humana.
    """
    result = []
    for estado, cuota in CUOTAS.items():
        pool = [r for r in registros if r['cribado_automatico'] == estado]
        # Muestreo pseudoaleatorio reproducible dentro de cada grupo.
        pool.sort(key=lambda r: hashlib.sha256(
            ('IPRE-cribado-v1.1:' + r['id_publicacion']).encode('utf8')).hexdigest())
        result.extend((r, 'muestra_estratificada') for r in pool[:cuota])
    ids = {r['id_publicacion'] for r, _ in result}
    for r in registros:
        if r['id_publicacion'] in CASOS_CENTINELA and r['id_publicacion'] not in ids:
            result.append((r, 'caso_centinela:' + CASOS_CENTINELA[r['id_publicacion']]))
            ids.add(r['id_publicacion'])
    salidas = []
    for r, motivo in result:
        salidas.append({k: r.get(k,'') for k in [
            'id_publicacion','titulo','resumen','tipo_documento','fuentes','numero_fuentes',
            'cribado_automatico','motivos_cribado','evidencia_contexto_minero',
            'evidencia_proceso_equipo','evidencia_objetivo','prioridad_revision']}
            | {'seleccion_muestra':motivo,'decision_humana':'','motivo_decision_humana':'',
               'revisor':'','fecha_revision':''})
    return salidas


def comparar(registros, matriz_anterior):
    if not Path(matriz_anterior).is_file():
        return [], {'disponible':False,'nota':'No se encontró el archivo del cribado anterior. No se infiere comparación.'}
    anteriores = {r['id_publicacion']:r for r in leer(matriz_anterior)}
    cambios = []
    for r in registros:
        v = anteriores.get(r['id_publicacion'])
        if v is None or v.get('cribado_automatico') == r['cribado_automatico']:
            continue
        cambios.append({
            'id_publicacion':r['id_publicacion'], 'titulo':r['titulo'], 'fuentes':r['fuentes'],
            'estado_anterior':v.get('cribado_automatico',''), 'motivo_anterior':v.get('motivos_cribado',''),
            'estado_actual':r['cribado_automatico'], 'motivo_actual':r['motivos_cribado'],
            'revisar_cambio':'', 'observaciones':'',
        })
    suma=Counter((r['estado_anterior'],r['estado_actual']) for r in cambios)
    return cambios, {'disponible':True,'total_registros_anteriores':len(anteriores),
                     'cambios':len(cambios),
                     'transiciones':[{'desde':a,'hacia':b,'cantidad':v} for (a,b),v in sorted(suma.items())],
                     'nota':'Los cambios no son mejoras confirmadas hasta la revisión humana.'}
