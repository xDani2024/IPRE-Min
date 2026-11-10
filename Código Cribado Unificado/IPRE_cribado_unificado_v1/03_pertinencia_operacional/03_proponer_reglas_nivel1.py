"""Etapa 3b: Nivel 1 (pertinencia a la operación minera a cielo abierto).

Las señales se toman de los diccionarios de los motores originales (filtro amplio,
v6, v7, v8 y v9). No se crea vocabulario temático nuevo salvo los marcadores de
vínculo operacional exigidos por las decisiones acordadas para geotecnia,
vibraciones, agua y componentes (ciclo, costos, tiempos, equipos), que reutilizan
los patrones de resultado operacional de v7/v8/v9.

Salida: propuesta por regla + cola de lectura dirigida (casos ambiguos).
Uso: py -3 03_pertinencia_operacional/03_proponer_reglas_nivel1.py [--motores RUTA] [--filtro RUTA] [--nucleo RUTA] [--salida RUTA]
"""
import csv, json, re, sys, importlib.util
from collections import Counter
from pathlib import Path

csv.field_size_limit(10**9)
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import argparse
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
def buscar_proyecto(p):
    """Carpeta IPRE-Min-main: la indicada o la primera carpeta superior que contiene integracion_corpus/."""
    if p: return Path(p).resolve()
    for d in ROOT.parents:
        if (d / 'integracion_corpus/resultados_validados/universo').is_dir(): return d
    sys.exit('No se encontró IPRE-Min-main (carpeta con integracion_corpus/). Indíquela con --proyecto.')
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--motores', type=Path, default=ROOT / 'motores_originales')
ap.add_argument('--filtro', type=Path, default=ROOT / '01_filtro_amplio/salida')
ap.add_argument('--nucleo', type=Path, default=ROOT / '02_nucleo_desempeno/salida')
ap.add_argument('--salida', type=Path, default=HERE / 'salida')
args = ap.parse_args()
CODE, IN1, IN2, OUT = args.motores.resolve(), args.filtro.resolve(), args.nucleo.resolve(), args.salida.resolve()
OUT.mkdir(parents=True, exist_ok=True)
def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, CODE / rel)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
F = load('f', '01_extraccion_y_filtro/02_filtrar_y_unificar.py')
V6 = load('v6', '02_cribado_v6/codigo/06_screening_multidimensional.py')
V7 = load('v7', '03_cribado_v8/entrada/v7/11_resolver_dudosos.py')
V8 = load('v8', '03_cribado_v8/15_aplicar_criterio_calibrado.py')
V9 = load('v9', '04_cierre_v9/22_cerrar_TC.py')
rx = lambda p: re.compile(p, re.I)

def read(p):
    with open(p, encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def write(p, rows, fields=None):
    with open(p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fields or list(rows[0]), extrasaction='ignore'); w.writeheader(); w.writerows(rows)

A = {r['id_publicacion']: r for r in read(IN1 / 'etapa2_filtro_amplio.csv')}
N = read(IN2 / 'etapa3a_nucleo_reglas.csv')

# --- Objeto operacional (procesos, equipos, decisiones, planificación) ------
# Términos de equipos y procesos del filtro amplio original (sin geotecnia).
OP_DICT_TERMS = [t for k, ts in F.EQUIPMENT_TERMS.items() for t in ts] + \
    [t for k, ts in F.PROCESS_TERMS.items() if k not in ('caracterizacion_topografia_geomecanica',) for t in ts] + \
    [t for k, ts in F.DIRECT_OPERATIONAL_TERMS.items()
     if k in ('planificacion_diseno', 'perforacion_tronadura', 'carguio_transporte', 'equipos_mantenimiento', 'agua_polvo_infraestructura')
     for t in ts]
OP_DICT = rx(r'(?<![a-z0-9])(?:' + '|'.join(sorted({re.escape(F.normalize(t)) for t in OP_DICT_TERMS}, key=len, reverse=True)) + r')(?![a-z0-9])')
OP_V6 = [V6.EQUIPMENT[k] for k in V6.EQUIPMENT] + [V6.PROCESSES[k] for k in ('perforacion', 'carguio', 'remocion_estéril',
          'caminos_mina', 'desague_apoyo', 'riego_polvo', 'botaderos_operacionales', 'chancado_en_mina')]
DEC_V6 = [V6.DECISIONS[k] for k in ('despacho_asignacion', 'planificacion_corta', 'mantencion')]
PLAN = rx(V9.STRATEGIC.pattern + '|' + V8.STRATEGIC_TITLE.pattern + r'|pit optimi[sz]|mine plan|mining plan|production plan|schedul|'
          r'mining sequence|extraction sequence|pushback|phase design|stripping ratio|mining method|equipment selection|'
          r'fleet (?:selection|sizing|size)|mine design|pit design|grade control|dig limit|stockpile|cut.?off|mining cost|production capacity|'
          r'ore quality|blending|queu|transport system|mining system|state of operations|automated .{0,20}mining|autonomous|'
          r'dewater|groundwater control|pit water|drainage of (?:the )?(?:pit|quarry|mine)|ventilat|airing|aeration|'
          r'управлен.{0,20}качеств|транспорт|экскават|самосвал|отвал|буровзрыв|карьерн.{0,10}транспорт|проектирован|'
          r'vehicles?\b|boundary|bench (?:geometry|height|width|parameter|design)|positioning|technological scheme|mining technolog|'
          r'machinery|dependabilit|continuous (?:sub)?systems?|opening cut|cut location|cost estimat|road dust|controlled blasting|'
          r'pre.?split|cushion blasting|smooth blasting|blasted|muckpile|mine development|pit development|geometri jenjang|jenjang|'
          r'produksi|penambangan|alat (?:gali|muat|angkut|berat)|drivers?\b|operators? (?:of|in)|mining operations?')
BLAST = rx(r'\bblast(?:ing|ed|s)?\b|explosive|fragmentation|drill(?:ing)?\b|blasthole|tronadura|voladura|perforaci')
def op_object(text):
    t = F.normalize(text); hits = []
    if OP_DICT.search(t): hits.append('diccionario_equipos_procesos')
    if any(p.search(text) for p in OP_V6): hits.append('equipo_proceso_v6')
    if any(p.search(text) for p in DEC_V6): hits.append('decision_operacional_v6')
    if PLAN.search(text): hits.append('planificacion_diseno')
    if BLAST.search(text): hits.append('perforacion_tronadura')
    return hits

# --- Focos alternativos (v6 NEGATIVE, v7 OTHER_FOCUS, v9 ALTERNATIVE) -------
ALT = {
 'ambiente_cierre_salud': [V6.NEGATIVE['ambiente_cierre'], V6.NEGATIVE['exposicion_ambiental'], V9.ALTERNATIVE['ambiente_seguridad'],
     rx(r'reclam|restor|revegetat|rehabilit|ecolog|ecosystem|biodivers|vegetation|forest|soil|landscape|land use|land cover|'
        r'pollut|contamin|heavy metal|toxic|health|epidemiolog|disease|mortality|asthma|wildlife|stream|river|watershed|'
        r'groundwater (?:quality|contamin|level)|hydrolog|climate|carbon emission|greenhouse|co2|ghg|pit lake|acid mine|closure|post.mining')],
 'geotecnia_estabilidad': [V6.NEGATIVE['geotecnia_talud'], V7.OTHER_FOCUS[0][1], V9.ALTERNATIVE['geotecnia_cartografia']],
 'geologia_recursos': [V6.NEGATIVE['geologia_exploracion'], V6.NEGATIVE['geologia_instrumental'],
     rx(r'mineraliz|ore genesis|geochronolog|petrolog|tecton|stratigraph|kriging|geostatist|resource model|reserve estimat')],
 'procesamiento_metalurgia': [V6.NEGATIVE['metalurgia_procesamiento'], rx(r'concentrator|comminution|grinding|milling plant|tailings|heap leach|smelter|refin')],
 'efectos_tronadura': [rx(r'(?:blast|explos)\w*.{0,40}vibration|vibration.{0,40}(?:blast|explos)|ground vibration|airblast|air blast|flyrock|fly rock|'
                          r'overpressure|peak particle|airwave|air wave|shock wave|seismic (?:effect|impact|wave)|elastic wave|blast.induced')],
 'componente_material': [V6.NEGATIVE['componente_aislado'], V7.OTHER_FOCUS[3][1], V8.COMPONENT],
 'economia_sociedad_politica': [rx(r'\bpolicy|policies|legislat|\blaw\b|legal|social (?:impact|licen)|community|communities|employment|labou?r market|'
     r'economic impact|\btax|royalt|governance|stakeholder|conflict|indigenous|gender|education|history of')],
 'teledeteccion_cartografia': [rx(r'remote sensing|satellite|landsat|sentinel|insar|land.?cover|change detection|mapping of|'
     r'mine area|mining area|extraction of (?:open.?pit|mining)|identification of (?:open.?pit|mining)|segmentation')],
 'seguridad_salud_ocupacional': [V6.NEGATIVE['seguridad_sin_desempeno'], rx(r'occupational|accident|injur|fatalit|ergonom|noise exposure|silica|pneumoconiosis|respirable')],
}
def alt_focus(text):
    return [k for k, ps in ALT.items() if any(p.search(text) for p in ps)]

# Vínculo operacional (decisiones acordadas): ciclo, costos, tiempos, equipos.
LINK = rx(V9.METRICS['productividad'].pattern + '|' + V9.METRICS['tiempos_esperas'].pattern + '|' +
          V9.METRICS['disponibilidad_utilizacion'].pattern + '|' + V9.METRICS['costo_tarea'].pattern + '|' +
          V9.METRICS['combustible_energia'].pattern + '|' + V9.METRICS['carga_transportada'].pattern + '|' +
          r'haul(?:age|ing)?|truck|shovel|excavator|dragline|loader|fleet|equipment|machine|conveyor|crusher|'
          r'mining (?:operation|cycle|productivity|cost)|production (?:rate|loss|plan)|ore loss|dilution|bench (?:height|width|design)|'
          r'blast(?:ing)? design|drilling and blasting|mining sequence|pit design|operational')
LINK_METRIC = rx('|'.join(p.pattern for p in V9.METRICS.values()) +
    r'|(?:truck|shovel|excavator|haul\w*|loading|equipment|fleet|dragline|conveyor)\b.{0,80}\b(?:cycle|costs?|time|productiv|efficien|availab)')
MINE_EQ = rx(r'truck|shovel|excavator|dragline|drill(?:ing)? rig|drill\b|dozer|loader|grader|bucket.?wheel|conveyor|crusher|'
             r'surface miner|spreader|stacker|haul|mining (?:equipment|machine)|open.?(?:pit|cast) (?:equipment|machine)|экскават|самосвал')
AUX_ENV = rx(r'dust suppress|dust control|watering|water truck|haul road|road dust|dewater|drain|fuel|diesel|emission.{0,30}(?:truck|haul|equipment|vehicle)|'
             r'(?:truck|haul|equipment|vehicle).{0,30}emission|energy (?:consumption|efficien)|electrif|trolley|ventilat')
UNDER = rx(r'underground|longwall|room.and.pillar|block cav|sublevel|stope|stoping|shaft|подземн')
SURF_T = rx(V9.SURFACE.pattern)
TRANSITION = rx(r'open.?pit (?:to|and) underground|transition|combined|hybrid|surface (?:and|to) underground|open.?cast (?:and|to) underground')
NONMINING = rx(r'construction site|tunnel|road construction(?! in)|highway|railway (?:construction|cut)|urban|building|agricultur|dam construction|archaeolog')

rows = []
for n in N:
    a = A[n['id_publicacion']]
    t, ab = a['title'], a['abstract']
    head = ab[:900]
    ctx = n['contexto_cielo_abierto_v6']
    opt, ops_abs = op_object(t), op_object(head)
    altt, alt_abs = alt_focus(t), alt_focus(head)
    link_abs = bool(LINK.search(ab))
    nucleo_cand = n['decision_v9_regla'] == 'IN'
    review = n['revision_secundaria_detectada'] == 'si' or a['type'] == 'review'
    no_abs = a['tiene_resumen'] == 'no'
    code = ''
    if UNDER.search(t) and not SURF_T.search(t) and not TRANSITION.search(t):
        dec, code = 'OUT', 'N1_O01_CONTEXTO_SUBTERRANEO'
    elif nucleo_cand:
        dec, code = 'AMBIGUO', 'N1_L00_CANDIDATO_NUCLEO_VERIFICAR'
    elif ctx == 'sin_evidencia_expresa' and not opt:
        dec, code = 'OUT', 'N1_O02_CONTEXTO_NO_ACREDITADO'
    elif opt and not altt:
        if ctx in ('explicito_titulo', 'explicito_resumen') or SURF_T.search(t):
            dec, code = 'IN', 'N1_I01_OBJETO_OPERACIONAL_EN_TITULO'
        else:
            dec, code = 'AMBIGUO', 'N1_L01_OBJETO_OPERACIONAL_CONTEXTO_PERIFERICO'
    elif opt and altt:
        fam = set(altt); lm = bool(LINK_METRIC.search(ab))
        if fam <= {'componente_material'} and MINE_EQ.search(t):
            dec, code = 'IN', 'N1_I02_COMPONENTE_O_CONDICION_DE_EQUIPO_DE_MINA'
        elif fam <= {'seguridad_salud_ocupacional'} and MINE_EQ.search(t) and not re.search(r'health|exposure|noise|disease|ergonom', t, re.I):
            dec, code = 'IN', 'N1_I03_SEGURIDAD_DE_LA_OPERACION_DE_EQUIPOS'
        elif 'ambiente_cierre_salud' in fam and AUX_ENV.search(t) and not (fam & {'geologia_recursos', 'teledeteccion_cartografia'}):
            dec, code = 'IN', 'N1_I04_PROCESO_AUXILIAR_O_ENERGIA_DE_EQUIPOS'
        elif fam & {'efectos_tronadura', 'geotecnia_estabilidad', 'ambiente_cierre_salud', 'teledeteccion_cartografia',
                    'geologia_recursos', 'procesamiento_metalurgia', 'economia_sociedad_politica'} and not lm:
            dec, code = 'OUT', 'N1_O05_FOCO_ALTERNATIVO_DOMINANTE_SIN_VINCULO:' + '|'.join(altt)
        else:
            dec, code = 'AMBIGUO', 'N1_L02_OBJETO_OPERACIONAL_Y_FOCO_ALTERNATIVO'
    elif altt and not opt:
        if LINK_METRIC.search(ab) and ops_abs:
            dec, code = 'AMBIGUO', 'N1_L03_FOCO_ALTERNATIVO_CON_POSIBLE_VINCULO'
        else:
            dec, code = 'OUT', 'N1_O03_FOCO_ALTERNATIVO_SIN_VINCULO:' + '|'.join(altt)
    else:  # título sin objeto operacional ni foco alternativo explícito
        if no_abs:
            dec, code = 'AMBIGUO', 'N1_L05_SIN_RESUMEN_TITULO_GENERICO'
        elif ops_abs and not alt_abs:
            dec, code = 'AMBIGUO', 'N1_L04_OBJETO_OPERACIONAL_SOLO_EN_RESUMEN'
        elif ops_abs and alt_abs and LINK_METRIC.search(ab):
            dec, code = 'AMBIGUO', 'N1_L06_RESUMEN_MIXTO'
        elif ops_abs and alt_abs:
            dec, code = 'OUT', 'N1_O06_RESUMEN_CON_FOCO_ALTERNATIVO_SIN_VINCULO:' + '|'.join(alt_abs)
        elif alt_abs:
            dec, code = 'OUT', 'N1_O03_FOCO_ALTERNATIVO_SIN_VINCULO:' + '|'.join(alt_abs)
        else:
            dec, code = 'AMBIGUO', 'N1_L07_SIN_OBJETO_NI_FOCO_DETECTADO'
    rows.append({'id_publicacion': n['id_publicacion'], 'nivel1_regla': dec, 'nivel1_codigo_regla': code,
                 'objeto_operacional_titulo': ';'.join(opt), 'objeto_operacional_resumen': ';'.join(ops_abs),
                 'foco_alternativo_titulo': ';'.join(altt), 'foco_alternativo_resumen': ';'.join(alt_abs),
                 'vinculo_operacional_resumen': 'si' if link_abs else 'no', 'revision_literatura': 'si' if review else 'no',
                 'contexto_v6': ctx, 'title': t})
write(OUT / 'etapa3b_nivel1_reglas.csv', rows)
s = {'nivel1': dict(Counter(r['nivel1_regla'] for r in rows)),
     'codigos': dict(Counter(r['nivel1_codigo_regla'].split(':')[0] for r in rows))}
(OUT / 'etapa3b_resumen.json').write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
print(json.dumps(s, ensure_ascii=False, indent=2))
