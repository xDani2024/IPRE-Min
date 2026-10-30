"""Reproduce filtro amplio y v6/v7/v8/v9 sin red ni API key.

Usa instantáneas y auditorías congeladas. No regenera juicios semánticos ni
reconstruye la descarga original de 9540 registros. No modifica los archivos
archivados: cada ejecución exige una carpeta de destino nueva.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def run(script,*args):
    print('Ejecutando',script.name,flush=True)
    result=subprocess.run([sys.executable,str(script),*map(str,args)],capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError(script.name+'\n'+result.stdout+'\n'+result.stderr)
    (logs/(script.stem+'.txt')).write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
def same(a,b):
    if sha(a)!=sha(b):raise ValueError('No coincide la reproducción: '+a.name)
    checks.append({'archivo':a.name,'sha256':sha(a),'reproducido_identico':True})

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida',type=Path,default=ROOT/'reproduccion_local')
    args=p.parse_args();dest=args.salida.resolve()
    if dest.exists() and any(dest.iterdir()):p.error('La salida contiene archivos. Elige otra carpeta.')
    dest.mkdir(parents=True,exist_ok=True);logs=dest/'bitacoras';logs.mkdir(exist_ok=True)
    checks=[];engines=dest/'motores';engines.mkdir(exist_ok=True)
    broad=ROOT/'01_extraccion_y_filtro';reference=broad/'referencia_archivada'
    run(broad/'02_filtrar_y_unificar.py','--entrada',broad/'datos_reconstruidos',
        '--historial',broad/'cribado_anterior_4773.csv','--salida',dest/'filtro_amplio')
    for name in ['corpus_general_aceptado.csv','excluidos_amplios_con_motivo.csv',
                 'corpus_unificado_con_historial.csv','correspondencias_ids_openalex.csv']:
        same(reference/name,dest/'filtro_amplio'/name)
    # v6 requiere una estructura de carpetas propia, por eso se clona el motor.
    v6=engines/'v6/codigo'
    for name in ['06_screening_multidimensional.py','auditoria_dirigida_48.csv']:
        copy(ROOT/'02_cribado_v6/codigo'/name,v6/name)
    run(v6/'06_screening_multidimensional.py','--entrada',dest/'filtro_amplio/corpus_unificado_con_historial.csv')
    same(ROOT/'02_cribado_v6/salida_archivada/screening_operacional_4735.csv',v6/'salida/screening_operacional_4735.csv')
    # Las alertas y la cola con prioridad son entradas históricas congeladas.
    archive_v7=ROOT/'03_cribado_v8/entrada/v7';v8=engines/'v8';v7=v8/'entrada/v7'
    for name in ['11_resolver_dudosos.py','auditoria_dirigida_de_reglas.psv',
                 'entrada/cola_dudosos_1241_v6.csv','entrada/alertas_metadata_ampliadas_v6.csv']:
        copy(archive_v7/name,v7/name)
    copy(v6/'salida/screening_operacional_4735.csv',v7/'entrada/screening_operacional_4735_v6.csv')
    run(v7/'11_resolver_dudosos.py')
    for name in ['matriz_nucleo_provisional_4735_v7.csv','decisiones_dudosos_1241_v7.csv','resumen_v7.json']:
        same(archive_v7/'salida'/name,v7/'salida'/name)
    copy(ROOT/'03_cribado_v8/15_aplicar_criterio_calibrado.py',v8/'15_aplicar_criterio_calibrado.py')
    copy(ROOT/'03_cribado_v8/entrada/calibracion_piloto.json',v8/'entrada/calibracion_piloto.json')
    run(v8/'15_aplicar_criterio_calibrado.py')
    frozen_v9=ROOT/'04_cierre_v9';v9=engines/'v9'
    same(frozen_v9/'entrada/matriz_completa_4735_v8.csv',v8/'salida/matriz_completa_4735_v8.csv')
    for name in ['22_cerrar_TC.py','23_verificar_cierre.py','auditoria_directa_IA.json',
                 'auditoria_complementaria_H011.json','entrada/procedencia.json',
                 'entrada/decisiones_humanas_conservadas.json']:
        copy(frozen_v9/name,v9/name)
    copy(v8/'salida/matriz_completa_4735_v8.csv',v9/'entrada/matriz_completa_4735_v8.csv')
    run(v9/'22_cerrar_TC.py');run(v9/'23_verificar_cierre.py')
    for path in sorted((frozen_v9/'salida').iterdir()):
        if path.is_file():same(path,v9/'salida'/path.name)
    final=dest/'resultado_v9';shutil.copytree(v9/'salida',final,dirs_exist_ok=True)
    report={'estado':'REPRODUCIDO','consulta_api':False,'api_key_necesaria':False,
        'punto_de_inicio':'Universo reconstruido de 9534 registros posteriores a segunda deduplicación',
        'filtrados_amplios':len(read(dest/'filtro_amplio/corpus_general_aceptado.csv')),
        'resultado_v9':json.loads((final/'Resumen_cierre_v9.json').read_text()),
        'cotejos':checks,'limite':'Se reutilizan auditorías IA y juicios humanos congelados; no se regeneran sus lecturas.'}
    (dest/'VERIFICACION_REPRODUCCION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Reproducción completada. IN:',report['resultado_v9']['resultado_nucleo_propuesto_v9']['IN'],
        '| OUT:',report['resultado_v9']['resultado_nucleo_propuesto_v9']['OUT'],'| TC: 0',flush=True)
    print('Resultados:',final)
