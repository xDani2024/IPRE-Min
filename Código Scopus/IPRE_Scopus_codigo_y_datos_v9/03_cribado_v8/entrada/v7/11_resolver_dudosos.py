from pathlib import Path
import argparse
ROOT = next((p for p in Path(__file__).resolve().parents if (p / 'PROCEDENCIA_DEL_PAQUETE.json').is_file()))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--entrada', type=Path, default=ROOT / '02_cribado_v6/codigo/salida/screening_operacional_scopus_fase02.csv')
parser.add_argument('--salida', type=Path, default=ROOT / '03_cribado_v8/entrada/v7/salida')
args = parser.parse_args()
if args.salida.exists() and any(args.salida.iterdir()):
    parser.error('La salida contiene archivos. Elija una carpeta nueva con --salida.')
args.salida.mkdir(parents=True, exist_ok=True)
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from types import SimpleNamespace
from functools import lru_cache
import csv, io, hashlib, json, random, re, sys, time, zipfile, unicodedata
RUTA_FASE02 = str(args.entrada)
CARPETA_SALIDA = args.salida
ARCHIVO_ESPERADO = 'screening_operacional_scopus_fase02.csv'
VERSION_LOCAL = 'v7_v8_scopus_sin_herencia_IA_openalex_2026_10'
SEED = 20261019

def huella(data):
    return hashlib.sha256(data).hexdigest()

def localizar_entrada():
    if RUTA_FASE02.strip():
        p = Path(RUTA_FASE02).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f'No existe: {p}')
        return p
    bases = [Path.cwd(), Path.cwd().parent]
    candidatos = []
    for base in bases:
        candidatos += [base / ARCHIVO_ESPERADO, base / 'resultados_fase02_scopus' / ARCHIVO_ESPERADO, base / 'IPRE_Scopus_Fase02' / 'resultados_fase02_scopus' / ARCHIVO_ESPERADO, base / 'IPRE_Scopus_Fase02_Resultados.zip', base / 'IPRE_Scopus_Fase02' / 'IPRE_Scopus_Fase02_Resultados.zip']
    for p in candidatos:
        if p.is_file():
            return p
    raise FileNotFoundError('No se encontró la matriz de Fase 02. Complete RUTA_FASE02 con su CSV o ZIP.')
ENTRADA = localizar_entrada()
if ENTRADA.suffix.lower() == '.zip':
    with zipfile.ZipFile(ENTRADA) as z:
        nombres = [s for s in z.namelist() if s.endswith('/' + ARCHIVO_ESPERADO) or s == ARCHIVO_ESPERADO]
        if len(nombres) != 1:
            raise ValueError(f'ZIP sin matriz inequívoca: {nombres}')
        datos = z.read(nombres[0])
else:
    datos = ENTRADA.read_bytes()
registros = list(csv.DictReader(io.StringIO(datos.decode('utf-8-sig'))))
ids = [str(r.get('scopus_id', '')).strip() for r in registros]
if any((not x for x in ids)) or len(set(ids)) != len(ids):
    raise ValueError('La entrada tiene scopus_id vacío o repetido.')
obligatorias = {'title', 'abstract', 'scopus_id', 'decision_final_propuesta', 'contexto_cielo_abierto', 'procedencia_ajuste', 'foco_alternativo_titulo', 'motivo_final_propuesto', 'evidencia_proceso_decision_resultado', 'evidencia_proceso_resultado_resumen', 'type'}
faltan = sorted(obligatorias - set(registros[0])) if registros else sorted(obligatorias)
if faltan:
    raise ValueError(f'Faltan columnas requeridas: {faltan}')
if not registros:
    raise ValueError('La matriz v6 está vacía.')
clases = Counter((r['decision_final_propuesta'] for r in registros))
if not set(clases) <= {'IN_FUERTE', 'IN_SECUNDARIO', 'DUDOSO', 'OUT'}:
    raise ValueError('Categorías v6 desconocidas.')
manifest_v6 = ENTRADA.parent / 'resumen_fase02_scopus.json'
control_v6 = json.loads(manifest_v6.read_text(encoding='utf-8'))
if control_v6.get('sha256_salidas_csv', {}).get(ENTRADA.name) != huella(datos):
    raise ValueError('La matriz v6 no coincide con el resumen de su ejecución.')
if any((r['procedencia_ajuste'] != 'regla_reproducible' for r in registros)):
    raise ValueError('La entrada contiene auditorías o etiquetas heredadas, que deben revisarse antes de v8.')
CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
print('Archivo:', ENTRADA)
print('Publicaciones:', len(registros), '| categorías Fase 02:', dict(clases))
print('SHA-256 archivo de entrada:', huella(datos))
print('Carpeta de salida:', CARPETA_SALIDA)
VERSION = 'v7_resolucion_nucleo_2026_09_28'

def rx(s):
    return re.compile(s, re.I)
SURFACE = rx('open[ -]?pit|open[ -]?cast|open.?cut|surface min(?:e|ing)|surface coal|quarr(?:y|ies)|strip min(?:e|ing)|cielo abierto|tajo abierto|cantera|карьер|разрез|terbuka|tambang terbuka')
A = rx('haul(?:age|ing)?|shovel|excavat(?:or|ion)|dragline|truck|dump(?:er|ing)|load(?:ing|er)|fleet|dispatch|conveyor|bucket.?wheel|surface miner|overburden|stripping|drill(?:ing| rig)|blast(?:ing| hole)|crusher|mine road|haul road|pit road|dewater|pit pump|sump|watering|material handling|material transport|mucking|perforaci[oó]n|cam[ií]on|pala minera|cargu[ií]o|acarreo|motoniveladora|pengupasan|alat (?:gali|muat|angkut)|samосвал|самосвал|экскаватор|конвейер|ecavation|excavaci[oó]n|transport(?:ation|e)')
B = rx('optimi[sz]|compar|allocat|assign|dispatch|schedul|simulat|model|evaluat|analys|analyz|measur|monitor|control|configur|sizi?ng|select|maintenan|repair|reliabilit|predict|improv|assess|test|plan(?:ning)?|design|operat|determin|estim|redu[cs]|increase|optimiza|anal[íi]s|peningkatan|kajian|evaluasi|pengaruh')
C = rx('productiv|production (?:rate|capacity|output|target|loss|efficien)|producci[oó]n(?:\\s+de\\s+(?:la\\s+)?)?(?:\\d|por|hora)|produktivitas|throughput|tonnage|tons? per|t/h\\b|tons?/?h|cycl(?:e|ing) time|waktu edar|tiempo de ciclo|waiting time|queu(?:e|ing)|idle time|downtime|loading time|travel time|hauling time|transport time|turnaround time|operating hours?|uptime|availability|(?:equipment|fleet|truck|shovel|excavator|conveyor|vehicle) utili[sz]ation|kesiapan|(?:equipment|fleet|truck|shovel|excavator|dragline|conveyor|drill|pump) reliability|failure rate|repair time|mean time (?:to|between)|mtbf|mttr|operat(?:ing|ional) costs?|haul(?:age|ing) costs?|transport(?:ation)? costs?|cost per (?:ton|tonne|m3|unit)|unit costs?|biaya operasional|fuel (?:use|consumption|saving|efficien)|diesel consumption|energy (?:use|consumption|saving|efficien)|bahan bakar|haul(?:age|ing)? distance|empty travel|travel distance|payload|truck.?shovel match|match factor|operat(?:ional|ing) efficien|excavator performance|shovel performance|truck performance|fleet performance|loading performance|haulage performance|transport(?:ation)? performance|dragline output|equipment effectiveness|alat (?:muat|angkut)')
EVALUATED = rx('result|findings?|found|show(?:s|ed)?|demonstrat|compar|experiment|case study|field (?:data|test|trial)|simulat|calculat|estimat|measur|observ|achiev|reduc|increas|improv|evaluat|assess|test|validat|analysis|analysed|model(?:led|ed|ing)?|determined|study|performance')
METHOD_ONLY = rx('accuracy|precision|recall|f.?score|rmse|mae\\b|mape\\b|r.?squared|r2\\b|convergence|comput(?:ation|ing) time|algorithm(?:ic)? performance|prediction error|classificat(?:ion|or) (?:accuracy|performance)')
STRONG_C = rx('productiv|production (?:rate|capacity|output|target|loss)|throughput|tonnage|tons? per|t/h\\b|tons?/?h|cycl(?:e|ing) time|waiting time|queu(?:e|ing)|idle time|downtime|loading time|travel time|haul(?:age|ing)? time|operating hours?|uptime|availability|reliabilit|failure rate|repair time|mean time (?:to|between)|mtbf|mttr|operat(?:ing|ional) costs?|haul(?:age|ing) costs?|transport(?:ation)? costs?|cost per (?:ton|tonne|m3|unit)|unit costs?|fuel (?:use|consumption|saving)|diesel consumption|energy (?:use|consumption|saving)|bahan bakar|haul(?:age|ing)? distance|empty travel|travel distance|payload|match factor|dragline output|equipment effectiveness|material transported per hour|ore attainment|kesiapan|biaya operasional|produktivitas|waktu edar|tiempo de ciclo')
RESULT_MARKER = rx('results? (?:show|indicat|reveal|demonstrat|found)|findings? (?:show|indicat|reveal)|was (?:found|reduced|increased|improved|measured)|were (?:found|reduced|increased|improved|measured)|achieved|improvement of|reduction of|increas(?:ed|es) by|reduc(?:ed|es) by|computed|calculated|estimated|measured|compar(?:ed|ison)|evaluat(?:ed|ion)|analysis of|simulation (?:results?|show)|experiment(?:al|s)?')
GOAL_MARKER = rx('minimi[sz]|maximi[sz]|optimi[sz]|reduc|increas|improv|estimat|evaluat|analys|measur|calculat|predict|determin|assess|cost function|objective function')
ASPIRATION = rx('could|would|may |might|potential to|aims to|in order to|expected to|is expected|provides? a basis|in the future')
OTHER_FOCUS = [('geotecnia', rx('slope|landslide|rockfall|rock mass|highwall|stabilit|pillar|shear strength|subsidence|seismic wave|rock fracture|rock hardness|cuttability|toppling|deformation|geo(?:techn|log)|talud|lereng')), ('ambiente_seguridad', rx('pollut|dust (?:emission|expos)|emission|air quality|water quality|acid mine|ecosystem|revegetat|rehabilitat|closure|fatalit|accident|fatigue|collision|hazard|safety|health|vibration (?:velocity|effect)|ground vibration|flyrock|airblast|peak particle|environment|runoff|erosion|soil contamin')), ('plan_estrategico', rx('ultimate pit|pit limit|block schedul|block sequenc|cut.?off grade|grade control|ore blending|life of mine|mine life|npv|net present value|investment|long.?term|pit shell|resource estimat|economic stripping ratio|orebody|stockpil(?:e|ing)|strategic plan')), ('componente', rx('finite element|stress analysis|structural integrity|microstructur|weld|wear of (?:a |the )?(?:tooth|roller)|bucket teeth|drill bit wear|rotary platform|frame optimization|mast.counterweight|shovel kinematics|excavat(?:ion|ing) resistance|rock cutting force|material failure|boom')), ('fragmentacion_sin_tarea', rx('fragment(?:ation| size)|blast(?:ing)? (?:quality|effect|vibration)|blast design|blasting parameter|blasting outcome|muckpile|rock movement|blast hole|boulder|mean fragment'))]
SUPPORT = rx('dewater|drainage|pump|sump|haul road|mine road|road maintenance|dust suppress|water truck|waste dump|spreader|in.?pit crush|conveyor|predictive maintenan|reliabilit|availability')
TEXT_SPLIT = re.compile('(?<=[.!?;])\\s+|\\n+')

def norm(s):
    s = unicodedata.normalize('NFKC', s or '')
    return ''.join(('-' if unicodedata.category(c) == 'Pd' else ' ' if c.isspace() else c for c in s))

def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter='|' if path.suffix == '.psv' else ','))

def write(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fields or list(rows[0]), extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def excerpt(s, max_length=320):
    return re.sub('\\s+', ' ', s).strip()[:max_length]

def assess(q, master, alert):
    title = norm(q['title'])
    abstract = norm(q['abstract'])
    sentences = [s.strip() for s in TEXT_SPLIT.split(abstract) if s.strip()]
    title_a = bool(A.search(title))
    title_b = bool(B.search(title))
    title_c = bool(C.search(title))
    title_surface = bool(SURFACE.search(title))
    abstract_surface = bool(SURFACE.search(abstract[:1200]))
    other = [name for name, p in OTHER_FOCUS if p.search(title)]
    c_sents = [(i, s) for i, s in enumerate(sentences) if C.search(s)]
    linked = []
    for i, s in c_sents:
        if A.search(s) and (B.search(s) or (title_a and title_b)):
            linked.append((i, s))
        elif i > 0 and A.search(sentences[i - 1]) and B.search(sentences[i - 1]) and rx('this|the (?:proposed|method|model|results?|system|approach)|such|thereby|which|it\\b|estas?|dicho').search(s):
            linked.append((i, s))
    explicit_eval = any((STRONG_C.search(s) and RESULT_MARKER.search(s) and (not ASPIRATION.search(s)) and (not (METHOD_ONLY.search(s) and (not STRONG_C.search(s)))) for _, s in linked))
    head = ' '.join(sentences[:3])
    tail = ' '.join(sentences[-3:])
    study_evaluated = bool(EVALUATED.search(head + ' ' + tail))
    applied = [(i, s) for i, s in linked if STRONG_C.search(s) and GOAL_MARKER.search(s) and (not ASPIRATION.search(s)) and (not (METHOD_ONLY.search(s) and (not RESULT_MARKER.search(s))))]
    evidence = excerpt((applied or linked or c_sents or [(0, title)])[0][1])
    c_abs = bool(c_sents)
    context = title_surface or abstract_surface or q['contexto'] in ('explicito_titulo', 'explicito_resumen')
    bad = (alert or {}).get('abstracto_invalido_para_cribado') == 'si'
    short = len(abstract.strip()) < 180
    relevant = title_a and (title_b or title_c) or bool(applied)
    if bad:
        proposed = 'OUT'
        code = 'F01_RESUMEN_INVALIDO'
        status = 'COTEJO_FUENTE'
        why = 'El resumen está cruzado o es editorial; no sirve para demostrar el vínculo operacional.'
    elif not context:
        proposed = 'OUT'
        code = 'F02_CONTEXTO_NO_ACREDITADO'
        status = 'TEXTO_COMPLETO_SI_SE_RESCATA'
        why = 'La ficha no acredita una operación minera a cielo abierto.'
    elif other and (not (title_a and title_c and applied and study_evaluated)):
        proposed = 'OUT'
        code = 'F03_FOCO_ALTERNATIVO'
        status = 'EVIDENCIA_TITULO_RESUMEN'
        why = 'Predomina ' + ','.join(other) + '; falta resultado evaluado de la tarea o equipo minero.'
    elif relevant and c_abs and applied and (explicit_eval or (title_a and title_b and any((RESULT_MARKER.search(s) for _, s in applied)))) and (title_a or title_b):
        proposed = 'IN'
        code = 'I01_VINCULO_A_B_C'
        status = 'PROPUESTA_TITULO_RESUMEN'
        why = 'Proceso/equipo y decisión o análisis conectados con resultado operacional evaluado.'
    elif title_a and title_c and c_abs and study_evaluated and STRONG_C.search(title) and (not other):
        proposed = 'IN'
        code = 'I02_DESEMPENO_TITULO_CONFIRMADO'
        status = 'PROPUESTA_TITULO_RESUMEN'
        why = 'Título centra equipo y desempeño; resumen confirma evaluación del resultado.'
    elif title_a and title_c and (not c_abs) and (not short) and study_evaluated and (not other):
        proposed = 'IN'
        code = 'I03_RESULTADO_EXPLICITO_TITULO'
        status = 'COTEJO_FUENTE'
        why = 'Título declara evaluación de desempeño operativo, aunque el resumen no precisa la métrica.'
    else:
        proposed = 'OUT'
        code = 'F04_VINCULO_NO_DEMOSTRADO'
        status = 'TEXTO_COMPLETO_SI_SE_RESCATA'
        why = 'Título/resumen no demuestran una evaluación vinculada de resultado operacional de tarea.'
    if short and proposed == 'OUT' and (code not in ('F01_RESUMEN_INVALIDO', 'F02_CONTEXTO_NO_ACREDITADO')):
        status = 'TEXTO_COMPLETO_SI_SE_RESCATA'
    if q['prioridad'].startswith('P0_') or alert:
        status = 'COTEJO_FUENTE'
    subtype = 'IN_APOYO' if proposed == 'IN' and SUPPORT.search(title) else 'IN_DIRECTO' if proposed == 'IN' else ''
    return {'decision_nucleo_v7': proposed, 'subtipo_v7': subtype, 'regla_v7': code, 'explicacion_v7': why, 'estado_documental_v7': status, 'contexto_v7': 'si' if context else 'no', 'A_titulo_v7': 'si' if title_a else 'no', 'B_titulo_v7': 'si' if title_b else 'no', 'C_titulo_v7': 'si' if title_c else 'no', 'foco_alternativo_v7': ';'.join(other), 'C_resumen_v7': 'si' if c_abs else 'no', 'oraciones_AC_v7': str(len(linked)), 'oraciones_ABC_eligibles_v7': str(len(applied)), 'evidencia_textual_v7': evidence, 'abstracto_invalido_v7': 'si' if bad else 'no' if alert else 'no_verificado', 'texto_completo_consultado_v7': 'no', 'fuente_externa_consultada_v7': 'no', 'procedencia_v7': 'regla_reproducible', 'version_v7': VERSION}
V7 = SimpleNamespace(**{k: globals()[k] for k in ('SURFACE', 'A', 'B', 'C', 'EVALUATED', 'METHOD_ONLY', 'STRONG_C', 'RESULT_MARKER', 'GOAL_MARKER', 'ASPIRATION', 'OTHER_FOCUS', 'SUPPORT', 'TEXT_SPLIT', 'norm', 'excerpt', 'assess')})
print('Reglas v7 cargadas; sin importar historial ni ajustes IA de OpenAlex.')

def prioridad_scopus(r):
    flag = ' '.join((str(r.get(k, '') or '') for k in ('alerta_metadata', 'quality_flags', 'documental_estado')))
    if 'invalido' in flag.casefold() or 'resumen_compartido' in flag.casefold():
        return 'P0_VERIFICAR_RESUMEN'
    if 'no_verificado' in flag.casefold() and r.get('contexto_cielo_abierto') not in ('explicito_titulo', 'explicito_resumen'):
        return 'P0_COTEJAR_METADATOS'
    if r.get('resultado_operacional_detectado', '') not in ('', 'no_identificado') and r.get('decision_operacional_detectada', '') not in ('', 'no_identificada'):
        return 'P1_ENLACE_CERCANO'
    if r.get('resultado_operacional_detectado', '') not in ('', 'no_identificado'):
        return 'P2_ENLACE_PARCIAL'
    return 'P3_CONTROL_FRONTERA'
v7_dudosos = []
for i, r in enumerate(registros, 1):
    if r['decision_final_propuesta'] != 'DUDOSO':
        continue
    q = {**r, 'contexto': r['contexto_cielo_abierto'], 'prioridad': prioridad_scopus(r)}
    d = V7.assess(q, r, None)
    d['decision_pre_auditoria_v7'] = d['decision_nucleo_v7']
    d['regla_pre_auditoria_v7'] = d['regla_v7']
    d['prioridad_scopus_v7'] = q['prioridad']
    v7_dudosos.append({**r, **d})
    if len(v7_dudosos) % 300 == 0:
        print(f'v7 DUDOSO: {len(v7_dudosos)}')
byid_v7 = {r['scopus_id']: r for r in v7_dudosos}
matriz_v7 = []
for r in registros:
    d = byid_v7.get(r['scopus_id'])
    in_v6 = r['decision_final_propuesta'] in ('IN_FUERTE', 'IN_SECUNDARIO')
    decision = d['decision_nucleo_v7'] if d else 'IN' if in_v6 else 'OUT'
    aux = {'decision_nucleo_v7': decision, 'origen_v7': 'resolucion_dudosos_v7' if d else 'conserva_v6', 'regla_v7': d['regla_v7'] if d else 'V6_SIN_CAMBIO', 'estado_documental_v7': d['estado_documental_v7'] if d else 'SEGUN_CONTROL_V6', 'subtipo_v7': d['subtipo_v7'] if d else r['decision_final_propuesta'] if in_v6 else '', 'version_v7': 'v7_resolucion_nucleo_2026_09_28'}
    matriz_v7.append({**r, **aux})
if not (len(matriz_v7) == len(registros) and len(v7_dudosos) == clases['DUDOSO']):
    raise ValueError('Control de integridad incumplido')
print('v7 dudosos:', dict(Counter((r['decision_nucleo_v7'] for r in v7_dudosos))))
print('v7 corpus completo:', dict(Counter((r['decision_nucleo_v7'] for r in matriz_v7))))
for nombre, rows in [('matriz_scopus_v7.csv', matriz_v7), ('decisiones_dudosos_scopus_v7.csv', v7_dudosos), ('corpus_IN_provisional_v7.csv', [r for r in matriz_v7 if r['decision_nucleo_v7'] == 'IN'])]:
    with (args.salida / nombre).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
        f.flush()
        import os
        os.fsync(f.fileno())
    if not len(read(args.salida / nombre)) == len(rows):
        raise ValueError((nombre, len(read(args.salida / nombre)), len(rows)))
    print('CSV comprobado:', nombre, len(rows), flush=True)
(args.salida / 'resumen_v7.json').write_text(json.dumps({'N': len(matriz_v7), 'conteos': dict(Counter((r['decision_nucleo_v7'] for r in matriz_v7))), 'sha256_entrada': huella(datos), 'N_dudosos_v6': len(v7_dudosos), 'auditorias_scopus_incorporadas': 0, 'verificacion_resumenes': 'pendiente', 'reglas_dudosos': dict(Counter((r['regla_v7'] for r in v7_dudosos))), 'sha256_salidas': {p.name: huella(p.read_bytes()) for p in args.salida.glob('*.csv')}}, ensure_ascii=False, indent=2), encoding='utf-8')
