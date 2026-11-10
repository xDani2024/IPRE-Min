"""Recuenta los resultados del cribado y genera las figuras del informe.

Lee el corpus final archivado (05_cierre_revision/salida_archivada: cribado con la revisión humana aplicada
y concordancia de la muestra de validación) y las tablas de 09_descripcion_bibliometrica.py. No altera decisiones ni consulta bases de datos. Usa el mismo
estilo gráfico que 05_descriptivos/24_generar_graficos.py del paquete IPRE_codigo_y_datos_v9.

Uso: py -3 06_descriptivos/10_generar_graficos_informe.py [--cribado RUTA]
Requiere matplotlib (requirements_complementarios.txt).
"""
from pathlib import Path
from collections import Counter
import argparse, csv, json, hashlib, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.ticker import FuncFormatter

csv.field_size_limit(10**9)
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--cribado', type=Path, default=ROOT / '05_cierre_revision/salida_archivada',
                help='Carpeta con 01_corpus_completo_cribado.csv, 06_prisma.json y concordancia_muestra_validacion.json')
args = ap.parse_args()
FIG = HERE / 'graficos_informe'; FIG.mkdir(exist_ok=True)
SOURCE = args.cribado / '01_corpus_completo_cribado.csv'
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8-sig', newline='')))
rows = rd(SOURCE)
PR = json.loads((args.cribado / '06_prisma.json').read_text(encoding='utf-8'))
T = {n: rd(HERE / 'tablas' / f'{n}.csv') for n in ('T00_indicadores_generales', 'T01_produccion_anual', 'T04_revistas',
                                                   'T04b_zonas_bradford', 'T06_paises', 'T09_palabras_clave')}
DESC = json.loads((HERE / 'Resultados_descriptivos.json').read_text(encoding='utf-8'))
acc = [r for r in rows if r['decision_filtro_amplio'] == 'ACEPTADO']
inc = [r for r in rows if r['decision_final'] == 'INCLUIDO']
nuc = [r for r in rows if r['decision_cribado_desempeno'] == 'IN']
NAVY = '#29475F'; GREEN = '#356859'; GRAY = '#B7C0C9'; GOLD = '#D7AE59'; LILAC = '#8B7AA8'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.labelsize': 10, 'figure.facecolor': 'white', 'savefig.facecolor': 'white'})
fmt = lambda n: f'{int(n):,}'.replace(',', '.')
def save(fig, name):
    fig.savefig(FIG / (name + '.png'), dpi=230, bbox_inches='tight', pad_inches=.13); plt.close(fig)

# ---------- recuentos ------------------------------------------------------------
def years(rs):
    y = Counter(int(r['anio_referencia']) for r in rs if r['anio_referencia'].isdigit())
    return {'por_ano': dict(sorted(y.items())), 'antes_2000': sum(n for a, n in y.items() if a < 2000),
            '2000_2025': sum(y[a] for a in range(2000, 2026)), 'posterior_2025': sum(n for a, n in y.items() if a > 2025),
            'sin_ano': sum(not r['anio_referencia'].isdigit() for r in rs)}
regla = Counter(r['regla_cribado_desempeno'].split('+')[0] for r in nuc if r['procedencia_decision'] != 'revision_humana')
amplio_motivos = Counter(m.split(':')[0] for r in rows if r['decision_filtro_amplio'] == 'EXCLUIDO' for m in r['motivo_filtro_amplio'].split('; '))
data = {
 'fecha': '2026-11-09', 'sha256_corpus_cribado': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 'prisma': PR,
 'filtro_amplio': {'aceptadas': len(acc), 'excluidas': len(rows) - len(acc), 'motivos': dict(amplio_motivos.most_common())},
 'nivel1': {'incluidas': len(inc), 'excluidas': len(acc) - len(inc),
            'motivos': dict(Counter(r['motivo_exclusion'].split(':')[0] for r in acc if r['decision_final'] == 'EXCLUIDO').most_common())},
 'procedencia': {f'{d}|{p}': n for (d, p), n in sorted(Counter((r['decision_final'], r['procedencia_decision']) for r in acc).items())},
 'nucleo': {'IN': len(nuc), 'por_regla': dict(regla)},
 'incluidos_por_ano': years(inc), 'nucleo_por_ano': years(nuc),
 'incluidos_revisiones': sum(r['revision_de_literatura'] == 'si' for r in inc),
 'incluidos_sin_resumen': sum('sin_resumen' in r['limitacion_informacion'] for r in inc),
 'revision_humana': dict(Counter(r['limitacion_informacion'] for r in rows if r['procedencia_decision'] == 'revision_humana')),
 'revision_humana_resultado': {'revisadas': sum(r['procedencia_decision'] == 'revision_humana' for r in rows),
     'excluidas': sum(r['procedencia_decision'] == 'revision_humana' and r['decision_final'] == 'EXCLUIDO' for r in rows),
     'nucleo_IN': sum(r['procedencia_decision'] == 'revision_humana' and r['decision_cribado_desempeno'] == 'IN' for r in rows)},
 'concordancia': (json.loads((args.cribado / 'concordancia_muestra_validacion.json').read_text(encoding='utf-8'))
                  if (args.cribado / 'concordancia_muestra_validacion.json').exists() else None),
 'indicadores': {r['indicador']: r['valor'] for r in T['T00_indicadores_generales']},
 'bradford': T['T04b_zonas_bradford'], 'redes': DESC['redes'], 'cobertura': DESC['cobertura_metadatos'],
 'top_revistas': T['T04_revistas'][:10], 'top_paises': T['T06_paises'][:10], 'top_palabras': T['T09_palabras_clave'][:20],
}
(HERE / 'Resultados_informe.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

# ---------- 1 flujo del cribado --------------------------------------------------
fig, ax = plt.subplots(figsize=(7.4, 5.0)); ax.set_xlim(0, 10); ax.set_ylim(-.25, 8.2); ax.axis('off')
def box(x, y, w, h, t, fc='#F4F5F6'):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=.05,rounding_size=.07', edgecolor='#9BA3A9', facecolor=fc, lw=.7))
    ax.text(x + w / 2, y + h / 2, t, ha='center', va='center', fontsize=9.5)
def arrow(a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=12, lw=.8, color='#64717C'))
reg = PR['identificacion']['registros_por_base_en_integracion']; dd = PR['deduplicacion']
box(2.4, 7.0, 5.2, .95, f"Registros integrados {fmt(PR['identificacion']['total_registros_integrados'])}\n"
    f"OpenAlex {fmt(reg['OpenAlex'])} · Scopus {fmt(reg['Scopus'])} · WoS {fmt(reg['WoS'])}")
box(2.5, 5.35, 5.0, .85, f"Publicaciones únicas\n{fmt(dd['publicaciones_unicas'])} ({fmt(dd['duplicados_eliminados'])} duplicados eliminados)", fc='#EAF0F4')
arrow((5, 6.97), (5, 6.25))
box(.4, 3.55, 4, .85, f"Aceptadas por el filtro amplio\n{fmt(len(acc))}", fc='#EAF0F4')
box(5.6, 3.55, 4, .85, f"Excluidas en el filtro amplio\n{fmt(len(rows) - len(acc))}")
arrow((4.4, 5.32), (2.4, 4.43)); arrow((5.6, 5.32), (7.6, 4.43))
box(.4, 1.75, 4, .85, f"Corpus incluido\n{fmt(len(inc))}", fc='#E8F0EC')
box(5.6, 1.75, 4, .85, f"Excluidas por pertinencia\no revisión humana {fmt(len(acc) - len(inc))}")
arrow((2.4, 3.52), (2.4, 2.63)); arrow((3.55, 3.52), (7.6, 2.63))
box(.4, .0, 4, .85, f"Núcleo de desempeño\n{fmt(len(nuc))} IN", fc='#E8F0EC')
box(5.6, .0, 4, .85, f"Incluidas fuera del núcleo\n{fmt(len(inc) - len(nuc))}")
arrow((2.4, 1.72), (2.4, .88)); arrow((3.55, 1.72), (7.6, .88))
save(fig, '01_flujo_del_cribado')

# ---------- 2 motivos de exclusión por pertinencia -------------------------------
LAB = {'F_GEO': 'Geotecnia sin vínculo operacional', 'F_AMB': 'Ambiental, hídrico o cierre', 'F_VIB': 'Efectos de tronadura',
       'F_CTX': 'Contexto distinto del rajo', 'F_ECO': 'Economía, sociedad o política', 'F_OTRO': 'No trata la operación',
       'F_GEOL': 'Geología o recursos', 'F_TELE': 'Teledetección o cartografía', 'F_SEG': 'Seguridad ocupacional general',
       'F_PROC': 'Planta o procesamiento', 'F_SALUD': 'Salud de trabajadores', 'F_COMP': 'Componente sin equipo de mina',
       'F_DOC': 'Sin estudio propio', 'REVISION_HUMANA': 'Revisión humana'}
mot = data['nivel1']['motivos']; keys = list(mot)
fig, ax = plt.subplots(figsize=(7.4, 3.9)); fig.subplots_adjust(left=.36, right=.97)
ax.barh(range(len(keys)), [mot[k] for k in keys], color=GRAY, height=.65)
for i, k in enumerate(keys): ax.text(mot[k] + 18, i, fmt(mot[k]), va='center', fontsize=8.7)
ax.set_yticks(range(len(keys)), [LAB.get(k, k) for k in keys], fontsize=9); ax.invert_yaxis()
ax.set_xlim(0, max(mot.values()) * 1.15); ax.set_xlabel(f'Excluidas después del filtro amplio (N = {fmt(len(acc) - len(inc))})')
ax.grid(axis='x', color='#DDDDDD', lw=.5); ax.set_axisbelow(True); save(fig, '02_motivos_de_exclusion')

# ---------- 3 cómo se formó el núcleo --------------------------------------------
def leidos(fn):
    p = ROOT / '04_integracion_final/entrada/lectura_dirigida' / fn
    return [l for l in p.read_text(encoding='utf-8').splitlines() if l.strip() and not l.startswith('#')]
n_v8_in = regla['I01_TAREA_RESULTADO_EVALUADO']; n_v9_in = regla['I01_EVIDENCIA_OPERACIONAL_EN_FICHA']; n_res = regla['RESCATE_LECTURA_DIRIGIDA']
n_cand = len(leidos('nucleo_rescate_candidatos.txt')); n_v9 = len(leidos('nucleo_v9.txt'))
n_v8 = n_v8_in + len(leidos('nucleo_v8.txt'))
rh = [r for r in rows if r['procedencia_decision'] == 'revision_humana' and r['decision_final'] == 'INCLUIDO']
n_rh_in = sum(r['decision_cribado_desempeno'] == 'IN' for r in rh)
comp = [('IN por regla v8', n_v8_in, n_v8 - n_v8_in), ('TC que v9 propone IN', n_v9_in, n_v9 - n_v9_in),
        ('Control de omisiones', n_res, n_cand - n_res), ('Revisión humana', n_rh_in, len(rh) - n_rh_in)]
data['nucleo']['composicion'] = {k: {'IN': a, 'OUT_tras_lectura': b} for k, a, b in comp}
(HERE / 'Resultados_informe.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
fig, ax = plt.subplots(figsize=(7.4, 3.1)); fig.subplots_adjust(left=.29, right=.98)
for i, (lab, a, b) in enumerate(comp):
    ax.barh(i, a, height=.52, color=GREEN, label='Confirmado IN' if i == 0 else None)
    ax.barh(i, b, left=a, height=.52, color=GRAY, label='OUT tras lectura' if i == 0 else None)
    if a >= 25: ax.text(a / 2, i, fmt(a), ha='center', va='center', color='white', fontsize=10)
    else: ax.text(a + 2, i, fmt(a), ha='left', va='center', color=GREEN, fontsize=10, fontweight='bold')
    if b: ax.text(a + b / 2 + (10 if a < 25 else 0), i, fmt(b), ha='center', va='center', color='#172027', fontsize=10)
ax.set_yticks(range(len(comp)), [c[0] for c in comp]); ax.invert_yaxis()
ax.set_xlabel(f'Casos leídos o revisados por grupo  |  núcleo final = {fmt(len(nuc))} IN'); ax.grid(axis='x', color='#DDDDDD', lw=.5); ax.set_axisbelow(True)
ax.legend(ncol=2, frameon=False, loc='upper center', bbox_to_anchor=(.5, -.28)); save(fig, '03_formacion_del_nucleo')

# ---------- 4 publicaciones por año ----------------------------------------------
fig, axes = plt.subplots(2, 1, figsize=(7.4, 4.05), sharex=True, gridspec_kw={'hspace': .42})
for ax, key, title, col in zip(axes, ['incluidos_por_ano', 'nucleo_por_ano'],
                               [f'Corpus incluido  |  N total = {fmt(len(inc))}', f'Núcleo de desempeño  |  N total = {fmt(len(nuc))}'], [NAVY, GREEN]):
    d = data[key]['por_ano']; ys = list(range(2000, 2026)); ns = [d.get(y, 0) for y in ys]
    ax.bar(ys, ns, color=col, width=.8); ax.set_title(title, loc='left', fontsize=10.5); ax.set_ylabel('Publicaciones')
    ax.grid(axis='y', color='#DDDDDD', lw=.5); ax.set_axisbelow(True)
    ax.text(2025, ns[-1] + max(ns) * .04, str(ns[-1]), ha='center', fontsize=9); ax.set_ylim(0, max(ns) * 1.23)
axes[-1].set_xticks([2000, 2005, 2010, 2015, 2020, 2025]); axes[-1].set_xlabel('Año de publicación  |  2026 y 2027 se informan por separado')
axes[-1].set_xlim(1999.2, 2025.8); save(fig, '04_publicaciones_por_ano')

# ---------- 5 revistas ----------------------------------------------------------
top = T['T04_revistas'][:12]
fig, ax = plt.subplots(figsize=(7.4, 3.9)); fig.subplots_adjust(left=.47, right=.97); ys = list(range(len(top)))
lab = [t['revista'] if len(t['revista']) <= 52 else t['revista'][:50] + '…' for t in top]
for off, key, col, name in [(-.18, 'publicaciones', NAVY, 'Corpus incluido'), (.18, 'nucleo_desempeno_IN', GREEN, 'Núcleo de desempeño')]:
    vals = [int(t[key]) for t in top]; ax.barh([y + off for y in ys], vals, height=.34, color=col, label=name)
    for y, n in zip(ys, vals): ax.text(n + 1, y + off, str(n), va='center', fontsize=8)
ax.set_yticks(ys, lab, fontsize=8.6); ax.invert_yaxis(); ax.set_xlabel('Publicaciones')
ax.grid(axis='x', color='#DDDDDD', lw=.5); ax.set_axisbelow(True)
ax.legend(loc='upper center', bbox_to_anchor=(.3, -.14), ncol=2, frameon=False, fontsize=9); save(fig, '05_revistas_principales')

# ---------- 6 países --------------------------------------------------------------
top = T['T06_paises'][:15]; con_pais = DESC['cobertura_metadatos']['paises_e_instituciones']['con']
fig, ax = plt.subplots(figsize=(7.4, 3.6)); fig.subplots_adjust(left=.12, right=.97)
solo = [int(t['publicaciones_un_solo_pais']) for t in top]; inter = [int(t['publicaciones_colaboracion_internacional']) for t in top]
ax.bar(range(len(top)), solo, color=NAVY, width=.7, label='Un solo país')
ax.bar(range(len(top)), inter, bottom=solo, color=GOLD, width=.7, label='Colaboración internacional')
for i, (a, b) in enumerate(zip(solo, inter)): ax.text(i, a + b + 4, str(a + b), ha='center', fontsize=8.5)
ax.set_xticks(range(len(top)), [t['pais_iso2'] for t in top]); ax.set_ylabel('Publicaciones')
ax.set_xlabel(f'País de afiliación (OpenAlex; {fmt(con_pais)} de {fmt(len(inc))} publicaciones con país)')
ax.grid(axis='y', color='#DDDDDD', lw=.5); ax.set_axisbelow(True); ax.legend(frameon=False, fontsize=9); save(fig, '06_paises')

# ---------- 7 palabras clave -------------------------------------------------------
top = T['T09_palabras_clave'][:18]; keys = [t['palabra_clave'] for t in top]
fig, axes = plt.subplots(1, 2, figsize=(7.4, 4.25), sharey=True, gridspec_kw={'wspace': .30}); fig.subplots_adjust(left=.27, right=.98)
for ax, col_key, col, label in zip(axes, ['publicaciones', 'nucleo_desempeno_IN'], [NAVY, GREEN], ['Corpus incluido', 'Núcleo de desempeño']):
    vals = [int(t[col_key]) for t in top]; ax.barh(range(len(keys)), vals, color=col, height=.65)
    ax.set_title(label, loc='left', fontsize=9.8); ax.set_xlim(0, max(vals) * 1.22)
    for i, n in enumerate(vals): ax.text(n + max(vals) * .025, i, fmt(n), va='center', fontsize=8.7)
    ax.grid(axis='x', color='#DDDDDD', lw=.5); ax.set_axisbelow(True); ax.set_xlabel('Publicaciones con la palabra clave')
axes[0].set_yticks(range(len(keys)), keys, fontsize=9); axes[0].invert_yaxis(); save(fig, '07_palabras_clave')

# ---------- 8 procedencia de las decisiones ---------------------------------------
fig, ax = plt.subplots(figsize=(7.4, 2.35)); fig.subplots_adjust(left=.29, right=.98)
pc = Counter((r['decision_final'], r['procedencia_decision']) for r in acc)
for i, dec in enumerate(['INCLUIDO', 'EXCLUIDO']):
    left = 0
    for p, col, name in [('regla_confirmada_por_lectura_de_titulo', NAVY, 'Regla confirmada por título'),
                         ('lectura_dirigida_titulo_resumen', LILAC, 'Lectura dirigida de título y resumen'),
                         ('revision_humana', GOLD, 'Revisión humana')]:
        n = pc.get((dec, p), 0); ax.barh(i, n, left=left, height=.5, color=col, label=name if i == 0 else None)
        if n > 150: ax.text(left + n / 2, i, fmt(n), ha='center', va='center', fontsize=10, color='white' if col != GOLD else '#172027')
        left += n
ax.set_yticks([0, 1], ['Incluidas', 'Excluidas después\ndel filtro amplio']); ax.invert_yaxis()
ax.set_xlabel(f'Decisiones posteriores al filtro amplio (N = {fmt(len(acc))})'); ax.grid(axis='x', color='#DDDDDD', lw=.5); ax.set_axisbelow(True)
ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: fmt(x)))
ax.legend(ncol=3, frameon=False, loc='upper center', bbox_to_anchor=(.42, -.38), fontsize=8.5); save(fig, '08_procedencia_de_decisiones')
print('Recuentos y ocho gráficos del informe generados. Incluidos:', len(inc), '| núcleo:', len(nuc))
