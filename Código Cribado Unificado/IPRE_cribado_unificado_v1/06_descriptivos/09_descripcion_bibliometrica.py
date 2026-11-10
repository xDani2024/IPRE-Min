"""Etapa 6: descripción bibliométrica del corpus incluido.

Tablas, redes y resumen usan solo la biblioteca estándar. Las figuras (matplotlib) y el libro
Excel (openpyxl) son opcionales: si falta el paquete se omiten y se informa.

Entradas
  - corpus final con la revisión humana aplicada (05_cierre_revision/salida o salida_archivada); acepta el
    corpus completo (se filtran las INCLUIDO) o el archivo de incluidas;
  - universos por base, en las rutas registradas por la integración (08_resumen_validacion.json):
    autores, países e instituciones (solo OpenAlex), palabras clave de autor (Scopus y WoS) y citas.

Salidas (por defecto en esta carpeta)
  tablas/T*.csv                      indicadores, producción anual, tipos, bases, revistas y zonas de Bradford,
                                     autores, países, instituciones, más citadas, palabras clave y su normalización
  redes/R*_map.txt, R*_network.txt   co-ocurrencia de palabras clave, coautoría y colaboración entre países (VOSviewer)
  redes/R*.graphml                   mismas redes para Gephi
  graficos/F*.png                    producción anual, revistas, países y palabras clave (opcional)
  descripcion_bibliometrica.xlsx     todas las tablas en un libro (opcional)
  Resultados_descriptivos.json       cifras clave, cobertura de cada metadato y decisiones de normalización

Uso: py -3 06_descriptivos/09_descripcion_bibliometrica.py [--corpus RUTA] [--proyecto RUTA] [--config RUTA] [--salida RUTA]
"""
import argparse, csv, json, re, sys, unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from xml.sax.saxutils import escape

csv.field_size_limit(10**9)
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
def buscar_proyecto(p):
    if p: return Path(p).resolve()
    for d in ROOT.parents:
        if (d / 'integracion_corpus/resultados_validados/universo').is_dir(): return d
    sys.exit('No se encontró IPRE-Min-main (carpeta con integracion_corpus/). Indíquela con --proyecto.')
def corpus_por_defecto():
    """Corpus final: el de la última ejecución del cierre o, si no existe, el archivado con la revisión humana aplicada."""
    for c in (ROOT / '05_cierre_revision/salida/01_corpus_completo_cribado.csv',
              ROOT / '05_cierre_revision/salida_archivada/01_corpus_completo_cribado.csv'):
        if c.exists(): return c
    return ROOT / '04_integracion_final/salida/02_corpus_incluido.csv'

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--corpus', type=Path)
ap.add_argument('--proyecto')
ap.add_argument('--config', type=Path, default=HERE / 'config_descriptivos.json')
ap.add_argument('--salida', type=Path, default=HERE)
args = ap.parse_args()
INC = (args.corpus or corpus_por_defecto()).resolve()
PROJ, OUT = buscar_proyecto(args.proyecto), args.salida.resolve()
CFG = json.loads(args.config.read_text(encoding='utf-8'))
for d in ('tablas', 'graficos', 'redes'): (OUT / d).mkdir(parents=True, exist_ok=True)
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8-sig', newline='')))
def write_csv(path, rows, fields=None):
    fields = fields or (list(rows[0]) if rows else ['sin_datos'])
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fields); w.writeheader(); w.writerows(rows)

# ---------------------------------------------------------------------------------
# 1. Carga y enlace con los registros de cada base
# ---------------------------------------------------------------------------------
VAL = json.loads((PROJ / 'integracion_corpus/resultados_validados/universo/08_resumen_validacion.json').read_text(encoding='utf-8'))
INCL = [r for r in rd(INC) if r.get('decision_final', 'INCLUIDO') == 'INCLUIDO']  # acepta 01 (completo) o 02 (incluidos)
SRC = {b: rd(PROJ / v['ruta'].replace('\\', '/')) for b, v in VAL['entradas'].items()}
IDX = {'OpenAlex': {r['openalex_id'].rsplit('/', 1)[-1]: r for r in SRC['OpenAlex']},
       'Scopus': {r['scopus_id']: r for r in SRC['Scopus']},
       'WoS': {r['wos_id']: r for r in SRC['WoS']}}
COLID = {'OpenAlex': 'identificadores_openalex', 'Scopus': 'identificadores_scopus', 'WoS': 'identificadores_wos'}
def ids(r, b): return [x.strip().rsplit('/', 1)[-1] for x in r[COLID[b]].split('|') if x.strip()]
REC, missing = {}, 0
for r in INCL:
    recs = {}
    for b in IDX:
        found = [IDX[b][i] for i in ids(r, b) if i in IDX[b]]
        missing += len(ids(r, b)) - len(found)
        if found: recs[b] = found
    REC[r['id_publicacion']] = recs

def ascii_fold(s): return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
def key(s): return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', ascii_fold(s).lower().replace('-', ' '))).strip()

# ---------------------------------------------------------------------------------
# 2. Campos derivados por publicación
# ---------------------------------------------------------------------------------
ANON = {key(a) for a in CFG['autores_anonimos']}
SPELL = {key(k): key(v) for k, v in CFG['variantes_ortograficas'].items()}
EXCL = {key(k) for k in CFG['palabras_clave_de_contexto_excluidas']}
CTX_T, CTX_REQ = set(CFG['tokens_de_contexto']), set(CFG['tokens_de_contexto_obligatorios'])
def is_context(k):
    t = set(k.split()); return k in EXCL or (t <= CTX_T and bool(t & CTX_REQ))

def year(r):
    try: return int(r['anio_referencia'])
    except ValueError: return None
def doctype(r):
    t = r['tipo_documento'].lower()
    return 'review' if 'review' in t else ('article' if 'article' in t else t or 'sin_tipo')

def authors(pid):
    """Lista 'apellido i' tomada de Scopus > WoS > OpenAlex (formato más estable primero)."""
    recs = REC[pid]
    if 'Scopus' in recs and recs['Scopus'][0]['authors']:
        out = []
        for a in (x.strip() for x in recs['Scopus'][0]['authors'].split(';')):
            if not a: continue
            m = re.match(r'^(.*?)\s+((?:[A-Z][a-z]?\.?-?\s?)+)$', a)
            sur, ini = (m.group(1), m.group(2)) if m else (a, '')
            out.append((key(sur) + ' ' + key(ini)[:1]).strip())
        return out, 'Scopus'
    if 'WoS' in recs and recs['WoS'][0]['authors']:
        out = []
        for a in recs['WoS'][0]['authors'].split(';'):
            if not a.strip(): continue
            sur, _, ini = a.partition(','); out.append((key(sur) + ' ' + key(ini)[:1]).strip())
        return out, 'WoS'
    if 'OpenAlex' in recs and recs['OpenAlex'][0]['authors']:
        out = []
        for a in recs['OpenAlex'][0]['authors'].split(';'):
            t = key(a).split()
            if t: out.append((t[-1] + ' ' + t[0][:1]) if len(t) > 1 else t[0])
        return out, 'OpenAlex'
    return [], ''

def author_keywords(pid):
    """Palabras clave de autor de Scopus y WoS (OpenAlex no entrega palabras clave de autor)."""
    kws, src = set(), []
    for b, sep in (('Scopus', '|'), ('WoS', ';')):
        for rec in REC[pid].get(b, []):
            vals = [key(k) for k in rec['keywords'].split(sep) if key(k)]
            if vals: src.append(b)
            for k in vals:
                k = ' '.join(SPELL.get(t, t) for t in k.split()); kws.add(SPELL.get(k, k))
    return kws, src

D = []
for r in INCL:
    pid = r['id_publicacion']; recs = REC[pid]
    au, au_src = authors(pid)
    au = list(dict.fromkeys(a for a in au if a and a not in ANON and a.split()[0] not in ANON))
    kws, kw_src = author_keywords(pid)
    oa = recs.get('OpenAlex', [None])[0]
    cites = {b: max(int(x['cited_by'] or 0) for x in v) for b, v in recs.items() if any(x.get('cited_by', '') != '' for x in v)}
    D.append({'id': pid, 'titulo': r['titulo'], 'anio': year(r), 'tipo': doctype(r), 'revista': r['revista'],
              'revista_key': key(r['revista']), 'fuentes': r['fuentes'], 'doi': r['doi'],
              'nucleo': r['decision_cribado_desempeno'] == 'IN', 'revision': r['revision_de_literatura'] == 'si',
              'autores': au, 'autores_fuente': au_src, 'kw_raw': kws, 'kw_fuente': kw_src,
              'paises': sorted({c.strip() for c in (oa['countries'].split(';') if oa else []) if c.strip()}),
              'instituciones': sorted({i.strip() for i in (oa['institutions'].split(';') if oa else []) if i.strip()}),
              'citas_max': max(cites.values()) if cites else None, 'citas': cites})

vocab = Counter(k for d in D for k in d['kw_raw'])
def singular(k):
    if k.endswith('ies') and k[:-3] + 'y' in vocab: return k[:-3] + 'y'
    if k.endswith('s') and not k.endswith('ss') and k[:-1] in vocab: return k[:-1]
    return k
for d in D: d['kw'] = sorted(k for k in {singular(k) for k in d['kw_raw']} if not is_context(k))

lab = defaultdict(Counter)
for d in D: lab[d['revista_key']][d['revista']] += 1
def journal_label(k):
    c = lab[k]; good = [v for v, _ in c.most_common() if v and not v.isupper()]
    return good[0] if good else (c.most_common(1)[0][0].title() if c else '')

# ---------------------------------------------------------------------------------
# 3. Tablas
# ---------------------------------------------------------------------------------
T = {}
N = len(D); years = [d['anio'] for d in D if d['anio']]
y0, y1, ymax = min(years), CFG['anio_ultimo_completo'], max(years)
pa = Counter(years)
def cagr(a, b):
    return round(((pa[b] / pa[a]) ** (1 / (b - a)) - 1) * 100, 2) if pa.get(a) and pa.get(b) and b > a else 'no calculable'

prod, acc = [], 0
for y in range(y0, ymax + 1):
    sub = [d for d in D if d['anio'] == y]; acc += len(sub)
    prod.append({'anio': y, 'publicaciones': len(sub), 'nucleo_desempeno_IN': sum(d['nucleo'] for d in sub),
                 'en_OpenAlex': sum('OpenAlex' in d['fuentes'] for d in sub), 'en_Scopus': sum('Scopus' in d['fuentes'] for d in sub),
                 'en_WoS': sum('WoS' in d['fuentes'] for d in sub), 'acumulado': acc})
T['T01_produccion_anual'] = prod
T['T02_tipo_documento'] = [{'tipo': k, 'publicaciones': v, 'porcentaje': round(100 * v / N, 1),
    'nucleo_desempeno_IN': sum(d['nucleo'] for d in D if d['tipo'] == k)} for k, v in Counter(d['tipo'] for d in D).most_common()]
T['T03_bases_de_origen'] = ([{'combinacion_de_bases': k, 'publicaciones': v, 'porcentaje': round(100 * v / N, 1)}
    for k, v in Counter(d['fuentes'] for d in D).most_common()] +
    [{'combinacion_de_bases': f'Total con {b}', 'publicaciones': n, 'porcentaje': round(100 * n / N, 1)}
     for b in ('OpenAlex', 'Scopus', 'WoS') for n in [sum(b in d['fuentes'] for d in D)]])

jc = Counter(d['revista_key'] for d in D if d['revista_key'])
jn = Counter(d['revista_key'] for d in D if d['revista_key'] and d['nucleo'])
jcit = Counter()
for d in D:
    if d['revista_key'] and d['citas_max']: jcit[d['revista_key']] += d['citas_max']
tot, cum, zone = sum(jc.values()), 0, {}
for k, v in jc.most_common():   # Bradford: tres zonas con un tercio de los artículos cada una
    zone[k] = 1 if cum < tot / 3 else (2 if cum < 2 * tot / 3 else 3); cum += v
T['T04_revistas'] = [{'revista': journal_label(k), 'publicaciones': v, 'porcentaje': round(100 * v / N, 2),
    'nucleo_desempeno_IN': jn[k], 'citas_totales': jcit[k], 'zona_bradford': zone[k]} for k, v in jc.most_common()]
T['T04b_zonas_bradford'] = [{'zona': z, 'revistas': sum(1 for k in zone if zone[k] == z),
    'publicaciones': sum(jc[k] for k in zone if zone[k] == z)} for z in (1, 2, 3)]

ac = Counter(a for d in D for a in d['autores']); acit = Counter(); anuc = Counter()
for d in D:
    for a in d['autores']: acit[a] += d['citas_max'] or 0; anuc[a] += d['nucleo']
T['T05_autores'] = [{'autor_normalizado': a, 'publicaciones': v, 'nucleo_desempeno_IN': anuc[a], 'citas_totales': acit[a]}
                    for a, v in ac.most_common(CFG['top_n_tablas'] * 3)]

with_c = [d for d in D if d['paises']]
pc = Counter(c for d in with_c for c in d['paises']); single = Counter(d['paises'][0] for d in with_c if len(d['paises']) == 1)
T['T06_paises'] = [{'pais_iso2': c, 'publicaciones': v, 'porcentaje_sobre_con_pais': round(100 * v / len(with_c), 1),
    'publicaciones_un_solo_pais': single[c], 'publicaciones_colaboracion_internacional': v - single[c]} for c, v in pc.most_common()]
T['T07_instituciones'] = [{'institucion': i, 'publicaciones': v}
                          for i, v in Counter(i for d in D for i in d['instituciones']).most_common(CFG['top_n_tablas'])]
cit = sorted([d for d in D if d['citas_max'] is not None], key=lambda d: (-d['citas_max'], d['id']))
T['T08_mas_citadas'] = [{'titulo': d['titulo'], 'anio': d['anio'], 'revista': d['revista'], 'doi': d['doi'],
    'citas_max': d['citas_max'], 'citas_OpenAlex': d['citas'].get('OpenAlex', ''), 'citas_Scopus': d['citas'].get('Scopus', ''),
    'citas_WoS': d['citas'].get('WoS', ''), 'nucleo_desempeno_IN': d['nucleo']} for d in cit[:CFG['top_n_tablas']]]
kc = Counter(k for d in D for k in d['kw']); knuc = Counter(k for d in D if d['nucleo'] for k in d['kw'])
T['T09_palabras_clave'] = [{'palabra_clave': k, 'publicaciones': v, 'nucleo_desempeno_IN': knuc[k]}
                           for k, v in kc.most_common(CFG['top_n_tablas'] * 2)]
T['T09b_normalizacion_palabras_clave'] = [{'forma_inicial': k, 'forma_final': singular(k),
    'excluida_por_contexto': is_context(singular(k)), 'frecuencia': vocab[k]} for k in sorted(vocab)]

with_kw = [d for d in D if d['kw_fuente']]
cites_all = sorted(d['citas_max'] for d in D if d['citas_max'] is not None)
n_auth = [len(d['autores']) for d in D if d['autores']]
ind = [('Publicaciones incluidas', N), ('Núcleo de desempeño (IN)', sum(d['nucleo'] for d in D)),
 ('Periodo', f'{y0}–{ymax}'), ('Sin año', N - len(years)),
 *[(f'Tasa de crecimiento anual compuesta {a}–{b} (%)', cagr(a, b)) for a, b in CFG['ventanas_crecimiento']],
 (f'Publicaciones con año posterior a {y1} (año en curso o en prensa)', sum(1 for y in years if y > y1)),
 ('Revistas o fuentes distintas', len(jc)), ('Revistas en zona 1 de Bradford', T['T04b_zonas_bradford'][0]['revistas']),
 ('Autores distintos (normalizados)', len(ac)), ('Autores por publicación (media)', round(sum(n_auth) / len(n_auth), 2)),
 ('Publicaciones de autoría única', sum(1 for x in n_auth if x == 1)),
 ('Publicaciones con país (OpenAlex)', len(with_c)), ('Cobertura de país (%)', round(100 * len(with_c) / N, 1)),
 ('Colaboración internacional sobre publicaciones con país (%)', round(100 * sum(len(d['paises']) > 1 for d in with_c) / len(with_c), 1) if with_c else ''),
 ('Publicaciones con palabras clave de autor (Scopus/WoS)', len(with_kw)), ('Cobertura de palabras clave de autor (%)', round(100 * len(with_kw) / N, 1)),
 ('Palabras clave distintas (normalizadas, sin términos de contexto)', len(kc)),
 ('Citas: media por publicación (máximo entre bases)', round(sum(cites_all) / len(cites_all), 2) if cites_all else ''),
 ('Citas: mediana', cites_all[len(cites_all) // 2] if cites_all else ''),
 ('Revisiones de literatura', sum(d['revision'] for d in D)),
 ('Identificadores de base no encontrados en los universos', missing)]
T['T00_indicadores_generales'] = [{'indicador': k, 'valor': v} for k, v in ind]
for name, rows in T.items(): write_csv(OUT / 'tablas' / f'{name}.csv', rows)

# ---------------------------------------------------------------------------------
# 4. Redes (VOSviewer: map + network; GraphML para Gephi)
# ---------------------------------------------------------------------------------
def components(nodes, edges):
    parent = {n: n for n in nodes}
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in edges: parent[find(a)] = find(b)
    return len({find(n) for n in nodes})

def network(name, docs_items, min_docs):
    occ = Counter(i for items in docs_items for i in set(items))
    keep = {i for i, v in occ.items() if v >= min_docs}
    links = Counter()
    for items in docs_items:
        for a, b in combinations(sorted(set(items) & keep), 2): links[(a, b)] += 1
    nodes = sorted(keep, key=lambda i: (-occ[i], i)); nid = {n: j + 1 for j, n in enumerate(nodes)}
    edges = sorted(links.items(), key=lambda x: (nid[x[0][0]], nid[x[0][1]]))
    with open(OUT / 'redes' / f'{name}_map.txt', 'w', encoding='utf-8', newline='\n') as f:
        f.write('id\tlabel\tweight<Documentos>\n')
        for n in nodes: f.write(f'{nid[n]}\t{n}\t{occ[n]}\n')
    with open(OUT / 'redes' / f'{name}_network.txt', 'w', encoding='utf-8', newline='\n') as f:
        for (a, b), w in edges: f.write(f'{nid[a]}\t{nid[b]}\t{w}\n')
    with open(OUT / 'redes' / f'{name}.graphml', 'w', encoding='utf-8', newline='\n') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n'
                '  <key id="label" for="node" attr.name="label" attr.type="string"/>\n'
                '  <key id="documentos" for="node" attr.name="documentos" attr.type="int"/>\n'
                '  <key id="weight" for="edge" attr.name="weight" attr.type="int"/>\n  <graph edgedefault="undirected">\n')
        for n in nodes:
            f.write(f'    <node id="n{nid[n]}"><data key="label">{escape(n)}</data><data key="documentos">{occ[n]}</data></node>\n')
        for (a, b), w in edges: f.write(f'    <edge source="n{nid[a]}" target="n{nid[b]}"><data key="weight">{w}</data></edge>\n')
        f.write('  </graph>\n</graphml>\n')
    return {'nodos': len(nodes), 'enlaces': len(edges), 'umbral_documentos': min_docs,
            'componentes': components(nodes, links) if nodes else 0}

nets = {'R1_coocurrencia_palabras_clave': network('R1_coocurrencia_palabras_clave', [d['kw'] for d in D if d['kw']], CFG['red_palabras_clave_min_documentos']),
        'R2_coautoria': network('R2_coautoria', [d['autores'] for d in D if d['autores']], CFG['red_coautoria_min_documentos']),
        'R3_colaboracion_paises': network('R3_colaboracion_paises', [d['paises'] for d in D if d['paises']], CFG['red_paises_min_documentos'])}

# ---------------------------------------------------------------------------------
# 5. Figuras y libro Excel (opcionales)
# ---------------------------------------------------------------------------------
opcionales = {}
try:
    import matplotlib
    matplotlib.use('Agg'); import matplotlib.pyplot as plt
    INK, INK2, GRID, S1, S2 = '#0b0b0b', '#52514e', '#e4e3df', '#2a78d6', '#eb6834'
    plt.rcParams.update({'font.size': 9, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2, 'xtick.color': INK2,
                         'ytick.color': INK2, 'axes.spines.top': False, 'axes.spines.right': False, 'figure.dpi': 150})
    def hbar(labels, values, title, fname):
        fig, ax = plt.subplots(figsize=(7.5, 0.32 * len(labels) + 1.2)); pos = list(range(len(labels)))[::-1]
        ax.barh(pos, values, color=S1, height=0.7, edgecolor='white', linewidth=1)
        ax.set_yticks(pos); ax.set_yticklabels(labels)
        for i, v in zip(pos, values): ax.text(v, i, f' {v}', va='center', color=INK2, fontsize=8)
        ax.set_xlabel('Publicaciones'); ax.set_title(title, loc='left', color=INK, fontsize=10)
        ax.xaxis.grid(True, color=GRID, linewidth=0.6); ax.set_axisbelow(True)
        fig.tight_layout(); fig.savefig(OUT / 'graficos' / fname); plt.close(fig)
    desde = CFG.get('figura_produccion_desde', y0); early = sum(1 for y in years if y < desde)
    xs = [p['anio'] for p in prod]; nuc = [p['nucleo_desempeno_IN'] for p in prod]
    resto = [p['publicaciones'] - p['nucleo_desempeno_IN'] for p in prod]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.bar(xs, nuc, color=S2, width=0.8, edgecolor='white', linewidth=0.6, label='Núcleo de desempeño (IN)')
    ax.bar(xs, resto, bottom=nuc, color=S1, width=0.8, edgecolor='white', linewidth=0.6, label='Resto del corpus incluido')
    ax.set_xlim(desde - 1, ymax + 1); ax.set_ylabel('Publicaciones')
    ax.set_title(f'Producción anual del corpus incluido (n = {N}' + (f'; {early} anteriores a {desde} no graficadas' if early else '') + ')',
                 loc='left', color=INK, fontsize=10)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6); ax.set_axisbelow(True); ax.legend(frameon=False, loc='upper left')
    if ymax > y1:
        ax.axvspan(y1 + 0.5, ymax + 0.5, color=GRID, alpha=0.6, lw=0, zorder=0)
        ax.text(y1 + 0.3, ax.get_ylim()[1] * 0.99, f'{y1 + 1}–{ymax}: año en curso o en prensa', fontsize=7, color=INK2, va='top', ha='right')
    fig.tight_layout(); fig.savefig(OUT / 'graficos' / 'F01_produccion_anual.png'); plt.close(fig)
    k = CFG['top_n_figuras']
    hbar([r['revista'] if len(r['revista']) <= 70 else r['revista'][:68] + '…' for r in T['T04_revistas'][:k]],
         [r['publicaciones'] for r in T['T04_revistas'][:k]], f'Revistas con más publicaciones (top {k})', 'F02_revistas_top.png')
    hbar([r['pais_iso2'] for r in T['T06_paises'][:k]], [r['publicaciones'] for r in T['T06_paises'][:k]],
         f'Países con más publicaciones (top {k}; {len(with_c)} publicaciones con país, OpenAlex)', 'F03_paises_top.png')
    hbar([r['palabra_clave'] for r in T['T09_palabras_clave'][:20]], [r['publicaciones'] for r in T['T09_palabras_clave'][:20]],
         f'Palabras clave de autor más frecuentes (top 20; {len(with_kw)} publicaciones con palabras clave)', 'F04_palabras_clave_top.png')
    opcionales['graficos'] = 'generados'
except ImportError:
    opcionales['graficos'] = 'omitidos: falta matplotlib (requirements_complementarios.txt)'
try:
    from openpyxl import Workbook
    wb = Workbook(); wb.remove(wb.active)
    for name in sorted(T):
        ws = wb.create_sheet(name[:31]); rows = T[name]
        if rows:
            ws.append(list(rows[0]))
            for r in rows: ws.append(list(r.values()))
    wb.save(OUT / 'descripcion_bibliometrica.xlsx'); opcionales['libro_excel'] = 'generado'
except ImportError:
    opcionales['libro_excel'] = 'omitido: falta openpyxl (requirements_complementarios.txt)'

# ---------------------------------------------------------------------------------
# 6. Resumen
# ---------------------------------------------------------------------------------
summary = {
 'corpus_de_entrada': 'corpus final con revisión humana' if 'cierre' in str(INC.parent) else 'integración (sin revisión humana aplicada)',
 'publicaciones': N, 'indicadores': dict(ind),
 'cobertura_metadatos': {
   'autores_por_fuente': dict(Counter(d['autores_fuente'] or 'sin_autores' for d in D).most_common()),
   'palabras_clave_de_autor': {'con': len(with_kw), 'fuente': 'Scopus y WoS (OpenAlex no entrega palabras clave de autor)'},
   'paises_e_instituciones': {'con': len(with_c), 'fuente': 'solo OpenAlex; los universos de Scopus y WoS no traen afiliaciones'},
   'citas': 'máximo entre bases; las fechas de extracción de cada base difieren'},
 'redes': nets,
 'decisiones_de_normalizacion': {
   'autores': 'apellido + inicial del primer nombre, sin tildes; prioridad Scopus > WoS > OpenAlex; se omiten autores anónimos. Puede unir homónimos o separar variantes de apellidos compuestos.',
   'palabras_clave': 'minúsculas, sin tildes ni guiones, variantes ortográficas de la configuración, plural->singular si ambas formas existen; se excluyen términos que solo describen el contexto de la búsqueda. Detalle en T09b.',
   'revistas': 'agrupadas por nombre normalizado; etiqueta = variante más frecuente que no esté en mayúsculas.'},
 'opcionales': opcionales}
(OUT / 'Resultados_descriptivos.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
print('Descriptivos:', N, 'publicaciones |', ' | '.join(f"{k}: {v['nodos']} nodos" for k, v in nets.items()), '|', opcionales)
