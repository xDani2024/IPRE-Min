from pathlib import Path
import argparse
ROOT = next((p for p in Path(__file__).resolve().parents if (p / 'PROCEDENCIA_DEL_PAQUETE.json').is_file()))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--entrada', type=Path, default=ROOT / '01_extraccion_y_filtro/salida')
parser.add_argument('--salida', type=Path, default=ROOT / '02_cribado_v6/codigo/salida')
args = parser.parse_args()
if args.salida.exists() and any(args.salida.iterdir()):
    parser.error('La salida contiene archivos. Elija una carpeta nueva con --salida.')
args.salida.mkdir(parents=True, exist_ok=True)
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv, hashlib, io, json, random, re, sys, unicodedata, zipfile
SEED = 20260928
TOTAL_ESPERADO_FASE01 = 4614
CARPETA_FASE01 = args.entrada
SALIDA = args.salida
SALIDA.mkdir(parents=True, exist_ok=True)
print('Directorio de trabajo:', Path.cwd().resolve())
print('Datos de Fase 01:', CARPETA_FASE01.resolve())
print('Salida Fase 02:', SALIDA.resolve())
print('No se utilizará Google Colab ni se volverán a descargar publicaciones.')
carpeta = Path(CARPETA_FASE01).expanduser().resolve()
manifest_path = carpeta / 'manifest_fase01.json'
aceptados_path = carpeta / 'corpus_general_aceptado_provisional.csv'
if not manifest_path.is_file() or not aceptados_path.is_file():
    raise FileNotFoundError(f'No encuentro los resultados completos de Fase 01. Ruta revisada: {carpeta}. Confirme que existen manifest_fase01.json y corpus_general_aceptado_provisional.csv. Si su carpeta se llama distinto, cambie CARPETA_FASE01 en el Paso 1.')
print('Carpeta de entrada:', carpeta)

def sha_bytes(contenido):
    return hashlib.sha256(contenido).hexdigest()

def leer_csv_bytes(contenido):
    return list(csv.DictReader(io.StringIO(contenido.decode('utf-8-sig'), newline='')))
raw_manifest = manifest_path.read_bytes()
raw_aceptados = aceptados_path.read_bytes()
manifest = json.loads(raw_manifest)
registros = leer_csv_bytes(raw_aceptados)
archivos_sha = manifest.get('archivo_sha256', {})
esperado = archivos_sha.get('corpus_general_aceptado_provisional.csv')
real = sha_bytes(raw_aceptados)
if not esperado or real != esperado:
    raise ValueError('No coincide SHA-256 del corpus de aceptados con el manifiesto de Fase 01.')
control_integridad = {}
for nombre, sha_esperado in archivos_sha.items():
    archivo = carpeta / nombre
    control_integridad[nombre] = archivo.is_file() and sha_bytes(archivo.read_bytes()) == sha_esperado
if not manifest.get('extraccion_completa') is True:
    raise ValueError('La extracción Fase 01 no consta como completa.')
if not manifest.get('filtro_automatico_ejecutado') is True:
    raise ValueError('No se ejecutó el filtro amplio de Fase 01.')
if not len(registros) == manifest['aceptados_amplios_provisionales']:
    raise ValueError('Inconsistencia entre corpus y manifiesto.')
if not len(registros) > 0:
    raise ValueError('El corpus aceptado está vacío.')
if not all((r.get('auto_screen_status') == 'include' for r in registros)):
    raise ValueError('Hay registros no aceptados en Fase 01.')
if not all((r.get('abstract', '').strip() for r in registros)):
    raise ValueError('Faltan resúmenes en el corpus de entrada.')
ids = [r.get('scopus_id', '').strip() for r in registros]
if not (all(ids) and len(set(ids)) == len(ids)):
    raise ValueError('Hay scopus_id vacíos o repetidos.')
if not (control_integridad and all(control_integridad.values())):
    raise ValueError('Hay archivos faltantes o SHA-256 diferentes respecto del manifiesto.')
print('Publicaciones Fase 01 aceptadas provisionalmente:', len(registros))
print('SHA-256 verificados:', sum(control_integridad.values()), '/', len(control_integridad))
print('Filtro Fase 01 validado académicamente:', manifest.get('filtro_validado_academicamente'))
print('Controles pendientes retractación/paratexto:', manifest.get('pendientes_retractacion_y_paratexto'))
print('Idioma sin informar:', sum((not r.get('language', '').strip() for r in registros)), '/', len(registros))
print('Alertas quality_flags:', sum((bool(r.get('quality_flags', '').strip()) for r in registros)))

def recompile(s):
    return re.compile(s, re.I)
CONTEXT = recompile('open[ -]?pit|open[ -]?cast|surface min(?:ing|e)|surface coal|surface operations?|strip min(?:e|ing)|quarr(?:y|ies)|mina a cielo abierto|tajo abierto|cantera|tambang terbuka|tambang terbuk|carri[eè]re|карьер|разрез')
PROCESSES = {'perforacion': recompile('\\bdrill(?:ing|er| rig| rigs)?\\b|blasthole|borehole|perforaci[oó]n|bor tambang|бурени'), 'tronadura': recompile('\\bblast(?:ing|ed| hole| holes)?\\b|fragmentation|explosive|tronadura|voladura|peledakan|взрыв'), 'carguio': recompile('\\bload(?:ing|er|ers)?\\b|shovel|excavat(?:or|ion)|dragline|bucket wheel|cargu[ií]o|pala minera|gali muat|экскаватор'), 'transporte': recompile('haul(?:ing|age)?|\\btrucks?\\b|\\btippers?\\b|fleet|conveyor|belt transport|rail haul|locomotive|acarreo|transport(?:ation|e)|angkut|самосвал|конвейер'), 'remocion_estéril': recompile('overburden|stripping|waste rock|spreader|surface miner|rock handling|est[eé]ril|destape|lapisan penutup'), 'caminos_mina': recompile('haul road|mine road|unpaved road|ramp construction|grader|road maintenance|road condition|jalan angkut|camino minero'), 'desague_apoyo': recompile('dewater|mine drainage|pit pump|pumping|sump|penyaliran|bomb(?:eo|as)|drenaje de mina'), 'riego_polvo': recompile('water truck|dust suppress|road watering|sprinkler|riego de caminos|penyiraman jalan'), 'botaderos_operacionales': recompile('rock dump|waste dump|dumping station|material placement|in.?pit dump|spoil spreader|botadero'), 'chancado_en_mina': recompile('in.?pit crush|ipcc|semi.?continuous haul|crusher.?conveyor|chancado en mina')}
EQUIPMENT = {'haul_truck': recompile('\\btrucks?\\b|\\btippers?\\b|camiones? mineros?|alat angkut|самосвал'), 'shovel': recompile('\\bshovels?\\b|electric shovels?|power shovels?|pala(?:s)? el[eé]ctric'), 'excavator': recompile('\\bexcavat(?:or|ors)\\b|excavadora|экскаватор'), 'loader': recompile('wheel loader|front.?end loader|\\bloaders?\\b|cargador frontal'), 'drill_rig': recompile('drill rigs?|blasthole drills?|rotary drill|perforadora|alat bor'), 'dragline': recompile('dragline|dragalina'), 'bucket_wheel_excavator': recompile('bucket wheel|rotary excavator|bwe|bager rotor'), 'surface_miner': recompile('surface miners?|layer milling machine|milling combine'), 'conveyor': recompile('conveyors?|belt transport|belt system|cinta transportadora|конвейер'), 'crusher_in_pit': recompile('in.?pit crush|ipcc|mobile crusher'), 'dozer': recompile('bulldoz|\\bdozer\\b|rip(?:per)? tip'), 'grader': recompile('grader|motoniveladora'), 'water_truck': recompile('water truck|sprinkler truck|cam[ií]on aljibe'), 'pump': recompile('\\bpumps?\\b|bomba|pompa|насос'), 'locomotive': recompile('locomotive|electrovoz|электровоз'), 'spreader': recompile('spreader|stacker|apilador')}
DECISIONS = {'despacho_asignacion': recompile('dispatch|allocat|assign|match(?:es|ing)? of hauling fleet|match factor|fleet management|despacho|asignaci[oó]n|penugasan'), 'planificacion_corta': recompile('short.?term|shift schedul|daily schedul|real.?time schedul|operational planning|planificaci[oó]n operacional|planning of excavation'), 'optimiza_configura': recompile('optimi[sz]|simulat|select(?:ion)? (?:procedure|method|of (?:equipment|fleet|truck|dragline))|configur|dimension|model(?:ing|ling) of (?:fleet|truck|shovel)|rational allocat|speed planning|traffic flow programming|optimiza|konfigurasi'), 'control_ejecucion': recompile('operat(?:ion|ing|ional) (?:control|strategy|decision|process)|perform(?:ance)? evaluat|performance analys|productivity analys|time study|cycle analys|measur(?:e|ing) of (?:output|performance)|monitoring of (?:fleet|truck|shovel|equipment)'), 'mantencion': recompile('maintenan|reliabilit|repair|fault diagnos|failure predict|time.?to.?failure|replacement time|predictive maintenan|mantenim|pemeliharaan'), 'informacion': recompile('fleet monitoring|equipment monitoring|production management system|digital twin|telemetr|sensor|computer vision|object detection|uav|remote sensing|tracking')}
PERFORMANCE = {'productividad_produccion': recompile('productivity|productive (?:time|hours)|production (?:rate|output|target|capacity|increase|loss)|(?:equipment|miner|dragline|mine) output|output of (?:the )?(?:surface miner|truck|shovel|excavator)|throughput|tonnage|rock.handling capacity|producci[oó]n|target produksi|produktivitas|производительност'), 'disponibilidad_confiabilidad': recompile('availability|(?:truck|shovel|excavator|conveyor|pump|equipment|fleet|drill rig|dragline) reliabilit|reliabilit(?:y|ies) of (?:the )?(?:truck|shovel|excavator|conveyor|pump|equipment|fleet|drill rig|dragline)|unplanned downtime|(?:equipment|machine|truck|conveyor) breakdown|equipment failure|disponibilidad|fiabilidad|keandalan'), 'utilizacion': recompile('(?:equipment|truck|shovel|excavator|drill|fleet|conveyor|dragline|pump) utili[sz]ation|utili[sz]ation (?:rate|of (?:the )?(?:equipment|truck|shovel|excavator|drill|fleet|conveyor|dragline|pump))|operating hours|productive time|operational time|time loss|utilizaci[oó]n|jam kerja'), 'tiempos_esperas': recompile('cycl(?:e|ing) time|waiting time|queue(?:ing)?|travel time|loading time|idle time|downtime|demora|tiempo de ciclo|waktu edar'), 'costo_operacional': recompile('operat(?:ing|ional) costs?|unit costs?|haulage costs?|cost per ton|truck costs?|vehicle operating costs?|costo operacional|biaya operasional'), 'energia_combustible': recompile('fuel (?:consumption|use|saving|efficiency)|energy (?:consumption|use|efficiency|losses)|diesel consumption|combustible|consumo energ[eé]tico'), 'eficiencia_tarea': recompile('(?:truck|shovel|excavator|bucket.wheel excavator|drill(?:ing)?|haulage|loading|transport|fleet|equipment|surface miner|dragline|conveyor|pump)\\s+(?:operation(?:al)?\\s+)?(?:efficien\\w*|performance)|(?:efficien\\w*|performance) of (?:the |a |an )?(?:truck|shovel|excavator|bucket.wheel excavator|drill|haulage|loading|transport|fleet|equipment|surface miner|dragline|conveyor|pump)|rendimiento (?:equipo|operacional)')}
NEGATIVE = {'geologia_exploracion': recompile('geolog|geophys|orebody|resource estimat|ore reserve|mineral explor|geochem|litholog|geostatis|mineralog'), 'geotecnia_talud': recompile('slope stabili|slope displacement|landslide|rockfall|geotech|pit wall|shear strength|factor of safety|bench slope|deformation monitoring|stability analysis of dump|dump stability|stability of (?:a |the )?dump'), 'ambiente_cierre': recompile('water quality|acid mine drainage|abandoned.mine drainage|mine drainage treatment|revegetat|rehabilitat|mine closure|pit lake|biodivers|soil fertili|soil contamin|methane emission|air pollut|environmental victim|ecotouris|dust emission|blast vibration|ground vibration|overpressure|environmental sustainability index|landscape fragmentation'), 'metalurgia_procesamiento': recompile('flotation|leach(?:ing)?|smelt|froth treatment|bitumen separation|beneficiat|ore processing|mineral processing'), 'estrategia_vida_mina': recompile('ultimate pit|pit limit|life.of.mine|long.?term (?:mine|waste|truck|production) (?:plan|schedul|management)|block model size|block size for an open.pit|strategic mine plan|net present value|npv|pushback|economic stripping ratio'), 'componente_aislado': recompile('finite element of (?:bucket|tooth|chassis|frame)|material propert|wear (?:prediction|behavio|rate)|structure analysis of a (?:dragline|shovel) tooth|stress analysis of (?:mast|connection|joint|frame)|structural (?:stress|integrity) of (?:a |the )?(?:shovel|excavator|truck)|protection means for high.voltage|microstructur|weld overlay|stress.strain of (?:tooth|chassis|steel)'), 'seguridad_sin_desempeno': recompile('hazard awareness|safety monitoring|personnel detection|collision avoidance|occupational health|whole.body vibration|accident risk'), 'efecto_voladura_no_operacional': recompile('flyrock|blast.induced vibration|ground vibration|particle vibration|blast seismic effects?|air over.pressure|nitrogen oxides|\\bnox\\b|rock fragmentation|fragmentation of rock|blasting outcomes|blastability'), 'exposicion_ambiental': recompile('\\bdust\\b|emission levels?|\\bpm10\\b|water balance|water quality|soil erosion'), 'geologia_instrumental': recompile('rock fracture density characteri[sz]ation|rock mass characteri[sz]ation|rock mass propert(?:y|ies) prediction|predicting rock hardness|rockmass classification|predicting cuttability'), 'insumos_fuera_de_mina': recompile('explosive production line|emulsion explosive production|manufactur(?:ing|e) of explosives'), 'deteccion_sin_resultado_tarea': recompile('object detection|road extraction from remote sensing|road mapping network|obstacle detection'), 'documento_no_investigacion': recompile('\\bbook review\\b|\\badvertisement\\b|\\breviewed by\\b')}
SENTENCE_SPLIT = re.compile('(?<=[.!?;])\\s+|\\n+')
UNDERGROUND_TITLE = recompile('underground|subterr[aá]ne|longwall|room.and.pillar|continuous miner|raisebor(?:e|ing)|extraction level')
NONMINING_TITLE = recompile('urban development|urban construction|pipeline laying|building demolition|demolition of (?:a |the )?(?:plant|building|structure)')

def normalized(s):
    """NFKC, Unicode dashes and typographic spaces to ASCII for matching."""
    s = unicodedata.normalize('NFKC', s or '')
    return ''.join(('-' if unicodedata.category(ch) == 'Pd' or ch == '−' else ' ' if ch.isspace() else ch for ch in s))

def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def write(path, rows, fields):
    path.parent.mkdir(exist_ok=True, parents=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def hits(patterns, text):
    return [name for name, p in patterns.items() if p.search(text)]

def snippet(units, condition):
    for s in units:
        if condition(s):
            return s.strip()[:400]
    return ''

def decide(r):
    t = normalized(r.get('title', '').strip())
    a = normalized(r.get('abstract', '').strip())
    head = a[:800]
    abs_units = [x for x in SENTENCE_SPLIT.split(a) if x.strip()]
    units = [t] + abs_units
    main = t + '. ' + a
    proc = hits(PROCESSES, main)
    equip = hits(EQUIPMENT, main)
    perf = hits(PERFORMANCE, main)
    decision = hits(DECISIONS, main)
    pt = hits(PROCESSES, t)
    et = hits(EQUIPMENT, t)
    dt = hits(DECISIONS, t)
    mt = hits(PERFORMANCE, t)
    negative = hits(NEGATIVE, t)
    negative_abs = hits(NEGATIVE, a)
    context_title = bool(CONTEXT.search(t))
    context_head = bool(CONTEXT.search(head))
    context_any = bool(CONTEXT.search(main))
    contextual = 'explicito_titulo' if context_title else 'explicito_resumen' if context_head else 'mencion_periferica' if context_any else 'sin_evidencia_expresa'
    link_ac = snippet(units, lambda s: bool(hits(PROCESSES, s) or hits(EQUIPMENT, s)) and bool(hits(PERFORMANCE, s)))
    link_ab = snippet(units, lambda s: bool(hits(PROCESSES, s) or hits(EQUIPMENT, s)) and bool(hits(DECISIONS, s)))
    link_abc = snippet(units, lambda s: bool(hits(PROCESSES, s) or hits(EQUIPMENT, s)) and bool(hits(DECISIONS, s)) and bool(hits(PERFORMANCE, s)))
    link_ac_abs = snippet(abs_units, lambda s: bool(hits(PROCESSES, s) or hits(EQUIPMENT, s)) and bool(hits(PERFORMANCE, s)))
    dominant = [x for x in negative if x in ('geologia_exploracion', 'geotecnia_talud', 'ambiente_cierre', 'metalurgia_procesamiento', 'estrategia_vida_mina', 'componente_aislado', 'seguridad_sin_desempeno', 'efecto_voladura_no_operacional', 'exposicion_ambiental', 'geologia_instrumental', 'insumos_fuera_de_mina', 'deteccion_sin_resultado_tarea', 'documento_no_investigacion')]
    operational_title = bool(pt or et or dt)
    operational_head = bool(hits(PROCESSES, head) or hits(EQUIPMENT, head))
    title_endpoint = bool((pt or et) and mt)
    prominent = bool(operational_title or mt)
    strong_outcome = bool(prominent and operational_head and link_ac or title_endpoint)
    strong_intervention = bool(prominent and link_ab or (operational_title and dt))
    abstract_confirmation = bool(link_ac_abs or (title_endpoint and operational_head and hits(PERFORMANCE, a) and re.search('\\b(?:performance|productivity|efficiency|capacity|output|consumption|cycle time|costs?|availability)\\b', a, re.I)))
    central = operational_title or operational_head
    support = bool(set(proc) & {'caminos_mina', 'desague_apoyo', 'riego_polvo', 'botaderos_operacionales', 'chancado_en_mina'} or set(decision) & {'mantencion', 'informacion', 'planificacion_corta'})
    language = (r.get('language') or '').lower()
    metadata = bool(r.get('quality_flags'))
    secondary_document = r.get('type') == 'review'
    if 'documento_no_investigacion' in dominant or re.search('\\(review\\)$', t, re.I):
        label = 'OUT'
        cause = 'documento_editorial_sin_estudio'
    elif UNDERGROUND_TITLE.search(t) or NONMINING_TITLE.search(t):
        label = 'OUT'
        cause = 'foco_subterraneo_o_extraccion_no_minera'
    elif not context_any and (not (operational_title and operational_head)):
        label = 'OUT'
        cause = 'sin_contexto_cielo_abierto'
    elif dominant and (not (title_endpoint and 'geologia_exploracion' in dominant and (len(dominant) == 1))):
        if central and (link_ac or link_ab) and ('componente_aislado' in dominant or 'estrategia_vida_mina' in dominant or 'efecto_voladura_no_operacional' in dominant or ('exposicion_ambiental' in dominant) or ('geologia_instrumental' in dominant) or ('deteccion_sin_resultado_tarea' in dominant)):
            label = 'DUDOSO'
            cause = 'foco_principal_alternativo_con_enlace_posible'
        else:
            label = 'OUT'
            cause = 'foco_principal_' + dominant[0]
    elif central and strong_outcome and abstract_confirmation and (strong_intervention or title_endpoint):
        if support or (secondary_document and (not link_abc)):
            label = 'IN_SECUNDARIO'
            cause = 'vinculo_indirecto_o_documento_secundario'
        else:
            label = 'IN_FUERTE'
            cause = 'proceso_decision_y_desempeno_vinculados'
    elif central and strong_outcome and abstract_confirmation and (pt or et) and (link_ac or mt):
        label = 'IN_SECUNDARIO' if support else 'IN_FUERTE'
        cause = 'evaluacion_directa_de_desempeno_sin_intervencion_explicita'
    elif central and (strong_intervention or strong_outcome or (decision and proc) or ((pt or et) and (decision or perf))):
        label = 'DUDOSO'
        cause = 'enlace_operacional_incompleto_en_resumen'
    elif not operational_title and (not operational_head):
        label = 'OUT'
        cause = 'mencion_incidental_de_operacion'
    else:
        label = 'OUT'
        cause = 'sin_desempeno_ni_decision_operacional_demostrada'
    if label == 'OUT' and language not in ('en', '') and operational_title and (not dominant) and (not strong_outcome) and (not UNDERGROUND_TITLE.search(t)):
        label = 'DUDOSO'
        cause = 'idioma_o_resumen_insuficiente'
    if label == 'OUT' and language not in ('en', '') and (not dominant) and context_any and operational_head and link_ac_abs:
        label = 'DUDOSO'
        cause = 'idioma_o_resumen_insuficiente'
    if metadata and label.startswith('IN') and (not link_abc):
        label = 'DUDOSO'
        cause = 'metadatos_incompatibles_verificar_fuente'
    if label == 'IN_FUERTE':
        confidence = 'alta' if link_abc or (operational_title and mt and strong_intervention) else 'media'
    elif label == 'IN_SECUNDARIO':
        confidence = 'media'
    elif label == 'DUDOSO':
        confidence = 'baja'
    else:
        confidence = 'alta' if dominant or not central else 'media'
    process = ';'.join(proc) or 'no_identificado'
    equipment = ';'.join(equip) or 'no_identificado'
    outcome = ';'.join(perf) or 'no_identificado'
    contribution = 'mantencion' if 'mantencion' in decision else 'asignacion_optimizacion' if 'despacho_asignacion' in decision else 'planificacion_operativa' if 'planificacion_corta' in decision else 'informacion_automatizacion' if 'informacion' in decision and (not strong_outcome) else 'auxiliares' if support else 'ejecucion_desempeno' if strong_outcome else 'diseno_planificacion' if 'estrategia_vida_mina' in negative else 'no_operacional'
    justification = f"{cause}; contexto={contextual}; proceso={process}; equipo={equipment}; decision={';'.join(decision) or 'no_identificada'}; resultado={outcome}"
    return {'contexto_cielo_abierto': contextual, 'proceso_detectado': process, 'equipo_detectado': equipment, 'decision_operacional_detectada': ';'.join(decision) or 'no_identificada', 'resultado_operacional_detectado': outcome, 'contribucion': contribution, 'foco_alternativo_titulo': ';'.join(negative) or '', 'evidencia_proceso_decision_resultado': link_abc, 'evidencia_proceso_resultado': link_ac, 'evidencia_proceso_resultado_resumen': link_ac_abs, 'evidencia_proceso_decision': link_ab, 'confirmacion_desempeno_en_resumen': 'si' if abstract_confirmation else 'no', 'decision_final_propuesta': label, 'motivo_codificado': cause, 'justificacion_por_dimensiones': justification, 'confianza_cualitativa_no_calibrada': confidence, 'requiere_texto_completo': 'si' if label == 'DUDOSO' else 'segun_control_humano', 'alerta_metadata': r.get('quality_flags', ''), 'protocolo_screening': 'v6_2026_09_28', 'decision_humana_1': '', 'decision_humana_2': '', 'consenso_humano': '', 'motivo_consenso': ''}
from functools import lru_cache
_registros_prueba = registros[:100]
_decisiones_originales = [decide(r) for r in _registros_prueba]
_hits_original = hits
_grupos_hit = {'procesos': PROCESSES, 'equipos': EQUIPMENT, 'decisiones': DECISIONS, 'resultados': PERFORMANCE, 'negativos': NEGATIVE}
_nombres_por_id = {id(v): k for k, v in _grupos_hit.items()}

@lru_cache(maxsize=50000)
def _coincidencias_memoizadas(grupo, texto):
    return tuple(_hits_original(_grupos_hit[grupo], texto))

def hits(patterns, text):
    grupo = _nombres_por_id.get(id(patterns))
    if grupo is None:
        return _hits_original(patterns, text)
    return list(_coincidencias_memoizadas(grupo, text))
_decisiones_optimizadas = [decide(r) for r in _registros_prueba]
if not _decisiones_originales == _decisiones_optimizadas:
    raise ValueError('La optimización modificó alguna decisión original; revisar antes de continuar.')
print('Optimización verificada: 100/100 decisiones completas idénticas a las funciones originales.')
print('Reglas originales de Joaquín: sin cambios. Optimización: solo caché para coincidencias repetidas.')
filas = []
for i, r in enumerate(registros, start=1):
    d = decide(r)
    d['decision_algoritmica_pre_auditoria'] = d['decision_final_propuesta']
    d['procedencia_ajuste'] = 'regla_reproducible'
    d['motivo_final_propuesto'] = d['motivo_codificado']
    d['justificacion_final_propuesta'] = d['justificacion_por_dimensiones']
    filas.append({**r, **d, 'fuente_cribado': 'Scopus', 'validacion_academica': 'pendiente'})
    if i % 500 == 0 or i == len(registros):
        print(f'Cribado: {i} / {len(registros)}')
etiquetas = ('IN_FUERTE', 'IN_SECUNDARIO', 'DUDOSO', 'OUT')
cuentas = Counter((f['decision_final_propuesta'] for f in filas))
if not set(cuentas) <= set(etiquetas):
    raise ValueError('Se detectó una etiqueta inesperada.')
if not sum(cuentas.values()) == len(registros):
    raise ValueError('No se clasificaron todos los registros.')
print('\nClasificaciones automáticas (sin auditoría dirigida ni revisión humana):')
for e in etiquetas:
    print(f'  {e:15s}: {cuentas.get(e, 0):,}')
print('Núcleo IN propuesto:', cuentas['IN_FUERTE'] + cuentas['IN_SECUNDARIO'])

def escribir_csv(destino, datos, campos=None):
    destino.parent.mkdir(parents=True, exist_ok=True)
    if campos is None:
        campos = list(datos[0]) if datos else list(filas[0])
    with destino.open('w', encoding='utf-8-sig', newline='') as archivo:
        writer = csv.DictWriter(archivo, fieldnames=campos, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(datos)
principal = SALIDA / 'screening_operacional_scopus_fase02.csv'
escribir_csv(principal, filas)
for e in etiquetas:
    escribir_csv(SALIDA / f'{e}_scopus.csv', [f for f in filas if f['decision_final_propuesta'] == e])
core_rows = [f for f in filas if f['decision_final_propuesta'] in ('IN_FUERTE', 'IN_SECUNDARIO')]
escribir_csv(SALIDA / 'corpus_IN_propuesto_scopus.csv', core_rows)
if not len(core_rows) == cuentas['IN_FUERTE'] + cuentas['IN_SECUNDARIO']:
    raise ValueError('Control de integridad incumplido')
print('Salidas CSV principales guardadas en:', SALIDA.resolve())

def genuine_boundary(r):
    return r['contexto_cielo_abierto'] in ('explicito_titulo', 'explicito_resumen') and r['proceso_detectado'] != 'no_identificado' and (r['resultado_operacional_detectado'] != 'no_identificado' or r['decision_operacional_detectada'] != 'no_identificada') and (r['motivo_codificado'] in ('enlace_operacional_incompleto_en_resumen', 'foco_principal_alternativo_con_enlace_posible', 'idioma_o_resumen_insuficiente'))
estratos = {'IN': [r for r in filas if r['decision_final_propuesta'] in ('IN_FUERTE', 'IN_SECUNDARIO')], 'OUT': [r for r in filas if r['decision_final_propuesta'] == 'OUT'], 'DUDOSO_CENTRAL': [r for r in filas if r['decision_final_propuesta'] == 'DUDOSO' and genuine_boundary(r)]}
objetivos = {'IN': 50, 'OUT': 50, 'DUDOSO_CENTRAL': 30}
prefijos = {'IN': 'I', 'OUT': 'O', 'DUDOSO_CENTRAL': 'D'}
ciega, clave = ([], [])
for nombre, n in objetivos.items():
    grupo = estratos[nombre]
    ordenados = sorted(grupo, key=lambda r: r['scopus_id'])
    seleccion = random.Random(SEED + len(nombre)).sample(ordenados, min(n, len(grupo)))
    if len(seleccion) != n:
        print(f'ATENCIÓN: {nombre} solo tiene {len(seleccion)} de {n} casos esperados.')
    for j, r in enumerate(seleccion, 1):
        codigo = f'{prefijos[nombre]}-{j:03d}'
        ciega.append({'codigo': codigo, 'title': r['title'], 'abstract': r['abstract'], 'doi': r['doi'], 'year': r['year'], 'decision_revisor_1_IN_OUT_TC': '', 'razon_revisor_1': '', 'decision_revisor_2_IN_OUT_TC': '', 'razon_revisor_2': '', 'consenso_IN_OUT_TC': '', 'razon_consenso': '', 'texto_completo_consultado': ''})
        clave.append({'codigo': codigo, 'scopus_id': r['scopus_id'], 'estrato': nombre, 'subcategoria_propuesta': r['decision_final_propuesta'], 'N': len(grupo), 'n': len(seleccion), 'probabilidad_n_sobre_N': f'{len(seleccion) / len(grupo):.10f}', 'peso_N_sobre_n': f'{len(grupo) / len(seleccion):.10f}'})
pares = list(zip(ciega, clave))
random.Random(SEED + 9001).shuffle(pares)
for numero, (ficha, llave) in enumerate(pares, 1):
    ficha['codigo'] = llave['codigo'] = f'R-{numero:03d}'
ciega = [f for f, k in pares]
clave = [k for f, k in pares]
escribir_csv(SALIDA / 'muestra_humana_ciega_130_scopus.csv', ciega, list(ciega[0]))
escribir_csv(SALIDA / 'clave_muestra_130_NO_ENTREGAR_A_REVISORES.csv', clave, list(clave[0]))
print('Muestra humana:', len(ciega), '; estratos:', dict(Counter((k['estrato'] for k in clave))))
print('NO compartir la clave con los revisores durante la evaluación ciega.')

def sha_archivo(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b''):
            h.update(bloque)
    return h.hexdigest()

def frecuencias_cadena(campo, separador=';'):
    return dict(Counter((v.strip() for r in filas for v in r.get(campo, '').split(separador) if v.strip() and v.strip() not in ('no_identificado', 'no_identificada'))))
alertas = {'aceptados_fase01_provisionales': len(registros), 'filtro_fase01_validado_academicamente': manifest.get('filtro_validado_academicamente'), 'retractacion_y_paratexto_pendientes_de_verificar': manifest.get('pendientes_retractacion_y_paratexto'), 'lengua_sin_informar_en_aceptados': sum((not r.get('language', '').strip() for r in registros)), 'quality_flags_no_vacios_en_aceptados': sum((bool(r.get('quality_flags', '').strip()) for r in registros)), 'auditoria_dirigida_48_heredada': False, 'reconciliacion_con_ids_openalex': False, 'correcciones_de_etiquetas_por_revisor': 0, 'filtro_fase02_validado_academicamente': False}
resumen = {'fuente': 'Scopus', 'fase': '02_cribado_multidimensional', 'protocolo_reglas_joaquin': 'v6_2026_09_28', 'fecha_utc': datetime.now(timezone.utc).isoformat(), 'total_entrada': len(registros), 'decisiones': {e: cuentas.get(e, 0) for e in etiquetas}, 'nucleo_in_propuesto': len(core_rows), 'motivos': dict(Counter((f['motivo_codificado'] for f in filas))), 'procesos': frecuencias_cadena('proceso_detectado'), 'equipos': frecuencias_cadena('equipo_detectado'), 'contribuciones': dict(Counter((f['contribucion'] for f in filas))), 'muestra': dict(Counter((k['estrato'] for k in clave))), 'marcos_de_muestra': {k: len(v) for k, v in estratos.items()}, 'alertas_y_pendientes': alertas, 'carpeta_fase01': str(carpeta), 'sha256_manifest_fase01': sha_archivo(manifest_path), 'sha256_corpus_aceptado_fase01': sha_bytes(raw_aceptados), 'sha256_fragmento_reglas_v6': '924b9e0ad681fe35fafc497d626f3b8cb98a7f0423b14267b9a209a7cb46aa2b', 'sha256_salidas_csv': {p.name: sha_archivo(p) for p in sorted(SALIDA.glob('*.csv'))}, 'alcance': 'Clasificación automática preliminar sin validación humana. No es el cierre v9 de OpenAlex.'}
(SALIDA / 'resumen_fase02_scopus.json').write_text(json.dumps(resumen, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'entrada': len(filas), 'decisiones': resumen['decisiones'], 'nucleo_IN': len(core_rows), 'muestra': resumen['muestra'], 'pendientes': alertas}, indent=2, ensure_ascii=False))
