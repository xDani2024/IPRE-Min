"""Comprueba integridad técnica del pre-cierre, sin validar pertinencia académica."""
from pathlib import Path
from collections import Counter
import argparse,csv,json,hashlib
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'PROCEDENCIA_DEL_PAQUETE.json').is_file())
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--entrada',type=Path,default=ROOT/'04_cierre_v9/entrada')
p.add_argument('--salida',type=Path,default=ROOT/'04_cierre_v9/salida')
a=p.parse_args()
def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def check(condition,message):
    if not condition:raise ValueError(message)
def index(rows):
    ids=[r['scopus_id'].strip() for r in rows]
    check(bool(rows) and all(ids) and len(set(ids))==len(ids),'Identificadores vacíos o duplicados.')
    return dict(zip(ids,rows))
source=a.entrada/'matriz_completa_scopus_v8.csv'
old=read(source);new=read(a.salida/'Matriz_Scopus_4614_con_pre_cierre_v9.csv')
before=index(old);after=index(new)
check(before.keys()==after.keys(),'Cambió la cobertura de la matriz.')
m=json.loads((a.salida/'Resumen_y_manifest_v9_scopus.json').read_text(encoding='utf-8'))
check(sha(source)==m['sha256_entrada'],'La entrada no coincide con el manifiesto v9.')
check(len(new)==m['base_amplia'],'Base amplia inconsistente.')
for oid,r in before.items():
    check(all(after[oid].get(k)==v for k,v in r.items()),'Se alteró una columna v8: '+oid)
    if r['decision_nucleo_v8_propuesta']!='TC':
        check(after[oid]['decision_nucleo_v9_propuesta']==r['decision_nucleo_v8_propuesta'],'Cambio fuera de TC sin auditoría: '+oid)
tc={oid for oid,r in before.items() if r['decision_nucleo_v8_propuesta']=='TC'}
decisions=read(a.salida/'Decisiones_TC_Scopus_v9.csv')
check(len(decisions)==len(tc) and {r['scopus_id'] for r in decisions}==tc,'Cobertura TC incompleta o duplicada.')
for r in decisions:
    check(r==after[r['scopus_id']],'Decisión TC difiere de la matriz.')
    check(all(r.get(k,'').strip() for k in ['regla_cierre_v9','motivo_cierre_v9','evidencia_cierre_v9']),'TC sin fundamento.')
counts=dict(Counter(r['decision_nucleo_v9_propuesta'] for r in new))
check(set(counts)<={'IN','OUT'} and counts==m['v9_propuesta_computacional_total'],'Conteos finales inconsistentes.')
for decision in ['IN','OUT']:
    rows=read(a.salida/f'{decision}_computacional_v9_PENDIENTE_REVISION.csv')
    expected={oid for oid,r in after.items() if r['decision_nucleo_v9_propuesta']==decision}
    check(len(rows)==len(expected) and {r['scopus_id'] for r in rows}==expected,'Partición '+decision+' inconsistente.')
    check(all(r==after[r['scopus_id']] for r in rows),'Contenido de partición alterado.')
for n,h in m['sha256_salidas'].items():check(sha(a.salida/n)==h,'Huella de salida inconsistente: '+n)
check(all(r['validacion_academica_v9']=='pendiente' for r in new),'Estado académico inesperado.')
report={'estado':'INTEGRIDAD_TECNICA_VERIFICADA','filas':len(new),'TC_comprobados':len(tc),'columnas_v8_conservadas':True,'conteos':counts,'sha256_entrada':sha(source),'validacion_humana_completada':False}
(a.salida/'Verificacion_integridad_v9.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Integridad técnica v9 verificada:',counts)
