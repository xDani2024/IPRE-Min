#!/usr/bin/env python3
"""Cruce auditable entre el cribado histórico v9 por fuente y el cribado unificado.

La decisión v9 es computacional/preliminar salvo revisión humana específica comprobada.
No modifica ni utiliza v9 como etiqueta del clasificador del corpus consolidado.
Solo compara ID bibliográficos exactos dentro de cada fuente (sin fuzzy matching).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUTAS_V9 = {s: HERE / 'entrada_historial_v9' / (s.lower() + '_v9.csv')
            for s in ('OpenAlex', 'Scopus', 'WoS')}


def leer(path: Path) -> list[dict[str, str]]:
    with path.open('r', newline='', encoding='utf-8-sig') as h:
        return list(csv.DictReader(h))


def guardar(path: Path, rows: list[dict], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as h:
        w = csv.DictWriter(h, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(1 << 20), b''):
            h.update(part)
    return h.hexdigest()


def diagnostico(estados: list[str], estado_actual: str) -> tuple[str, str]:
    """Cruza propuestas, sin transformar ninguna en selección definitiva."""
    s = set(estados)
    if 'IN' in s and 'OUT' in s:
        return 'CONTRADICCION_V9_ENTRE_FUENTES', 'ALTA'
    if 'IN' in s and estado_actual == 'EXCLUSION_PROPUESTA':
        return 'V9_IN_ACTUAL_EXCLUSION_PROPUESTA', 'ALTA'
    if 'IN' in s and estado_actual in ('PENDIENTE_REVISION', 'REVISION_PRIORITARIA'):
        return 'V9_IN_ACTUAL_PENDIENTE_O_PRIORITARIA', 'ALTA'
    if 'OUT' in s and estado_actual == 'CANDIDATO':
        return 'V9_OUT_ACTUAL_CANDIDATO', 'MEDIA'
    if 'IN' in s and estado_actual == 'CANDIDATO':
        return 'V9_IN_ACTUAL_CANDIDATO', 'MEDIA'
    if not s:
        return 'SIN_DECISION_V9', 'NORMAL'
    return 'RESTO_SIN_CONTRADICCION_DIRECTA', 'NORMAL'


def ejecutar(resultados: Path, salida: Path, rutas_v9: dict[str, Path] | None = None) -> dict:
    rutas = {k: Path(v) for k, v in (rutas_v9 or RUTAS_V9).items()}
    base = resultados / '02_integracion_y_deduplicacion'
    ruta_correspondencias = base / '03_correspondencias_procedencia.csv'
    ruta_corpus = base / '02_corpus_consolidado_provisional.csv'
    ruta_cribado = resultados / '03_cribado_comun' / '01_matriz_cribado_automatico.csv'
    correspondencias = leer(ruta_correspondencias)
    corpus = leer(ruta_corpus)
    cribado = leer(ruta_cribado)
    ruta_normalizados = base / '01_registros_normalizados.csv'
    ruta_alertas = base / '04_alertas_revision.csv'
    normalizados = {r['registro_uid']:r for r in leer(ruta_normalizados)}
    alertas = leer(ruta_alertas)
    # Las huellas y campos bibliográficos deben coincidir con la base de referencia.
    from sys import path as pythonpath
    import sys
    pythonpath.insert(0, str(HERE.parent / 'integracion_corpus'))
    from normalizacion import normalizar_doi, normalizar_titulo

    idx_correspondencias = {r['registro_uid']: r for r in correspondencias}
    if len(idx_correspondencias) != len(correspondencias):
        raise ValueError('Hay identificadores de registro duplicados en correspondencias.')
    if len({r['id_publicacion'] for r in corpus}) != len(corpus):
        raise ValueError('Los id_publicacion no son únicos.')
    idx_cribado = {r['id_publicacion']: r for r in cribado}
    if len(idx_cribado) != len(corpus):
        raise ValueError('La matriz de cribado no contiene exactamente una fila por publicación.')
    if set(idx_cribado) != {r['id_publicacion'] for r in corpus}:
        raise ValueError('Los identificadores de corpus y cribado no coinciden.')

    historias = []
    encontrados = defaultdict(list)
    fuente_conteos = {}
    duplicados_historicos = []
    sin_cruce = []
    incongruencias_metadatos = []
    for source in ('OpenAlex', 'Scopus', 'WoS'):
        ruta = rutas[source]
        rows = leer(ruta)
        fuente_conteos[source] = {'total_v9': len(rows), 'in_v9': sum(r['decision_v9_propuesta']=='IN' for r in rows),
                                  'out_v9': sum(r['decision_v9_propuesta']=='OUT' for r in rows)}
        vistos = set()
        for r in rows:
            key = source + '::' + r['id_fuente']
            if key in vistos:
                duplicados_historicos.append(key)
                continue
            vistos.add(key)
            referencia = idx_correspondencias.get(key)
            destino = referencia['id_publicacion'] if referencia else ''
            estado = idx_cribado[destino]['cribado_automatico'] if destino else ''
            if referencia:
                nr=normalizados[key]
                if (normalizar_doi(r['doi_original']) != nr['doi_normalizado']
                    or normalizar_titulo(r['titulo_original']) != nr['titulo_normalizado']
                    or str(r['anio_original']).strip() != nr['anio']):
                    incongruencias_metadatos.append(key)
            cruce = {**r, 'registro_uid': key, 'id_publicacion': destino, 'cribado_unificado_v1_1': estado,
                     'resultado_vinculacion': 'ID_EXACTO' if referencia else 'SIN_VINCULACION'}
            historias.append(cruce)
            if referencia:
                encontrados[destino].append(cruce)
            else:
                sin_cruce.append(cruce)
    if duplicados_historicos:
        raise ValueError(f'IDs históricos duplicados: {len(duplicados_historicos)}')
    if incongruencias_metadatos:
        raise ValueError(f'Las instantáneas v9 presentan {len(incongruencias_metadatos)} discrepancias de DOI, título o año respecto de los universos actuales.')

    coincidencias = []
    prioridades = []
    for r in corpus:
        pid = r['id_publicacion']
        hist = sorted(encontrados.get(pid, []), key=lambda x: (x['fuente'], x['id_fuente']))
        estados = [h['decision_v9_propuesta'] for h in hist if h['decision_v9_propuesta'] in ('IN','OUT')]
        estado_nuevo = idx_cribado[pid]['cribado_automatico']
        diagnost, priority = diagnostico(estados, estado_nuevo)
        sources_in = sorted({h['fuente'] for h in hist if h['decision_v9_propuesta']=='IN'})
        sources_out = sorted({h['fuente'] for h in hist if h['decision_v9_propuesta']=='OUT'})
        decisions = {h['fuente']: h['decision_v9_propuesta'] for h in hist}
        human = {h['fuente']: h['decision_humana_historica'] for h in hist if h['decision_humana_historica']}
        row = {
            'id_publicacion': pid, 'titulo': r['titulo'], 'doi': r['doi'], 'anio': r['anio_referencia'],
            'fuentes': r['fuentes'], 'numero_fuentes': r['numero_fuentes'],
            'cribado_unificado_v1_1': estado_nuevo, 'numero_registros_v9': len(hist),
            'decision_v9_openalex': decisions.get('OpenAlex','SIN_HISTORIAL'),
            'decision_v9_scopus': decisions.get('Scopus','SIN_HISTORIAL'),
            'decision_v9_wos': decisions.get('WoS','SIN_HISTORIAL'),
            'fuentes_con_in_v9': '|'.join(sources_in), 'fuentes_con_out_v9':'|'.join(sources_out),
            'n_in_v9': len(sources_in), 'n_out_v9': len(sources_out),
            'decision_humana_historica_registrada_json': json.dumps(human, sort_keys=True,ensure_ascii=False),
            'diagnostico_cruce': diagnost, 'prioridad_revision': priority,
            'decision_humana_final': '', 'justificacion_revision': '',
        }
        coincidencias.append(row)
        if priority in ('ALTA','MEDIA'):
            prioridades.append(row)

    # Mantener la clave del corpus original para vincular con la plantilla de revisión humana.
    prioridades.sort(key=lambda r: (0 if r['prioridad_revision']=='ALTA' else 1,
                                    -int(r['n_in_v9']),r['id_publicacion']))
    salida.mkdir(parents=True, exist_ok=True)
    guardar(salida/'01_cruce_por_registro.csv', historias, list(historias[0]))
    guardar(salida/'02_cruce_por_publicacion.csv', coincidencias, list(coincidencias[0]))
    guardar(salida/'03_casos_para_revisar.csv', prioridades, list(prioridades[0]))
    if sin_cruce:
        guardar(salida/'04_historicos_sin_correspondencia.csv', sin_cruce, list(sin_cruce[0]))

    # Las alertas históricas de deduplicación se presentan junto a los metadatos
    # y los estados v9 para facilitar decisiones bibliográficas posteriores.
    hist_por_uid = {r['registro_uid']:r for r in historias}
    alertas_enriquecidas = []
    for j, alerta in enumerate(alertas, 1):
        uid_a = alerta['registro_a']
        ids_b = [u for u in alerta['registro_b'].split('|') if u]
        a = normalizados.get(uid_a, {})
        bb = [normalizados.get(u, {}) for u in ids_b]
        grado = ('ALTA' if alerta['tipo'] in ('DOI_TITULOS_O_ANIOS_DIVERGENTES',
                                        'TITULO_ANIO_DOI_CONFLICTIVOS',
                                        'MULTIPLES_IDS_MISMA_FUENTE_REVISAR',
                                        'GRUPO_DOIS_MULTIPLES_REVISAR') else
                 'MEDIA' if alerta['tipo'] == 'TITULO_CON_ANIOS_DISTINTOS' else 'NORMAL')
        alertas_enriquecidas.append({
            'id_alerta':f'ALERTA-{j:04d}', 'tipo_alerta':alerta['tipo'],
            'prioridad':grado, 'registro_a':uid_a,'titulo_a':a.get('titulo',''),
            'anio_a':a.get('anio',''),'doi_a':a.get('doi_normalizado',''),
            'v9_a':hist_por_uid.get(uid_a,{}).get('decision_v9_propuesta','SIN_HISTORIAL'),
            'registros_b':'|'.join(ids_b),
            'titulos_b_json':json.dumps([b.get('titulo','') for b in bb],ensure_ascii=False),
            'anios_b':'|'.join(b.get('anio','') for b in bb),
            'dois_b':'|'.join(b.get('doi_normalizado','') for b in bb),
            'decisiones_v9_b':'|'.join(hist_por_uid.get(u,{}).get('decision_v9_propuesta','SIN_HISTORIAL') for u in ids_b),
            'detalle_original':alerta['detalle'],
            'decision_bibliografica_humana':'', 'justificacion':'', 'revisor':'', 'fecha_revision':'',
        })
    if alertas_enriquecidas:
        guardar(salida/'06_alertas_deduplicacion_para_revisar.csv',alertas_enriquecidas,list(alertas_enriquecidas[0]))
    # Resumen distingue 977 registros IN antiguos del número de publicaciones únicas.
    resumen = {
        'version_cruce': '1.0',
        'n_registros_provenientes_de_v9': len(historias),
        'registros_v9_sin_correspondencia':len(sin_cruce),
        'discrepancias_metadatos_v9_vs_universo': len(incongruencias_metadatos),
        'alertas_deduplicacion_para_revisar':len(alertas_enriquecidas),
        'n_publicaciones_unicas_del_corpus': len(coincidencias),
        'fuentes': fuente_conteos,
        'registros_in_v9_total': sum(r['in_v9'] for r in fuente_conteos.values()),
        'publicaciones_unicas_con_al_menos_un_in_v9': sum(bool(r['n_in_v9']) for r in coincidencias),
        'publicaciones_unicas_con_in_v9_y_out_v9':sum(bool(r['n_in_v9']) and bool(r['n_out_v9']) for r in coincidencias),
        'comparacion_estado_nuevo_para_publicaciones_con_in_v9':dict(sorted(Counter(r['cribado_unificado_v1_1'] for r in coincidencias if r['n_in_v9']).items())),
        'resumen_diagnosticos':dict(sorted(Counter(r['diagnostico_cruce'] for r in coincidencias).items())),
        'prioridades':dict(sorted(Counter(r['prioridad_revision'] for r in coincidencias).items())),
        'sha256_entradas':{str(p.relative_to(HERE)) if p.is_relative_to(HERE) else str(p):hash_file(p)
                          for p in [ruta_correspondencias,ruta_corpus,ruta_cribado,ruta_normalizados,ruta_alertas,*rutas.values()]},
        'limitaciones':[
            'IN y OUT históricos de v9 son propuestas computacionales; no se convierten en decisiones humanas.',
            'Los historiales v9 cubren bases amplias, no todos los registros del universo bibliográfico.',
            'El cruce se realiza por ID de fuente exacto, no mediante parecido textual ni inferencias.',
            'Los identificadores IPRE-UNIVERSO-XXXXXX son ordinales y pueden cambiar al actualizar el corpus; relacionar mediante registro_uid.',
            'Las alertas de deduplicación de la versión integrada todavía requieren revisión humana.',
            'Las clasificaciones temáticas definitivas se elaboran después del cribado humano.',
        ],
    }
    resumen['sha256_salidas'] = {p.name:hash_file(p) for p in sorted(salida.glob('*.csv'))}
    (salida/'05_resumen_cruce_v9.json').write_text(json.dumps(resumen, ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('Cruce v9:',len(historias),'registros históricos; correspondencias no halladas:',len(sin_cruce))
    print('IN v9 (registros):',resumen['registros_in_v9_total'])
    print('IN v9 (publicaciones únicas):',resumen['publicaciones_unicas_con_al_menos_un_in_v9'])
    print('Estados actuales de publicaciones con algún IN v9:',resumen['comparacion_estado_nuevo_para_publicaciones_con_in_v9'])
    print('Diagnósticos:',resumen['resumen_diagnosticos'])
    return resumen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resultados',type=Path,default=HERE/'resultados_calibracion_v1_1')
    parser.add_argument('--salida',type=Path,default=None)
    a=parser.parse_args()
    ejecutar(a.resultados, a.salida or a.resultados/'07_cruce_historico_v9')


if __name__ == '__main__':
    main()
