from pathlib import Path
from collections import Counter
import csv, json, hashlib, datetime, zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.ticker import FuncFormatter
RAIZ = ROOT
RUTA_ENTRADA = args.entrada / 'Matriz_Scopus_4614_con_pre_cierre_v9.csv'
RUTA_MANIFIESTO = args.entrada / 'Resumen_y_manifest_v9_scopus.json'
SALIDA = args.salida
FIG = SALIDA / 'graficos'
FIG.mkdir(parents=True, exist_ok=True)
if not RUTA_ENTRADA.is_file():
    raise ValueError(f'No está la matriz v9: {RUTA_ENTRADA}')
if not RUTA_MANIFIESTO.is_file():
    raise ValueError(f'No está el manifiesto: {RUTA_MANIFIESTO}')

def sha256(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()
with RUTA_MANIFIESTO.open(encoding='utf-8') as f:
    man = json.load(f)
expected = man.get('sha256_salidas', {}).get(RUTA_ENTRADA.name)
if not expected or sha256(RUTA_ENTRADA) != expected:
    raise ValueError('El SHA-256 de la matriz v9 difiere del manifiesto. Detenga esta ejecución.')
print('Matriz:', RUTA_ENTRADA)
print('SHA-256:', sha256(RUTA_ENTRADA))
print('Salida:', SALIDA)
print('Fuente:', man.get('fuente'), '| Estado:', man.get('tipo_resultado'))
with RUTA_ENTRADA.open(encoding='utf-8-sig', newline='') as f:
    registros = list(csv.DictReader(f))
if not len(registros) == man['base_amplia']:
    raise ValueError('Difieren la matriz y el manifiesto de la Fase 4')
if not all((r.get('scopus_id') for r in registros)):
    raise ValueError('Hay scopus_id vacíos')
if not len({r['scopus_id'] for r in registros}) == len(registros):
    raise ValueError('Hay scopus_id repetidos')
conteos_v9 = Counter((r.get('decision_nucleo_v9_propuesta', '') for r in registros))
if not dict(conteos_v9) == man['v9_propuesta_computacional_total']:
    raise ValueError('Descuadre de IN/OUT contra Fase 4')
base_amplia = registros
nucleo = [r for r in registros if r['decision_nucleo_v9_propuesta'] == 'IN']
pendientes = [r for r in registros if r.get('validacion_academica_v9') == 'pendiente']
print('Base amplia:', len(base_amplia))
print('Núcleo IN computacional:', len(nucleo))
print('OUT computacional:', conteos_v9['OUT'])
print('Pendientes de validación académica:', len(pendientes))
print('Ningún conteo de este notebook implica revisión humana completada.')

def etiquetas(filas, campo):
    c = Counter()
    for r in filas:
        c.update(set((x.strip() for x in (r.get(campo) or '').split(';') if x.strip())))
    return dict(c.most_common())

def describir(filas):
    años = Counter()
    faltantes = 0
    for r in filas:
        v = str(r.get('year', '')).strip()
        if v.isdigit() and len(v) == 4:
            años[int(v)] += 1
        else:
            faltantes += 1
    return {'N': len(filas), 'por_ano': dict(sorted(años.items())), 'antes_2000': sum((n for a, n in años.items() if a < 2000)), '2000_2025': sum((años[a] for a in range(2000, 2026))), '2026_parcial': años[2026], 'posteriores_2026': sum((n for a, n in años.items() if a > 2026)), 'sin_ano': faltantes, **{k: etiquetas(filas, k) for k in ['auto_process_tags', 'auto_equipment_tags', 'equipment_title_tags', 'auto_focus_tags']}}

def v6_estado(r):
    s = (r.get('decision_final_propuesta') or '').upper()
    return 'IN' if s.startswith('IN') else 'TC' if s == 'DUDOSO' else 'OUT'
versiones = {'v6': dict(Counter((v6_estado(r) for r in registros))), 'v7': dict(Counter((r['decision_nucleo_v7'] for r in registros))), 'v8': dict(Counter((r['decision_nucleo_v8_propuesta'] for r in registros))), 'v9': dict(conteos_v9)}
tc_previos = [r for r in registros if r['decision_nucleo_v8_propuesta'] == 'TC']
disposiciones_tc = dict(Counter((r['disposicion_documental_v9'] for r in tc_previos)))
if not len(tc_previos) == man['TC_v8_evaluados']:
    raise ValueError('Control de integridad incumplido')
if not dict(Counter(disposiciones_tc)) == dict(Counter(man['disposiciones_TC'])):
    raise ValueError('Descuadre de disposiciones v9')
if not sum(disposiciones_tc.values()) == len(tc_previos):
    raise ValueError('Control de integridad incumplido')
manifest_fase01=ROOT/'01_extraccion_y_filtro/referencia_archivada/manifest_fase01.json'
fase01=json.loads(manifest_fase01.read_text(encoding='utf-8'))
if fase01['aceptados_amplios_provisionales']!=len(registros):raise ValueError('El manifiesto de fase 1 corresponde a otra base.')
etapa01={'coincidencias':fase01['filas_descargadas'],'unicos':fase01['publicaciones_unicas'],'documentales':fase01['documentales_excluidos'],'excluidos_amplios':fase01['excluidos_amplios'],'nota':'Recuentos del manifiesto fase 1 de referencia incluido.'}
data = {'fecha_generacion_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'fuente': 'Scopus', 'tipo': 'DESCRIPTIVOS_PRELIMINARES_NO_VALIDADOS', 'sha256_matriz_v9': sha256(RUTA_ENTRADA), 'base_amplia': describir(base_amplia), 'nucleo_propuesto_v9': describir(nucleo), **versiones, 'TC_cierre': disposiciones_tc,     'resumen_etapa01': etapa01,
'calibracion_humana_scopus': {'revisiones_independientes_realizadas': 0, 'IN_pendientes_revision': len(nucleo), 'OUT_seleccionados_muestra': man['OUT_seleccionados_muestra']}, 'nota_metodologica': 'Las etiquetas son menciones no excluyentes, no objetos centrales validados. IN/OUT son pre-cierre computacional.'}
with (SALIDA / 'Resultados_descriptivos_scopus_v9.json').open('w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('Conteos por versión:')
for k, v in versiones.items():
    print(k, v)
print('Disposiciones antiguos TC:', disposiciones_tc)
print('Por año, 2026 / posterior a 2026:', data['base_amplia']['2026_parcial'], data['base_amplia']['posteriores_2026'])
NAVY = '#29475F'
GREEN = '#356859'
GRAY = '#B7C0C9'
GOLD = '#D7AE59'
LILAC = '#8B7AA8'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.labelsize': 10, 'figure.facecolor': 'white', 'savefig.facecolor': 'white'})
fmt = lambda n: f'{int(n):,}'.replace(',', '.')

def guardar(fig, nombre):
    fig.savefig(FIG / (nombre + '.png'), dpi=185, bbox_inches='tight', pad_inches=0.15)
    plt.close(fig)
    print('Figura creada:', nombre)
fig, ax = plt.subplots(figsize=(8.1, 4.3))
ax.set_xlim(0, 11)
ax.set_ylim(0, 7)
ax.axis('off')

def caja(x, y, w, h, t, fc='#F4F5F6'):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=.07,rounding_size=.09', edgecolor='#9BA3A9', facecolor=fc, lw=0.9))
    ax.text(x + w / 2, y + h / 2, t, ha='center', va='center', fontsize=10)

def flecha(a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=12, lw=0.9, color='#64717C'))
caja(3.4, 5.75, 4.2, 0.8, f'Coincidencias de búsqueda Scopus\n{fmt(etapa01["coincidencias"])} (10 expresiones)')
caja(3.4, 4.35, 4.2, 0.75, f'Registros únicos Scopus\n{fmt(etapa01["unicos"])}')
flecha((5.5, 5.7), (5.5, 5.12))
ax.text(7.8, 5.38, f'{fmt(etapa01["coincidencias"]-etapa01["unicos"])} duplicados fusionados', fontsize=9)
caja(0.45, 2.5, 4.35, 0.8, f'Base amplia preliminar\n{fmt(len(registros))} registros', fc='#EAF0F4')
caja(6.2, 2.5, 4.35, 0.8, f'Exclusiones previas al cribado\n{fmt(etapa01["excluidos_amplios"])} amplias + {fmt(etapa01["documentales"])} documentales')
flecha((4.7, 4.28), (2.6, 3.35))
flecha((6.3, 4.28), (8.35, 3.35))
caja(0.45, 0.9, 4.35, 0.8, f'Núcleo operacional propuesto\n{fmt(len(nucleo))} IN', fc='#E8F0EC')
caja(6.2, 0.9, 4.35, 0.8, f'Fuera del núcleo propuesto\n{fmt(conteos_v9["OUT"])} OUT')
flecha((2.6, 2.43), (2.6, 1.78))
flecha((3.45, 2.43), (8.35, 1.78))
ax.text(5.5, 0.2, 'IN/OUT v9 automáticos, pendientes de validación; OUT continúa en la base amplia.', ha='center', fontsize=9)
guardar(fig, '01_flujo_del_estudio')
fig, ax = plt.subplots(figsize=(8.3, 3.7))
fig.subplots_adjust(left=0.27, bottom=0.27)
for i, k in enumerate(['v6', 'v7', 'v8', 'v9']):
    left = 0
    for lab, col in [('IN', GREEN), ('OUT', GRAY), ('TC', GOLD)]:
        n = data[k].get(lab, 0)
        ax.barh(i, n, left=left, height=0.57, color=col, label=lab if i == 0 else None)
        if n > 90:
            ax.text(left + n / 2, i, fmt(n), ha='center', va='center', fontsize=9, color='white' if lab == 'IN' else '#1C262E')
        left += n
ax.set_yticks(range(4), ['v6 | primer cribado', 'v7 | revisión dudosos', 'v8 | criterio ajustado', 'v9 | pre-cierre'])
ax.invert_yaxis()
ax.set_xlim(0, len(registros))
ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: fmt(x)))
ax.set_xlabel(f'Propuestas sobre {fmt(len(registros))} registros; sin validación humana Scopus')
ax.grid(axis='x', color='#DDDDDD', lw=0.5)
ax.set_axisbelow(True)
ax.legend(ncol=3, frameon=False, loc='upper center', bbox_to_anchor=(0.52, -0.22))
guardar(fig, '02_versiones_del_cribado')
labels = ['IN con evidencia (regla)', 'OUT por foco', 'OUT documental']
vals = [disposiciones_tc.get('inclusion_con_evidencia', 0), disposiciones_tc.get('exclusion_por_foco', 0), disposiciones_tc.get('exclusion_documental', 0)]
fig, ax = plt.subplots(figsize=(8, 2.7))
fig.subplots_adjust(left=0.28)
ax.barh(range(3), vals, color=[GREEN, GRAY, GOLD], height=0.62)
ax.set_yticks(range(3), labels)
ax.invert_yaxis()
ax.set_xlim(0, max(vals) * 1.18)
for i, n in enumerate(vals):
    ax.text(n + max(vals) * 0.02, i, fmt(n), va='center')
ax.set_xlabel(f'Disposición computacional de {len(tc_previos):,} antiguos TC'.replace(',', '.'))
ax.grid(axis='x', color='#DDDDDD', lw=0.5)
ax.set_axisbelow(True)
guardar(fig, '03_cierre_de_TC')
fig, axes = plt.subplots(2, 1, figsize=(8, 4.7), sharex=True, gridspec_kw={'hspace': 0.47})
for ax, k, t, col in zip(axes, ['base_amplia', 'nucleo_propuesto_v9'], [f'Base amplia | N = {len(base_amplia):,}', f'Núcleo v9 propuesto | N = {len(nucleo):,}'], [NAVY, GREEN]):
    ys = list(range(2000, 2026))
    cnt = data[k]['por_ano']
    ns = [cnt.get(y, 0) for y in ys]
    ax.bar(ys, ns, color=col, width=0.8)
    ax.set_title(t.replace(',', '.'), loc='left', fontsize=10.5)
    ax.set_ylabel('Registros')
    ax.grid(axis='y', color='#DDDDDD', lw=0.5)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(ns) * 1.18 if max(ns) else 1)
axes[-1].set_xticks([2000, 2005, 2010, 2015, 2020, 2025])
axes[-1].set_xlabel('Año de publicación | 2026 y posteriores informados fuera del gráfico')
axes[-1].set_xlim(1999.2, 2025.8)
guardar(fig, '04_publicaciones_por_ano')
PROCESS = {'caracterizacion_topografia_geomecanica': 'Geotecnia y caracterización', 'tronadura': 'Tronadura', 'perforacion': 'Perforación', 'transporte_acarreo': 'Transporte y acarreo', 'planificacion_programacion': 'Planificación y programación', 'desague_drenaje': 'Desagüe y drenaje', 'carguio': 'Carguío', 'regadio_control_polvo': 'Riego y control de polvo', 'descarga_chancado_botadero': 'Descarga y botadero', 'caminos_pisos_frentes': 'Caminos pisos y frentes', 'mantenimiento_equipos': 'Mantenimiento de equipos', 'limpieza_apoyo_movimiento_material': 'Limpieza y apoyo', 'senalizacion_transito': 'Señalización y tránsito', 'soporte_personal': 'Soporte al personal', 'alimentacion_electrica_cables': 'Electricidad y cables'}
EQUIP = {'chancador_correa': 'Chancador o correa', 'camion_extraccion': 'Camión de extracción', 'pala_excavadora': 'Pala o excavadora', 'dragalina': 'Dragalina', 'cargador_lhd': 'Cargador o LHD', 'perforadora': 'Perforadora', 'bulldozer': 'Bulldozer', 'surface_miner': 'Surface miner', 'scraper_compactador': 'Scraper o compactador', 'motoniveladora': 'Motoniveladora', 'camion_aljibe': 'Camión aljibe', 'camion_servicio_combustible': 'Camión de combustible', 'bomba_desague': 'Bomba de desagüe', 'wheeldozer': 'Wheeldozer'}
FOCUS = {'diseno_planificacion': 'Diseño y planificación', 'desempeno_operacional': 'Desempeño operacional', 'seguridad': 'Seguridad', 'automatizacion_datos': 'Automatización y datos', 'mantenimiento_confiabilidad': 'Mantenimiento y confiabilidad', 'asignacion_programacion_despacho': 'Asignación programación y despacho'}

def grafico_menciones(campo, etiquetas, nombre):
    keys = list(data['base_amplia'][campo])
    keys += [k for k in data['nucleo_propuesto_v9'][campo] if k not in keys]
    keys.sort(key=lambda k: -data['base_amplia'][campo].get(k, 0))
    if not keys:
        return
    height = max(3.2, len(keys) * 0.31)
    fig, axes = plt.subplots(1, 2, figsize=(10.3, height), sharey=True, gridspec_kw={'wspace': 0.23})
    fig.subplots_adjust(left=0.31, right=0.96)
    for ax, k, col, t in zip(axes, ['base_amplia', 'nucleo_propuesto_v9'], [NAVY, GREEN], [f'Base amplia (N={len(base_amplia):,})', f'Núcleo propuesto (N={len(nucleo):,})']):
        vals = [data[k][campo].get(x, 0) for x in keys]
        ma = max(vals + [1])
        ax.barh(range(len(keys)), vals, color=col, height=0.7)
        ax.set_xlim(0, ma * 1.22)
        ax.set_title(t.replace(',', '.'), loc='left', fontsize=10)
        for i, n in enumerate(vals):
            if n:
                ax.text(n + ma * 0.015, i, fmt(n), va='center', fontsize=8)
        ax.grid(axis='x', color='#DDDDDD', lw=0.5)
        ax.set_axisbelow(True)
        ax.set_xlabel('IDs con etiqueta')
    axes[0].set_yticks(range(len(keys)), [etiquetas.get(k, k.replace('_', ' ')) for k in keys], fontsize=8.5)
    axes[0].invert_yaxis()
    guardar(fig, nombre)
grafico_menciones('auto_process_tags', PROCESS, '05_menciones_de_procesos')
grafico_menciones('auto_equipment_tags', EQUIP, '06_menciones_de_equipos')
keys = list(data['base_amplia']['auto_focus_tags'])
keys.sort(key=lambda k: -data['base_amplia']['auto_focus_tags'].get(k, 0))
fig, ax = plt.subplots(figsize=(9.0, 3.7))
fig.subplots_adjust(left=0.32, right=0.96, bottom=0.27)
ys = list(range(len(keys)))
for off, k, col, t in [(-0.18, 'base_amplia', NAVY, f'Base amplia N = {len(base_amplia)}'), (0.18, 'nucleo_propuesto_v9', GREEN, f'Núcleo IN N = {len(nucleo)}')]:
    n = data[k]['N']
    vals = [100 * data[k]['auto_focus_tags'].get(x, 0) / n for x in keys]
    ax.barh([y + off for y in ys], vals, height=0.32, color=col, label=t)
    for y, x in zip(ys, vals):
        ax.text(x + 0.5, y + off, f'{x:.1f}%'.replace('.', ','), va='center', fontsize=8)
ax.set_yticks(ys, [FOCUS.get(k, k) for k in keys], fontsize=9)
ax.invert_yaxis()
ax.set_xlim(0, min(100, max([100 * max(data[s]['auto_focus_tags'].values() or [0]) / data[s]['N'] for s in ['base_amplia', 'nucleo_propuesto_v9']]) * 1.28 + 5))
ax.set_xlabel('Porcentaje de cada base con la etiqueta (no excluyente)')
ax.grid(axis='x', color='#DDDDDD', lw=0.5)
ax.set_axisbelow(True)
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.26), ncol=2, frameon=False, fontsize=9)
guardar(fig, '07_focos_en_cada_base')
fig, ax = plt.subplots(figsize=(8, 2.75))
fig.subplots_adjust(left=0.36, right=0.95, bottom=0.22)
labels = ['IN v9 pendientes de revisar', 'OUT v9 seleccionados para muestra']
vals = [len(nucleo), int(man['OUT_seleccionados_muestra'])]
ax.barh(range(2), vals, color=[GOLD, GRAY], height=0.58)
for i, n in enumerate(vals):
    ax.text(n + 6, i, fmt(n), va='center', fontsize=10)
ax.set_yticks([0, 1], labels)
ax.invert_yaxis()
ax.set_xlim(0, max(vals) * 1.2)
ax.set_xlabel('Cantidad de fichas por revisar; no son grupos complementarios')
fig.text(0.5, -0.04, 'Revisión humana independiente completada en Scopus: 0', ha='center', fontsize=9)
ax.grid(axis='x', color='#DDDDDD', lw=0.5)
ax.set_axisbelow(True)
guardar(fig, '08_estado_validacion_pendiente')
if not len(list(FIG.glob('*.png'))) == 8:
    raise ValueError('Se esperaban exactamente ocho gráficos')
print('Figuras generadas:', len(list(FIG.glob('*.png'))))
