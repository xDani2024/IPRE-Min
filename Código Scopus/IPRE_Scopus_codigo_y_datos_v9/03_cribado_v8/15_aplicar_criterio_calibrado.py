from pathlib import Path
import argparse
ROOT = next((p for p in Path(__file__).resolve().parents if (p / 'PROCEDENCIA_DEL_PAQUETE.json').is_file()))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--entrada', type=Path, default=ROOT / '03_cribado_v8/entrada/v7/salida')
parser.add_argument('--salida', type=Path, default=ROOT / '03_cribado_v8/salida')
parser.add_argument('--entrada-v6', type=Path, default=ROOT / '02_cribado_v6/codigo/salida/screening_operacional_scopus_fase02.csv')
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
RUTA_FASE02 = str(args.entrada_v6)
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
matriz_v7 = read(args.entrada / 'matriz_scopus_v7.csv')
v7_dudosos = read(args.entrada / 'decisiones_dudosos_scopus_v7.csv')
control_v7 = json.loads((args.entrada / 'resumen_v7.json').read_text(encoding='utf-8'))
if control_v7.get('sha256_entrada') != huella(datos):
    raise ValueError('v7 procede de otra matriz v6.')
for nombre in ('matriz_scopus_v7.csv', 'decisiones_dudosos_scopus_v7.csv'):
    if control_v7.get('sha256_salidas', {}).get(nombre) != huella((args.entrada / nombre).read_bytes()):
        raise ValueError('Archivo v7 modificado: ' + nombre)
if not [r['scopus_id'] for r in matriz_v7] == [r['scopus_id'] for r in registros]:
    raise ValueError('Control de integridad incumplido')
if not len(v7_dudosos) == clases['DUDOSO']:
    raise ValueError('Control de integridad incumplido')
REVIEW = rx('\\bsystematic (?:literature )?review\\b|\\bscoping review\\b|\\bliterature review\\b|\\bmeta.analysis\\b|\\breview (?:of|on)\\b|\\ba review\\b|\\breview and research agenda\\b')
SECONDARY_ABSTRACT = rx('\\bthis (?:systematic |literature |scoping )?review\\b|\\bsystematic literature review\\b|\\b(?:bibliometric|scientometric) analysis\\b')
OWN_EVALUATION = rx('\\b(?:we|this (?:study|paper)) (?:propos|develop|present|introduc)|\\bnew (?:model|method|algorithm)\\b|\\bfield experiment\\b')
SUPPORT = rx('water(?:ing)? truck|dust (?:suppress|palliat|control)|watering|road maintenance|haul road management|fuel truck|refuel|dewater|drainage|sump|pit pump|riego|abastecimiento')
WHOLE_EQUIPMENT = rx('truck|shovel|excavator|dragline|drilling rig|fleet|conveyor|surface miner|equipment|cam[ií]on|pala|perforadora')
WHOLE_METRIC = rx('productiv|production (?:rate|capacity|output)|throughput|cycl(?:e|ing) time|downtime|availability|utili[sz]ation|operating hours?|uptime|fuel consumption|energy consumption|operat(?:ing|ional) cost|repair time|mtbf|mttr')
FUTURE_ONLY = rx('\\bcould\\b|\\bwould\\b|\\bmay\\b|\\bmight\\b|\\bpotential to\\b|\\bexpected to\\b|\\bin the future\\b|\\byet to be\\b|\\bwill be (?:tested|evaluated|validated)\\b')
OUTSIDE = rx('underground (?:mine|mining)|deep sea|subsea|ocean mining|offshore|tunnel boring|tunnell?ing|oil (?:well|drilling)')
EDITORIAL = rx('^editorial\\b|^preface\\b|^foreword\\b|^erratum\\b|^corrigendum\\b')
COMPONENT = rx('\\btires?\\b|\\btyres?\\b|bucket teeth|drill bits?|gearbox|bearings?|weld|microstructur|hydraulic cylinder|wheel (?:repair|weld)|drive wheel')
COMPONENT_ENDPOINT = rx('microstructur|wear resistance|residual life|remaining life|hardness|tensile strength|fatigue strength')
STRATEGIC_TITLE = rx('final pit|ultimate pit|pit limit|pit delimit|block sequenc|block schedul|cut.off grade|ore blending')
PROJECT_VALUE = rx('net present value|\\bnpv\\b|revenue factor|mining asset')
PROCESS_PATTERNS = {'perforacion': 'drill|perforaci[oó]n|bor rig', 'tronadura': 'blast|tronadura|voladura', 'carguio_excavacion': 'shovel|excavat|dragline|loader|loading|cargu[ií]o|pala minera', 'acarreo': 'haul|truck|material transport|acarreo|cam[ií]on', 'riego_control_polvo': 'water(?:ing)? truck|dust (?:suppress|palliat|control)|watering|riego', 'caminos': 'haul road|mine road|road maintenance|road management', 'abastecimiento': 'fuel truck|refuel|fuel supply|abastecimiento', 'desague': 'dewater|drainage|sump|pit pump', 'mantenimiento_equipos': 'maintenan|reliabilit|repair|mantenim|mantenci[oó]n', 'transporte_continuo': 'conveyor|in.pit crush|ipcc|spreader'}
PROBLEM_PATTERNS = {'diseno': 'design|sizing|disen[oó]|diseñ', 'planificacion': '\\bplanning\\b|\\bplan(?:s|ned)?\\b|schedul|sequenc|programaci[oó]n', 'asignacion_despacho': 'allocat|assign|dispatch|fleet management|despacho', 'ejecucion_operacion': 'productiv|cycle time|operational performance|loading|haulage performance', 'mantenimiento_confiabilidad': 'maintenan|reliabilit|repair|downtime|availability', 'reemplazo_ciclo_vida': 'replac|lifetime|life cycle|equipment life', 'ambiente_seguridad': 'environment|emission|pollut|safety|accident|dust|hazard', 'automatizacion_control': 'autonom|automat|control|robot|intelligent|machine learning'}
INDICATOR_PATTERNS = {'produccion_productividad': 'productiv|production (?:rate|capacity|output|target)|throughput|tonnage|tons? per|increase in production|production (?:increas|improv|decreas|reduc)', 'ciclo_tiempos': 'cycle time|loading time|travel time|hauling time|operating hours|waktu edar', 'esperas': 'waiting time|queue|queuing|idle time', 'disponibilidad_confiabilidad': 'availability|downtime|uptime|reliabilit|failure rate|mtbf|mttr|repair time', 'utilizacion': 'utili[sz]ation|equipment effectiveness', 'combustible_energia': 'fuel (?:use|consumption|saving)|energy (?:use|consumption|saving)|diesel consumption', 'distancia': '(?:travel|haulage|hauling|route|routing) distance|distance traveled|route length|travel length|path length', 'costo_tarea': 'operat(?:ing|ional) costs?|haul(?:age|ing) costs?|unit costs?|cost per (?:ton|tonne|unit)|drilling costs?|blasting costs?|watering costs?|costs? of (?:drilling|blasting|watering|haulage)', 'frecuencia_apoyo': '(?:watering|spray|application|maintenance) frequency|frequency of (?:watering|application|maintenance)|application rate', 'indicador_ambiental': 'emission|pollut|air quality|water quality|dust concentration|ghg', 'precision_tiempo_algoritmo': 'accuracy|precision|recall|rmse|mae\\b|convergence|computational time'}
EVIDENCE_PATTERNS = {'campo': 'field (?:data|test|trial|experiment|measurement)|operational data|historical data|real.world data|collected data|case study', 'laboratorio': 'laboratory|laborat[oó]rio|laboratorio', 'simulacion': 'simulat|discrete.event|simulaci[oó]n', 'modelo_analitico_optimizacion': 'mathematical model|analytical model|optimization model|mixed.integer|linear programming|queueing model'}

def signals(patterns, text):
    return ';'.join((k for k, p in patterns.items() if rx(p).search(text)))
old = V7
audits7 = {}
human = {}
alerts = {}
VERSION = 'v8_calibrada_1_implementacion_SCOPUS_LOCAL'
CRITERIO = 'v8_calibrada_1_reglas_sin_ajustes_IA_OpenAlex'
FECHA = '2026-10-19'
print('Patrones v8 cargados y herencia histórica desactivada.')
metric = rx(old.STRONG_C.pattern + '|' + '|'.join((p for k, p in INDICATOR_PATTERNS.items() if k not in ('indicador_ambiental', 'precision_tiempo_algoritmo'))))
task = rx(old.A.pattern + '|' + SUPPORT.pattern)
evaluated = rx(old.RESULT_MARKER.pattern + '|\\bresults?\\b|\\bfindings?\\b|\\bcase study\\b|\\bmeasur|\\bexperiment|\\bshow(?:s|n|ed)?\\b|\\bsav(?:ed|ing|ings)\\b')
rows = matriz_v7
out = []
events = []
development = []
print('Iniciando v8...')
t0 = time.time()
for r in rows:
    oid = r['scopus_id']
    title = old.norm(r['title'])
    abstract = old.norm(r['abstract'])
    text = title + '\n' + abstract
    sents = [s.strip() for s in old.TEXT_SPLIT.split(abstract) if s.strip()]
    context = bool(old.SURFACE.search(text)) or r['contexto_cielo_abierto'] in ('explicito_titulo', 'explicito_resumen')
    a = bool(task.search(title)) or bool(task.search(abstract))
    b = bool(old.B.search(text))
    metric_sents = [s for s in sents if metric.search(s)]
    linked = []
    for i, s in enumerate(sents):
        if not metric.search(s):
            continue
        prev = sents[i - 1] if i else ''
        antecedent = prev if task.search(prev) and old.B.search(prev) and rx('this|these|the (?:proposed|method|model|results?|system)|which|thereby').search(s) else ''
        window = (antecedent + ' ' + s).strip()
        relation = task.search(s) or antecedent or (task.search(title) and (old.B.search(title) or old.EVALUATED.search(title)))
        result = evaluated.search(window)
        if relation and result and (not FUTURE_ONLY.search(s)):
            if old.METHOD_ONLY.search(s) and (not WHOLE_METRIC.search(s)) and (not rx(INDICATOR_PATTERNS['distancia'] + '|' + INDICATOR_PATTERNS['costo_tarea']).search(s)):
                continue
            linked.append(window)
    c = bool(linked)
    invalid = alerts.get(oid, {}).get('abstracto_invalido_para_cribado') == 'si'
    secondary_title = bool(REVIEW.search(title))
    secondary_text = bool(SECONDARY_ABSTRACT.search(abstract[:1200]))
    secondary = secondary_title or secondary_text
    hybrid = secondary and bool(OWN_EVALUATION.search(abstract)) and c
    focus = [(name, p.search(title)) for name, p in old.OTHER_FOCUS if p.search(title)]
    alt_previous = r['foco_alternativo_titulo']
    component = bool(COMPONENT.search(title)) or any((name == 'componente' for name, _ in focus))
    component_link = any((WHOLE_EQUIPMENT.search(s) and WHOLE_METRIC.search(s) for s in linked))
    reasons_dev = []
    if r['procedencia_ajuste'] == 'relectura_IA_dirigida_titulo_resumen':
        reasons_dev.append('auditoria_IA_v6')
    if oid in audits7:
        reasons_dev.append('auditoria_IA_v7')
    if oid in human:
        reasons_dev.append('piloto_humano_visible_20')
    for d in reasons_dev:
        development.append({'scopus_id': oid, 'origen_desarrollo': d})
    evidence = old.excerpt((linked or metric_sents or [title])[0], 700)
    source = 'titulo_resumen_congelado'
    doc = 'mixto_por_cotejar' if hybrid else 'secundario_detectado' if secondary else 'no_determinable'
    if invalid:
        decision, rule = ('TC', 'T01_METADATA_INVALIDA')
        why = 'Resumen diagnosticado como cruzado/editorial. Cotejar la fuente antes de interpretar A/B/C.'
        source = 'alerta_bibliografica_previa'
    elif EDITORIAL.search(title):
        decision, rule = ('OUT', 'O01_EDITORIAL')
        why = 'El título identifica un editorial, prefacio o corrección, sin estudio primario.'
        evidence = title
    elif secondary and (not hybrid):
        decision, rule = ('OUT', 'O02_LITERATURA_SECUNDARIA')
        why = 'La ficha identifica una revisión/síntesis sin evaluación primaria propia detectada. Se conserva en la base amplia.'
        evidence = title if secondary_title else old.excerpt(abstract, 700)
    elif hybrid:
        decision, rule = ('TC', 'T02_DOCUMENTO_HIBRIDO')
        why = 'Coexisten señales de revisión y evaluación propia. Cotejar el documento, no decidir solo por su tipo OpenAlex.'
    elif not context:
        if OUTSIDE.search(title) and (not old.SURFACE.search(title)):
            decision, rule = ('OUT', 'O03_CONTEXTO_ALTERNATIVO')
            why = 'El título centra la operación en un contexto distinto del alcance a cielo abierto.'
            evidence = title
        else:
            decision, rule = ('TC', 'T03_CONTEXTO_INSUFICIENTE')
            why = 'La ficha no establece suficientemente el contexto a cielo abierto. Falta cotejo.'
    elif component and (not component_link) and COMPONENT_ENDPOINT.search(abstract) and (not WHOLE_METRIC.search(abstract)):
        decision, rule = ('OUT', 'O06_RESULTADO_DE_COMPONENTE')
        why = 'El objeto es un componente/material y los resultados identificados corresponden a ese nivel; no son desempeño operacional del equipo completo.'
        evidence = old.excerpt(next((s for s in sents if COMPONENT_ENDPOINT.search(s)), title), 700)
    elif component and (not component_link):
        decision, rule = ('TC', 'T04_COMPONENTE_SIN_VINCULO_OPERACIONAL')
        why = 'Predomina un componente/material. No se acredita su vínculo con el desempeño del equipo completo.'
        evidence = title
    elif a and b and c:
        decision, rule = ('IN', 'I01_TAREA_RESULTADO_EVALUADO')
        why = 'Se detecta vínculo entre tarea/equipo, evaluación y resultado operacional evaluado; requiere control humano.'
        doc = 'primario_propuesto'
    elif oid in audits7 and audits7[oid]['decision_ajustada'] == 'IN':
        audit = audits7[oid]
        decision, rule = ('IN', 'I02_AUDITORIA_IA_PREVIA_COMPATIBLE')
        why = 'Se conserva la auditoría IA v7: ' + audit['razon_concreta']
        evidence = audit['cita_breve_de_ficha']
        source = 'auditoria_IA_v7_titulo_resumen_heredada'
        doc = 'primario_propuesto'
    elif r['procedencia_ajuste'] == 'relectura_IA_dirigida_titulo_resumen' and r['decision_nucleo_v7'] == 'IN' and (not rx('a[uú]n prevista|prueba.*prevista|pilot.*planned|verificar cercan[ií]a bibliogr').search(r['motivo_final_propuesto'])):
        decision, rule = ('IN', 'I03_AUDITORIA_IA_V6_COMPATIBLE')
        why = 'Se conserva la lectura dirigida IA v6: ' + r['motivo_final_propuesto']
        source = 'auditoria_IA_v6_titulo_resumen_heredada'
        evidence = r['evidencia_proceso_decision_resultado'] or r['evidencia_proceso_resultado_resumen'] or old.excerpt(abstract, 700)
        doc = 'primario_propuesto'
    elif STRATEGIC_TITLE.search(title) or (PROJECT_VALUE.search(abstract) and (not linked)):
        decision, rule = ('OUT', 'O07_RESULTADO_DE_MINA_PROYECTO')
        why = 'Se identifica diseño/secuencia de pit o valor del proyecto, sin resultado operacional propio de tarea/equipo acreditado.'
        evidence = title if STRATEGIC_TITLE.search(title) else old.excerpt(next((s for s in sents if PROJECT_VALUE.search(s))), 700)
    elif focus or alt_previous:
        decision, rule = ('OUT', 'O04_FOCO_ALTERNATIVO_IDENTIFICADO')
        why = 'Foco alternativo identificado en título/ficha: ' + (';'.join((name for name, _ in focus)) or alt_previous) + '. No se detectó resultado propio de la tarea operacional.'
        evidence = title
    elif oid in audits7 and audits7[oid]['regla_ajustada'] in ('A02_METRICA_DEL_MODELO', 'A04_FOCO_ESTRATEGICO', 'A05_FUERA_DE_MINA'):
        decision, rule = ('OUT', 'O05_AUDITORIA_IA_PREVIA_FOCO_EXPLICITO')
        why = 'Se conserva el foco documentado en la auditoría IA v7: ' + audits7[oid]['razon_concreta']
        evidence = audits7[oid]['cita_breve_de_ficha']
        source = 'auditoria_IA_v7_titulo_resumen_heredada'
    else:
        decision, rule = ('TC', 'T05_RESULTADO_NO_ACREDITADO')
        why = 'La evidencia de título/resumen no acredita conjuntamente A/B/C. No se infiere irrelevancia definitiva.'
    h = human.get(oid, {})
    old_insufficient = r['estado_documental_v7'] == 'TEXTO_COMPLETO_SI_SE_RESCATA'
    evsignals = signals(EVIDENCE_PATTERNS, text)
    process = signals(PROCESS_PATTERNS, title)
    problem = signals(PROBLEM_PATTERNS, title)
    function = 'no_determinable'
    principal = bool(rx('perforacion|tronadura|carguio_excavacion|acarreo').search(process))
    support = bool(rx('riego_control_polvo|caminos|abastecimiento|desague|mantenimiento_equipos').search(process))
    if principal and support:
        function = 'ambas_segun_senales_titulo'
    elif support:
        function = 'auxiliar_segun_senales_titulo'
    elif principal:
        function = 'principal_segun_senales_titulo'
    if rx('fuel truck|water(?:ing)? truck').search(title):
        function = 'auxiliar_segun_senales_titulo'
    if 'mantenimiento_equipos' in process or rx('replac|lifetime|life cycle').search(title):
        function = 'transversal_mantenimiento_por_cotejar'
    level = 'no_determinable'
    if component:
        level = 'componente_por_cotejar'
    elif SUPPORT.search(title):
        level = 'tarea_auxiliar_propuesta'
    elif rx('fleet|truck.shovel|dispatch|system').search(title):
        level = 'flota_sistema_propuesto'
    elif WHOLE_EQUIPMENT.search(title):
        level = 'equipo_propuesto'
    x = {'decision_regla_v8': decision, 'decision_nucleo_v8_propuesta': decision, 'regla_v8': rule, 'motivo_v8': why, 'evidencia_textual_v8': evidence, 'fuente_decision_v8': source, 'contexto_A_v8': 'acreditado_en_ficha' if context else 'por_cotejar', 'tarea_A_senal_v8': 'si' if a else 'no', 'evaluacion_B_senal_v8': 'si' if b else 'no', 'resultado_C_enlace_regla_v8': 'si' if c else 'no', 'oraciones_resultado_enlazado_v8': str(len(linked)), 'documento_v8_propuesto': doc, 'tipo_scopus_review_sin_confirmacion_v8': 'si' if r['type'] == 'review' and (not secondary) else 'no', 'alerta_bibliografica_previa_v8': 'si' if oid in alerts else 'sin_auditoria_bibliografica', 'cotejo_bibliografico_pendiente_v8': 'no' if oid in alerts and alerts[oid].get('verificado_en_fuente') else 'si', 'senales_proceso_titulo_v8': process or 'no_identificadas', 'senales_problema_titulo_v8': problem or 'no_identificadas', 'funcion_v8_propuesta': function, 'indicadores_mencionados_v8': signals(INDICATOR_PATTERNS, text) or 'ninguno_identificado', 'indicadores_en_evidencia_v8': signals(INDICATOR_PATTERNS, ' '.join(linked)) or 'ninguno_identificado', 'nivel_resultado_v8_propuesto': level, 'tipo_evidencia_mencionada_v8': ('revision;' if secondary else '') + (evsignals or 'no_determinable'), 'estado_evidencia_regla_v8': 'evaluado_detectado' if c else 'por_cotejar', 'texto_completo_leido_en_corrida_v8': 'no', 'metodo_v8': 'reglas_computacionales_sin_auditorias_openalex_heredadas', 'fuera_nucleo_no_excluye_base_amplia_v8': 'si', 'pertenece_piloto_calibracion_v8': 'si' if h else 'no', 'codigo_piloto_v8': h.get('codigo', ''), 'sugerencia_IA_piloto_conservada_v8': h.get('sugerencia_IA', ''), 'decision_humana_piloto_original_v8': h.get('decision_humana', ''), 'motivo_humano_piloto_original_v8': h.get('motivo', ''), 'decision_humana_piloto_actual_v8': h.get('decision_humana_actual', ''), 'humano_y_regla_v8_coinciden_en_piloto': ('si' if h['decision_humana_actual'] == decision else 'no') if h else '', 'caso_desarrollo_v8': ';'.join(reasons_dev), 'insuficiente_v7_conservado_v8': 'si' if old_insufficient else 'no', 'cambio_propuesto_v7_a_v8': r['decision_nucleo_v7'] + '>' + decision, 'version_criterio_v8': CRITERIO, 'version_implementacion_v8': VERSION, 'fecha_instantanea_v8': FECHA}
    if set(x) & set(r):
        raise ValueError('Intento de sobrescribir columnas históricas.')
    out.append({**r, **x})
    events.append({'scopus_id': oid, 'version': VERSION, 'actor_tipo': 'regla_computacional', 'etiqueta_previa_v7': r['decision_nucleo_v7'], 'propuesta_v8': decision, 'regla': rule, 'motivo': why, 'fuente': source, 'evidencia': evidence, 'fecha': FECHA, 'estado': 'propuesta_sin_validacion_independiente'})
print('v8 terminada en', round(time.time() - t0, 1), 'segundos')
if not len(out) == len(registros):
    raise ValueError('Control de integridad incumplido')
if not len(set((r['scopus_id'] for r in out))) == len(registros):
    raise ValueError('Control de integridad incumplido')
print('Conteos v8:', dict(Counter((r['decision_nucleo_v8_propuesta'] for r in out))))
print('Transiciones v7->v8:', dict(Counter((r['cambio_propuesto_v7_a_v8'] for r in out))))

def exportar_csv(p, filas, columnas=None):
    columnas = columnas or (list(filas[0]) if filas else [])
    with p.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction='ignore')
        w.writeheader()
        w.writerows(filas)
        f.flush()
        import os
        os.fsync(f.fileno())
outputs = []

def exporta(nombre, filas, columnas=None):
    p = CARPETA_SALIDA / nombre
    exportar_csv(p, filas, columnas)
    outputs.append(p)
    print(nombre, ':', len(filas))
exporta('matriz_scopus_v7.csv', matriz_v7)
exporta('decisiones_dudosos_scopus_v7.csv', v7_dudosos)
exporta('matriz_completa_scopus_v8.csv', out)
for etiqueta in ('IN', 'OUT', 'TC'):
    exporta(f'{etiqueta}_propuesto_scopus_v8.csv', [r for r in out if r['decision_nucleo_v8_propuesta'] == etiqueta], list(out[0]))
cambios = [{'scopus_id': r['scopus_id'], 'title': r['title'], 'decision_nucleo_v7': r['decision_nucleo_v7'], 'decision_nucleo_v8_propuesta': r['decision_nucleo_v8_propuesta'], 'regla_v8': r['regla_v8'], 'motivo_v8': r['motivo_v8'], 'evidencia_textual_v8': r['evidencia_textual_v8']} for r in out if r['decision_nucleo_v7'] != r['decision_nucleo_v8_propuesta']]
exporta('cambios_propuestos_por_ID_scopus_v8.csv', cambios, ['scopus_id', 'title', 'decision_nucleo_v7', 'decision_nucleo_v8_propuesta', 'regla_v8', 'motivo_v8', 'evidencia_textual_v8'])
exporta('eventos_propuesta_scopus_v8.csv', events)
exporta('casos_desarrollo_scopus_v8.csv', development, ['scopus_id', 'origen_desarrollo'])
objetivos = {'IN': 40, 'OUT': 40, 'TC': 50}
ciega = []
clave = []
for estado, n in objetivos.items():
    pool = sorted((r for r in out if r['decision_nucleo_v8_propuesta'] == estado), key=lambda r: r['scopus_id'])
    n = min(n, len(pool))
    for i, r in enumerate(random.Random(SEED + len(estado)).sample(pool, n), 1):
        c = f'{estado}-{i:03d}'
        ciega.append({'codigo': c, 'title': r['title'], 'abstract': r['abstract'], 'doi': r['doi'], 'year': r['year'], 'decision_revisor_1_IN_OUT_TC': '', 'motivo_revisor_1': '', 'decision_revisor_2_IN_OUT_TC': '', 'motivo_revisor_2': '', 'consenso_IN_OUT_TC': '', 'motivo_consenso': '', 'texto_completo_consultado': ''})
        clave.append({'codigo': c, 'scopus_id': r['scopus_id'], 'estrato_v8': estado, 'N': len(pool), 'n': n, 'regla_v8': r['regla_v8'], 'propuesta_v8': estado})
pares = list(zip(ciega, clave))
random.Random(SEED + 9001).shuffle(pares)
for numero, (ficha, llave) in enumerate(pares, 1):
    ficha['codigo'] = llave['codigo'] = f'R-{numero:03d}'
ciega = [f for f, k in pares]
clave = [k for f, k in pares]
exporta('muestra_ciega_130_scopus_v8.csv', ciega)
exporta('clave_muestra_130_NO_ENTREGAR_A_REVISORES.csv', clave)
conteos = dict(Counter((r['decision_nucleo_v8_propuesta'] for r in out)))
summary = {'fuente': 'Scopus', 'etapa': 'v7_v8_cribado_calibrado', 'N_base_amplia_sin_alterar': len(out), 'N_dudosos_fase02': len(v7_dudosos), 'conteos_fase02': dict(clases), 'conteos_v7': dict(Counter((r['decision_nucleo_v7'] for r in matriz_v7))), 'conteos_propuesta_v8': conteos, 'transiciones_v7_a_v8': dict(sorted(Counter((r['cambio_propuesto_v7_a_v8'] for r in out)).items())), 'reglas_v8': dict(sorted(Counter((r['regla_v8'] for r in out)).items())), 'N_cambios_propuestos': len(cambios), 'auditorias_IA_openalex_heredadas': 0, 'piloto_humano_openalex_heredado': 0, 'v7_casos_auditados_manualmente': 0, 'v8_validacion_independiente_completada': False, 'texto_completo_leido': 0, 'llamadas_API': 0, 'fecha_utc': datetime.now(timezone.utc).isoformat(), 'nota': 'Etiquetas automáticas. Fase 1 aún pendiente de validación documental. No sustituye revisión humana.', 'metodo': 'Mismos patrones y orden de reglas v7/v8; sin heredar auditorías de IA ni juicios humanos de OpenAlex.', 'SHA256_entrada_fase02': huella(datos), 'SHA256_salidas': {p.name: huella(p.read_bytes()) for p in outputs}}
resumen = CARPETA_SALIDA / 'resumen_scopus_v8.json'
resumen.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('\nRESUMEN:', json.dumps({k: summary[k] for k in ('N_base_amplia_sin_alterar', 'conteos_v7', 'conteos_propuesta_v8', 'N_cambios_propuestos')}, ensure_ascii=False, indent=2))
print('Resultados guardados en:', CARPETA_SALIDA)
if not sum(conteos.values()) == len(registros):
    raise ValueError('Control de integridad incumplido')
if not all((r['auto_screen_status'] == 'include' for r in out)):
    raise ValueError('Control de integridad incumplido')
if not all((r['fuera_nucleo_no_excluye_base_amplia_v8'] == 'si' for r in out)):
    raise ValueError('Control de integridad incumplido')
if not not any((r['caso_desarrollo_v8'] for r in out)):
    raise ValueError('Control de integridad incumplido')
for p in outputs:
    if not (p.exists() and huella(p.read_bytes()) == summary['SHA256_salidas'][p.name]):
        raise ValueError(p.name)
print('Verificaciones de integridad y ausencia de decisiones heredadas: correctas.')
print('Reglas principales:', Counter((r['regla_v8'] for r in out)).most_common(12))
print('Muestra para evaluación humana:', len(ciega))
