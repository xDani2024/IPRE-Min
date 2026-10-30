"""Verifica integridad, cobertura, trazabilidad y respeto de decisiones humanas."""
import csv
import hashlib
import json
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def normalize(s):return ' '.join(unicodedata.normalize('NFKD',s).split())

source=read(ROOT/'entrada/matriz_completa_4735_v8.csv')
master=read(ROOT/'salida/Matriz_4735_con_cierre_v9.csv')
decisions=read(ROOT/'salida/Decisiones_2399_TC_v9.csv')
human=json.loads((ROOT/'entrada/decisiones_humanas_conservadas.json').read_text())
audit=json.loads((ROOT/'auditoria_directa_IA.json').read_text())
summary=json.loads((ROOT/'salida/Resumen_cierre_v9.json').read_text())
old={r['openalex_id']:r for r in source};new={r['openalex_id']:r for r in master}
tc_ids={r['openalex_id'] for r in source if r['decision_nucleo_v8_propuesta']=='TC'}
assert len(source)==len(old)==len(master)==len(new)==4735
assert len(decisions)==len(tc_ids)==2399
assert {r['openalex_id'] for r in decisions}==tc_ids
assert all(r['decision_nucleo_v9_propuesta'] in ('IN','OUT') for r in master)
assert all({k:new[id][k] for k in row}==row for id,row in old.items())
assert sha(ROOT/'entrada/matriz_completa_4735_v8.csv')==summary['sha256_matriz_v8']
for r in decisions:
    assert r['motivo_cierre_v9'] and r['evidencia_cierre_v9'] and r['regla_cierre_v9']
    if r['decision_nucleo_v9_propuesta']=='IN':assert r['lectura_semantica_directa_IA_v9']=='si'
    if r['lectura_semantica_directa_IA_v9']=='si':
        quote=audit[r['openalex_id']]['evidencia']
        text=old[r['openalex_id']]['title']+' '+old[r['openalex_id']]['abstract']
        assert normalize(quote) in normalize(text),r['openalex_id']
assert len(human)==len({r['openalex_id'] for r in human})==40
for h in human:
    r=new[h['openalex_id']]
    assert r['decision_humana_conservada_v9']==h['decision_humana']
    assert r['motivo_humano_conservado_v9']==h['motivo']
    if h['decision_humana'] in ('IN','OUT'):assert r['decision_nucleo_v9_propuesta']==h['decision_humana']
assert next(h for h in human if h['codigo']=='P04')['decision_humana']=='IN'
assert next(h for h in human if h['codigo']=='P07')['decision_humana']=='IN'
assert next(h for h in human if h['codigo']=='H011')['decision_humana']=='TC'
changed_outside=[id for id in old if id not in tc_ids and old[id]['decision_nucleo_v8_propuesta']!=new[id]['decision_nucleo_v9_propuesta']]
assert set(changed_outside)=={h['openalex_id'] for h in human if h['codigo'] in ('H003','H015')}
assert summary['pendientes_de_decision_binaria']==0
assert len(read(ROOT/'salida/IN_propuesto_v9.csv'))==summary['resultado_nucleo_propuesto_v9']['IN']
assert len(read(ROOT/'salida/OUT_propuesto_v9.csv'))==summary['resultado_nucleo_propuesto_v9']['OUT']
report={'resultado':'VERIFICADO','base_amplia':4735,'TC_con_decision_binaria_unica':2399,
    'TC_pendientes_de_propuesta':0,'original_v8_preservado':True,
    'decisiones_humanas_preservadas':40,'nuevos_IN_con_lectura_directa_IA':True,
    'citas_de_auditoria_presentes_en_fuente':True,'cambios_fuera_de_TC':'Solo precedencia de H003 y H015 (OUT humanos previos)',
    'sha256_entrada':sha(ROOT/'entrada/matriz_completa_4735_v8.csv')}
(ROOT/'salida/Verificacion_integridad_v9.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
