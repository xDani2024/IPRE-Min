"""Etapa 6: planillas de cierre del cribado.

1) 01_revision_humana_86.xlsx  -> casos con requiere_revision_humana = si (con la decisión automática visible).
2) 02_muestra_validacion_ciega.xlsx -> muestra aleatoria estratificada, SIN la decisión automática.
   03_clave_muestra_validacion.csv  -> decisión automática de la muestra (no abrir antes de revisar).

Requiere openpyxl (requirements_complementarios.txt). Por seguridad no sobrescribe planillas existentes:
si ya están completadas, use --salida en otra carpeta o --sobrescribir.
Uso: py -3 05_cierre_revision/07_preparar_planillas.py [--entrada RUTA] [--salida RUTA] [--n-por-estrato 25] [--semilla 20261109]
"""
import argparse, csv, json, random, re, sys
from collections import defaultdict
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

csv.field_size_limit(10**9)
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--entrada', type=Path, default=ROOT / '04_integracion_final/salida', help='Carpeta con 01_corpus_completo_cribado.csv')
ap.add_argument('--filtro', type=Path, default=ROOT / '01_filtro_amplio/salida', help='Carpeta con etapa2_filtro_amplio.csv (resúmenes usados en el cribado)')
ap.add_argument('--traducciones', type=Path, default=HERE / 'entrada/traducciones_es.json', help='Traducciones al español (entrada congelada; opcional)')
ap.add_argument('--salida', type=Path, default=HERE / 'planillas')
ap.add_argument('--n-por-estrato', type=int, default=25)
ap.add_argument('--semilla', type=int, default=20261109)
ap.add_argument('--sobrescribir', action='store_true')
args = ap.parse_args()
DEL, OUT, N_H, SEED = args.entrada.resolve(), args.salida.resolve(), args.n_por_estrato, args.semilla
OUT.mkdir(parents=True, exist_ok=True)
if not args.sobrescribir and any((OUT / n).exists() for n in ('01_revision_humana_86.xlsx', '02_muestra_validacion_ciega.xlsx')):
    sys.exit('Ya existen planillas en ' + str(OUT) + '. No se sobrescriben (podrían estar completadas).')
R = list(csv.DictReader(open(DEL / '01_corpus_completo_cribado.csv', encoding='utf-8-sig')))

def doi_url(d): return ('https://doi.org/' + d) if d else ''
def norm_abs(s): return re.sub(r'\W+', ' ', s.lower()).strip()

# Publicaciones que comparten resumen (para mostrar al revisor con qué se comparte)
# Misma agrupación que la alerta de la etapa 2: resumen usado en el cribado, solo letras y dígitos, >= 120 caracteres.
def nabs(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
ETAPA2 = args.filtro / 'etapa2_filtro_amplio.csv'
ABS = ({e['id_publicacion']: e['abstract'] for e in csv.DictReader(open(ETAPA2, encoding='utf-8-sig'))}
       if ETAPA2.exists() else {r['id_publicacion']: r['resumen'] for r in R})
by_abs = defaultdict(list)
for r in R:
    k = nabs(ABS.get(r['id_publicacion'], ''))
    if len(k) >= 120: by_abs[k].append(r)

TR = (json.loads(args.traducciones.read_text(encoding='utf-8'))['traducciones'] if args.traducciones.exists() else {})
def tr(r, k): return TR.get(r['id_publicacion'], {}).get(k, '')
NOTA_TR = ('Columnas titulo_es y resumen_es: traducción al español hecha con IA (Claude) como apoyo a la lectura; '
           'ante cualquier duda, prima el texto original.')

HEAD_FILL = PatternFill('solid', fgColor='1F3A5F'); REV_FILL = PatternFill('solid', fgColor='FFF2CC')

def sheet(ws, cols, rows, review_cols, widths):
    ws.append([c[0] for c in cols] + [c[0] for c in review_cols])
    for c in ws[1]:
        c.font = Font(bold=True, color='FFFFFF'); c.fill = HEAD_FILL; c.alignment = Alignment(wrap_text=True, vertical='top')
    for r in rows: ws.append([c[1](r) for c in cols] + [''] * len(review_cols))
    n = len(rows) + 1; base = len(cols)
    for j, (name, opts) in enumerate(review_cols):
        col = ws.cell(1, base + j + 1).column_letter
        for i in range(2, n + 1): ws[f'{col}{i}'].fill = REV_FILL
        if opts:
            dv = DataValidation(type='list', formula1='"' + ','.join(opts) + '"', allow_blank=True)
            ws.add_data_validation(dv); dv.add(f'{col}2:{col}{n}')
    for j, w in enumerate(widths + [16] * len(review_cols)):
        ws.column_dimensions[ws.cell(1, j + 1).column_letter].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row: c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'C2'

REVIEW = [('decision_revisor', ['INCLUIDO', 'EXCLUIDO']), ('nucleo_revisor', ['IN', 'OUT', 'NO_APLICA']),
          ('motivo_o_comentario_revisor', None)]
INSTR = [
 'Criterios de decisión (resumen):',
 'INCLUIDO (Nivel 1): estudia procesos, equipos, actividades o decisiones de planificación, asignación, mantenimiento o desempeño de la operación a cielo abierto, con el contexto de rajo como foco central.',
 '- Geotecnia/estabilidad, vibraciones de tronadura y aguas: solo con vínculo operacional explícito (ciclo, costos, tiempos, equipos).',
 '- Componentes o condición de equipos: solo equipos móviles o del rajo (incluye IPCC, correas en mina, bombeo de desagüe); plantas de proceso fuera.',
 '- Revisiones de literatura: INCLUIDO si son pertinentes; núcleo OUT salvo evaluación propia.',
 '- Procesos auxiliares (riego, caminos, dozer, desagüe, combustible, servicios) no se excluyen por ser auxiliares.',
 'Núcleo IN (solo si INCLUIDO): (A) contexto y tarea/equipo del rajo + (B) evaluación propia (datos, modelo, comparación, simulación) + (C) resultado operacional (productividad, tiempos, disponibilidad, costos, consumo, confiabilidad).',
 'Si es EXCLUIDO, marcar nucleo_revisor = NO_APLICA.',
]

def add_instr(wb, extra):
    ws = wb.create_sheet('Instrucciones', 0)
    for line in extra + [''] + INSTR: ws.append([line])
    ws.column_dimensions['A'].width = 160
    for row in ws.iter_rows():
        for c in row: c.alignment = Alignment(wrap_text=True)

# ---------- 1) revisión humana -------------------------------------------------
H = [r for r in R if r['requiere_revision_humana'] == 'si']
H.sort(key=lambda r: (r['limitacion_informacion'], r['id_publicacion']))
def shared(r):
    if 'resumen_compartido' not in r['limitacion_informacion']: return ''
    others = [o for o in by_abs.get(nabs(ABS.get(r['id_publicacion'], '')), []) if o['id_publicacion'] != r['id_publicacion']]
    return ' || '.join(f"{o['id_publicacion']}: {o['titulo'][:120]}" for o in others)
cols = [('id_publicacion', lambda r: r['id_publicacion']), ('motivo_revision', lambda r: r['limitacion_informacion']),
        ('titulo', lambda r: r['titulo']), ('titulo_es', lambda r: tr(r, 'titulo_es')),
        ('anio', lambda r: r['anio_referencia']), ('revista', lambda r: r['revista']),
        ('doi', lambda r: doi_url(r['doi'])), ('tipo_documento', lambda r: r['tipo_documento']),
        ('palabras_clave', lambda r: r['palabras_clave']), ('resumen', lambda r: r['resumen'] or ABS.get(r['id_publicacion'], '')),
        ('resumen_es', lambda r: tr(r, 'resumen_es')),
        ('comparte_resumen_con', shared),
        ('decision_automatica', lambda r: r['decision_final']),
        ('nucleo_automatico', lambda r: r['decision_cribado_desempeno']),
        ('justificacion_automatica', lambda r: r['justificacion'])]
wb = Workbook(); ws = wb.active; ws.title = 'Revision_86'
sheet(ws, cols, H, REVIEW, [30, 22, 45, 45, 7, 25, 25, 12, 30, 70, 70, 45, 12, 10, 45])
add_instr(wb, [f'Revisión humana: {len(H)} publicaciones incluidas con información insuficiente o dudosa.',
               'Motivos: sin_resumen_en_las_tres_bases (decididas por título); resumen_compartido_con_otra_publicacion '
               '(el resumen puede no corresponder al título: decidir por título o buscar el resumen real vía DOI); '
               'solo_titulo_y_resumen_no_ingles (traducir título/resumen).',
               'Completar las columnas amarillas. Si confirma la decisión automática, puede dejar el comentario vacío.',
               NOTA_TR])
wb.save(OUT / '01_revision_humana_86.xlsx')

# ---------- 2) muestra de validación estratificada y ciega ---------------------
def stratum(r):
    if r['decision_filtro_amplio'] == 'EXCLUIDO': return 'E1_excluido_filtro_amplio'
    if r['decision_final'] == 'EXCLUIDO': return 'E2_excluido_pertinencia'
    return 'E4_incluido_nucleo_IN' if r['decision_cribado_desempeno'] == 'IN' else 'E3_incluido_nucleo_OUT'
pool = defaultdict(list)
for r in R:
    if r['requiere_revision_humana'] != 'si': pool[stratum(r)].append(r)
rng = random.Random(SEED); sample = []
for h in sorted(pool):
    ids = sorted(pool[h], key=lambda r: r['id_publicacion'])
    sample += [(h, r) for r in rng.sample(ids, N_H)]
rng.shuffle(sample)
for k, (h, r) in enumerate(sample, 1): r['_cod'] = f'M{k:03d}'
cols = [('codigo_muestra', lambda r: r['_cod']), ('id_publicacion', lambda r: r['id_publicacion']),
        ('titulo', lambda r: r['titulo']), ('titulo_es', lambda r: tr(r, 'titulo_es')),
        ('anio', lambda r: r['anio_referencia']), ('revista', lambda r: r['revista']),
        ('doi', lambda r: doi_url(r['doi'])), ('tipo_documento', lambda r: r['tipo_documento']),
        ('palabras_clave', lambda r: r['palabras_clave']), ('resumen', lambda r: r['resumen']),
        ('resumen_es', lambda r: tr(r, 'resumen_es'))]
wb = Workbook(); ws = wb.active; ws.title = 'Muestra'
sheet(ws, cols, [r for _, r in sample], REVIEW, [10, 30, 45, 45, 7, 25, 25, 12, 30, 75, 75])
add_instr(wb, [f'Muestra de validación ciega: {len(sample)} publicaciones ({N_H} por estrato, semilla {SEED}).',
               'La decisión automática NO se muestra. Decidir solo con la información de la fila (y el DOI si hace falta).',
               'No abrir 03_clave_muestra_validacion.csv antes de terminar.',
               NOTA_TR])
wb.save(OUT / '02_muestra_validacion_ciega.xlsx')
with open(OUT / '03_clave_muestra_validacion.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['codigo_muestra', 'id_publicacion', 'estrato', 'tamano_estrato', 'decision_automatica', 'nucleo_automatico',
                'procedencia_decision'])
    for h, r in sorted(sample, key=lambda x: x[1]['_cod']):
        w.writerow([r['_cod'], r['id_publicacion'], h, len(pool[h]), r['decision_final'],
                    r['decision_cribado_desempeno'] if r['decision_final'] == 'INCLUIDO' else 'NO_APLICA',
                    r['procedencia_decision']])
print('revision_humana:', len(H), '| muestra:', len(sample), {h: len(v) for h, v in sorted(pool.items())})
