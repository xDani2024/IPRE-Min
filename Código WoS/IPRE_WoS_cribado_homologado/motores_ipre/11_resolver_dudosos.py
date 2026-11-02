"""Adjudicación operacional reproducible de las 1.241 fronteras v6.

No es consenso humano ni consulta de texto completo. Cada ficha recibe una
disposición binaria para el *núcleo bibliométrico provisional*, junto con una
categoría de certeza documental. Se exige evidencia positiva vinculada para
entrar; ausencia de evidencia implica fuera del núcleo, y NO equivale a una
declaración de irrelevancia definitiva. No consulta la etiqueta histórica.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
INPUT = BASE / 'entrada' / 'cola_dudosos_1241_v6.csv'
MASTER = BASE / 'entrada' / 'screening_operacional_4735_v6.csv'
ALERTS = BASE / 'entrada' / 'alertas_metadata_ampliadas_v6.csv'
OVERRIDES = BASE / 'auditoria_dirigida_de_reglas.psv'
OUTPUT = BASE / 'salida'
VERSION = 'v7_resolucion_nucleo_2026_09_28'


def rx(s):
    return re.compile(s, re.I)


SURFACE = rx(r'open[ -]?pit|open[ -]?cast|open.?cut|surface min(?:e|ing)|'
             r'surface coal|quarr(?:y|ies)|strip min(?:e|ing)|cielo abierto|'
             r'tajo abierto|cantera|карьер|разрез|terbuka|tambang terbuka')
A = rx(r'haul(?:age|ing)?|shovel|excavat(?:or|ion)|dragline|truck|dump(?:er|ing)|'
       r'load(?:ing|er)|fleet|dispatch|conveyor|bucket.?wheel|surface miner|'
       r'overburden|stripping|drill(?:ing| rig)|blast(?:ing| hole)|crusher|'
       r'mine road|haul road|pit road|dewater|pit pump|sump|watering|'
       r'material handling|material transport|mucking|perforaci[oó]n|'
       r'cam[ií]on|pala minera|cargu[ií]o|acarreo|motoniveladora|'
       r'pengupasan|alat (?:gali|muat|angkut)|samосвал|самосвал|экскаватор|'
       r'конвейер|ecavation|excavaci[oó]n|transport(?:ation|e)')
B = rx(r'optimi[sz]|compar|allocat|assign|dispatch|schedul|simulat|model|'
       r'evaluat|analys|analyz|measur|monitor|control|configur|sizi?ng|'
       r'select|maintenan|repair|reliabilit|predict|improv|assess|test|'
       r'plan(?:ning)?|design|operat|determin|estim|redu[cs]|increase|'
       r'optimiza|anal[íi]s|peningkatan|kajian|evaluasi|pengaruh')
C = rx(r'productiv|production (?:rate|capacity|output|target|loss|efficien)|'
       r'producci[oó]n(?:\s+de\s+(?:la\s+)?)?(?:\d|por|hora)|produktivitas|'
       r'throughput|tonnage|tons? per|t/h\b|tons?/?h|'
       r'cycl(?:e|ing) time|waktu edar|tiempo de ciclo|'
       r'waiting time|queu(?:e|ing)|idle time|downtime|loading time|'
       r'travel time|hauling time|transport time|turnaround time|'
       r'operating hours?|uptime|availability|(?:equipment|fleet|truck|'
       r'shovel|excavator|conveyor|vehicle) utili[sz]ation|kesiapan|'
       r'(?:equipment|fleet|truck|shovel|excavator|dragline|conveyor|drill|pump) reliability|'
       r'failure rate|repair time|mean time (?:to|between)|mtbf|mttr|'
       r'operat(?:ing|ional) costs?|haul(?:age|ing) costs?|transport(?:ation)? costs?|'
       r'cost per (?:ton|tonne|m3|unit)|unit costs?|biaya operasional|'
       r'fuel (?:use|consumption|saving|efficien)|diesel consumption|'
       r'energy (?:use|consumption|saving|efficien)|bahan bakar|'
       r'haul(?:age|ing)? distance|empty travel|travel distance|'
       r'payload|truck.?shovel match|match factor|'
       r'operat(?:ional|ing) efficien|excavator performance|shovel performance|'
       r'truck performance|fleet performance|loading performance|'
       r'haulage performance|transport(?:ation)? performance|'
       r'dragline output|equipment effectiveness|alat (?:muat|angkut)')
EVALUATED = rx(r'result|findings?|found|show(?:s|ed)?|demonstrat|'
               r'compar|experiment|case study|field (?:data|test|trial)|'
               r'simulat|calculat|estimat|measur|observ|achiev|reduc|'
               r'increas|improv|evaluat|assess|test|validat|analysis|analysed|'
               r'model(?:led|ed|ing)?|determined|study|performance')
METHOD_ONLY = rx(r'accuracy|precision|recall|f.?score|rmse|mae\b|mape\b|'
                 r'r.?squared|r2\b|convergence|comput(?:ation|ing) time|'
                 r'algorithm(?:ic)? performance|prediction error|'
                 r'classificat(?:ion|or) (?:accuracy|performance)')
STRONG_C = rx(r'productiv|production (?:rate|capacity|output|target|loss)|'
              r'throughput|tonnage|tons? per|t/h\b|tons?/?h|'
              r'cycl(?:e|ing) time|waiting time|queu(?:e|ing)|idle time|'
              r'downtime|loading time|travel time|haul(?:age|ing)? time|'
              r'operating hours?|uptime|availability|reliabilit|'
              r'failure rate|repair time|mean time (?:to|between)|mtbf|mttr|'
              r'operat(?:ing|ional) costs?|haul(?:age|ing) costs?|'
              r'transport(?:ation)? costs?|cost per (?:ton|tonne|m3|unit)|'
              r'unit costs?|fuel (?:use|consumption|saving)|diesel consumption|'
              r'energy (?:use|consumption|saving)|bahan bakar|'
              r'haul(?:age|ing)? distance|empty travel|travel distance|'
              r'payload|match factor|dragline output|equipment effectiveness|'
              r'material transported per hour|ore attainment|kesiapan|'
              r'biaya operasional|produktivitas|waktu edar|tiempo de ciclo')
RESULT_MARKER = rx(r'results? (?:show|indicat|reveal|demonstrat|found)|'
                   r'findings? (?:show|indicat|reveal)|was (?:found|reduced|'
                   r'increased|improved|measured)|were (?:found|reduced|'
                   r'increased|improved|measured)|achieved|improvement of|'
                   r'reduction of|increas(?:ed|es) by|reduc(?:ed|es) by|'
                   r'computed|calculated|estimated|measured|'
                   r'compar(?:ed|ison)|evaluat(?:ed|ion)|analysis of|'
                   r'simulation (?:results?|show)|experiment(?:al|s)?')
GOAL_MARKER = rx(r'minimi[sz]|maximi[sz]|optimi[sz]|reduc|increas|'
                 r'improv|estimat|evaluat|analys|measur|calculat|'
                 r'predict|determin|assess|cost function|objective function')
ASPIRATION = rx(r'could|would|may |might|potential to|aims to|in order to|'
                r'expected to|is expected|provides? a basis|in the future')
OTHER_FOCUS = [
 ('geotecnia',rx(r'slope|landslide|rockfall|rock mass|highwall|stabilit|'
                  r'pillar|shear strength|subsidence|seismic wave|'
                  r'rock fracture|rock hardness|cuttability|toppling|'
                  r'deformation|geo(?:techn|log)|talud|lereng')),
 ('ambiente_seguridad',rx(r'pollut|dust (?:emission|expos)|emission|'
                        r'air quality|water quality|acid mine|ecosystem|'
                        r'revegetat|rehabilitat|closure|fatalit|accident|'
                        r'fatigue|collision|hazard|safety|health|'
                        r'vibration (?:velocity|effect)|ground vibration|'
                        r'flyrock|airblast|peak particle|environment|'
                        r'runoff|erosion|soil contamin')),
 ('plan_estrategico',rx(r'ultimate pit|pit limit|block schedul|'
                       r'block sequenc|cut.?off grade|grade control|'
                       r'ore blending|life of mine|mine life|npv|'
                       r'net present value|investment|long.?term|'
                       r'pit shell|resource estimat|economic stripping ratio|'
                       r'orebody|stockpil(?:e|ing)|strategic plan')),
 ('componente',rx(r'finite element|stress analysis|structural integrity|'
                  r'microstructur|weld|wear of (?:a |the )?(?:tooth|roller)|'
                  r'bucket teeth|drill bit wear|rotary platform|'
                  r'frame optimization|mast.counterweight|'
                  r'shovel kinematics|excavat(?:ion|ing) resistance|'
                  r'rock cutting force|material failure|boom')),
 ('fragmentacion_sin_tarea',rx(r'fragment(?:ation| size)|blast(?:ing)? (?:quality|effect|vibration)|'
                             r'blast design|blasting parameter|'
                             r'blasting outcome|muckpile|rock movement|'
                             r'blast hole|boulder|mean fragment')),
]
SUPPORT = rx(r'dewater|drainage|pump|sump|haul road|mine road|'
             r'road maintenance|dust suppress|water truck|'
             r'waste dump|spreader|in.?pit crush|conveyor|'
             r'predictive maintenan|reliabilit|availability')
TEXT_SPLIT = re.compile(r'(?<=[.!?;])\s+|\n+')


def norm(s):
    s = unicodedata.normalize('NFKC', s or '')
    return ''.join('-' if unicodedata.category(c)=='Pd' else
                   ' ' if c.isspace() else c for c in s)


def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f, delimiter='|' if path.suffix=='.psv' else ','))


def write(path, rows, fields=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f, fields or list(rows[0]), extrasaction='ignore')
        w.writeheader();w.writerows(rows)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def excerpt(s, max_length=320):
    return re.sub(r'\s+',' ',s).strip()[:max_length]


def assess(q, master, alert):
    title=norm(q['title']);abstract=norm(q['abstract'])
    sentences=[s.strip() for s in TEXT_SPLIT.split(abstract) if s.strip()]
    title_a=bool(A.search(title));title_b=bool(B.search(title))
    title_c=bool(C.search(title));title_surface=bool(SURFACE.search(title))
    abstract_surface=bool(SURFACE.search(abstract[:1200]))
    other=[name for name,p in OTHER_FOCUS if p.search(title)]
    c_sents=[(i,s) for i,s in enumerate(sentences) if C.search(s)]
    linked=[]
    for i,s in c_sents:
        # A+C dentro de una oración; se admite la anterior solo cuando
        # comparte B y la oración del resultado refiere esa intervención.
        if A.search(s) and (B.search(s) or title_a and title_b):
            linked.append((i,s))
        elif i>0 and A.search(sentences[i-1]) and B.search(sentences[i-1]) and \
             rx(r'this|the (?:proposed|method|model|results?|system|approach)|'
                r'such|thereby|which|it\b|estas?|dicho').search(s):
            linked.append((i,s))
    explicit_eval=any(STRONG_C.search(s) and RESULT_MARKER.search(s) and
                      not ASPIRATION.search(s) and
                      not (METHOD_ONLY.search(s) and not STRONG_C.search(s))
                      for _,s in linked)
    head=' '.join(sentences[:3]); tail=' '.join(sentences[-3:])
    study_evaluated=bool(EVALUATED.search(head+' '+tail))
    # Ventanas donde el resultado es el desempeño de tarea, no la exactitud
    # de un modelo predictivo, un indicador ambiental o una promesa general.
    applied=[(i,s) for i,s in linked if STRONG_C.search(s) and
             GOAL_MARKER.search(s) and not ASPIRATION.search(s) and not (
                 METHOD_ONLY.search(s) and not RESULT_MARKER.search(s))]
    evidence=excerpt((applied or linked or c_sents or [(0,title)])[0][1])
    c_abs=bool(c_sents);context=title_surface or abstract_surface or q['contexto'] in ('explicito_titulo','explicito_resumen')
    bad=(alert or {}).get('abstracto_invalido_para_cribado')=='si'
    short=len(abstract.strip())<180
    relevant=title_a and (title_b or title_c) or bool(applied)
    if bad:
        proposed='OUT';code='F01_RESUMEN_INVALIDO';status='COTEJO_FUENTE'
        why='El resumen está cruzado o es editorial; no sirve para demostrar el vínculo operacional.'
    elif not context:
        proposed='OUT';code='F02_CONTEXTO_NO_ACREDITADO';status='TEXTO_COMPLETO_SI_SE_RESCATA'
        why='La ficha no acredita una operación minera a cielo abierto.'
    elif other and not (title_a and title_c and applied and study_evaluated):
        # Un foco alternativo en el título solo cede ante desempeño operacional
        # explícito de equipo/proceso y evaluación en el resumen.
        proposed='OUT';code='F03_FOCO_ALTERNATIVO';status='EVIDENCIA_TITULO_RESUMEN'
        why='Predomina '+','.join(other)+'; falta resultado evaluado de la tarea o equipo minero.'
    elif relevant and c_abs and applied and (explicit_eval or
         (title_a and title_b and any(RESULT_MARKER.search(s) for _,s in applied))) and (title_a or title_b):
        proposed='IN';code='I01_VINCULO_A_B_C';status='PROPUESTA_TITULO_RESUMEN'
        why='Proceso/equipo y decisión o análisis conectados con resultado operacional evaluado.'
    elif (title_a and title_c and c_abs and study_evaluated and
          STRONG_C.search(title) and not other):
        proposed='IN';code='I02_DESEMPENO_TITULO_CONFIRMADO';status='PROPUESTA_TITULO_RESUMEN'
        why='Título centra equipo y desempeño; resumen confirma evaluación del resultado.'
    elif title_a and title_c and not c_abs and not short and study_evaluated and not other:
        proposed='IN';code='I03_RESULTADO_EXPLICITO_TITULO';status='COTEJO_FUENTE'
        why='Título declara evaluación de desempeño operativo, aunque el resumen no precisa la métrica.'
    else:
        proposed='OUT';code='F04_VINCULO_NO_DEMOSTRADO';status='TEXTO_COMPLETO_SI_SE_RESCATA'
        why='Título/resumen no demuestran una evaluación vinculada de resultado operacional de tarea.'
    if short and proposed=='OUT' and code not in ('F01_RESUMEN_INVALIDO','F02_CONTEXTO_NO_ACREDITADO'):
        status='TEXTO_COMPLETO_SI_SE_RESCATA'
    if q['prioridad'].startswith('P0_') or alert:
        status='COTEJO_FUENTE'
    subtype='IN_APOYO' if proposed=='IN' and SUPPORT.search(title) else 'IN_DIRECTO' if proposed=='IN' else ''
    return {'decision_nucleo_v7':proposed,'subtipo_v7':subtype,'regla_v7':code,
            'explicacion_v7':why,'estado_documental_v7':status,
            'contexto_v7':'si' if context else 'no','A_titulo_v7':'si' if title_a else 'no',
            'B_titulo_v7':'si' if title_b else 'no','C_titulo_v7':'si' if title_c else 'no',
            'foco_alternativo_v7':';'.join(other),'C_resumen_v7':'si' if c_abs else 'no',
            'oraciones_AC_v7':str(len(linked)),'oraciones_ABC_eligibles_v7':str(len(applied)),
            'evidencia_textual_v7':evidence,'abstracto_invalido_v7':'si' if bad else 'no',
            'texto_completo_consultado_v7':'no','fuente_externa_consultada_v7':'no',
            'procedencia_v7':'regla_reproducible','version_v7':VERSION}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--cola',type=Path,default=INPUT)
    p.add_argument('--matriz',type=Path,default=MASTER)
    p.add_argument('--alertas',type=Path,default=ALERTS)
    p.add_argument('--auditoria',type=Path,default=OVERRIDES)
    p.add_argument('--salida',type=Path,default=OUTPUT)
    args=p.parse_args()
    q=read(args.cola);base=read(args.matriz);alerts=read(args.alertas);overrides=read(args.auditoria)
    if len(q)!=1241 or len({x['openalex_id'] for x in q})!=1241:raise ValueError('Cola no íntegra')
    if len(base)!=4735 or len({x['openalex_id'] for x in base})!=4735:raise ValueError('Matriz no íntegra')
    if len(alerts)!=58:raise ValueError('Alertas no íntegras')
    if sum(x['decision_final_propuesta']=='DUDOSO' for x in base)!=1241:raise ValueError('Versiones incongruentes')
    idset={x['openalex_id'] for x in q};lookup={x['openalex_id']:x for x in base}
    if idset!={x['openalex_id'] for x in base if x['decision_final_propuesta']=='DUDOSO'}:raise ValueError('IDs incongruentes')
    alook={x['openalex_id']:x for x in alerts}
    ol={x['openalex_id']:x for x in overrides}
    if len(ol)!=len(overrides) or set(ol)-idset:raise ValueError('Auditoría duplicada/fuera de cohorte')
    out=[]
    for x in q:
        id=x['openalex_id'];v=assess(x,lookup[id],alook.get(id))
        v['decision_pre_auditoria_v7']=v['decision_nucleo_v7']
        v['regla_pre_auditoria_v7']=v['regla_v7']
        if id in ol:
            o=ol[id]
            if o['decision_ajustada'] not in ('IN','OUT') or not o['razon_concreta']:
                raise ValueError('Ajuste inválido '+id)
            if norm(o['cita_breve_de_ficha']).casefold() not in norm(x['title']+' '+x['abstract']).casefold():
                raise ValueError('Evidencia no localizable en la ficha: '+id+' '+o['cita_breve_de_ficha'])
            v.update(decision_nucleo_v7=o['decision_ajustada'],regla_v7=o['regla_ajustada'],
                     explicacion_v7=o['razon_concreta'],
                     estado_documental_v7=o['estado_documental'],
                     evidencia_textual_v7=o['cita_breve_de_ficha'],
                     procedencia_v7='auditoria_asistida_titulo_resumen')
            v['subtipo_v7']=o['subtipo'] if o['decision_ajustada']=='IN' else ''
        out.append({**x,**v})
    # La decisión para el núcleo no sobrescribe ninguna etiqueta de la versión v6.
    args.salida.mkdir(parents=True,exist_ok=True)
    write(args.salida/'decisiones_dudosos_1241_v7.csv',out)
    byid={x['openalex_id']:x for x in out}
    master=[]
    for r in base:
        x=byid.get(r['openalex_id'])
        decision=x['decision_nucleo_v7'] if x else ('IN' if r['decision_final_propuesta'].startswith('IN') else 'OUT')
        master.append({**r,'decision_nucleo_v7':decision,
                       'origen_v7':'resolucion_dudosos_v7' if x else 'conserva_v6',
                       'regla_v7':x['regla_v7'] if x else 'V6_SIN_CAMBIO',
                       'estado_documental_v7':x['estado_documental_v7'] if x else 'SEGUN_CONTROL_V6',
                       'subtipo_v7':x['subtipo_v7'] if x else r['decision_final_propuesta'] if decision=='IN' else '',
                       'version_v7':VERSION})
    write(args.salida/'matriz_nucleo_provisional_4735_v7.csv',master)
    core=[x for x in master if x['decision_nucleo_v7']=='IN']
    write(args.salida/'corpus_IN_provisional_v7.csv',core)
    summary={'version':VERSION,'entradas_sha256':{x.name:sha(x) for x in
             (args.cola,args.matriz,args.alertas,args.auditoria)},
             'N_dudosos_v6':len(q),'N_total':len(master),
             'disposicion_dudosos':dict(Counter(x['decision_nucleo_v7'] for x in out)),
             'motivos_dudosos':dict(Counter(x['regla_v7'] for x in out)),
             'estado_documental_dudosos':dict(Counter(x['estado_documental_v7'] for x in out)),
             'prioridad_por_decision':{k:dict(v) for k,v in
                  sorted((k,Counter(x['decision_nucleo_v7'] for x in out if x['prioridad']==k))
                         for k in {x['prioridad'] for x in out})},
             'auditoria_casos':len(overrides),'cambios_auditoria':sum(x['decision_nucleo_v7']!=x['decision_pre_auditoria_v7'] for x in out),
             'decision_total':dict(Counter(x['decision_nucleo_v7'] for x in master)),
             'advertencia':'IN/OUT es una disposición provisional para el núcleo. OUT por evidencia insuficiente no afirma irrelevancia definitiva; no hay doble revisión humana ni cotejo de texto completo.'}
    (args.salida/'resumen_v7.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if len(core)+sum(x['decision_nucleo_v7']=='OUT' for x in master)!=4735:raise ValueError('Partición inválida')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
