"""Etapa 3a: cadena de reglas del núcleo de desempeño (v6 -> v7 -> v8 -> v9).

Importa los motores originales sin modificarlos y reproduce sus pasos sobre las
publicaciones ACEPTADAS por el filtro amplio. Las auditorías IA, juicios humanos y
pilotos históricos NO se cargan (cribado desde cero): esos insumos estaban
indexados por ID OpenAlex y correspondían a otra cohorte.

Adaptaciones estrictamente necesarias (documentadas en las columnas):
 * v6 `quality_flags` y v7/v8 `abstracto_invalido_para_cribado`: el corpus unificado
   no trae el archivo de alertas v6. Se reconstruye la misma alerta histórica
   («resumen compartido con título incompatible») comparando resúmenes idénticos
   entre publicaciones distintas.
 * v7 `prioridad`: P0 solo si hay alerta (equivale a la regla de estado documental).
 * v8: se reproduce el bucle principal fila a fila; se omiten las ramas que
   dependen de auditorías IA previas (I02, I03, O05) porque no existen para esta cohorte.

Uso: py -3 02_nucleo_desempeno/02_aplicar_reglas_v6_a_v9.py [--motores RUTA] [--entrada RUTA] [--salida RUTA]
"""
import csv, json, re, sys, difflib, hashlib, importlib.util
from collections import Counter, defaultdict
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
ap.add_argument('--entrada', type=Path, default=ROOT / '01_filtro_amplio/salida', help='Carpeta con etapa2_filtro_amplio.csv')
ap.add_argument('--salida', type=Path, default=HERE / 'salida')
args = ap.parse_args()
CODE, IN1, OUT = args.motores.resolve(), args.entrada.resolve(), args.salida.resolve()
OUT.mkdir(parents=True, exist_ok=True)

def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, CODE / rel)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
V6 = load('v6', '02_cribado_v6/codigo/06_screening_multidimensional.py')
V7 = load('v7', '03_cribado_v8/entrada/v7/11_resolver_dudosos.py')
V8 = load('v8', '03_cribado_v8/15_aplicar_criterio_calibrado.py')
V9 = load('v9', '04_cierre_v9/22_cerrar_TC.py')

def read(p):
    with open(p, encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def write(p, rows, fields=None):
    with open(p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fields or list(rows[0]), extrasaction='ignore'); w.writeheader(); w.writerows(rows)

ALL = read(IN1 / 'etapa2_filtro_amplio.csv')

# --- Alerta de resumen compartido (equivalente a alertas_metadata v6) ---------
def nabs(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def ntit(s): return re.sub(r'[^a-z0-9 ]', '', (s or '').lower())
by_abs = defaultdict(list)
for r in ALL:
    k = nabs(r['abstract'])
    if len(k) >= 120: by_abs[k].append(r)
shared = {}
for k, rs in by_abs.items():
    if len(rs) < 2: continue
    for r in rs:
        others = [o for o in rs if o is not r]
        incompatible = all(difflib.SequenceMatcher(None, ntit(r['title']), ntit(o['title'])).ratio() < 0.80 for o in others)
        shared[r['id_publicacion']] = ('resumen_compartido_con_titulo_incompatible' if incompatible
                                       else 'resumen_compartido_titulo_similar', len(rs))

rows = [r for r in ALL if r['decision_filtro_amplio'] == 'ACEPTADO']
out = []
for r in rows:
    pid = r['id_publicacion']
    flag, ngroup = shared.get(pid, ('', 0))
    invalid = flag == 'resumen_compartido_con_titulo_incompatible'
    base = {'openalex_id': pid, 'title': r['title'], 'abstract': r['abstract'],
            'language': r['language'], 'type': r['type'], 'quality_flags': flag}
    # ---- v6 ---------------------------------------------------------------
    d6 = V6.decide(base)
    # ---- v7 (solo DUDOSO) -------------------------------------------------
    v7 = {'decision_nucleo_v7': 'IN' if d6['decision_final_propuesta'].startswith('IN') else 'OUT',
          'regla_v7': 'V6_SIN_CAMBIO', 'estado_documental_v7': 'SEGUN_CONTROL_V6'}
    if d6['decision_final_propuesta'] == 'DUDOSO':
        q = {**base, 'contexto': d6['contexto_cielo_abierto'],
             'prioridad': 'P0_VERIFICAR_RESUMEN' if invalid else 'P2_ENLACE_PARCIAL'}
        a7 = V7.assess(q, base, {'abstracto_invalido_para_cribado': 'si'} if invalid else None)
        v7 = {'decision_nucleo_v7': a7['decision_nucleo_v7'], 'regla_v7': a7['regla_v7'],
              'estado_documental_v7': a7['estado_documental_v7']}
    # ---- v8 (réplica del bucle principal, sin auditorías previas) -----------
    old = V7
    metric = V8.rx(old.STRONG_C.pattern + '|' + '|'.join(
        p for k, p in V8.INDICATOR_PATTERNS.items() if k not in ('indicador_ambiental', 'precision_tiempo_algoritmo')))
    task = V8.rx(old.A.pattern + '|' + V8.SUPPORT.pattern)
    evaluated = V8.rx(old.RESULT_MARKER.pattern + r'|\bresults?\b|\bfindings?\b|\bcase study\b|\bmeasur|\bexperiment|\bshow(?:s|n|ed)?\b|\bsav(?:ed|ing|ings)\b')
    title = old.norm(r['title']); abstract = old.norm(r['abstract']); text = title + '\n' + abstract
    sents = [s.strip() for s in old.TEXT_SPLIT.split(abstract) if s.strip()]
    context = bool(old.SURFACE.search(text)) or d6['contexto_cielo_abierto'] in ('explicito_titulo', 'explicito_resumen')
    a = bool(task.search(title)) or bool(task.search(abstract))
    b = bool(old.B.search(text))
    metric_sents = [s for s in sents if metric.search(s)]
    linked = []
    for i, s in enumerate(sents):
        if not metric.search(s): continue
        prev = sents[i - 1] if i else ''
        antecedent = prev if (task.search(prev) and old.B.search(prev) and
            V8.rx(r'this|these|the (?:proposed|method|model|results?|system)|which|thereby').search(s)) else ''
        window = (antecedent + ' ' + s).strip()
        relation = task.search(s) or antecedent or (task.search(title) and (old.B.search(title) or old.EVALUATED.search(title)))
        result = evaluated.search(window)
        if relation and result and not V8.FUTURE_ONLY.search(s):
            if old.METHOD_ONLY.search(s) and not V8.WHOLE_METRIC.search(s) and not V8.rx(
                V8.INDICATOR_PATTERNS['distancia'] + '|' + V8.INDICATOR_PATTERNS['costo_tarea']).search(s):
                continue
            linked.append(window)
    c = bool(linked)
    secondary_title = bool(V8.REVIEW.search(title))
    secondary_text = bool(V8.SECONDARY_ABSTRACT.search(abstract[:1200]))
    secondary = secondary_title or secondary_text
    hybrid = secondary and bool(V8.OWN_EVALUATION.search(abstract)) and c
    focus = [(name, p.search(title)) for name, p in old.OTHER_FOCUS if p.search(title)]
    alt_previous = d6['foco_alternativo_titulo']
    component = bool(V8.COMPONENT.search(title)) or any(n == 'componente' for n, _ in focus)
    component_link = any(V8.WHOLE_EQUIPMENT.search(s) and V8.WHOLE_METRIC.search(s) for s in linked)
    evidence = old.excerpt((linked or metric_sents or [title])[0], 700)
    if invalid:
        dec, rule = 'TC', 'T01_METADATA_INVALIDA'
    elif V8.EDITORIAL.search(title):
        dec, rule = 'OUT', 'O01_EDITORIAL'
    elif secondary and not hybrid:
        dec, rule = 'OUT', 'O02_LITERATURA_SECUNDARIA'
    elif hybrid:
        dec, rule = 'TC', 'T02_DOCUMENTO_HIBRIDO'
    elif not context:
        if V8.OUTSIDE.search(title) and not old.SURFACE.search(title): dec, rule = 'OUT', 'O03_CONTEXTO_ALTERNATIVO'
        else: dec, rule = 'TC', 'T03_CONTEXTO_INSUFICIENTE'
    elif component and not component_link and V8.COMPONENT_ENDPOINT.search(abstract) and not V8.WHOLE_METRIC.search(abstract):
        dec, rule = 'OUT', 'O06_RESULTADO_DE_COMPONENTE'
    elif component and not component_link:
        dec, rule = 'TC', 'T04_COMPONENTE_SIN_VINCULO_OPERACIONAL'
    elif a and b and c:
        dec, rule = 'IN', 'I01_TAREA_RESULTADO_EVALUADO'
    elif V8.STRATEGIC_TITLE.search(title) or (V8.PROJECT_VALUE.search(abstract) and not linked):
        dec, rule = 'OUT', 'O07_RESULTADO_DE_MINA_PROYECTO'
    elif focus or alt_previous:
        dec, rule = 'OUT', 'O04_FOCO_ALTERNATIVO_IDENTIFICADO'
    else:
        dec, rule = 'TC', 'T05_RESULTADO_NO_ACREDITADO'
    # ---- v9 (solo TC) -------------------------------------------------------
    v9 = {'decision_v9_regla': dec, 'regla_v9': 'V8_CONSERVADA', 'disposicion_v9': 'v8_conservada',
          'motivo_v9': '', 'evidencia_v9': evidence, 'indicadores_v9': ''}
    if dec == 'TC':
        row9 = {'title': r['title'], 'abstract': r['abstract'], 'regla_v8': rule,
                'contexto_A_v8': 'acreditado_en_ficha' if context else 'por_cotejar'}
        d9, r9, disp9, why9, ev9, ind9, typ9 = V9.classify(row9)
        v9 = {'decision_v9_regla': d9, 'regla_v9': r9, 'disposicion_v9': disp9, 'motivo_v9': why9,
              'evidencia_v9': ev9, 'indicadores_v9': ind9}
    out.append({'id_publicacion': pid,
        'contexto_cielo_abierto_v6': d6['contexto_cielo_abierto'],
        'decision_v6': d6['decision_final_propuesta'], 'motivo_v6': d6['motivo_codificado'],
        'foco_alternativo_titulo_v6': d6['foco_alternativo_titulo'],
        'decision_v7': v7['decision_nucleo_v7'], 'regla_v7': v7['regla_v7'],
        'decision_v8': dec, 'regla_v8': rule, 'evidencia_v8': evidence,
        'senal_A_v8': 'si' if a else 'no', 'senal_B_v8': 'si' if b else 'no', 'senal_C_v8': 'si' if c else 'no',
        'revision_secundaria_detectada': 'si' if secondary else 'no',
        'alerta_resumen_compartido': flag, 'n_publicaciones_mismo_resumen': ngroup or '',
        **v9})

write(OUT / 'etapa3a_nucleo_reglas.csv', out)
summ = {'evaluadas': len(out),
        'v6': dict(Counter(o['decision_v6'] for o in out)),
        'v7': dict(Counter(o['decision_v7'] for o in out)),
        'v8': dict(Counter(o['decision_v8'] for o in out)),
        'reglas_v8': dict(Counter(o['regla_v8'] for o in out)),
        'v9_regla': dict(Counter(o['decision_v9_regla'] for o in out)),
        'reglas_v9_TC': dict(Counter(o['regla_v9'] for o in out if o['decision_v8'] == 'TC')),
        'alertas_resumen_compartido': dict(Counter(o['alerta_resumen_compartido'] for o in out if o['alerta_resumen_compartido']))}
(OUT / 'etapa3a_resumen.json').write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
print(json.dumps(summ, ensure_ascii=False, indent=2))
