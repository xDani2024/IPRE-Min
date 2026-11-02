"""Flujo WoS: base amplia fase 01 -> IPRE v6 -> v7 -> v8 -> v9 (solo reglas).

No se reutilizan auditorías IA, pilotos, decisiones humanas ni IDs específicos de OpenAlex.
Preserva el UID WoS original; openalex_id es un alias de compatibilidad únicamente.
La salida v9 es computacional preliminar y no una validación humana ni un núcleo definitivo.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
import random
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'entrada_fase01'
ENGINES=ROOT/'motores_ipre'

def read(path, delimiter=','):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter=delimiter))

def write(path, data, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields=fields or (list(data[0]) if data else ['wos_id'])
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='raise')
        w.writeheader();w.writerows(data)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    x=importlib.util.module_from_spec(spec);sys.modules[name]=x;spec.loader.exec_module(x)
    return x

def count(rows, key):
    return dict(sorted(Counter(r[key] for r in rows).items()))

def adapt(raw, alert_docs, alert_dedup):
    oid=raw['wos_id']
    original_type=raw.get('document_type','')
    original_lang=raw.get('language','')
    language='en' if original_lang.lower().startswith('english') else original_lang.lower()
    flags=[]
    if oid in alert_docs: flags.append('alerta_documental_pendiente')
    if oid in alert_dedup: flags.append('posible_coincidencia_bibliografica_uid_distinto')
    return {**raw,
        # Alias de compatibilidad: NO es un OpenAlex ID ni se usa para deduplicar.
        'openalex_id':oid,
        'retrieval_branches':raw.get('first_discovery_query',''),
        'type':'review' if 'review' in original_type.lower() else 'article',
        'language':language,
        'source':raw.get('source_title',''),
        'quality_flags':';'.join(flags),
        'estado_cribado_especifico':raw.get('auto_screen_status',''),
        'procedencia_decision_especifica':'filtro_amplio_fase01_wos',
        'motivo_decision_especifica':raw.get('auto_screen_reasons',''),
        'estatus_validacion':'sin_revision_humana',
        'fuente_bibliografica':'Web of Science Core Collection',
        'metodo_extraccion':'exportacion_web_manual_incremental_not',
    }

def sample(rows, label, n, seed):
    rng=random.Random(seed)
    subset=rng.sample(sorted(rows,key=lambda r:r['wos_id']),min(len(rows),n))
    records=[];keys=[]
    for i,r in enumerate(subset,1):
        code=f'{label}-{i:03d}'
        records.append({'codigo':code,'titulo':r['title'],'resumen':r['abstract'],
            'doi':r['doi'],'anio':r['year'],'revision_1_IN_OUT_TC':'','motivo_1':'',
            'revision_2_IN_OUT_TC':'','motivo_2':'','consenso_IN_OUT_TC':'',
            'motivo_consenso':'','texto_completo_consultado':''})
        keys.append({'codigo':code,'wos_id':r['wos_id'],'estrato':label,
            'decision_computacional_v6':r['decision_final_propuesta'],
            'N_marco':len(rows),'n_muestra':len(subset),
            'semilla':seed})
    return records,keys

def run(output):
    if output.exists() and any(output.iterdir()):
        raise ValueError('La carpeta de salida contiene archivos. Elija otra con --salida.')
    output.mkdir(parents=True,exist_ok=True)
    files=['04_base_amplia_provisional.csv','05_excluidos_filtro_amplio.csv',
        '03_sin_abstract.csv','01_registros_unicos_normalizados.csv']
    for f in files:
        if not (SOURCE/f).is_file(): raise FileNotFoundError(SOURCE/f)
    original=read(SOURCE/files[3]);base=read(SOURCE/files[0]);excluded=read(SOURCE/files[1]);noabs=read(SOURCE/files[2])
    if len(original)!=5071 or len(base)!=2238 or len(excluded)!=2635 or len(noabs)!=198:
        raise ValueError('Los recuentos de Fase 1 no coinciden con el manifiesto.')
    ids=lambda x: [r['wos_id'] for r in x]
    if len(set(ids(original)))!=len(original) or set(ids(original)) != set(ids(base)+ids(excluded)+ids(noabs)):
        raise ValueError('La partición de Fase 1 no es íntegra en WOS:UID.')
    alert_docs={r['wos_id'] for r in read(SOURCE/'09_alertas_documentales.csv')}
    dup=[]
    for r in read(SOURCE/'06_alertas_deduplicacion.csv'):
        dup.extend(i.strip() for i in r['wos_ids'].split('|'))
    alert_dedup=set(dup)

    v6=module(ENGINES/'06_screening_multidimensional.py','motor_v6_ipre')
    r6=[]
    for original_row in base:
        row=adapt(original_row,alert_docs,alert_dedup)
        result=v6.decide(row)
        result.update({'decision_algoritmica_pre_auditoria':result['decision_final_propuesta'],
            'procedencia_ajuste':'regla_reproducible_sin_auditoria_historica',
            'motivo_relectura_IA_dirigida':'',
            'motivo_final_propuesto':result['motivo_codificado'],
            'justificacion_final_propuesta':result['justificacion_por_dimensiones']})
        r6.append({**row,**result})
    assert len(r6)==len({r['wos_id'] for r in r6})==len(base)
    out6=output/'01_v6'
    write(out6/'matriz_cribado_v6.csv',r6)
    for label in ('IN_FUERTE','IN_SECUNDARIO','DUDOSO','OUT'):
        write(out6/f'{label}.csv',[r for r in r6 if r['decision_final_propuesta']==label],list(r6[0]))
    cohorts={'I':[r for r in r6 if r['decision_final_propuesta'].startswith('IN')],
      'O':[r for r in r6 if r['decision_final_propuesta']=='OUT'],
      'D':[r for r in r6 if r['decision_final_propuesta']=='DUDOSO' and v6.genuine_boundary(r)]}
    # La muestra conserva las etiquetas de estrato fuera de la ficha revisada.
    blind=[];key=[]
    for label,n in (('I',50),('O',50),('D',30)):
        xs,ks=sample(cohorts[label],label,n,20261101+ord(label))
        blind+=xs;key+=ks
    write(out6/'muestra_humana_ciega.csv',blind)
    write(out6/'clave_muestra_NO_ENTREGAR_A_REVISORES.csv',key)

    v7=module(ENGINES/'11_resolver_dudosos.py','motor_v7_ipre')
    queue=[];mapped={}
    for r in r6:
        if r['decision_final_propuesta']!='DUDOSO':continue
        q={'title':r['title'],'abstract':r['abstract'],
           'contexto':r['contexto_cielo_abierto'],'prioridad':'P1_CASO_DUDOSO'}
        res=v7.assess(q,r,None)
        res.update({'decision_pre_auditoria_v7':res['decision_nucleo_v7'],
                    'regla_pre_auditoria_v7':res['regla_v7']})
        rr={**r,**res};queue.append(rr);mapped[r['wos_id']]=rr
    r7=[]
    for r in r6:
        v=mapped.get(r['wos_id'])
        decision=v['decision_nucleo_v7'] if v else 'IN' if r['decision_final_propuesta'].startswith('IN') else 'OUT'
        r7.append({**r,'decision_nucleo_v7':decision,
          'origen_v7':'resolucion_dudosos_v7' if v else 'conserva_v6',
          'regla_v7':v['regla_v7'] if v else 'V6_SIN_CAMBIO',
          'estado_documental_v7':v['estado_documental_v7'] if v else 'SEGUN_CONTROL_V6',
          'subtipo_v7':v['subtipo_v7'] if v else r['decision_final_propuesta'] if decision=='IN' else '',
          'version_v7':v7.VERSION})
    out7=output/'02_v7'
    write(out7/'decisiones_dudosos_v7.csv',queue,list(queue[0]) if queue else list(r6[0]))
    write(out7/'matriz_nucleo_v7.csv',r7)

    # Ejecuta el motor v8 del paquete de referencia con adaptaciones estructurales
    # mínimas; las auditorías y el piloto de OpenAlex son reemplazados por entradas vacías.
    stage=output/'_entorno_v8'
    folder=stage/'entrada/v7';(folder/'entrada').mkdir(parents=True,exist_ok=True)
    (folder/'salida').mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'motor_v8_adaptado.py',stage/'15_aplicar_criterio_calibrado.py')
    shutil.copy2(ENGINES/'11_resolver_dudosos.py',folder/'11_resolver_dudosos.py')
    shutil.copy2(out7/'matriz_nucleo_v7.csv',folder/'salida/matriz_nucleo_provisional_4735_v7.csv')
    shutil.copy2(out7/'decisiones_dudosos_v7.csv',folder/'salida/decisiones_dudosos_1241_v7.csv')
    write(folder/'entrada/alertas_metadata_ampliadas_v6.csv',[],['openalex_id','abstracto_invalido_para_cribado','verificado_en_fuente'])
    (folder/'auditoria_dirigida_de_reglas.psv').write_text('openalex_id|decision_ajustada|regla_ajustada|razon_concreta|cita_breve_de_ficha\n',encoding='utf-8')
    (stage/'entrada/calibracion_piloto.json').write_text(json.dumps({'estado_humano_actual_piloto':[]}),encoding='utf-8')
    proc=subprocess.run([sys.executable,str(stage/'15_aplicar_criterio_calibrado.py'),'--salida',str(output/'03_v8')],text=True,capture_output=True)
    if proc.returncode:raise RuntimeError('Motor v8: '+proc.stdout+'\n'+proc.stderr)
    r8=read(output/'03_v8/matriz_completa_4735_v8.csv')
    if len(r8)!=len(r7) or {r['wos_id'] for r in r8}!={r['wos_id'] for r in r7}:
        raise ValueError('Matriz v8 no conserva integridad de cohorte')
    # Renombra la salida v8 para evitar nombres fijos históricos en entregables.
    (output/'03_v8/matriz_completa_4735_v8.csv').rename(output/'03_v8/matriz_completa_v8.csv')
    shutil.rmtree(stage)

    # Cierre algorítmico v9 SIN auditoría IA de lectura directa ni juicios humanos.
    # Se conserva TC_v8 y la disposición documental. No es homologable al
    # cierre auditado de OpenAlex hasta realizar controles independientes WoS.
    v9=module(ENGINES/'22_cerrar_TC.py','motor_v9_ipre')
    r9=[];tc=[]
    for r in r8:
        if r['decision_nucleo_v8_propuesta']=='TC':
            decision,rule,doc,why,evidence,indicators,typ=v9.classify(r)
            origen='clasificador_computacional_v9_sin_auditoria'
            tc.append(r['wos_id'])
        else:
            decision=r['decision_nucleo_v8_propuesta']
            rule='V8_SIN_CAMBIO';doc='v8_conservada';why=r['motivo_v8']
            evidence=r['evidencia_textual_v8'];indicators='';typ='v8_conservada'
            origen='v8_conservada'
        r9.append({**r,'decision_nucleo_v9_propuesta':decision,
          'origen_v9':origen,'regla_cierre_v9':rule,
          'disposicion_documental_v9':doc,'motivo_cierre_v9':why,
          'evidencia_cierre_v9':evidence,'indicadores_cierre_v9':indicators,
          'tipo_evidencia_cierre_v9':typ,'fuente_texto_v9':'titulo_resumen_wos',
          'lectura_semantica_directa_IA_v9':'no','texto_completo_consultado_v9':'no',
          'validacion_humana_independiente':'pendiente',
          'alerta_revision_bibliografica':'si' if r['wos_id'] in alert_docs|alert_dedup else 'no',
          'version_cierre_v9':'v9_solo_reglas_transferidas_wos',
        })
    if len(r9)!=len(base) or len({r['wos_id'] for r in r9})!=len(base):
        raise ValueError('Cierre perdió registros')
    out9=output/'04_v9_preliminar'
    write(out9/'matriz_completa_v9_preliminar.csv',r9)
    for status in ('IN','OUT'):
        write(out9/f'{status}_computacional_v9.csv',
          [r for r in r9 if r['decision_nucleo_v9_propuesta']==status],list(r9[0]))
    write(out9/'resolucion_TC_v8_solo_reglas.csv',
        [r for r in r9 if r['wos_id'] in set(tc)],list(r9[0]))
    review=[{'wos_id':r['wos_id'],'title':r['title'],'doi':r['doi'],
       'decision_v9_computacional':r['decision_nucleo_v9_propuesta'],
       'motivo_computacional':r['motivo_cierre_v9'],
       'alerta_bibliografica':r['alerta_revision_bibliografica'],
       'decision_humana_IN_OUT_TC':'','motivo_humano':'','fecha_revision':'',
       'texto_completo_leido':'','id_revisor':''} for r in r9]
    write(out9/'plantilla_revision_humana.csv',review)
    manifest={
      'fecha_ejecucion_utc':datetime.now(timezone.utc).isoformat(),
      'fuente':'Web of Science Core Collection',
      'metodo_extraccion':'manual incremental, 10 exportaciones WoS (Fase 1)',
      'etapa_entrada':'04_base_amplia_provisional.csv de Fase 1',
      'conteos_fase01':{'total_uid':len(original),'sin_resumen':len(noabs),
         'elegibles_filtro_amplio':len(base),'excluidos_filtro_amplio':len(excluded)},
      'v6':count(r6,'decision_final_propuesta'),
      'v7':count(r7,'decision_nucleo_v7'),
      'v8':count(r8,'decision_nucleo_v8_propuesta'),
      'v9_solo_reglas':count(r9,'decision_nucleo_v9_propuesta'),
      'tc_v8_procesados_solo_reglas':len(tc),
      'alertas_documentales':len(alert_docs),
      'alertas_deduplicacion_grupos':len(read(SOURCE/'06_alertas_deduplicacion.csv')),
      'muestra_ciega_v6':len(blind),'marcos_muestra_v6':{k:len(v) for k,v in cohorts.items()},
      'verificaciones':{
        'particion_fase01_por_UID':True,
        'base_v6_v7_v8_v9_con_mismos_wos_id':{r['wos_id'] for r in r6}=={r['wos_id'] for r in r7}=={r['wos_id'] for r in r8}=={r['wos_id'] for r in r9},
        'sin_traspaso_juicios_humanos_openalex':True,
        'sin_traspaso_auditorias_IA_openalex':True,
        'sin_lectura_texto_completo':True,
        'validacion_humana_completada':False,
      },
      'sha256_entrada':{k:sha(SOURCE/k) for k in files},
      'sha256_matrices':{'v6':sha(out6/'matriz_cribado_v6.csv'),
        'v7':sha(out7/'matriz_nucleo_v7.csv'),
        'v8':sha(output/'03_v8/matriz_completa_v8.csv'),
        'v9':sha(out9/'matriz_completa_v9_preliminar.csv')},
      'observaciones':[ 
        'La etiqueta openalex_id es un alias tecnico del wos_id, no una vinculacion a OpenAlex.',
        'Las reglas de cribado provienen de IPRE_codigo v9 y se aplicaron a fichas WoS sin adaptar su contenido semantico.',
        'v8 transfiere reglas calibradas en OpenAlex sin repetir el piloto humano en WoS.',
        'v9 es una aplicacion automatica de reglas, sin las auditorias semanticas ni decisiones humanas especificas del v9 OpenAlex.',
        'Las 198 fichas sin resumen y las 2635 excluidas del filtro amplio se conservaron en la Fase 1 para auditoria y sensibilidad.',
        'IN/OUT en v9 no equivalen a validacion humana ni elegibilidad definitiva.',
        'Revisar alertas de posibles retractaciones y duplicados por titulo-ano antes de integrar bases.',
        'Pendiente total original consulta WoS 05 surface mining.'
      ]
    }
    (output/'RESUMEN_FLUJO_WOS.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'v6':manifest['v6'],'v7':manifest['v7'],'v8':manifest['v8'],
          'v9_solo_reglas':manifest['v9_solo_reglas'],
          'integridad':manifest['verificaciones']['base_v6_v7_v8_v9_con_mismos_wos_id']},ensure_ascii=False,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--salida',type=Path,default=ROOT/'resultados_cribado_wos')
    args=ap.parse_args()
    run(args.salida.resolve())
