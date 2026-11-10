"""Etapas 1 y 2: revisión del corpus unificado y filtro amplio original.

- Carga el corpus unificado (15.297) y su procedencia (24.152 registros).
- Construye, por publicación, los campos que espera screen_record() del código
  original OpenAlex (title, abstract, keywords, topics, concepts, type, language).
- Aplica screen_record() SIN MODIFICAR, importado del archivo original
  02_filtrar_y_unificar.py.
- Coteja la decisión con el estado histórico de filtro de los registros OpenAlex.

Uso: py -3 01_filtro_amplio/01_aplicar_filtro_amplio.py [--proyecto RUTA] [--motores RUTA] [--salida RUTA]
"""
import csv, json, re, sys, hashlib, importlib.util
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
ap.add_argument('--proyecto', help='Carpeta IPRE-Min-main (por defecto se busca hacia arriba).')
ap.add_argument('--motores', type=Path, default=ROOT / 'motores_originales')
ap.add_argument('--salida', type=Path, default=HERE / 'salida')
args = ap.parse_args()
PROJ, CODE, OUT = buscar_proyecto(args.proyecto), args.motores.resolve(), args.salida.resolve()
OUT.mkdir(parents=True, exist_ok=True)

ORIG = CODE / '01_extraccion_y_filtro/02_filtrar_y_unificar.py'
spec = importlib.util.spec_from_file_location('filtro_original', ORIG)
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)

UNI = PROJ / 'integracion_corpus/resultados_validados/universo/01_corpus_unificado_identidad.csv'
PRO = PROJ / 'integracion_corpus/resultados_validados/universo/02_procedencia_registros.csv'
VAL = json.loads((PROJ / 'integracion_corpus/resultados_validados/universo/08_resumen_validacion.json').read_text(encoding='utf-8'))
OAU = PROJ / VAL['entradas']['OpenAlex']['ruta'].replace('\\', '/')  # misma instantánea usada por la integración

def read(p):
    with open(p, encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

U = read(UNI); P = read(PRO); OA = {r['openalex_id']: r for r in read(OAU)}
assert len(U) == 15297 and len({u['id_publicacion'] for u in U}) == 15297
assert len(P) == 24152
grp = defaultdict(list)
for p in P: grp[p['id_publicacion']].append(p)
assert set(grp) == {u['id_publicacion'] for u in U}

def nonlatin(s): return bool(s) and sum(ord(c) > 591 for c in s) > len(s) * 0.3
def uniq_join(vals, sep='; '):
    seen = []; low = set()
    for v in vals:
        for t in re.split(r'\s*[;|]\s*', v or ''):
            t = t.strip()
            if t and t.lower() not in low: low.add(t.lower()); seen.append(t)
    return sep.join(seen)

ENG = {'en', 'english'}
records = []; diag = Counter()
for u in U:
    ps = grp[u['id_publicacion']]
    title = u['titulo']; title_src = 'unificado'
    if nonlatin(title):
        alt = next((p['titulo'] for p in ps if p['titulo'] and not nonlatin(p['titulo'])), '')
        if alt: title, title_src = alt, 'alternativa_latina_otra_base'; diag['titulo_alternativo'] += 1
    abstract = u['resumen']; abs_src = u['fuente_resumen'] or ''
    if not abstract.strip():
        alt = next((p for p in ps if p['resumen'].strip()), None)
        if alt: abstract, abs_src = alt['resumen'], alt['registro_uid']; diag['resumen_recuperado'] += 1
    elif nonlatin(abstract):
        alt = next((p for p in ps if p['resumen'].strip() and not nonlatin(p['resumen'])), None)
        if alt: abstract, abs_src = alt['resumen'], alt['registro_uid']; diag['resumen_alternativo_latino'] += 1
    oa_ids = ['https://openalex.org/' + x if not x.startswith('http') else x
              for x in re.split(r'[;|]\s*', u['identificadores_openalex']) if x.strip()]
    concepts = uniq_join([OA[i]['concepts'] for i in oa_ids if i in OA])
    topics = uniq_join([p['topics'] for p in ps])
    keywords = uniq_join([u['palabras_clave']] + [p['palabras_clave'] for p in ps])
    langs = sorted({(p['idioma'] or '').strip().lower() for p in ps if p['idioma']})
    lang = 'en' if (set(langs) & ENG) else (langs[0] if langs else '')
    types = sorted({(p['tipo_documento'] or '').strip() for p in ps if p['tipo_documento']})
    is_review = any(t.lower().startswith('review') for t in types)
    hist = sorted({p['estado_filtro_fuente'] for p in ps if p['fuente'] == 'OpenAlex' and p['estado_filtro_fuente']})
    rec = {
        'id_publicacion': u['id_publicacion'], 'title': title, 'abstract': abstract,
        'keywords': keywords, 'topics': topics, 'concepts': concepts,
        'type': 'review' if is_review else 'article', 'tipos_fuente': ' | '.join(types),
        'language': lang, 'retrieval_branches': '', 'quality_flags': '',
        'titulo_cribado_origen': title_src, 'resumen_cribado_origen': abs_src,
        'tiene_resumen': 'si' if abstract.strip() else 'no',
        'filtro_amplio_historico_openalex': '|'.join(hist),
    }
    records.append(rec)

# Filtro amplio con la función original sin cambios.
rows = []
for rec in records:
    inc, ann = F.screen_record(rec)
    # Sensibilidad: misma regla sin el campo concepts (solo existe en OpenAlex).
    inc_nc, ann_nc = F.screen_record({**rec, 'concepts': ''})
    rows.append({**rec,
        'decision_filtro_amplio': 'ACEPTADO' if inc else 'EXCLUIDO',
        'motivo_filtro_amplio': ann['auto_screen_reasons'],
        'senales_operacionales_filtro': ann['operational_signals'],
        'frases_contexto_detectadas': ann['matched_open_pit_phrases'],
        'etiquetas_proceso_auto': ann['auto_process_tags'],
        'etiquetas_equipo_auto': ann['auto_equipment_tags'],
        'etiquetas_foco_auto': ann['auto_focus_tags'],
        'sensibilidad_sin_concepts': 'ACEPTADO' if inc_nc else 'EXCLUIDO'})

fields = list(rows[0])
with open(OUT / 'etapa2_filtro_amplio.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fields); w.writeheader(); w.writerows(rows)

cmp = Counter((r['filtro_amplio_historico_openalex'], r['decision_filtro_amplio']) for r in rows
              if r['filtro_amplio_historico_openalex'])
summary = {
    'publicaciones': len(rows),
    'diagnostico_campos': dict(diag),
    'sin_resumen_tras_recuperacion': sum(r['tiene_resumen'] == 'no' for r in rows),
    'filtro_amplio': dict(Counter(r['decision_filtro_amplio'] for r in rows)),
    'filtro_amplio_sin_concepts': dict(Counter(r['sensibilidad_sin_concepts'] for r in rows)),
    'decisiones_que_dependen_de_concepts': sum(r['decision_filtro_amplio'] != r['sensibilidad_sin_concepts'] for r in rows),
    'coteja_con_historico_openalex(hist,nuevo)': {f'{a}->{b}': n for (a, b), n in cmp.items()},
    'motivos_exclusion': dict(Counter(m.split(':')[0] for r in rows if r['decision_filtro_amplio'] == 'EXCLUIDO'
                                       for m in r['motivo_filtro_amplio'].split('; '))),
    'sha256_codigo_original': sha(ORIG), 'sha256_corpus_unificado': sha(UNI), 'sha256_procedencia': sha(PRO),
}
(OUT / 'etapa2_resumen.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
print(json.dumps(summary, ensure_ascii=False, indent=2))
