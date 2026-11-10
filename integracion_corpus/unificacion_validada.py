#!/usr/bin/env python3
"""Unificación de identificadores bibliográficos, sin cribado temático.

Parte de instantáneas congeladas. Aplica primero vínculos humanos aprobados, respeta
separaciones y pendientes, y añade sólo vínculos automáticos compatibles. Usa UID
estables, no identificadores ordinales de alertas. Nunca cambia fuentes originales.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from deduplicacion import vincular
from fuentes import RUTAS, leer_corpus
from normalizacion import hash_archivo

ROOT = Path(__file__).resolve().parents[1]
DIR = Path(__file__).resolve().parent
FLUJO = ROOT / 'flujo_unificado'
sys.path.insert(0, str(FLUJO))
from reproducir_revision_bibliografica import auditar  # noqa: E402


def leer_csv(path):
    with Path(path).open('r', newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def escribir_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def escribir_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')


def id_estable(uids):
    txt = '\n'.join(sorted(uids))
    return 'IPRE-U-' + hashlib.sha256(txt.encode('utf-8')).hexdigest()[:20].upper()


class AgrupadorSeguro:
    """DSU con restricciones no-fusionar, incluidas las indirectas."""
    def __init__(self, registros, bloqueos):
        self.p = list(range(len(registros)))
        self.size = [1] * len(registros)
        self.members = [{i} for i in range(len(registros))]
        self.sources = [{r['fuente']} for r in registros]
        self.registros = registros
        self.bloqueos = set((min(a, b), max(a, b)) for a,b in bloqueos if a != b)
        self.razones = {pair: [] for pair in self.bloqueos}

    def find(self, a):
        if self.p[a] != a:
            self.p[a] = self.find(self.p[a])
        return self.p[a]

    def fusionar(self, a, b, aprobado=False):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return True, 'YA_MISMO_GRUPO'
        if not aprobado and self.sources[ra] & self.sources[rb]:
            return False, 'MISMA_FUENTE_SIN_AUTORIZACION'
        small, large = (ra, rb) if len(self.members[ra]) < len(self.members[rb]) else (rb, ra)
        for x in self.members[small]:
            for y in self.members[large]:
                if (min(x,y), max(x,y)) in self.bloqueos:
                    return False, 'SEPARACION_O_CASO_PENDIENTE'
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.p[rb] = ra
        self.size[ra] += self.size[rb]
        self.members[ra].update(self.members[rb])
        self.members[rb].clear()
        self.sources[ra].update(self.sources[rb])
        self.sources[rb].clear()
        return True, 'FUSION_APROBADA' if aprobado else 'VINCULO_AUTOMATICO'

    def grupos(self):
        return [sorted(m) for m in self.members if m]


def unificar(raiz=ROOT, salida=None, etapa='universo', normalizacion='unicode_v2',
            salida_auditoria=None):
    raiz = Path(raiz).resolve()
    salida = (Path(salida) if salida else raiz/'integracion_corpus'/'resultados_validados'/etapa).resolve()
    if etapa not in RUTAS:
        raise ValueError('Etapa no reconocida')
    if normalizacion != 'unicode_v2':
        raise ValueError('La unificación validada exige Unicode v2; modo histórico sólo para reconstruir alertas')
    auditoria = (Path(salida_auditoria) if salida_auditoria else raiz/'flujo_unificado'/'auditoria_revision_aprobada').resolve()
    if salida == auditoria or auditoria in salida.parents or salida in auditoria.parents:
        raise ValueError('La salida no puede sobrescribir decisiones ni auditoría')
    # Verificar huellas de entrada y reconstruir la revisión humana a partir de su origen.
    informe_aprobadas = auditar(raiz=raiz, salida=auditoria, validar_fuentes=True)
    registros, entradas = leer_corpus(raiz, etapa, normalizacion_titulos=normalizacion)
    indices = {r['registro_uid']: i for i,r in enumerate(registros)}
    if len(indices) != len(registros):
        raise ValueError('UID duplicados en los datos originales')

    aristas_humanas = leer_csv(auditoria/'02_aristas_fusion_aprobadas_NO_APLICAR.csv')
    aristas_no = leer_csv(auditoria/'03_restricciones_no_fusionar.csv')
    pendientes = leer_csv(auditoria/'10_pendientes_bibliograficos.csv')
    relaciones = leer_csv(auditoria/'11_relaciones_no_fusionar.csv')
    matriz = leer_csv(auditoria/'01_decisiones_bibliograficas.csv')
    alertas_uid = defaultdict(set)
    for r in matriz:
        for uid in r['registro_uids'].split('|'):
            alertas_uid[uid].add(r['id_alerta'])
    bloqueo_indices, det_bloqueos = set(), []
    for r in aristas_no:
        a, b = r['registro_uid_a'], r['registro_uid_b']
        if a in indices and b in indices:
            bloqueo_indices.add((indices[a], indices[b]))
            det_bloqueos.append({**r, 'motivo': 'SEPARACION_APROBADA'})
    # Un pendiente no puede fusionarse por heurística mientras esté sin dictamen.
    for r in pendientes:
        uids = [uid for uid in r['registro_uids'].split('|') if uid in indices]
        for i, a in enumerate(uids):
            for b in uids[i+1:]:
                bloqueo_indices.add((indices[a], indices[b]))
                det_bloqueos.append({'id_alerta': r['id_alerta'], 'registro_uid_a':a,
                    'registro_uid_b':b, 'caracter':'SIN_DICTAMEN', 'estado':'PENDIENTE',
                    'motivo':'ALERTA_PENDIENTE_NO_FUSIONAR_AUTOMATICAMENTE'})
    uf = AgrupadorSeguro(registros, bloqueo_indices)
    log = []
    aplicadas = 0
    aristas_aprobadas_fuera_etapa = 0
    for e in aristas_humanas:
        a,b = e['registro_uid_a'],e['registro_uid_b']
        if a not in indices or b not in indices:
            if etapa == 'universo':
                raise ValueError(f'Decisión aprobada con UID inexistente en el universo: {e}')
            aristas_aprobadas_fuera_etapa += 1
            continue
        ok, razon = uf.fusionar(indices[a], indices[b], aprobado=True)
        if not ok:
            raise ValueError(f'Incompatibilidad entre decisiones aprobadas: {e} ({razon})')
        if razon == 'FUSION_APROBADA':
            aplicadas += 1
        log.append({'etapa':etapa,'registro_uid_a':a,'registro_uid_b':b,
                    'origen':'HUMANO_APROBADO', 'id_alerta':e['id_alerta'],
                    'resultado':razon, 'aplicado':'SI'})

    # Las propuestas automáticas se calculan sobre los mismos registros y normalización
    # Unicode, sin recurrir a los IDs secuenciales de publicaciones provisionales.
    grupos_propuestos, alertas_auto, _ = vincular(registros)
    propuestas = []
    for grupo in grupos_propuestos:
        if len(grupo) > 1:
            piv = min(grupo, key=lambda i: registros[i]['registro_uid'])
            for idx in sorted((i for i in grupo if i != piv), key=lambda i: registros[i]['registro_uid']):
                propuestas.append((registros[piv]['registro_uid'], registros[idx]['registro_uid']))
    # Primero las propuestas en orden determinista por UID, no por orden de entrada.
    rechazadas = Counter()
    auto_aplicados = 0
    auto_ya = 0
    for a,b in sorted(propuestas):
        ok, razon = uf.fusionar(indices[a], indices[b], aprobado=False)
        if not ok:
            rechazadas[razon] += 1
        elif razon == 'VINCULO_AUTOMATICO':
            auto_aplicados += 1
        else:
            auto_ya += 1
        log.append({'etapa':etapa,'registro_uid_a':a,'registro_uid_b':b,
                    'origen':'AUTOMATICO_CONSERVADOR', 'id_alerta':'',
                    'resultado':razon,'aplicado':'SI' if ok else 'NO'})

    grupos = uf.grupos()
    grupos.sort(key=lambda g: id_estable(registros[i]['registro_uid'] for i in g))
    nombres = set()
    corpus, procedencia, map_uid_pid = [], [], {}
    human_uid = {r['registro_uid_a'] for r in aristas_humanas} | {r['registro_uid_b'] for r in aristas_humanas}
    for g in grupos:
        uids = [registros[i]['registro_uid'] for i in g]
        pid = id_estable(uids)
        if pid in nombres:
            raise ValueError('Colisión en ID estable')
        nombres.add(pid)
        rows = [registros[i] for i in g]
        for uid in uids:
            map_uid_pid[uid] = pid
        dois = sorted({r['doi_normalizado'] for r in rows if r['doi_normalizado']})
        años = sorted({r['anio'] for r in rows if r['anio']})
        fuentes = sorted({r['fuente'] for r in rows})
        titulo = max(rows, key=lambda r:(len(r['titulo']),r['registro_uid']))['titulo']
        resumen = max(rows, key=lambda r:(len(r['resumen']),r['registro_uid']))
        anio_ref = sorted(años, key=lambda x:(-sum(r['anio']==x for r in rows),x))[0] if años else ''
        revision = sorted(set.union(*(alertas_uid.get(u, set()) for u in uids))) if uids else []
        tiene_pendiente = any(r['id_alerta'] in revision for r in pendientes)
        estado = ('PENDIENTE_BIBLIOGRAFICO_PARCIAL' if tiene_pendiente else
                  'FUSION_APROBADA' if any(u in human_uid for u in uids) and len(g)>1 else
                  'VINCULACION_AUTOMATICA' if len(g)>1 else 'UNICO_SIN_FUSION')
        row = {'id_publicacion':pid,'titulo':titulo,'anio_referencia':anio_ref,
               'anios_observados':'|'.join(años),
               'doi':dois[0] if len(dois)==1 else '',
               'dois_observados':'|'.join(dois),
               'autores':max(rows,key=lambda r:(len(r['autores']),r['registro_uid']))['autores'],
               'revista':max(rows,key=lambda r:(len(r['revista']),r['registro_uid']))['revista'],
               'tipo_documento':max(rows,key=lambda r:(len(r['tipo_documento']),r['registro_uid']))['tipo_documento'],
               'resumen':resumen['resumen'],'fuente_resumen':resumen['registro_uid'],
               'palabras_clave':max(rows,key=lambda r:(len(r['palabras_clave']),r['registro_uid']))['palabras_clave'],
               'fuentes':'|'.join(fuentes),'numero_fuentes':len(fuentes),'numero_registros':len(g),
               'identificadores_openalex':'|'.join(sorted(r['id_fuente'] for r in rows if r['fuente']=='OpenAlex')),
               'identificadores_scopus':'|'.join(sorted(r['id_fuente'] for r in rows if r['fuente']=='Scopus')),
               'identificadores_wos':'|'.join(sorted(r['id_fuente'] for r in rows if r['fuente']=='WoS')),
               'estado_identidad_bibliografica':estado,
               'alertas_asociadas':'|'.join(revision),
               'seguimiento_editorial_pendiente':'|'.join(a for a in revision if a in {'ALERTA-0467','ALERTA-0519'}),
               'version_normalizacion':'unicode_v2',
               'doi_alternativos_preservados':len(dois)>1,
               'metadatos_por_fuente_json':json.dumps([{
                   'registro_uid':r['registro_uid'],'fuente':r['fuente'],'titulo':r['titulo'],
                   'anio':r['anio'],'fecha_publicacion':r['fecha_publicacion'],
                   'doi_original':r['doi_original'],'doi_normalizado':r['doi_normalizado'],
                   'revista':r['revista'],'idioma':r['idioma'],
                   'estado_filtro_fuente':r['estado_filtro_fuente']
               } for r in rows], ensure_ascii=False, sort_keys=True),
               'clasificacion_tematica_consolidada':'',
               'estado_revision_tematica':'NO_EVALUADO_EN_ESTA_ETAPA'}
        corpus.append(row)
        for r in rows:
            procedencia.append({'id_publicacion':pid, **r})
    procedencia.sort(key=lambda r:(r['id_publicacion'],r['registro_uid']))

    # Validaciones: cardinalidad, decisiones completas, separaciones (incluso indirectas).
    if len(procedencia)!=len(registros) or len(map_uid_pid)!=len(registros):
        raise AssertionError('No se conservaron todos los registros de entrada')
    for e in aristas_humanas:
        a,b = e['registro_uid_a'],e['registro_uid_b']
        if a in indices and b in indices and map_uid_pid[a]!=map_uid_pid[b]:
            raise AssertionError(f'Fusión humana no aplicada: {e["id_alerta"]}')
    for e in det_bloqueos:
        a,b = e['registro_uid_a'],e['registro_uid_b']
        if map_uid_pid[a]==map_uid_pid[b]:
            raise AssertionError(f'Se unió un par bloqueado: {e["id_alerta"]}')

    salida.mkdir(parents=True, exist_ok=True)
    # Evitar que un archivo legado del corte anterior contamine el manifiesto de salida.
    legado = salida/'06_pendientes_cuatro.csv'
    if legado.is_file(): legado.unlink()
    escribir_csv(salida/'01_corpus_unificado_identidad.csv',corpus,list(corpus[0]))
    escribir_csv(salida/'02_procedencia_registros.csv',procedencia,list(procedencia[0]))
    escribir_csv(salida/'03_bitacora_vinculos.csv',log,list(log[0]))
    escribir_csv(salida/'04_restricciones_y_pendientes.csv',det_bloqueos,
                 ['id_alerta','registro_uid_a','registro_uid_b','caracter','estado','motivo'])
    escribir_csv(salida/'05_relaciones_editoriales.csv', relaciones,
                 list(relaciones[0]) if relaciones else ['id_alerta'])
    escribir_csv(salida/'06_pendientes_bibliograficos.csv',pendientes,
                 list(matriz[0]) if matriz else ['id_alerta'])
    escribir_csv(salida/'07_alertas_automaticas_unicode.csv',alertas_auto,
                 ['tipo','registro_a','registro_b','detalle'])
    # Respetar la condición de exclusión de los 105 para base_amplia: no se incluyen por esta acción.
    fuentes_n = Counter(r['fuente'] for r in registros)
    origenes={k:{'ruta':v['ruta'],'sha256':hash_archivo(raiz/v['ruta']), 'registros':v['registros']}
             for k,v in entradas.items()}
    informe={'version':'unificacion_validada_v2_cierre','etapa':etapa,'normalizacion':'unicode_v2',
          'entradas':origenes,'registros_originales':len(registros),'por_fuente':dict(fuentes_n),
          'publicaciones_unificadas':len(corpus),'reduccion_total':len(registros)-len(corpus),
          'fusiones_humanas_aplicadas_efecto_neto':aplicadas,
          'vinculos_automaticos_adicionales_efecto_neto':auto_aplicados,
          'vinculos_automaticos_ya_aprobados':auto_ya,
          'vinculos_automaticos_rechazados':dict(rechazadas),
          'separaciones_o_pendientes_respetados':len(det_bloqueos),
          'publicaciones_multifuente':sum(x['numero_fuentes']>1 for x in corpus),
          'publicaciones_con_varios_doi':sum(x['doi_alternativos_preservados'] for x in corpus),
          'aristas_humanas_aprobadas_cargadas':len(aristas_humanas),
          'aristas_humanas_fuera_de_la_etapa':aristas_aprobadas_fuera_etapa,
          'aristas_humanas_procesadas_en_la_etapa':len(aristas_humanas)-aristas_aprobadas_fuera_etapa,
          'identificadores_humanos_aprobados_cargados':len(aristas_humanas),
          'alertas_originales_auditadas':informe_aprobadas['alertas_totales'],
          'pendientes_sin_dictamen':sorted(r['id_alerta'] for r in pendientes),
          'decisiones_cierre_aprobadas': ['ALERTA-0111','ALERTA-0500','ALERTA-0529','ALERTA-0534','ALERTA-0467','ALERTA-0519'],
          'seguimientos_no_resueltos':['ALERTA-0467','ALERTA-0519'],
          'cobertura_original_excluida_no_reincorporada':105,
          'cribado_tematico_modificado':False,
          'todos_los_registros_representados_una_vez':True,
          'fuentes_originales_modificadas':False,
          'archivos_decisiones_sha256':{p.name:hash_archivo(p) for p in sorted((raiz/'flujo_unificado'/'decisiones_aprobadas').glob('*.csv'))},
          'codigo_unificacion_sha256':{p.name:hash_archivo(p) for p in [DIR/'unificacion_validada.py', DIR/'deduplicacion.py', DIR/'normalizacion.py', DIR/'fuentes.py']},
          'archivos_sha256':{p.name:hash_archivo(p) for p in sorted(salida.glob('*.csv'))}}
    escribir_json(salida/'08_resumen_validacion.json',informe)
    return informe


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz',type=Path,default=ROOT)
    p.add_argument('--salida',type=Path,default=ROOT/'integracion_corpus'/'resultados_validados')
    p.add_argument('--etapa',choices=['universo','base_amplia','ambas'],default='ambas')
    a=p.parse_args()
    etapas=['universo','base_amplia'] if a.etapa=='ambas' else [a.etapa]
    for etapa in etapas:
        r=unificar(raiz=a.raiz,salida=a.salida/etapa,etapa=etapa)
        print(f"{etapa}: {r['registros_originales']} registros -> "
              f"{r['publicaciones_unificadas']} publicaciones; "
              f"fusiones humanas efectivas: {r['fusiones_humanas_aplicadas_efecto_neto']}; "
              f"vinculos automaticos adicionales: {r['vinculos_automaticos_adicionales_efecto_neto']}")
    print('Se conservaron las fuentes originales y el cribado. Resultados:',a.salida.resolve())

if __name__=='__main__':
    main()
