"""Cierre binario provisional de TODOS los TC v8, con disposición documental.

No es lectura humana ni revisión de texto completo. Se exige evidencia positiva
para IN de IA. Se conservan por precedencia las decisiones humanas previas.
Una exclusión documental no afirma irrelevancia temática. No reescribe las
columnas v8 ni los juicios humanos. Sin API ni dependencias externas.
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parent
VERSION='v9_cierre_binario_documental_20261008_1'
INPUT=ROOT/'entrada/matriz_completa_4735_v8.csv'
OUTPUT=ROOT/'salida'

def rx(pattern):return re.compile(pattern,re.I)
def norm(text):
    s=unicodedata.normalize('NFKD',text or '')
    s=''.join(c for c in s if not unicodedata.combining(c))
    s=re.sub('[‐‑–—−]','-',s)
    return re.sub(r'\s+',' ',s).strip()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(path,rows,fields=None):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)

SURFACE=rx(r'open[ -]?(?:pit|cast|cut)|surface[ -]min(?:e|ing)|surface coal|quarr(?:y|ies)|strip min|cielo abierto|tajo abierto|cantera|tambang terbuka|карьер|разрез')
TASK=rx(r'haul|truck|shovel|excavat|dragline|load(?:ing|er)|fleet|dispatch|conveyor|bucket[ -]?wheel|surface miner|overburden|stripping|drill|blast|crusher|mine road|haul road|pit road|dewater|drainage|pump|sump|water(?:ing)? truck|watering|dust (?:suppress|control)|road maintenance|refuel|material handling|material transport|camion|carguio|acarreo|perforaci|motoniveladora|pala minera|regadio|bombeo|desague|pengupasan|alat (?:gali|muat|angkut)|angkut|pemuatan|konveyor|экскаватор|самосвал|бурени|конвейер')
METRICS={
 'productividad':rx(r'productiv|produktivitas|throughput|production (?:rate|capacity|output|efficien|increase|gain|loss)|tons? per|tonnes? per|(?:ton|tons|tonnes|m3)\s*/\s*h|t/h\b|produccion por|rendimiento operacional|производительност'),
 'tiempos_esperas':rx(r'cycl(?:e|ing) time|cycle duration|loading time|travel time|hauling time|haulage time|transport time|waiting time|queuing time|queueing time|idle time|turnaround time|downtime|repair time|waktu edar|tiempo de ciclo|tiempos? de espera|врем[яени].{0,25}цикл'),
 'disponibilidad_utilizacion':rx(r'availability|uptime|equipment effectiveness|(?:equipment|fleet|truck|shovel|excavator|conveyor|vehicle|machine) utili[sz]ation|utili[sz]ation (?:of|rate)|match factor|kesiapan|disponibilidad|utilizacion|коэффициент.{0,25}использован'),
 'confiabilidad_equipo':rx(r'(?:(?:truck|shovel|excavator|dragline|conveyor|drill|pump|equipment|fleet|machine).{0,20}reliability|reliability.{0,30}(?:truck|shovel|excavator|dragline|conveyor|drill|pump|equipment|fleet))|failure rate|mean time (?:to|between)|mtbf|mttr'),
 'combustible_energia':rx(r'fuel (?:use|consumption|saving|efficien)|diesel consumption|energy (?:use|consumption|saving|efficien)|specific energy consumption|electricity consumption|consumo de (?:combustible|energia)|bahan bakar|расход.{0,15}топлив'),
 'costo_tarea':rx(r'operat(?:ing|ional) costs?|haul(?:age|ing) costs?|transport(?:ation)? costs?|truck.{0,15}costs?|costs?.{0,15}(?:haulage|drilling|watering|blasting|loading|transportation)|drill(?:ing)? costs?|blast(?:ing)? costs?|watering costs?|cost per (?:ton|tonne|m3|unit)|unit costs?|biaya operasional|costo.{0,15}(?:acarreo|riego|perforacion|operacional)|costs? of (?:drilling|blasting|watering|haulage)'),
 'distancia_frecuencia':rx(r'(?:travel|haulage|hauling|route|routing) distance|distance traveled|route length|travel length|(?:watering|spray|application|maintenance) frequency|frequency of (?:watering|application|maintenance)|application rate|frecuencia de riego|distancia recorrida'),
 'carga_transportada':rx(r'payload|material transported per hour|ore attainment|tons? hauled|tonnes? hauled'),
 'caudal_bombeo':rx(r'pumping discharge|pumping rate|pump capacity|caudal de bombeo|debit pompa'),
}
RESULT=rx(r'results?.{0,45}(?:show|indicat|reveal|demonstrat|obtain)|findings?.{0,35}(?:show|indicat|reveal)|show(?:ed|n|s)? that|was (?:found|measured|reduced|increased|improved|estimated|calculated)|were (?:found|measured|reduced|increased|improved|estimated|calculated)|has been (?:measured|calculated|evaluated)|achiev|reduc(?:ed|tion) (?:by|of|in)|increas(?:ed|es) by|improvement (?:of|in)|measured|calculated|computed|observed|found to|compar(?:ed|ison)|evaluat(?:ed|ion)|assess(?:ed|ment)|field (?:data|test|trial|experiment)|experimental|simulation (?:results|shows)|data.{0,30}show|hasil.{0,40}(?:penelitian|menunjuk|diperoleh)|diperoleh|berdasarkan hasil|resultados.{0,40}(?:muestra|indica)|se obtuvo|se midio|se evaluo|получен|результат')
RESULT=rx(RESULT.pattern+r'|\b(?:reduced|increased|decreased|improved)\b')
NUMERIC=rx(r'\d+(?:[.,]\d+)?\s*(?:%|percent|ton|tons|tonnes|t/h|m3|minutes|hours|seconds|liters|litres|gallons|mj|kw|kg|menit|jam|rp\b|usd|dollar)')
ASPIRATION=rx(r'\baims? to\b|\bobjective is\b|\bgoal is\b|\bin order to\b|\bwith the aim\b|\bcan (?:improve|reduce|increase)\b|\bcould\b|\bwould\b|\bmight\b|\bpotential to\b|\bexpected to\b|\bwill be (?:tested|evaluated|validated)\b')
PREDICTOR=rx(r'predict|forecast|machine learning|neural network|case.based reasoning')
MODEL_METRIC=rx(r'accuracy|precision|recall|f.?score|rmse|mae\b|mape\b|r.?squared|prediction error|forecast(?:ing)? error|convergence|computational (?:time|efficiency)|running time|algorithm.{0,15}performance')
DIRECT_CHANGE=rx(r'reduc(?:ed|tion) (?:by|of|in)|increas(?:ed|es) by|improvement (?:of|in)|measured|observed|field (?:data|test|trial|experiment)|actual (?:fuel|cycle|production)|collected.{0,35}(?:fuel|cycle|production)')
REVIEW=rx(r'\bsystematic (?:literature )?review\b|\bscoping review\b|\bliterature review\b|\bmeta.analysis\b|\breview (?:of|on)\b|\ba review\b|bibliometric|scientometric')
COMPONENT=rx(r'gearbox|bearing|tire|tyre|bucket teeth|drill bit|weld|microstructur|hydraulic cylinder|drive wheel|finite element|stress analysis|rock cutting force|excavat(?:ion|ing) resistance')
UNDERGROUND=rx(r'underground|mineria subterranea|sous.terrain|подземн')
WHOLE=rx(r'truck|shovel|excavator|dragline|fleet|conveyor|equipment|machine|drilling rig|surface miner|camion|pala minera|perforadora')
STRATEGIC=rx(r'ultimate pit|pit limit|final pit|open.pit min(?:e|ing) problem|production scheduling|long.term|strategic|block sequenc|block schedul|net present value|\bnpv\b|ore blending|mine design')
ALTERNATIVE={
 'geotecnia_cartografia':rx(r'slope stability|landslide|rock mass|highwall|subsidence|shear strength|geomechanic|photogrammetr|laser scanning|point cloud|land cover|geological model|geo.position|digital surface model|topographic'),
 'ambiente_seguridad':rx(r'air quality|water quality|acid mine|ecosystem|revegetat|land reclamation|dust concentration|dust exposure|occupational|health|ground vibration|flyrock|peak particle velocity|runoff|erosion|soil|contamination|fatigue detection|collision detection'),
 'fragmentacion_componente':rx(r'fragmentation|fragment size|muckpile|microstructur|wear resistance|tensile strength|fatigue strength|hardness'),
 'desarrollo_algoritmico':MODEL_METRIC,
 'planificacion_valor_proyecto':STRATEGIC,
}

def sentences(text):
    # Mantiene texto original y referencias exactas; no corta dentro de decimales.
    return [s.strip() for s in re.split(r'(?<=[.!?;])\s+|\n+',text) if s.strip()]
def metric_names(text):return [k for k,p in METRICS.items() if p.search(norm(text))]
def clip(text,limit=1500):return text if len(text)<=limit else text[:limit]+' [fragmento truncado]'

def classify(row):
    title=norm(row['title']);abstract=row['abstract'];sents=sentences(abstract)
    nt=norm(title+' '+abstract);rule=row['regla_v8']
    context=bool(SURFACE.search(nt)) or row['contexto_A_v8']=='acreditado_en_ficha'
    # No se interpreta como evidencia válida un resumen previamente cruzado.
    if rule=='T01_METADATA_INVALIDA':
        return 'OUT','D01_FUENTE_NO_FIABLE','exclusion_documental','La alerta identifica un resumen cruzado/editorial. Con la fuente congelada no se justifica la inclusión; se excluye del núcleo de esta versión por fuente no fiable.',row['title'],'','no'
    if UNDERGROUND.search(title) and not SURFACE.search(title):
        return 'OUT','O05_CONTEXTO_SUBTERRANEO','exclusion_por_foco','El estudio se identifica como subterráneo en el título. Una mención de minería superficial en antecedentes no acredita una evaluación propia en ese contexto.',row['title'],'','no'
    if not context:
        return 'OUT','D02_CONTEXTO_NO_ACREDITADO','exclusion_documental','La ficha disponible no acredita el contexto a cielo abierto exigido para el núcleo. Se excluye por evidencia contextual insuficiente.',row['title'],'','no'
    if REVIEW.search(title) or rule=='T02_DOCUMENTO_HIBRIDO':
        return 'OUT','O01_SINTESIS_SECUNDARIA','exclusion_por_foco','El documento se identifica como revisión/síntesis. Los resultados de estudios revisados no se cuentan como evaluación primaria propia en este núcleo.',row['title'],'','no'
    linked=[]
    for i,s in enumerate(sents):
        ns=norm(s);metrics=metric_names(s)
        if not metrics:continue
        # Ventana de hasta tres oraciones contiguas para antecedentes de tarea.
        prev=' '.join(sents[max(0,i-2):i]);window=norm(prev+' '+s)
        relation=bool(TASK.search(ns)) or (bool(TASK.search(title)) and bool(TASK.search(window)))
        if not relation:continue
        positive=bool(RESULT.search(ns)) or (bool(NUMERIC.search(ns)) and bool(rx(r'\b(?:was|were|is|are|has|have|diperoleh|se obtuvo)\b').search(ns)))
        if not positive and i and RESULT.search(norm(sents[i-1])) and rx(r'\b(?:this|these|the results|it|its|they|respectively)\b').search(ns):positive=True
        if not positive:continue
        if ASPIRATION.search(ns) and not DIRECT_CHANGE.search(ns):continue
        # Precisión del predictor o solver no demuestra rendimiento de la tarea.
        if MODEL_METRIC.search(ns) and not DIRECT_CHANGE.search(ns):continue
        if PREDICTOR.search(title) and MODEL_METRIC.search(nt) and not DIRECT_CHANGE.search(ns):continue
        # Reemplazo/mantenimiento debe mostrar la disponibilidad o producción
        # del equipo; la resistencia o vida de una pieza no basta.
        if rule=='T04_COMPONENTE_SIN_VINCULO_OPERACIONAL' or COMPONENT.search(title):
            if not (WHOLE.search(ns) and any(k in metrics for k in ['productividad','tiempos_esperas','disponibilidad_utilizacion','combustible_energia','costo_tarea'])):continue
        linked.append((s,metrics,prev))
    if linked:
        s,metrics,prev=max(linked,key=lambda x:(bool(NUMERIC.search(norm(x[0]))),len(x[1]),len(x[0])))
        evidence=clip((prev+' '+s).strip())
        method='simulacion_modelo' if rx(r'simulat|mathematical model|optimization model|mixed.integer').search(nt) else 'tipo_no_confirmado'
        why='La ficha vincula una tarea/equipo minero con evaluación y resultado operacional ('+', '.join(metrics)+'). Propuesta basada en título y resumen; no equivale a validación humana ni verificación externa del resultado.'
        return 'IN','I01_EVIDENCIA_OPERACIONAL_EN_FICHA','inclusion_con_evidencia',why,evidence,';'.join(metrics),method
    if rule=='T04_COMPONENTE_SIN_VINCULO_OPERACIONAL':
        evidence=next((s for s in sents if COMPONENT.search(norm(s))),row['title'])
        return 'OUT','O02_COMPONENTE_SIN_RESULTADO_DE_TAREA','exclusion_por_foco','El foco identificado es un componente, material o respuesta mecánica y no se acredita un resultado operacional atribuible al equipo/tarea. Se mantiene fuera de este núcleo.',clip(evidence),'','no'
    for name,pattern in ALTERNATIVE.items():
        endpoint=next((s for s in reversed(sents) if pattern.search(norm(s)) and (RESULT.search(norm(s)) or MODEL_METRIC.search(norm(s)))),None)
        if pattern.search(title) or endpoint:
            evidence=endpoint or row['title']
            return 'OUT','O03_'+name.upper(),'exclusion_por_foco','Se identifica un foco de '+name.replace('_',' ')+' y no se acredita resultado propio de tarea/equipo operacional en la ficha disponible. Permanece en la base amplia.',clip(evidence),'','no'
    return 'OUT','D03_EVIDENCIA_OPERACIONAL_INSUFICIENTE','exclusion_documental','La ficha disponible no permite justificar conjuntamente contexto/tarea, evaluación y resultado operacional. Se excluye del núcleo de esta versión por evidencia insuficiente; no se afirma irrelevancia definitiva.',clip(' '.join(sents[-2:]) or row['title']),'','no'

def main():
    OUTPUT.mkdir(exist_ok=True)
    rows=read(INPUT)
    assert len(rows)==4735 and len({r['openalex_id'] for r in rows})==4735
    source_hash=sha(INPUT)
    manifest=json.loads((ROOT/'entrada/procedencia.json').read_text())
    assert source_hash==manifest['sha256_matriz_v8']
    overrides=json.loads((ROOT/'auditoria_directa_IA.json').read_text())
    extra=json.loads((ROOT/'auditoria_complementaria_H011.json').read_text())
    human=json.loads((ROOT/'entrada/decisiones_humanas_conservadas.json').read_text())
    human_by_id={r['openalex_id']:r for r in human}
    decisions=[];master=[];human_integrations=[]
    fields=None
    for r in rows:
        h=human_by_id.get(r['openalex_id'],{})
        x={'decision_nucleo_v9_propuesta':r['decision_nucleo_v8_propuesta'],
           'origen_v9':'v8_conservada','regla_cierre_v9':'NO_REEVALUADO_EN_ESTA_ETAPA',
           'disposicion_documental_v9':'v8_conservada','motivo_cierre_v9':r['motivo_v8'],
           'evidencia_cierre_v9':r['evidencia_textual_v8'],'indicadores_cierre_v9':'',
           'tipo_evidencia_cierre_v9':'v8_conservada','fuente_texto_v9':'titulo_resumen_congelado',
           'lectura_semantica_directa_IA_v9':'no','texto_completo_consultado_v9':'no',
           'decision_humana_conservada_v9':h.get('decision_humana',''),
           'codigo_humano_conservado_v9':h.get('codigo',''),
           'motivo_humano_conservado_v9':h.get('motivo',''),
           'version_cierre_v9':VERSION}
        if r['decision_nucleo_v8_propuesta']=='TC':
            decision,rule,disposition,why,evidence,indicators,typ=classify(r)
            x.update({'decision_nucleo_v9_propuesta':decision,'origen_v9':'cierre_documental_computacional',
                      'regla_cierre_v9':rule,'disposicion_documental_v9':disposition,'motivo_cierre_v9':why,
                      'evidencia_cierre_v9':evidence,'indicadores_cierre_v9':indicators,'tipo_evidencia_cierre_v9':typ})
            if r['openalex_id'] in overrides:
                o=overrides[r['openalex_id']]
                assert o['decision'] in ('IN','OUT')
                assert o['evidencia'] and o['motivo']
                # Cita literal presente en el título o resumen congelado.
                assert norm(o['evidencia']) in norm(r['title']+' '+r['abstract']),r['openalex_id']
                x.update({'decision_nucleo_v9_propuesta':o['decision'],'origen_v9':'auditoria_directa_IA_titulo_resumen',
                    'regla_cierre_v9':o['regla'],'disposicion_documental_v9':o['disposicion'],
                    'motivo_cierre_v9':o['motivo'],'evidencia_cierre_v9':o['evidencia'],
                    'indicadores_cierre_v9':o.get('indicadores',''),'lectura_semantica_directa_IA_v9':'si'})
                x['tipo_evidencia_cierre_v9']=o.get('tipo_evidencia','simulacion_modelo' if o['regla'].startswith('I04') else 'medicion_reportada' if o['regla'].startswith('I03') else 'analitica_comparativa' if o['regla'].startswith('I02') else 'tipo_no_confirmado' if o['decision']=='IN' else 'no')
            x['decision_solo_IA_v9']=x['decision_nucleo_v9_propuesta']
            x['motivo_solo_IA_v9']=x['motivo_cierre_v9']
            x['precedencia_decision_humana_v9']='no'
            if h.get('decision_humana') in ('IN','OUT'):
                x['precedencia_decision_humana_v9']='si'
                if h['decision_humana']!=x['decision_solo_IA_v9']:
                    x.update({'decision_nucleo_v9_propuesta':h['decision_humana'],
                        'origen_v9':'juicio_humano_previo_conservado',
                        'regla_cierre_v9':'H01_PRECEDENCIA_JUICIO_HUMANO',
                        'disposicion_documental_v9':'inclusion_por_juicio_humano_previo' if h['decision_humana']=='IN' else 'exclusion_por_juicio_humano_previo',
                        'motivo_cierre_v9':'Se da precedencia al juicio humano previo '+h.get('codigo','')+': '+h.get('motivo','')+' La propuesta IA y su evidencia se conservan separadamente; no se atribuye validación independiente a esta calibración.',
                        'tipo_evidencia_cierre_v9':'calibracion_humana_previa_con_sugerencia_visible'})
            assert x['decision_nucleo_v9_propuesta'] in ('IN','OUT')
            base={k:r[k] for k in ['openalex_id','doi','title','year','abstract','decision_nucleo_v7','decision_nucleo_v8_propuesta','regla_v8','motivo_v8']}
            decisions.append({**base,**x})
        else:
            x.update({'decision_solo_IA_v9':x['decision_nucleo_v9_propuesta'],'motivo_solo_IA_v9':x['motivo_cierre_v9'],'precedencia_decision_humana_v9':'no_reevaluado'})
            if r['openalex_id'] in extra:
                o=extra[r['openalex_id']]
                assert o['decision']==r['decision_nucleo_v8_propuesta']
                assert norm(o['evidencia']) in norm(r['title']+' '+r['abstract'])
                x.update({'origen_v9':'auditoria_complementaria_IA_H011','regla_cierre_v9':o['regla'],
                    'motivo_cierre_v9':o['motivo'],'motivo_solo_IA_v9':o['motivo'],
                    'evidencia_cierre_v9':o['evidencia'],'indicadores_cierre_v9':o['indicadores'],
                    'lectura_semantica_directa_IA_v9':'si','tipo_evidencia_cierre_v9':'caracterizacion_operacion_existente'})
            if h.get('decision_humana') in ('IN','OUT'):
                x['precedencia_decision_humana_v9']='si'
                if h['decision_humana']!=x['decision_nucleo_v9_propuesta']:
                    human_integrations.append({'codigo':h['codigo'],'openalex_id':r['openalex_id'],'propuesta_v8':r['decision_nucleo_v8_propuesta'],'juicio_humano':h['decision_humana']})
                    x.update({'decision_nucleo_v9_propuesta':h['decision_humana'],'origen_v9':'juicio_humano_previo_conservado',
                        'regla_cierre_v9':'H01_PRECEDENCIA_JUICIO_HUMANO','disposicion_documental_v9':'inclusion_por_juicio_humano_previo' if h['decision_humana']=='IN' else 'exclusion_por_juicio_humano_previo',
                        'motivo_cierre_v9':'Se conserva e integra el juicio humano previo '+h['codigo']+': '+h['motivo']+' La propuesta computacional v8 permanece en su columna original.',
                        'tipo_evidencia_cierre_v9':'calibracion_humana_previa_con_sugerencia_visible'})
        master.append({**r,**x})
    assert len(decisions)==2399
    assert len({r['openalex_id'] for r in decisions})==2399
    assert all(r['decision_nucleo_v9_propuesta'] in ('IN','OUT') for r in master)
    original_fields=list(rows[0])
    assert all({k:n[k] for k in original_fields}==o for o,n in zip(rows,master))
    assert all(r['lectura_semantica_directa_IA_v9']=='si' for r in decisions if r['decision_nucleo_v9_propuesta']=='IN')
    assert all(r['decision_nucleo_v9_propuesta']==r['decision_humana_conservada_v9'] for r in master if r['decision_humana_conservada_v9'] in ('IN','OUT'))
    assert set(overrides)<=set(r['openalex_id'] for r in decisions)
    write(OUTPUT/'Decisiones_2399_TC_v9.csv',decisions)
    write(OUTPUT/'Matriz_4735_con_cierre_v9.csv',master)
    for d in ['IN','OUT']:
        write(OUTPUT/f'{d}_propuesto_v9.csv',[r for r in master if r['decision_nucleo_v9_propuesta']==d])
    minimal=['openalex_id','title','decision_nucleo_v8_propuesta','decision_nucleo_v9_propuesta','regla_cierre_v9','disposicion_documental_v9','motivo_cierre_v9','evidencia_cierre_v9','decision_solo_IA_v9','motivo_solo_IA_v9','decision_humana_conservada_v9','codigo_humano_conservado_v9','motivo_humano_conservado_v9','lectura_semantica_directa_IA_v9']
    write(OUTPUT/'Resumen_por_ID_2399_TC_v9.csv',[{k:r[k] for k in minimal} for r in decisions])
    summary={'version':VERSION,'fecha':'2026-10-08','base_amplia':4735,'TC_v8_cerrados':2399,
       'TC_con_propuesta_IN':sum(r['decision_nucleo_v9_propuesta']=='IN' for r in decisions),
       'TC_con_propuesta_OUT':sum(r['decision_nucleo_v9_propuesta']=='OUT' for r in decisions),
       'resultado_nucleo_propuesto_v9':dict(Counter(r['decision_nucleo_v9_propuesta'] for r in master)),
       'pendientes_de_decision_binaria':0,
       'disposiciones_de_los_2399':dict(Counter(r['disposicion_documental_v9'] for r in decisions)),
       'reglas_de_los_2399':dict(Counter(r['regla_cierre_v9'] for r in decisions)),
       'auditoria_directa_IA':len(overrides),'lectura_texto_completo_nueva':0,
       'auditoria_complementaria_H011':len(extra),
       'integracion_juicios_humanos_fuera_de_TC':human_integrations,
       'discrepancias_IA_humano_TC':[{'openalex_id':r['openalex_id'],'codigo':r['codigo_humano_conservado_v9'],'propuesta_IA':r['decision_solo_IA_v9'],'juicio_humano':r['decision_humana_conservada_v9'],'propuesta_integrada':r['decision_nucleo_v9_propuesta']} for r in decisions if r['precedencia_decision_humana_v9']=='si' and r['decision_solo_IA_v9']!=r['decision_humana_conservada_v9']],
       'decision_humana_nueva_inventada':0,'decisiones_humanas_conservadas':len(human),
       'cruces_humanos_TC':[{k:r[k] for k in ['openalex_id','codigo_humano_conservado_v9','decision_humana_conservada_v9','decision_nucleo_v9_propuesta']} for r in decisions if r['codigo_humano_conservado_v9']],
       'validacion_humana_independiente_realizada':False,
       'matriz_v8_y_todas_sus_columnas_preservadas':True,
       'interpretacion':'Cierre provisional del núcleo con evidencia disponible. OUT documental no prueba irrelevancia ni revisión completa; la incertidumbre de fuente se conserva en la disposición documental.',
       'sha256_matriz_v8':source_hash}
    (OUTPUT/'Resumen_cierre_v9.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert sha(INPUT)==source_hash
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
