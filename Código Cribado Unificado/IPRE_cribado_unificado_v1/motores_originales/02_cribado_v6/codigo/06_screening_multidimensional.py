"""Segunda capa de cribado propuesta, independiente de las etiquetas históricas.

Lee cada título y resumen con reglas dimensionales observables. No usa I/Q/G
anteriores para decidir. Genera una propuesta íntegra, no una revisión humana.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
BASE=Path(__file__).resolve().parent
SOURCE=ROOT/'notebook_openalex_corpus/resultado_reconciliado_2026_09_28/corpus_unificado_con_historial.csv'
AUDIT=BASE/'auditoria_dirigida_48.csv'
OUTPUT=BASE/'salida'
SEED=20260928

def recompile(s): return re.compile(s,re.I)

CONTEXT=recompile(r'open[ -]?pit|open[ -]?cast|surface min(?:ing|e)|surface coal|surface operations?|strip min(?:e|ing)|quarr(?:y|ies)|mina a cielo abierto|tajo abierto|cantera|tambang terbuka|tambang terbuk|carri[eè]re|карьер|разрез')
PROCESSES={
 'perforacion':recompile(r'\bdrill(?:ing|er| rig| rigs)?\b|blasthole|borehole|perforaci[oó]n|bor tambang|бурени'),
 'tronadura':recompile(r'\bblast(?:ing|ed| hole| holes)?\b|fragmentation|explosive|tronadura|voladura|peledakan|взрыв'),
 'carguio':recompile(r'\bload(?:ing|er|ers)?\b|shovel|excavat(?:or|ion)|dragline|bucket wheel|cargu[ií]o|pala minera|gali muat|экскаватор'),
 'transporte':recompile(r'haul(?:ing|age)?|\btrucks?\b|\btippers?\b|fleet|conveyor|belt transport|rail haul|locomotive|acarreo|transport(?:ation|e)|angkut|самосвал|конвейер'),
 'remocion_estéril':recompile(r'overburden|stripping|waste rock|spreader|surface miner|rock handling|est[eé]ril|destape|lapisan penutup'),
 'caminos_mina':recompile(r'haul road|mine road|unpaved road|ramp construction|grader|road maintenance|road condition|jalan angkut|camino minero'),
 'desague_apoyo':recompile(r'dewater|mine drainage|pit pump|pumping|sump|penyaliran|bomb(?:eo|as)|drenaje de mina'),
 'riego_polvo':recompile(r'water truck|dust suppress|road watering|sprinkler|riego de caminos|penyiraman jalan'),
 'botaderos_operacionales':recompile(r'rock dump|waste dump|dumping station|material placement|in.?pit dump|spoil spreader|botadero'),
 'chancado_en_mina':recompile(r'in.?pit crush|ipcc|semi.?continuous haul|crusher.?conveyor|chancado en mina'),
}
EQUIPMENT={
 'haul_truck':recompile(r'\btrucks?\b|\btippers?\b|camiones? mineros?|alat angkut|самосвал'),
 'shovel':recompile(r'\bshovels?\b|electric shovels?|power shovels?|pala(?:s)? el[eé]ctric'),
 'excavator':recompile(r'\bexcavat(?:or|ors)\b|excavadora|экскаватор'),
 'loader':recompile(r'wheel loader|front.?end loader|\bloaders?\b|cargador frontal'),
 'drill_rig':recompile(r'drill rigs?|blasthole drills?|rotary drill|perforadora|alat bor'),
 'dragline':recompile(r'dragline|dragalina'),
 'bucket_wheel_excavator':recompile(r'bucket wheel|rotary excavator|bwe|bager rotor'),
 'surface_miner':recompile(r'surface miners?|layer milling machine|milling combine'),
 'conveyor':recompile(r'conveyors?|belt transport|belt system|cinta transportadora|конвейер'),
 'crusher_in_pit':recompile(r'in.?pit crush|ipcc|mobile crusher'),
 'dozer':recompile(r'bulldoz|\bdozer\b|rip(?:per)? tip'),
 'grader':recompile(r'grader|motoniveladora'),
 'water_truck':recompile(r'water truck|sprinkler truck|cam[ií]on aljibe'),
 'pump':recompile(r'\bpumps?\b|bomba|pompa|насос'),
 'locomotive':recompile(r'locomotive|electrovoz|электровоз'),
 'spreader':recompile(r'spreader|stacker|apilador'),
}
DECISIONS={
 'despacho_asignacion':recompile(r'dispatch|allocat|assign|match(?:es|ing)? of hauling fleet|match factor|fleet management|despacho|asignaci[oó]n|penugasan'),
 'planificacion_corta':recompile(r'short.?term|shift schedul|daily schedul|real.?time schedul|operational planning|planificaci[oó]n operacional|planning of excavation'),
 'optimiza_configura':recompile(r'optimi[sz]|simulat|select(?:ion)? (?:procedure|method|of (?:equipment|fleet|truck|dragline))|configur|dimension|model(?:ing|ling) of (?:fleet|truck|shovel)|rational allocat|speed planning|traffic flow programming|optimiza|konfigurasi'),
 'control_ejecucion':recompile(r'operat(?:ion|ing|ional) (?:control|strategy|decision|process)|perform(?:ance)? evaluat|performance analys|productivity analys|time study|cycle analys|measur(?:e|ing) of (?:output|performance)|monitoring of (?:fleet|truck|shovel|equipment)'),
 'mantencion':recompile(r'maintenan|reliabilit|repair|fault diagnos|failure predict|time.?to.?failure|replacement time|predictive maintenan|mantenim|pemeliharaan'),
 'informacion':recompile(r'fleet monitoring|equipment monitoring|production management system|digital twin|telemetr|sensor|computer vision|object detection|uav|remote sensing|tracking'),
}
PERFORMANCE={
 'productividad_produccion':recompile(r'productivity|productive (?:time|hours)|production (?:rate|output|target|capacity|increase|loss)|(?:equipment|miner|dragline|mine) output|output of (?:the )?(?:surface miner|truck|shovel|excavator)|throughput|tonnage|rock.handling capacity|producci[oó]n|target produksi|produktivitas|производительност'),
 'disponibilidad_confiabilidad':recompile(r'availability|(?:truck|shovel|excavator|conveyor|pump|equipment|fleet|drill rig|dragline) reliabilit|reliabilit(?:y|ies) of (?:the )?(?:truck|shovel|excavator|conveyor|pump|equipment|fleet|drill rig|dragline)|unplanned downtime|(?:equipment|machine|truck|conveyor) breakdown|equipment failure|disponibilidad|fiabilidad|keandalan'),
 'utilizacion':recompile(r'(?:equipment|truck|shovel|excavator|drill|fleet|conveyor|dragline|pump) utili[sz]ation|utili[sz]ation (?:rate|of (?:the )?(?:equipment|truck|shovel|excavator|drill|fleet|conveyor|dragline|pump))|operating hours|productive time|operational time|time loss|utilizaci[oó]n|jam kerja'),
 'tiempos_esperas':recompile(r'cycl(?:e|ing) time|waiting time|queue(?:ing)?|travel time|loading time|idle time|downtime|demora|tiempo de ciclo|waktu edar'),
 'costo_operacional':recompile(r'operat(?:ing|ional) costs?|unit costs?|haulage costs?|cost per ton|truck costs?|vehicle operating costs?|costo operacional|biaya operasional'),
 'energia_combustible':recompile(r'fuel (?:consumption|use|saving|efficiency)|energy (?:consumption|use|efficiency|losses)|diesel consumption|combustible|consumo energ[eé]tico'),
 'eficiencia_tarea':recompile(r'(?:truck|shovel|excavator|bucket.wheel excavator|drill(?:ing)?|haulage|loading|transport|fleet|equipment|surface miner|dragline|conveyor|pump)\s+(?:operation(?:al)?\s+)?(?:efficien\w*|performance)|(?:efficien\w*|performance) of (?:the |a |an )?(?:truck|shovel|excavator|bucket.wheel excavator|drill|haulage|loading|transport|fleet|equipment|surface miner|dragline|conveyor|pump)|rendimiento (?:equipo|operacional)'),
}
NEGATIVE={
 'geologia_exploracion':recompile(r'geolog|geophys|orebody|resource estimat|ore reserve|mineral explor|geochem|litholog|geostatis|mineralog'),
 'geotecnia_talud':recompile(r'slope stabili|slope displacement|landslide|rockfall|geotech|pit wall|shear strength|factor of safety|bench slope|deformation monitoring|stability analysis of dump|dump stability|stability of (?:a |the )?dump'),
 'ambiente_cierre':recompile(r'water quality|acid mine drainage|abandoned.mine drainage|mine drainage treatment|revegetat|rehabilitat|mine closure|pit lake|biodivers|soil fertili|soil contamin|methane emission|air pollut|environmental victim|ecotouris|dust emission|blast vibration|ground vibration|overpressure|environmental sustainability index|landscape fragmentation'),
 'metalurgia_procesamiento':recompile(r'flotation|leach(?:ing)?|smelt|froth treatment|bitumen separation|beneficiat|ore processing|mineral processing'),
 'estrategia_vida_mina':recompile(r'ultimate pit|pit limit|life.of.mine|long.?term (?:mine|waste|truck|production) (?:plan|schedul|management)|block model size|block size for an open.pit|strategic mine plan|net present value|npv|pushback|economic stripping ratio'),
 'componente_aislado':recompile(r'finite element of (?:bucket|tooth|chassis|frame)|material propert|wear (?:prediction|behavio|rate)|structure analysis of a (?:dragline|shovel) tooth|stress analysis of (?:mast|connection|joint|frame)|structural (?:stress|integrity) of (?:a |the )?(?:shovel|excavator|truck)|protection means for high.voltage|microstructur|weld overlay|stress.strain of (?:tooth|chassis|steel)'),
 'seguridad_sin_desempeno':recompile(r'hazard awareness|safety monitoring|personnel detection|collision avoidance|occupational health|whole.body vibration|accident risk'),
 'efecto_voladura_no_operacional':recompile(r'flyrock|blast.induced vibration|ground vibration|particle vibration|blast seismic effects?|air over.pressure|nitrogen oxides|\bnox\b|rock fragmentation|fragmentation of rock|blasting outcomes|blastability'),
 'exposicion_ambiental':recompile(r'\bdust\b|emission levels?|\bpm10\b|water balance|water quality|soil erosion'),
 'geologia_instrumental':recompile(r'rock fracture density characteri[sz]ation|rock mass characteri[sz]ation|rock mass propert(?:y|ies) prediction|predicting rock hardness|rockmass classification|predicting cuttability'),
 'insumos_fuera_de_mina':recompile(r'explosive production line|emulsion explosive production|manufactur(?:ing|e) of explosives'),
 'deteccion_sin_resultado_tarea':recompile(r'object detection|road extraction from remote sensing|road mapping network|obstacle detection'),
 'documento_no_investigacion':recompile(r'\bbook review\b|\badvertisement\b|\breviewed by\b'),
}
SENTENCE_SPLIT=re.compile(r'(?<=[.!?;])\s+|\n+')
UNDERGROUND_TITLE=recompile(r'underground|subterr[aá]ne|longwall|room.and.pillar|continuous miner|raisebor(?:e|ing)|extraction level')
NONMINING_TITLE=recompile(r'urban development|urban construction|pipeline laying|building demolition|demolition of (?:a |the )?(?:plant|building|structure)')

def normalized(s):
 """NFKC, Unicode dashes and typographic spaces to ASCII for matching."""
 s=unicodedata.normalize('NFKC',s or '')
 return ''.join('-' if unicodedata.category(ch)=='Pd' or ch=='\u2212' else
                ' ' if ch.isspace() else ch for ch in s)

def read(path):
 with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(path,rows,fields):
 path.parent.mkdir(exist_ok=True,parents=True)
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def hits(patterns,text):return [name for name,p in patterns.items() if p.search(text)]
def snippet(units,condition):
 for s in units:
  if condition(s):return s.strip()[:400]
 return ''

def decide(r):
 t=normalized(r.get('title','').strip()); a=normalized(r.get('abstract','').strip())
 head=a[:800];abs_units=[x for x in SENTENCE_SPLIT.split(a) if x.strip()];units=[t]+abs_units
 main=t+'. '+a
 proc=hits(PROCESSES,main);equip=hits(EQUIPMENT,main)
 perf=hits(PERFORMANCE,main);decision=hits(DECISIONS,main)
 pt=hits(PROCESSES,t);et=hits(EQUIPMENT,t);dt=hits(DECISIONS,t);mt=hits(PERFORMANCE,t)
 negative=hits(NEGATIVE,t);negative_abs=hits(NEGATIVE,a)
 context_title=bool(CONTEXT.search(t));context_head=bool(CONTEXT.search(head))
 context_any=bool(CONTEXT.search(main))
 # Una mención solo en keywords no basta para declarar contexto.
 contextual='explicito_titulo' if context_title else 'explicito_resumen' if context_head else 'mencion_periferica' if context_any else 'sin_evidencia_expresa'
 link_ac=snippet(units,lambda s:bool(hits(PROCESSES,s) or hits(EQUIPMENT,s)) and bool(hits(PERFORMANCE,s)))
 link_ab=snippet(units,lambda s:bool(hits(PROCESSES,s) or hits(EQUIPMENT,s)) and bool(hits(DECISIONS,s)))
 link_abc=snippet(units,lambda s:bool(hits(PROCESSES,s) or hits(EQUIPMENT,s)) and bool(hits(DECISIONS,s)) and bool(hits(PERFORMANCE,s)))
 link_ac_abs=snippet(abs_units,lambda s:bool(hits(PROCESSES,s) or hits(EQUIPMENT,s)) and bool(hits(PERFORMANCE,s)))
 # Títulos de seguridad/ambiente/estabilidad tienen sus propios resultados;
 # menciones de productividad en la introducción no los convierten en IN.
 dominant=[x for x in negative if x in ('geologia_exploracion','geotecnia_talud','ambiente_cierre','metalurgia_procesamiento','estrategia_vida_mina','componente_aislado','seguridad_sin_desempeno','efecto_voladura_no_operacional','exposicion_ambiental','geologia_instrumental','insumos_fuera_de_mina','deteccion_sin_resultado_tarea','documento_no_investigacion')]
 operational_title=bool(pt or et or dt)
 operational_head=bool(hits(PROCESSES,head) or hits(EQUIPMENT,head))
 title_endpoint=bool((pt or et) and mt)
 prominent=bool(operational_title or mt)
 strong_outcome=bool((prominent and operational_head and link_ac) or title_endpoint)
 strong_intervention=bool((prominent and link_ab) or (operational_title and dt))
 abstract_confirmation=bool(link_ac_abs or
   (title_endpoint and operational_head and hits(PERFORMANCE,a) and
    re.search(r'\b(?:performance|productivity|efficiency|capacity|output|consumption|cycle time|costs?|availability)\b',a,re.I)))
 central=operational_title or operational_head
 support=bool(set(proc)&{'caminos_mina','desague_apoyo','riego_polvo','botaderos_operacionales','chancado_en_mina'} or
             set(decision)&{'mantencion','informacion','planificacion_corta'})
 language=(r.get('language') or '').lower()
 metadata=bool(r.get('quality_flags'))
 secondary_document=r.get('type')=='review'
 # El tipo 'review' se admite en el mapa de publicaciones y se señala para
 # análisis de sensibilidad; reseñas de libros/anuncios sí se apartan.
 if 'documento_no_investigacion' in dominant or re.search(r'\(review\)$',t,re.I):
  label='OUT';cause='documento_editorial_sin_estudio'
 elif UNDERGROUND_TITLE.search(t) or NONMINING_TITLE.search(t):
  label='OUT';cause='foco_subterraneo_o_extraccion_no_minera'
 elif not context_any and not (operational_title and operational_head):
  label='OUT';cause='sin_contexto_cielo_abierto'
 elif dominant and not (title_endpoint and 'geologia_exploracion' in dominant and len(dominant)==1):
  if central and (link_ac or link_ab) and ('componente_aislado' in dominant or 'estrategia_vida_mina' in dominant or 'efecto_voladura_no_operacional' in dominant or 'exposicion_ambiental' in dominant or 'geologia_instrumental' in dominant or 'deteccion_sin_resultado_tarea' in dominant):
   label='DUDOSO';cause='foco_principal_alternativo_con_enlace_posible'
  else:
   label='OUT';cause='foco_principal_'+dominant[0]
 elif central and strong_outcome and abstract_confirmation and (strong_intervention or title_endpoint):
  if support or (secondary_document and not link_abc):
   label='IN_SECUNDARIO';cause='vinculo_indirecto_o_documento_secundario'
  else:
   label='IN_FUERTE';cause='proceso_decision_y_desempeno_vinculados'
 elif central and strong_outcome and abstract_confirmation and (pt or et) and (link_ac or mt):
  label='IN_SECUNDARIO' if support else 'IN_FUERTE'
  cause='evaluacion_directa_de_desempeno_sin_intervencion_explicita'
 elif central and (strong_intervention or strong_outcome or (decision and proc) or
                   ((pt or et) and (decision or perf))):
  label='DUDOSO';cause='enlace_operacional_incompleto_en_resumen'
 elif not operational_title and not operational_head:
  label='OUT';cause='mencion_incidental_de_operacion'
 else:
  label='OUT';cause='sin_desempeno_ni_decision_operacional_demostrada'
 # Evita sesgo por resúmenes en otros idiomas cuando el foco del título sí
 # parece operacional, pero la evidencia lexicográfica es escasa.
 if label=='OUT' and language not in ('en','') and operational_title and not dominant and not strong_outcome and not UNDERGROUND_TITLE.search(t):
  label='DUDOSO';cause='idioma_o_resumen_insuficiente'
 if label=='OUT' and language not in ('en','') and not dominant and context_any and operational_head and link_ac_abs:
  label='DUDOSO';cause='idioma_o_resumen_insuficiente'
 if metadata and label.startswith('IN') and not link_abc:
  label='DUDOSO';cause='metadatos_incompatibles_verificar_fuente'
 # La distinción entre directo y secundario describe la ruta de evidencia,
 # no dos corpus finales distintos. DUDOSO se deja fuera del núcleo estricto.
 if label=='IN_FUERTE':confidence='alta' if link_abc or (operational_title and mt and strong_intervention) else 'media'
 elif label=='IN_SECUNDARIO':confidence='media'
 elif label=='DUDOSO':confidence='baja'
 else:confidence='alta' if dominant or not central else 'media'
 process=';'.join(proc) or 'no_identificado'
 equipment=';'.join(equip) or 'no_identificado'
 outcome=';'.join(perf) or 'no_identificado'
 contribution=('mantencion' if 'mantencion' in decision else
               'asignacion_optimizacion' if 'despacho_asignacion' in decision else
               'planificacion_operativa' if 'planificacion_corta' in decision else
               'informacion_automatizacion' if 'informacion' in decision and not strong_outcome else
               'auxiliares' if support else
               'ejecucion_desempeno' if strong_outcome else
               'diseno_planificacion' if 'estrategia_vida_mina' in negative else
               'no_operacional')
 justification=(f'{cause}; contexto={contextual}; proceso={process}; equipo={equipment}; '
                f'decision={";".join(decision) or "no_identificada"}; resultado={outcome}')
 return {
  'contexto_cielo_abierto':contextual,'proceso_detectado':process,'equipo_detectado':equipment,
  'decision_operacional_detectada':';'.join(decision) or 'no_identificada',
  'resultado_operacional_detectado':outcome,'contribucion':contribution,
  'foco_alternativo_titulo':';'.join(negative) or '',
  'evidencia_proceso_decision_resultado':link_abc,
  'evidencia_proceso_resultado':link_ac,'evidencia_proceso_resultado_resumen':link_ac_abs,
  'evidencia_proceso_decision':link_ab,
  'confirmacion_desempeno_en_resumen':'si' if abstract_confirmation else 'no',
  'decision_final_propuesta':label,'motivo_codificado':cause,
  'justificacion_por_dimensiones':justification,'confianza_cualitativa_no_calibrada':confidence,
  'requiere_texto_completo': 'si' if label=='DUDOSO' else 'segun_control_humano',
  'alerta_metadata':r.get('quality_flags',''),
  'protocolo_screening':'v6_2026_09_28',
  'decision_humana_1':'','decision_humana_2':'','consenso_humano':'','motivo_consenso':'',
 }

def sample(rows,n,seed,prefix,stratum):
 rng=random.Random(seed);chosen=rng.sample(sorted(rows,key=lambda r:r['openalex_id']),min(n,len(rows)))
 out=[];key=[]
 for i,r in enumerate(chosen,1):
  code=f'{prefix}-{i:03}'
  out.append({'codigo':code,'title':r['title'],'abstract':r['abstract'],'doi':r['doi'],'year':r['year'],
    'decision_revisor_1_IN_OUT_TC':'','razon_revisor_1':'','decision_revisor_2_IN_OUT_TC':'',
    'razon_revisor_2':'','consenso_IN_OUT_TC':'','razon_consenso':'','texto_completo_consultado':''})
  key.append({'codigo':code,'openalex_id':r['openalex_id'],'estrato':stratum,
    'subcategoria_propuesta':r['decision_final_propuesta'],
    'N':len(rows),'n':len(chosen),'probabilidad_n_sobre_N':f'{len(chosen)/len(rows):.10f}',
    'peso_N_sobre_n':f'{len(rows)/len(chosen):.10f}'})
 return out,key

def genuine_boundary(r):
 """Submarco diagnóstico: tema operacional central e indicio de resultado o intervención.

No utiliza las decisiones antiguas. El resto de DUDOSO sigue en el registro
y necesitaría un control aparte antes de atribuirle elegibilidad definitiva.
 """
 return (r['contexto_cielo_abierto'] in ('explicito_titulo','explicito_resumen') and
         r['proceso_detectado']!='no_identificado' and
         (r['resultado_operacional_detectado']!='no_identificado' or
          r['decision_operacional_detectada']!='no_identificada') and
         r['motivo_codificado'] in ('enlace_operacional_incompleto_en_resumen',
                                   'foco_principal_alternativo_con_enlace_posible',
                                   'idioma_o_resumen_insuficiente'))

def main():
 parser=argparse.ArgumentParser(description='Cribado operacional de cohorte OpenAlex congelada')
 parser.add_argument('--entrada',type=Path,default=SOURCE)
 args=parser.parse_args()
 source_path=args.entrada.resolve()
 source=read(source_path)
 if len(source)!=4735 or len({r['openalex_id'] for r in source})!=4735:raise ValueError('Corpus fuente no íntegro')
 OUTPUT.mkdir(exist_ok=True)
 audit=read(AUDIT)
 if len(audit)!=48 or len({r['openalex_id'] for r in audit})!=48:raise ValueError('Auditoría dirigida no íntegra')
 overrides={r['openalex_id']:r for r in audit}
 rows=[];audit_output=[]
 for r in source:
  result=decide(r)
  idshort=r['openalex_id'].rsplit('/',1)[-1]
  result['decision_algoritmica_pre_auditoria']=result['decision_final_propuesta']
  result['procedencia_ajuste']='regla_reproducible'
  result['motivo_relectura_IA_dirigida']=''
  if idshort in overrides:
   check=overrides[idshort]
   if check['decision_IA_dirigida'] not in ('IN_FUERTE','IN_SECUNDARIO','DUDOSO','OUT'):
    raise ValueError('Etiqueta inválida en auditoría: '+idshort)
   result['decision_final_propuesta']=check['decision_IA_dirigida']
   result['procedencia_ajuste']='relectura_IA_dirigida_titulo_resumen'
   result['motivo_relectura_IA_dirigida']=check['motivo_IA_dirigida']
   result['confianza_cualitativa_no_calibrada']='media' if result['decision_final_propuesta'].startswith('IN') else 'baja' if result['decision_final_propuesta']=='DUDOSO' else 'media'
   if result['decision_final_propuesta']=='DUDOSO':result['requiere_texto_completo']='si'
   audit_output.append({'openalex_id':r['openalex_id'],'title':r['title'],
     'decision_algoritmica_pre_auditoria':result['decision_algoritmica_pre_auditoria'],
     'decision_IA_dirigida':check['decision_IA_dirigida'],
     'motivo_IA_dirigida':check['motivo_IA_dirigida'],
     'cambio':'si' if result['decision_algoritmica_pre_auditoria']!=check['decision_IA_dirigida'] else 'no'})
  result['motivo_final_propuesto']=(result['motivo_relectura_IA_dirigida'] or result['motivo_codificado'])
  result['justificacion_final_propuesta']=(result['justificacion_por_dimensiones']+
    ('; relectura_IA='+result['motivo_relectura_IA_dirigida'] if idshort in overrides else ''))
  rows.append({**r,**result})
 if len(audit_output)!=len(audit):raise ValueError('ID de auditoría ausente de entrada')
 write(OUTPUT/'auditoria_IA_dirigida_48.csv',audit_output,list(audit_output[0]))
 fields=list(rows[0]);write(OUTPUT/'screening_operacional_4735.csv',rows,fields)
 by_label=defaultdict(list)
 for r in rows:by_label[r['decision_final_propuesta']].append(r)
 for label,name in [('IN_FUERTE','IN_fuerte'),('IN_SECUNDARIO','IN_secundario'),('DUDOSO','dudosos'),('OUT','OUT')]:
  write(OUTPUT/f'{name}.csv',by_label[label],fields)
 core=by_label['IN_FUERTE']+by_label['IN_SECUNDARIO']
 write(OUTPUT/'corpus_IN_propuesto.csv',core,fields)
 # Muestra de control separada de los 48 casos utilizados para afinar la regla.
 # Los N de la clave se refieren únicamente a marcos no usados en desarrollo.
 # 50 IN, 50 OUT y 30 fronteras. Otros DUDOSO siguen registrados.
 sample_rows=[];keys=[]
 unaudited=lambda rows:[r for r in rows if r['procedencia_ajuste']=='regla_reproducible']
 core_control=unaudited(core);out_control=unaudited(by_label['OUT'])
 ambiguous=[r for r in unaudited(by_label['DUDOSO']) if genuine_boundary(r)]
 if len(ambiguous)<30:raise ValueError('Submarco ambiguo demasiado pequeño')
 for label,cohort,n,prefix in [('IN',core_control,50,'I'),('OUT',out_control,50,'O'),('DUDOSO_CENTRAL',ambiguous,30,'D')]:
  blind,key=sample(cohort,n,SEED+len(label),prefix,label);sample_rows+=blind;keys+=key
 write(OUTPUT/'muestra_humana_ciega_130.csv',sample_rows,list(sample_rows[0]))
 write(OUTPUT/'clave_muestra_130_NO_ENTREGAR_A_REVISORES.csv',keys,list(keys[0]))
 counts=Counter(r['decision_final_propuesta'] for r in rows)
 transitions=defaultdict(Counter)
 for r in rows:transitions[r['estado_cribado_especifico']][r['decision_final_propuesta']]+=1
 summary={'fecha_utc':datetime.now(timezone.utc).isoformat(),'version':'v6_2026_09_28',
  'total':len(rows),'decisiones':dict(counts),'transiciones_anteriores_solo_auditoria':{k:dict(v) for k,v in transitions.items()},
  'motivos':dict(Counter(r['motivo_codificado'] for r in rows)),
  'procesos':dict(Counter(p for r in rows for p in r['proceso_detectado'].split(';') if p!='no_identificado')),
  'equipos':dict(Counter(p for r in rows for p in r['equipo_detectado'].split(';') if p!='no_identificado')),
  'contribucion':dict(Counter(r['contribucion'] for r in rows)),
  'alerta_metadata':sum(bool(r['alerta_metadata']) for r in rows),
  'muestra':dict(Counter(k['estrato'] for k in keys)),
  'marcos_muestra_no_usados_en_desarrollo':{'IN':len(core_control),'OUT':len(out_control),
    'DUDOSO_CENTRAL':len(ambiguous)},
  'marco_muestra_dudoso_central':len(ambiguous),
  'auditoria_IA_dirigida':{'total':len(audit_output),'cambios':sum(x['cambio']=='si' for x in audit_output),
    'confirmaciones':sum(x['cambio']=='no' for x in audit_output)},
  'sha256_entrada':sha(source_path),
  'sha256_auditoria_dirigida':sha(AUDIT),
  'sha256_salidas':{p.name:sha(p) for p in sorted(OUTPUT.glob('*.csv'))},
  'aviso':'Clasificación computacional de apoyo, no revisión humana ni elegibilidad final. La cohorte DUDOSO se excluye del núcleo estricto y queda disponible para análisis de sensibilidad y texto completo.'}
 (OUTPUT/'resumen_flujo.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'total':len(rows),'decisiones':dict(counts),'muestra':summary['muestra']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
