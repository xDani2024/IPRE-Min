"""Etapa 4: integra reglas y decisiones de lectura dirigida y exporta los resultados finales.

Entradas: salidas de las etapas 1-3 y los archivos de entrada/lectura_dirigida/ (índice, código y motivo,
sobre listas ordenadas por id_publicacion). Salidas: 01 corpus completo cribado, 02 incluidos,
03 excluidos, 04 núcleo de desempeño IN y 05 resumen. Termina con aserciones de partición e integridad.

Uso: py -3 04_integracion_final/04_integrar_decisiones.py [--proyecto RUTA] [--filtro RUTA] [--nucleo RUTA] [--nivel1 RUTA] [--lectura RUTA] [--salida RUTA]
"""
import csv, json, re, sys, hashlib
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
ap.add_argument('--proyecto')
ap.add_argument('--filtro', type=Path, default=ROOT / '01_filtro_amplio/salida')
ap.add_argument('--nucleo', type=Path, default=ROOT / '02_nucleo_desempeno/salida')
ap.add_argument('--nivel1', type=Path, default=ROOT / '03_pertinencia_operacional/salida')
ap.add_argument('--lectura', type=Path, default=HERE / 'entrada/lectura_dirigida')
ap.add_argument('--salida', type=Path, default=HERE / 'salida')
args = ap.parse_args()
PROJ, LEC, DEL = buscar_proyecto(args.proyecto), args.lectura.resolve(), args.salida.resolve()
DEL.mkdir(parents=True, exist_ok=True)
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8-sig')))
U = rd(PROJ / 'integracion_corpus/resultados_validados/universo/01_corpus_unificado_identidad.csv')
A = {r['id_publicacion']: r for r in rd(args.filtro / 'etapa2_filtro_amplio.csv')}
N = {r['id_publicacion']: r for r in rd(args.nucleo / 'etapa3a_nucleo_reglas.csv')}
L = {r['id_publicacion']: r for r in rd(args.nivel1 / 'etapa3b_nivel1_reglas.csv')}

# ---------- lectura de archivos de decisiones ---------------------------------
def load(name):
    p = LEC / name; default = None; d = {}
    for line in p.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or (line.startswith('#') and not line.startswith('#DEFAULT')): continue
        if line.startswith('#DEFAULT'):
            parts = line.split(' ', 3) + ['REGLA', '']; default = (parts[1], parts[2], parts[3] if len(parts) > 3 else ''); continue
        k, dec, code, why = (line.split(' ', 3) + [''])[:4]
        d[k] = (dec, code, why)
    return default, d

def ordered(pred):
    return sorted([pid for pid in L if pred(pid)])

# Núcleo: candidatos v8 (IN por regla) y v9 (TC -> IN por regla) en el mismo orden que ver.py
v8_ids = ordered(lambda p: N[p]['decision_v8'] == 'IN')
v9_ids = ordered(lambda p: N[p]['decision_v8'] == 'TC' and N[p]['decision_v9_regla'] == 'IN')
_, nuc_v8 = load('nucleo_v8.txt'); _, nuc_v9 = load('nucleo_v9.txt'); _, n1_l00 = load('n1_L00.txt')
assert len(nuc_v9) == len(v9_ids) == 137, (len(nuc_v9), len(v9_ids))
NUC = {}; N1_OVR = {}
for i, pid in enumerate(v9_ids):
    NUC[pid] = ('v9', nuc_v9[str(i)])
    if f'v9:{i}' in n1_l00: N1_OVR[pid] = n1_l00[f'v9:{i}']
for i, pid in enumerate(v8_ids):
    NUC[pid] = ('v8', nuc_v8.get(str(i), ('NI_A', 'REGLA_V8', '')))
    if f'v8:{i}' in n1_l00: N1_OVR[pid] = n1_l00[f'v8:{i}']

# Rescate por riesgo de omisión (lectura dirigida de candidatos N1 con términos de desempeño)
RESC_IDS = [x.strip() for x in (LEC / 'nucleo_rescate_candidatos.txt').read_text(encoding='utf-8').splitlines() if x.strip() and not x.startswith('#')]
_, resc = load('nucleo_rescate.txt')
assert len(RESC_IDS) == 378 and all(int(k) < 378 for k in resc)
RESC = {RESC_IDS[int(k)]: v for k, v in resc.items() if v[0] == 'NI_A'}

# Nivel 1 por grupo de regla
GROUPS = {'N1_L01': 'n1_L01.txt', 'N1_L02': 'n1_L02.txt', 'N1_L03': 'n1_L03.txt', 'N1_L04': 'n1_L04.txt',
          'N1_L05': 'n1_L05.txt', 'N1_L06': 'n1_L06.txt', 'N1_L07': 'n1_L07.txt', 'N1_O03': 'n1_O03.txt',
          'N1_O05': 'n1_O05.txt', 'N1_O06': 'n1_O06.txt', 'N1_I01': 'n1_I01.txt', 'N1_I03': 'n1_I03.txt',
          'N1_I04': 'n1_I04.txt', 'N1_O01': 'n1_O01.txt', 'N1_O02': 'n1_O02.txt'}
N1 = {}
for pre, f in GROUPS.items():
    default, d = load(f)
    ids = ordered(lambda p: L[p]['nivel1_codigo_regla'].startswith(pre))
    assert all(int(k) < len(ids) for k in d), (pre, max(map(int, d)), len(ids))
    for i, pid in enumerate(ids):
        dec, code, why = d.get(str(i), default)
        src = 'lectura_dirigida_titulo_resumen' if str(i) in d else 'regla_confirmada_por_lectura_de_titulo'
        if pre in ('N1_L01', 'N1_L02', 'N1_L03', 'N1_L04', 'N1_L05', 'N1_L06', 'N1_L07') and str(i) not in d:
            src = 'lectura_dirigida_titulo_resumen'
        N1[pid] = (dec, code, why, src)
for pid in ordered(lambda p: L[p]['nivel1_codigo_regla'].startswith('N1_I02')):
    N1[pid] = ('I', 'EQUIPO', 'Componente o condición de un equipo de la mina.', 'regla_confirmada_por_lectura_de_titulo')

FAM2CODE = {'ambiente_cierre_salud': 'F_AMB', 'geotecnia_estabilidad': 'F_GEO', 'geologia_recursos': 'F_GEOL',
            'procesamiento_metalurgia': 'F_PROC', 'efectos_tronadura': 'F_VIB', 'componente_material': 'F_COMP',
            'economia_sociedad_politica': 'F_ECO', 'teledeteccion_cartografia': 'F_TELE',
            'seguridad_salud_ocupacional': 'F_SEG'}
MOTIVO = {
 'F_AMB': 'Foco ambiental, hídrico, de emisiones, cierre o recuperación de terrenos, sin vínculo con la ejecución de la operación.',
 'F_GEO': 'Foco geotécnico o de estabilidad sin vínculo operacional explícito (ciclo, costos, tiempos o equipos).',
 'F_VIB': 'Efectos de la tronadura (vibraciones, onda aérea, proyecciones, daño) sin vínculo operacional.',
 'F_GEOL': 'Foco geológico, geofísico, de exploración o estimación de recursos.',
 'F_PROC': 'Procesamiento o planta fuera de la operación del rajo.',
 'F_ECO': 'Foco económico agregado, social, legal, de política o educativo, sin objeto operacional.',
 'F_SEG': 'Seguridad ocupacional general, sin vínculo con la operación de equipos o procesos.',
 'F_SALUD': 'Salud o exposición ocupacional (vibración, ruido, polvo, calor) de los trabajadores.',
 'F_CTX': 'Contexto distinto de la operación a cielo abierto (subterráneo, otra industria u otra aplicación).',
 'F_COMP': 'Componente o material sin vínculo con un equipo de la operación del rajo.',
 'F_TELE': 'Cartografía o teledetección del área minera sin objeto operacional.',
 'F_OTRO': 'No trata procesos, equipos, actividades ni decisiones de la operación del rajo (tema general o de gestión).',
 'F_DOC': 'Documento sin estudio propio (editorial, reseña, bibliografía, actas o publicación retractada).',
}
FILTRO_TXT = {
 'sin_foco_operacional_suficiente': 'Filtro amplio original: sin señal operacional suficiente (título, resumen y metadatos).',
 'tema_excluido_en_titulo': 'Filtro amplio original: tema excluido en el título (p. ej., recuperación, ecología, uso de suelo).',
 'tema_periferico_en_titulo': 'Filtro amplio original: tema periférico en el título.',
 'metodo_subterraneo_fuera_de_alcance': 'Filtro amplio original: método subterráneo en el título.',
}
NUC_TXT = {
 'NI_A': 'Núcleo IN: la ficha vincula tarea o equipo del rajo, evaluación propia y resultado operacional.',
 'NO_D': 'Núcleo OUT documental: la ficha no acredita evaluación propia con resultado operacional (descripción, nota técnica o beneficio no evaluado).',
 'NO_F': 'Núcleo OUT por foco: el resultado evaluado no es desempeño de la tarea o equipo.',
 'NO_M': 'Núcleo OUT: el resultado es la métrica de un modelo o detector, no el desempeño de la tarea.',
 'NO_C': 'Núcleo OUT: resultado a nivel de componente sin vínculo con el desempeño del equipo.',
 'NO_V': 'Núcleo OUT: resultado a nivel de mina, proyecto o plan estratégico, sin tarea aislada.',
 'NO_R': 'Núcleo OUT: revisión o síntesis sin evaluación propia.',
 'NO_U': 'Núcleo OUT: contexto subterráneo.',
}

def nonlatin(s): return bool(s) and sum(ord(c) > 591 for c in s) > len(s) * 0.3

rows = []; audit = Counter()
for u in U:
    pid = u['id_publicacion']; a = A[pid]
    r = {**u}
    r['titulo_usado_en_cribado'] = a['title'] if a['titulo_cribado_origen'] != 'unificado' else ''
    r['resumen_usado_en_cribado_origen'] = a['resumen_cribado_origen']
    r['decision_filtro_amplio'] = a['decision_filtro_amplio']
    r['motivo_filtro_amplio'] = a['motivo_filtro_amplio']
    rev = 'si' if (a['type'] == 'review' or (pid in N and N[pid]['revision_secundaria_detectada'] == 'si')) else 'no'
    lim = []
    if a['tiene_resumen'] == 'no': lim.append('sin_resumen_en_las_tres_bases')
    if nonlatin(a['title']) and (not a['abstract'] or nonlatin(a['abstract'])): lim.append('solo_titulo_y_resumen_no_ingles')
    if pid in N and N[pid]['alerta_resumen_compartido'] == 'resumen_compartido_con_titulo_incompatible':
        lim.append('resumen_compartido_con_otra_publicacion')
    if a['decision_filtro_amplio'] == 'EXCLUIDO':
        reasons = [x.split(':')[0] for x in a['motivo_filtro_amplio'].split('; ') if x]
        r.update({'decision_pertinencia_nivel1': 'NO_EVALUADO', 'decision_cribado_desempeno': 'NO_EVALUADO',
                  'regla_cribado_desempeno': '', 'decision_final': 'EXCLUIDO', 'etapa_exclusion': 'filtro_amplio',
                  'motivo_exclusion': ' | '.join(FILTRO_TXT[x] for x in reasons),
                  'justificacion': 'Detalle de la regla original: ' + a['motivo_filtro_amplio'],
                  'procedencia_decision': 'regla_filtro_amplio_original'})
    else:
        n = N[pid]; l = L[pid]
        # ---- Nivel 1 ----
        if pid in NUC:
            dec, code, why = N1_OVR.get(pid, ('I', 'NUCLEO', ''))
            src = 'lectura_dirigida_titulo_resumen'
        elif pid in N1:
            dec, code, why, src = N1[pid]
        else:
            raise RuntimeError('Sin decisión de Nivel 1: ' + pid)
        if dec == 'O' and code == 'REGLA':
            fam = (l['foco_alternativo_titulo'] or l['foco_alternativo_resumen']).split(';')[0]
            rc = l['nivel1_codigo_regla']
            code = ('F_CTX' if rc.startswith(('N1_O01', 'N1_O02')) else FAM2CODE.get(fam, 'F_OTRO'))
            why = ''
        n1_in = dec == 'I'
        # ---- Núcleo de desempeño ----
        if pid in NUC:
            ncode, nreg, nwhy = NUC[pid][1]
            nuc_in = ncode == 'NI_A'
            ntext = NUC_TXT[ncode] + (' ' + nwhy if nwhy else '')
            nsrc = 'lectura_dirigida' if (NUC[pid][0] == 'v9' or nreg != 'REGLA_V8') else 'regla_v8'
            nrule = ('I01_TAREA_RESULTADO_EVALUADO' if NUC[pid][0] == 'v8' else 'I01_EVIDENCIA_OPERACIONAL_EN_FICHA') + ('' if nsrc == 'regla_v8' else '+LECTURA_' + ncode)
        elif pid in RESC and n1_in:
            nuc_in = True; nsrc = 'lectura_dirigida'
            nrule = 'RESCATE_LECTURA_DIRIGIDA+LECTURA_NI_A'
            ntext = NUC_TXT['NI_A'] + ' ' + RESC[pid][2]
        else:
            nuc_in = False
            if n['decision_v8'] == 'TC':
                nrule = n['regla_v9']; ntext = n['motivo_v9']
            else:
                nrule = n['regla_v8']
                ntext = {'O02_LITERATURA_SECUNDARIA': 'Núcleo OUT: revisión o síntesis sin evaluación primaria propia (se conserva en el corpus si es pertinente).',
                         'O04_FOCO_ALTERNATIVO_IDENTIFICADO': 'Núcleo OUT: foco alternativo identificado en el título sin resultado propio de la tarea.',
                         'O07_RESULTADO_DE_MINA_PROYECTO': 'Núcleo OUT: diseño o secuencia del pit o valor del proyecto, sin resultado operacional de tarea o equipo.',
                         'O06_RESULTADO_DE_COMPONENTE': 'Núcleo OUT: resultados de componente o material.',
                         'O01_EDITORIAL': 'Núcleo OUT: editorial o corrección.',
                         'O03_CONTEXTO_ALTERNATIVO': 'Núcleo OUT: contexto distinto del rajo.'}.get(nrule, nrule)
            nsrc = 'regla'
        if not n1_in and nuc_in:
            audit['nucleo_IN_anulado_por_nivel1_OUT'] += 1
            nuc_in = False; ntext = 'Núcleo OUT: la publicación queda fuera del alcance de pertinencia (Nivel 1). ' + ntext
        r['decision_pertinencia_nivel1'] = 'INCLUIDO' if n1_in else 'EXCLUIDO'
        r['decision_cribado_desempeno'] = 'IN' if nuc_in else 'OUT'
        r['regla_cribado_desempeno'] = nrule
        r['justificacion_cribado_desempeno'] = ntext
        r['decision_final'] = 'INCLUIDO' if n1_in else 'EXCLUIDO'
        r['etapa_exclusion'] = '' if n1_in else 'cribado_pertinencia_operacional'
        r['motivo_exclusion'] = '' if n1_in else (code + ': ' + MOTIVO[code])
        if n1_in:
            base = ('Incluido: estudia procesos, equipos, actividades o decisiones de planificación, asignación, '
                    'mantenimiento o desempeño de la operación a cielo abierto.')
            r['justificacion'] = base + (' Lectura: ' + why if why and src.startswith('lectura') else '')
        else:
            r['justificacion'] = (why or ('Regla: ' + l['nivel1_codigo_regla']))
        r['procedencia_decision'] = src
    r['revision_de_literatura'] = rev
    r['limitacion_informacion'] = ';'.join(lim)
    r['requiere_revision_humana'] = 'si' if (r['decision_final'] == 'INCLUIDO' and
        ('solo_titulo_y_resumen_no_ingles' in lim or 'resumen_compartido_con_otra_publicacion' in lim or
         ('sin_resumen_en_las_tres_bases' in lim and r.get('procedencia_decision', '').startswith('regla')))) else 'no'
    r.setdefault('decision_cribado_desempeno', 'NO_EVALUADO'); r.setdefault('regla_cribado_desempeno', '')
    r.setdefault('justificacion_cribado_desempeno', '')
    rows.append(r)

orig = list(U[0].keys())
added = ['titulo_usado_en_cribado', 'resumen_usado_en_cribado_origen', 'decision_filtro_amplio', 'motivo_filtro_amplio',
         'decision_pertinencia_nivel1', 'decision_cribado_desempeno', 'regla_cribado_desempeno',
         'justificacion_cribado_desempeno', 'decision_final', 'etapa_exclusion', 'motivo_exclusion', 'justificacion',
         'procedencia_decision', 'revision_de_literatura', 'limitacion_informacion', 'requiere_revision_humana']
fields = orig + added
def write(p, rs, fs=fields):
    with open(p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fs, extrasaction='ignore'); w.writeheader(); w.writerows(rs)
inc = [r for r in rows if r['decision_final'] == 'INCLUIDO']
exc = [r for r in rows if r['decision_final'] == 'EXCLUIDO']
nuc = [r for r in rows if r['decision_cribado_desempeno'] == 'IN']
write(DEL / '01_corpus_completo_cribado.csv', rows)
write(DEL / '02_corpus_incluido.csv', inc)
write(DEL / '03_corpus_excluido.csv', exc)
write(DEL / '04_nucleo_desempeno_IN.csv', nuc)

# ---------- verificaciones -------------------------------------------------------
assert len(rows) == 15297 and len({r['id_publicacion'] for r in rows}) == 15297
assert len(inc) + len(exc) == 15297
assert all(r['decision_final'] in ('INCLUIDO', 'EXCLUIDO') for r in rows)
assert all(r['motivo_exclusion'] for r in exc)
assert all(r['decision_pertinencia_nivel1'] == 'INCLUIDO' for r in nuc)
assert all({k: r[k] for k in orig} == u for r, u in zip(rows, U))

C = Counter
acc = [r for r in rows if r['decision_filtro_amplio'] == 'ACEPTADO']
summ = {
 'publicaciones_evaluadas': len(rows),
 'etapa2_filtro_amplio': dict(C(r['decision_filtro_amplio'] for r in rows)),
 'etapa2_motivos_exclusion': dict(C(m.split(':')[0] for r in rows if r['decision_filtro_amplio'] == 'EXCLUIDO' for m in r['motivo_filtro_amplio'].split('; '))),
 'etapa3_nivel1_sobre_aceptados': dict(C(r['decision_pertinencia_nivel1'] for r in acc)),
 'etapa3_nivel1_motivos_exclusion': dict(C(r['motivo_exclusion'].split(':')[0] for r in acc if r['decision_pertinencia_nivel1'] == 'EXCLUIDO').most_common()),
 'etapa3_procedencia_nivel1': dict(C(r['procedencia_decision'] for r in acc)),
 'nucleo_desempeno_sobre_aceptados': dict(C(r['decision_cribado_desempeno'] for r in acc)),
 'nucleo_desempeno_en_incluidos': dict(C(r['decision_cribado_desempeno'] for r in inc)),
 'decision_final': dict(C(r['decision_final'] for r in rows)),
 'incluidos_revision_de_literatura': sum(r['revision_de_literatura'] == 'si' for r in inc),
 'incluidos_sin_resumen': sum('sin_resumen' in r['limitacion_informacion'] for r in inc),
 'requiere_revision_humana': sum(r['requiere_revision_humana'] == 'si' for r in rows),
 'incluidos_por_fuente': dict(C(r['fuentes'] for r in inc)),
 'nucleo_rescate_lectura_dirigida': sum(r['regla_cribado_desempeno'].startswith('RESCATE') for r in rows),
 'auditoria_consistencia': dict(audit),
}
(DEL / '05_resumen_cribado.json').write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
print(json.dumps(summ, ensure_ascii=False, indent=2))
