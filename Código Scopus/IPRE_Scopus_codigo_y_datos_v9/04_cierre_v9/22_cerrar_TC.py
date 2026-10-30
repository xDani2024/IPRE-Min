from pathlib import Path
import argparse
ROOT = next((p for p in Path(__file__).resolve().parents if (p / 'PROCEDENCIA_DEL_PAQUETE.json').is_file()))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--entrada', type=Path, default=ROOT / '04_cierre_v9/entrada')
parser.add_argument('--salida', type=Path, default=ROOT / '04_cierre_v9/salida')
args = parser.parse_args()
if args.salida.exists() and any(args.salida.iterdir()):
    parser.error('La salida contiene archivos. Elija una carpeta nueva con --salida.')
args.salida.mkdir(parents=True, exist_ok=True)
from pathlib import Path
import csv, json, hashlib, random, datetime, collections
BASE = ROOT
SALIDA = args.salida
ORIGEN = args.entrada
MATRIZ = ORIGEN / 'matriz_completa_scopus_v8.csv'
RESUMEN_PREVIO = ORIGEN / 'resumen_scopus_v8.json'
if not RESUMEN_PREVIO.is_file():
    raise FileNotFoundError(f'Falta el resumen de procedencia: {RESUMEN_PREVIO}')

def calcular_sha256(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()
MANIFEST_V8 = json.loads(RESUMEN_PREVIO.read_text(encoding='utf-8'))
SHA_MATRIZ = calcular_sha256(MATRIZ)
ESPERADO = (MANIFEST_V8.get('SHA256_salidas') or {}).get('matriz_completa_scopus_v8.csv')
if not ESPERADO:
    raise ValueError('El manifiesto de Fase 3 no declara el SHA de su matriz v8.')
if not SHA_MATRIZ == ESPERADO:
    raise ValueError('Matriz modificada o no coincide con el manifiesto v8. Detener ejecución.')
print('Directorio:', BASE)
print('Entrada validada:', MATRIZ)
print('SHA-256:', SHA_MATRIZ)
print('Salida:', SALIDA)
with MATRIZ.open('r', encoding='utf-8-sig', newline='') as f:
    lector = csv.DictReader(f)
    CAMPOS_V8 = list(lector.fieldnames or [])
    FILAS_V8 = list(lector)
if not {'scopus_id', 'title', 'abstract', 'decision_nucleo_v8_propuesta', 'regla_v8', 'motivo_v8', 'contexto_A_v8'} <= set(CAMPOS_V8):
    raise ValueError('Control de integridad incumplido')
IDS = [r['scopus_id'] for r in FILAS_V8]
if not (all(IDS) and len(IDS) == len(set(IDS))):
    raise ValueError('Identificadores Scopus vacíos o duplicados.')
ESTADOS_V8 = collections.Counter((r['decision_nucleo_v8_propuesta'] for r in FILAS_V8))
if not set(ESTADOS_V8) <= {'IN', 'OUT', 'TC'}:
    raise ValueError('Control de integridad incumplido')
if not len(FILAS_V8) == int(MANIFEST_V8['N_base_amplia_sin_alterar']):
    raise ValueError('Control de integridad incumplido')
if not ESTADOS_V8 == MANIFEST_V8['conteos_propuesta_v8']:
    raise ValueError('Control de integridad incumplido')
TC_V8 = [r for r in FILAS_V8 if r['decision_nucleo_v8_propuesta'] == 'TC']
print('Publicaciones:', len(FILAS_V8))
print('Distribución v8:', dict(ESTADOS_V8))
print('Pendientes TC:', len(TC_V8))
import re, unicodedata
from collections import Counter

def rx(pattern):
    return re.compile(pattern, re.I)

def norm(text):
    s = unicodedata.normalize('NFKD', text or '')
    s = ''.join((c for c in s if not unicodedata.combining(c)))
    s = re.sub('[‐‑–—−]', '-', s)
    return re.sub('\\s+', ' ', s).strip()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def write(path, rows, fields=None):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)
SURFACE = rx('open[ -]?(?:pit|cast|cut)|surface[ -]min(?:e|ing)|surface coal|quarr(?:y|ies)|strip min|cielo abierto|tajo abierto|cantera|tambang terbuka|карьер|разрез')
TASK = rx('haul|truck|shovel|excavat|dragline|load(?:ing|er)|fleet|dispatch|conveyor|bucket[ -]?wheel|surface miner|overburden|stripping|drill|blast|crusher|mine road|haul road|pit road|dewater|drainage|pump|sump|water(?:ing)? truck|watering|dust (?:suppress|control)|road maintenance|refuel|material handling|material transport|camion|carguio|acarreo|perforaci|motoniveladora|pala minera|regadio|bombeo|desague|pengupasan|alat (?:gali|muat|angkut)|angkut|pemuatan|konveyor|экскаватор|самосвал|бурени|конвейер')
METRICS = {'productividad': rx('productiv|produktivitas|throughput|production (?:rate|capacity|output|efficien|increase|gain|loss)|tons? per|tonnes? per|(?:ton|tons|tonnes|m3)\\s*/\\s*h|t/h\\b|produccion por|rendimiento operacional|производительност'), 'tiempos_esperas': rx('cycl(?:e|ing) time|cycle duration|loading time|travel time|hauling time|haulage time|transport time|waiting time|queuing time|queueing time|idle time|turnaround time|downtime|repair time|waktu edar|tiempo de ciclo|tiempos? de espera|врем[яени].{0,25}цикл'), 'disponibilidad_utilizacion': rx('availability|uptime|equipment effectiveness|(?:equipment|fleet|truck|shovel|excavator|conveyor|vehicle|machine) utili[sz]ation|utili[sz]ation (?:of|rate)|match factor|kesiapan|disponibilidad|utilizacion|коэффициент.{0,25}использован'), 'confiabilidad_equipo': rx('(?:(?:truck|shovel|excavator|dragline|conveyor|drill|pump|equipment|fleet|machine).{0,20}reliability|reliability.{0,30}(?:truck|shovel|excavator|dragline|conveyor|drill|pump|equipment|fleet))|failure rate|mean time (?:to|between)|mtbf|mttr'), 'combustible_energia': rx('fuel (?:use|consumption|saving|efficien)|diesel consumption|energy (?:use|consumption|saving|efficien)|specific energy consumption|electricity consumption|consumo de (?:combustible|energia)|bahan bakar|расход.{0,15}топлив'), 'costo_tarea': rx('operat(?:ing|ional) costs?|haul(?:age|ing) costs?|transport(?:ation)? costs?|truck.{0,15}costs?|costs?.{0,15}(?:haulage|drilling|watering|blasting|loading|transportation)|drill(?:ing)? costs?|blast(?:ing)? costs?|watering costs?|cost per (?:ton|tonne|m3|unit)|unit costs?|biaya operasional|costo.{0,15}(?:acarreo|riego|perforacion|operacional)|costs? of (?:drilling|blasting|watering|haulage)'), 'distancia_frecuencia': rx('(?:travel|haulage|hauling|route|routing) distance|distance traveled|route length|travel length|(?:watering|spray|application|maintenance) frequency|frequency of (?:watering|application|maintenance)|application rate|frecuencia de riego|distancia recorrida'), 'carga_transportada': rx('payload|material transported per hour|ore attainment|tons? hauled|tonnes? hauled'), 'caudal_bombeo': rx('pumping discharge|pumping rate|pump capacity|caudal de bombeo|debit pompa')}
RESULT = rx('results?.{0,45}(?:show|indicat|reveal|demonstrat|obtain)|findings?.{0,35}(?:show|indicat|reveal)|show(?:ed|n|s)? that|was (?:found|measured|reduced|increased|improved|estimated|calculated)|were (?:found|measured|reduced|increased|improved|estimated|calculated)|has been (?:measured|calculated|evaluated)|achiev|reduc(?:ed|tion) (?:by|of|in)|increas(?:ed|es) by|improvement (?:of|in)|measured|calculated|computed|observed|found to|compar(?:ed|ison)|evaluat(?:ed|ion)|assess(?:ed|ment)|field (?:data|test|trial|experiment)|experimental|simulation (?:results|shows)|data.{0,30}show|hasil.{0,40}(?:penelitian|menunjuk|diperoleh)|diperoleh|berdasarkan hasil|resultados.{0,40}(?:muestra|indica)|se obtuvo|se midio|se evaluo|получен|результат')
RESULT = rx(RESULT.pattern + '|\\b(?:reduced|increased|decreased|improved)\\b')
NUMERIC = rx('\\d+(?:[.,]\\d+)?\\s*(?:%|percent|ton|tons|tonnes|t/h|m3|minutes|hours|seconds|liters|litres|gallons|mj|kw|kg|menit|jam|rp\\b|usd|dollar)')
ASPIRATION = rx('\\baims? to\\b|\\bobjective is\\b|\\bgoal is\\b|\\bin order to\\b|\\bwith the aim\\b|\\bcan (?:improve|reduce|increase)\\b|\\bcould\\b|\\bwould\\b|\\bmight\\b|\\bpotential to\\b|\\bexpected to\\b|\\bwill be (?:tested|evaluated|validated)\\b')
PREDICTOR = rx('predict|forecast|machine learning|neural network|case.based reasoning')
MODEL_METRIC = rx('accuracy|precision|recall|f.?score|rmse|mae\\b|mape\\b|r.?squared|prediction error|forecast(?:ing)? error|convergence|computational (?:time|efficiency)|running time|algorithm.{0,15}performance')
DIRECT_CHANGE = rx('reduc(?:ed|tion) (?:by|of|in)|increas(?:ed|es) by|improvement (?:of|in)|measured|observed|field (?:data|test|trial|experiment)|actual (?:fuel|cycle|production)|collected.{0,35}(?:fuel|cycle|production)')
REVIEW = rx('\\bsystematic (?:literature )?review\\b|\\bscoping review\\b|\\bliterature review\\b|\\bmeta.analysis\\b|\\breview (?:of|on)\\b|\\ba review\\b|bibliometric|scientometric')
COMPONENT = rx('gearbox|bearing|tire|tyre|bucket teeth|drill bit|weld|microstructur|hydraulic cylinder|drive wheel|finite element|stress analysis|rock cutting force|excavat(?:ion|ing) resistance')
UNDERGROUND = rx('underground|mineria subterranea|sous.terrain|подземн')
WHOLE = rx('truck|shovel|excavator|dragline|fleet|conveyor|equipment|machine|drilling rig|surface miner|camion|pala minera|perforadora')
STRATEGIC = rx('ultimate pit|pit limit|final pit|open.pit min(?:e|ing) problem|production scheduling|long.term|strategic|block sequenc|block schedul|net present value|\\bnpv\\b|ore blending|mine design')
ALTERNATIVE = {'geotecnia_cartografia': rx('slope stability|landslide|rock mass|highwall|subsidence|shear strength|geomechanic|photogrammetr|laser scanning|point cloud|land cover|geological model|geo.position|digital surface model|topographic'), 'ambiente_seguridad': rx('air quality|water quality|acid mine|ecosystem|revegetat|land reclamation|dust concentration|dust exposure|occupational|health|ground vibration|flyrock|peak particle velocity|runoff|erosion|soil|contamination|fatigue detection|collision detection'), 'fragmentacion_componente': rx('fragmentation|fragment size|muckpile|microstructur|wear resistance|tensile strength|fatigue strength|hardness'), 'desarrollo_algoritmico': MODEL_METRIC, 'planificacion_valor_proyecto': STRATEGIC}

def sentences(text):
    return [s.strip() for s in re.split('(?<=[.!?;])\\s+|\\n+', text) if s.strip()]

def metric_names(text):
    return [k for k, p in METRICS.items() if p.search(norm(text))]

def clip(text, limit=1500):
    return text if len(text) <= limit else text[:limit] + ' [fragmento truncado]'

def classify(row):
    title = norm(row['title'])
    abstract = row['abstract']
    sents = sentences(abstract)
    nt = norm(title + ' ' + abstract)
    rule = row['regla_v8']
    context = bool(SURFACE.search(nt)) or row['contexto_A_v8'] == 'acreditado_en_ficha'
    if rule == 'T01_METADATA_INVALIDA':
        return ('OUT', 'D01_FUENTE_NO_FIABLE', 'exclusion_documental', 'La alerta identifica un resumen cruzado/editorial. Con la fuente congelada no se justifica la inclusión; se excluye del núcleo de esta versión por fuente no fiable.', row['title'], '', 'no')
    if UNDERGROUND.search(title) and (not SURFACE.search(title)):
        return ('OUT', 'O05_CONTEXTO_SUBTERRANEO', 'exclusion_por_foco', 'El estudio se identifica como subterráneo en el título. Una mención de minería superficial en antecedentes no acredita una evaluación propia en ese contexto.', row['title'], '', 'no')
    if not context:
        return ('OUT', 'D02_CONTEXTO_NO_ACREDITADO', 'exclusion_documental', 'La ficha disponible no acredita el contexto a cielo abierto exigido para el núcleo. Se excluye por evidencia contextual insuficiente.', row['title'], '', 'no')
    if REVIEW.search(title) or rule == 'T02_DOCUMENTO_HIBRIDO':
        return ('OUT', 'O01_SINTESIS_SECUNDARIA', 'exclusion_por_foco', 'El documento se identifica como revisión/síntesis. Los resultados de estudios revisados no se cuentan como evaluación primaria propia en este núcleo.', row['title'], '', 'no')
    linked = []
    for i, s in enumerate(sents):
        ns = norm(s)
        metrics = metric_names(s)
        if not metrics:
            continue
        prev = ' '.join(sents[max(0, i - 2):i])
        window = norm(prev + ' ' + s)
        relation = bool(TASK.search(ns)) or (bool(TASK.search(title)) and bool(TASK.search(window)))
        if not relation:
            continue
        positive = bool(RESULT.search(ns)) or (bool(NUMERIC.search(ns)) and bool(rx('\\b(?:was|were|is|are|has|have|diperoleh|se obtuvo)\\b').search(ns)))
        if not positive and i and RESULT.search(norm(sents[i - 1])) and rx('\\b(?:this|these|the results|it|its|they|respectively)\\b').search(ns):
            positive = True
        if not positive:
            continue
        if ASPIRATION.search(ns) and (not DIRECT_CHANGE.search(ns)):
            continue
        if MODEL_METRIC.search(ns) and (not DIRECT_CHANGE.search(ns)):
            continue
        if PREDICTOR.search(title) and MODEL_METRIC.search(nt) and (not DIRECT_CHANGE.search(ns)):
            continue
        if rule == 'T04_COMPONENTE_SIN_VINCULO_OPERACIONAL' or COMPONENT.search(title):
            if not (WHOLE.search(ns) and any((k in metrics for k in ['productividad', 'tiempos_esperas', 'disponibilidad_utilizacion', 'combustible_energia', 'costo_tarea']))):
                continue
        linked.append((s, metrics, prev))
    if linked:
        s, metrics, prev = max(linked, key=lambda x: (bool(NUMERIC.search(norm(x[0]))), len(x[1]), len(x[0])))
        evidence = clip((prev + ' ' + s).strip())
        method = 'simulacion_modelo' if rx('simulat|mathematical model|optimization model|mixed.integer').search(nt) else 'tipo_no_confirmado'
        why = 'La ficha vincula una tarea/equipo minero con evaluación y resultado operacional (' + ', '.join(metrics) + '). Propuesta basada en título y resumen; no equivale a validación humana ni verificación externa del resultado.'
        return ('IN', 'I01_EVIDENCIA_OPERACIONAL_EN_FICHA', 'inclusion_con_evidencia', why, evidence, ';'.join(metrics), method)
    if rule == 'T04_COMPONENTE_SIN_VINCULO_OPERACIONAL':
        evidence = next((s for s in sents if COMPONENT.search(norm(s))), row['title'])
        return ('OUT', 'O02_COMPONENTE_SIN_RESULTADO_DE_TAREA', 'exclusion_por_foco', 'El foco identificado es un componente, material o respuesta mecánica y no se acredita un resultado operacional atribuible al equipo/tarea. Se mantiene fuera de este núcleo.', clip(evidence), '', 'no')
    for name, pattern in ALTERNATIVE.items():
        endpoint = next((s for s in reversed(sents) if pattern.search(norm(s)) and (RESULT.search(norm(s)) or MODEL_METRIC.search(norm(s)))), None)
        if pattern.search(title) or endpoint:
            evidence = endpoint or row['title']
            return ('OUT', 'O03_' + name.upper(), 'exclusion_por_foco', 'Se identifica un foco de ' + name.replace('_', ' ') + ' y no se acredita resultado propio de tarea/equipo operacional en la ficha disponible. Permanece en la base amplia.', clip(evidence), '', 'no')
    return ('OUT', 'D03_EVIDENCIA_OPERACIONAL_INSUFICIENTE', 'exclusion_documental', 'La ficha disponible no permite justificar conjuntamente contexto/tarea, evaluación y resultado operacional. Se excluye del núcleo de esta versión por evidencia insuficiente; no se afirma irrelevancia definitiva.', clip(' '.join(sents[-2:]) or row['title']), '', 'no')
PROPUESTAS_TC = {}
for i, r in enumerate(TC_V8, 1):
    d, reg, disp, mot, evid, inds, tipo = classify(r)
    if not (d in ('IN', 'OUT') and reg and mot and evid):
        raise ValueError('Control de integridad incumplido')
    PROPUESTAS_TC[r['scopus_id']] = (d, reg, disp, mot, evid, inds, tipo)
    if i % 500 == 0 or i == len(TC_V8):
        print(f'  Evaluadas {i:,} / {len(TC_V8):,} fichas TC')
CUENTA_TC = collections.Counter((p[0] for p in PROPUESTAS_TC.values()))
REGLAS_TC = collections.Counter((p[1] for p in PROPUESTAS_TC.values()))
DISPOSICIONES_TC = collections.Counter((p[2] for p in PROPUESTAS_TC.values()))
print('Pre-cierre de TC:', dict(CUENTA_TC))
print('Disposición documental:', dict(DISPOSICIONES_TC))
VERSION_LOCAL = 'Scopus_v9_pre_cierre_computacional_2026_10_19'
FILAS_V9 = []
for row in FILAS_V8:
    anterior = row['decision_nucleo_v8_propuesta']
    x = {'decision_nucleo_v9_propuesta': anterior, 'decision_nucleo_v9_computacional': anterior, 'origen_v9': 'v8_automatica_conservada', 'regla_cierre_v9': 'NO_REEVALUADO_EN_ESTA_ETAPA', 'disposicion_documental_v9': 'v8_conservada_sin_validacion', 'motivo_cierre_v9': row.get('motivo_v8', ''), 'evidencia_cierre_v9': row.get('evidencia_textual_v8', ''), 'indicadores_cierre_v9': '', 'tipo_evidencia_cierre_v9': 'v8_conservada', 'fuente_texto_v9': 'titulo_resumen_fase03_congelado', 'lectura_semantica_directa_IA_v9': 'no', 'texto_completo_consultado_v9': 'no', 'decision_humana_conservada_v9': '', 'precedencia_decision_humana_v9': 'no_hay_juicios_scopus', 'validacion_academica_v9': 'pendiente', 'advertencia_v9': 'pre_cierre_solo_reglas; no_inferir_pertinencia_definitiva', 'version_cierre_v9': VERSION_LOCAL}
    if anterior == 'TC':
        d, reg, disp, mot, evid, inds, tipo = PROPUESTAS_TC[row['scopus_id']]
        x.update({'decision_nucleo_v9_propuesta': d, 'decision_nucleo_v9_computacional': d, 'origen_v9': 'cierre_documental_computacional_sin_auditoria', 'regla_cierre_v9': reg, 'disposicion_documental_v9': disp, 'motivo_cierre_v9': mot, 'evidencia_cierre_v9': evid, 'indicadores_cierre_v9': inds, 'tipo_evidencia_cierre_v9': tipo, 'advertencia_v9': 'IN_pendiente_auditoria_semantica' if d == 'IN' else 'OUT_documental_no_demuestra_irrelevancia' if disp == 'exclusion_documental' else 'OUT_foco_pendiente_revision_muestral'})
    FILAS_V9.append({**row, **x})
if not len(FILAS_V9) == len(FILAS_V8):
    raise ValueError('Control de integridad incumplido')
if not all(({c: r[c] for c in CAMPOS_V8} == orig for orig, r in zip(FILAS_V8, FILAS_V9))):
    raise ValueError('Control de integridad incumplido')
if not all((r['decision_nucleo_v9_propuesta'] in ('IN', 'OUT') for r in FILAS_V9)):
    raise ValueError('Control de integridad incumplido')
CUENTA_V9 = collections.Counter((r['decision_nucleo_v9_propuesta'] for r in FILAS_V9))
print('Corpus Scopus v8:', dict(ESTADOS_V8))
print('Pre-cierre Scopus v9:', dict(CUENTA_V9))
print('Sin validación humana:', all((r['validacion_academica_v9'] == 'pendiente' for r in FILAS_V9)))
CAMPOS_V9 = list(FILAS_V9[0].keys())

def exportar_csv(nombre, filas, campos=None):
    ruta = SALIDA / nombre
    with ruta.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=campos or list(filas[0]), extrasaction='ignore')
        w.writeheader()
        w.writerows(filas)
    return ruta
RUTAS_GENERADAS = []
RUTAS_GENERADAS.append(exportar_csv('Matriz_Scopus_4614_con_pre_cierre_v9.csv', FILAS_V9, CAMPOS_V9))
IN = [r for r in FILAS_V9 if r['decision_nucleo_v9_propuesta'] == 'IN']
OUT = [r for r in FILAS_V9 if r['decision_nucleo_v9_propuesta'] == 'OUT']
TC_CERRADOS = [r for r in FILAS_V9 if r['decision_nucleo_v8_propuesta'] == 'TC']
RUTAS_GENERADAS.append(exportar_csv('IN_computacional_v9_PENDIENTE_REVISION.csv', IN, CAMPOS_V9))
RUTAS_GENERADAS.append(exportar_csv('OUT_computacional_v9_PENDIENTE_REVISION.csv', OUT, CAMPOS_V9))
RUTAS_GENERADAS.append(exportar_csv('Decisiones_TC_Scopus_v9.csv', TC_CERRADOS, CAMPOS_V9))
RUTAS_GENERADAS.append(exportar_csv('Resumen_por_ID_TC_scopus_v9.csv', [{k: r.get(k, '') for k in ['scopus_id', 'title', 'decision_nucleo_v8_propuesta', 'decision_nucleo_v9_propuesta', 'regla_cierre_v9', 'disposicion_documental_v9', 'motivo_cierre_v9', 'evidencia_cierre_v9']} for r in TC_CERRADOS]))
NUEVOS_IN_DESDE_TC = [r for r in TC_CERRADOS if r['decision_nucleo_v9_propuesta'] == 'IN']
RUTAS_GENERADAS.append(exportar_csv('Nuevos_IN_desde_TC_PENDIENTE_REVISION.csv', NUEVOS_IN_DESDE_TC, CAMPOS_V9))
GRUPOS = {}
for row in OUT:
    key = row['regla_cierre_v9']
    GRUPOS.setdefault(key, []).append(row)
TOTAL_MUESTRA_OUT = min(120, len(OUT))
RNG = random.Random(20261019)
for filas in GRUPOS.values():
    RNG.shuffle(filas)
CUPOS = {k: 1 for k in GRUPOS}
if not len(CUPOS) <= TOTAL_MUESTRA_OUT:
    raise ValueError('Control de integridad incumplido')
while sum(CUPOS.values()) < TOTAL_MUESTRA_OUT:
    elegibles = [k for k in GRUPOS if CUPOS[k] < len(GRUPOS[k])]
    k = max(elegibles, key=lambda k: (TOTAL_MUESTRA_OUT * len(GRUPOS[k]) / len(OUT) - CUPOS[k], k))
    CUPOS[k] += 1
MUESTRA_OUT = [r for k in sorted(GRUPOS) for r in GRUPOS[k][:CUPOS[k]]]
RNG.shuffle(MUESTRA_OUT)
FORMULARIO_CAMPOS = ['codigo_revision', 'scopus_id', 'doi', 'title', 'abstract', 'year', 'estado_v8', 'propuesta_computacional_v9', 'regla_v9', 'disposicion_documental_v9', 'motivo_automatico', 'evidencia_automatica', 'estrato_revision', 'decision_revisor_1_IN_OUT_DUDA', 'motivo_revisor_1', 'decision_revisor_2_IN_OUT_DUDA', 'motivo_revisor_2', 'consenso_IN_OUT_DUDA', 'motivo_consenso', 'texto_completo_consultado_si_no', 'fecha_revision']

def fila_revision(row, codigo, estrato):
    return {'codigo_revision': codigo, 'scopus_id': row['scopus_id'], 'doi': row.get('doi', ''), 'title': row['title'], 'abstract': row['abstract'], 'year': row.get('year', ''), 'estado_v8': row['decision_nucleo_v8_propuesta'], 'propuesta_computacional_v9': row['decision_nucleo_v9_propuesta'], 'regla_v9': row['regla_cierre_v9'], 'disposicion_documental_v9': row['disposicion_documental_v9'], 'motivo_automatico': row['motivo_cierre_v9'], 'evidencia_automatica': row['evidencia_cierre_v9'], 'estrato_revision': estrato, 'decision_revisor_1_IN_OUT_DUDA': '', 'motivo_revisor_1': '', 'decision_revisor_2_IN_OUT_DUDA': '', 'motivo_revisor_2': '', 'consenso_IN_OUT_DUDA': '', 'motivo_consenso': '', 'texto_completo_consultado_si_no': '', 'fecha_revision': ''}
REV_IN = [fila_revision(r, f'IN-{i:04d}', 'IN_computacional') for i, r in enumerate(IN, 1)]
REV_OUT = [fila_revision(r, f'OUT-{i:04d}', 'OUT_estratificado') for i, r in enumerate(MUESTRA_OUT, 1)]
RUTAS_GENERADAS.append(exportar_csv('Revisar_TODOS_los_IN_v9.csv', REV_IN, FORMULARIO_CAMPOS))
RUTAS_GENERADAS.append(exportar_csv('Muestra_120_OUT_v9.csv', REV_OUT, FORMULARIO_CAMPOS))
mezcla=IN+MUESTRA_OUT
random.Random(20261020).shuffle(mezcla)
ciega=[];clave=[]
for numero,row in enumerate(mezcla,1):
    codigo=f'R-{numero:04d}'
    ciega.append({'codigo':codigo,**{k:row.get(k,'') for k in ['title','abstract','doi','year']},'decision_revisor_1':'','motivo_revisor_1':'','decision_revisor_2':'','motivo_revisor_2':'','consenso':'','motivo_consenso':''})
    es_in=row['decision_nucleo_v9_propuesta']=='IN'
    grupo=row['regla_cierre_v9']
    N=len(IN) if es_in else len(GRUPOS[grupo]);n=len(IN) if es_in else CUPOS[grupo]
    clave.append({'codigo':codigo,'scopus_id':row['scopus_id'],'propuesta_v9':row['decision_nucleo_v9_propuesta'],'estrato':'IN' if es_in else grupo,'N':N,'n':n,'probabilidad':n/N,'peso':N/n})
RUTAS_GENERADAS.append(exportar_csv('Revision_independiente_ciega_v9.csv',ciega))
RUTAS_GENERADAS.append(exportar_csv('Clave_revision_independiente_NO_ENTREGAR_A_REVISORES.csv',clave))
print('Propuestas IN para revisar:', len(REV_IN))
print('Muestra OUT:', len(REV_OUT), 'en', len(GRUPOS), 'reglas')
if not len(TC_CERRADOS) == ESTADOS_V8['TC']:
    raise ValueError('Control de integridad incumplido')
if not {r['scopus_id'] for r in TC_CERRADOS} == {r['scopus_id'] for r in TC_V8}:
    raise ValueError('Control de integridad incumplido')
if not len(IN) + len(OUT) == len(FILAS_V9):
    raise ValueError('Control de integridad incumplido')
if not len({r['scopus_id'] for r in FILAS_V9}) == len(FILAS_V9):
    raise ValueError('Control de integridad incumplido')
if not all((r['motivo_cierre_v9'] and r['evidencia_cierre_v9'] for r in TC_CERRADOS)):
    raise ValueError('Control de integridad incumplido')
if not all((r['lectura_semantica_directa_IA_v9'] == 'no' for r in FILAS_V9)):
    raise ValueError('Control de integridad incumplido')
if not all((r['decision_nucleo_v9_computacional'] == r['decision_nucleo_v9_propuesta'] for r in FILAS_V9)):
    raise ValueError('Control de integridad incumplido')
manifest = {'fuente': 'Scopus', 'version': VERSION_LOCAL, 'fecha_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'tipo_resultado': 'PRE_CIERRE_AUTOMATICO_NO_VALIDADO', 'protocolo_base': '22_cerrar_TC.py (Joaquín, v9)', 'base_amplia': len(FILAS_V9), 'conteos_v8': dict(ESTADOS_V8), 'TC_v8_evaluados': len(TC_CERRADOS), 'TC_resultado_computacional': dict(CUENTA_TC), 'v9_propuesta_computacional_total': dict(CUENTA_V9), 'reglas_TC': dict(REGLAS_TC), 'disposiciones_TC': dict(DISPOSICIONES_TC), 'todos_los_TC_con_propuesta_binaria': True, 'validacion_humana_independiente_realizada': False, 'auditorias_IA_directas_scopus_realizadas': 0, 'decisiones_humanas_openalex_heredadas': 0, 'decisiones_humanas_scopus_registradas': 0, 'revisiones_de_texto_completo': 0, 'IN_pendientes_revision': len(REV_IN), 'OUT_seleccionados_muestra': len(REV_OUT), 'filas_originales_v8_preservadas': True, 'sha256_entrada': SHA_MATRIZ, 'sha256_salidas': {p.name: calcular_sha256(p) for p in RUTAS_GENERADAS}, 'limites': ['Las auditorias directas IA de 118 registros OpenAlex no se transfieren a Scopus.', 'Los 40 juicios humanos de OpenAlex no se transfieren a Scopus.', 'OUT documental no demuestra irrelevancia del articulo completo.', 'Los IN no equivalen a un nucleo validado. Revisar inclusiones y exclusiones.', 'La Fase 1 continua con validacion documental pendiente de retractacion y paratexto.']}
(SALIDA / 'Resumen_y_manifest_v9_scopus.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('VERIFICADO: matriz v8 preservada; IDs y recuentos conciliados; no se inventaron auditorías.')
print(json.dumps({k: manifest[k] for k in ['base_amplia', 'TC_v8_evaluados', 'TC_resultado_computacional', 'v9_propuesta_computacional_total', 'IN_pendientes_revision', 'OUT_seleccionados_muestra', 'validacion_humana_independiente_realizada']}, ensure_ascii=False, indent=2))
print('Archivos creados en:', SALIDA)
