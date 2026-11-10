"""Etapa 7: cierre del cribado con las planillas completadas.

A) Concordancia de la muestra ciega (02_muestra_validacion_ciega.xlsx vs 03_clave_muestra_validacion.csv):
   - acuerdo por estrato (inclusión y núcleo) con IC de Wilson al 95 %;
   - kappa de Cohen en la muestra;
   - acuerdo ponderado por el tamaño de cada estrato (estimación para el corpus completo);
   - estimación de falsos excluidos y falsos incluidos en el corpus.
B) Aplicación de la revisión humana (01_revision_humana_86.xlsx) al corpus cribado:
   reescribe los archivos 01-04 y el resumen en <dir_salida>, sin tocar los originales.
   Las filas sin decisión del revisor conservan la decisión automática y siguen marcadas.

Requiere openpyxl (requirements_complementarios.txt).
Uso: py -3 05_cierre_revision/08_aplicar_revision_y_concordancia.py [--entrada RUTA] [--planillas RUTA] [--salida RUTA]
"""
import argparse, csv, json, math, sys
from collections import Counter, defaultdict
from pathlib import Path
from openpyxl import load_workbook

csv.field_size_limit(10**9)
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--entrada', type=Path, default=ROOT / '04_integracion_final/salida')
ap.add_argument('--planillas', type=Path, default=HERE / 'planillas')
ap.add_argument('--salida', type=Path, default=HERE / 'salida')
args = ap.parse_args()
DEL, CIE, OUT = args.entrada.resolve(), args.planillas.resolve(), args.salida.resolve()
OUT.mkdir(parents=True, exist_ok=True)

def read_sheet(path, name):
    ws = load_workbook(path, read_only=True, data_only=True)[name]
    it = ws.iter_rows(values_only=True); head = [str(h) for h in next(it)]
    return [{h: ('' if v is None else str(v).strip()) for h, v in zip(head, row)} for row in it if any(row)]

def wilson(k, n, z=1.96):
    if n == 0: return (None, None)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (round((c - m) / d, 3), round((c + m) / d, 3))

def kappa(pairs):
    n = len(pairs)
    if n == 0: return None
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)

# ---------------- A) concordancia -------------------------------------------------
M = {r['codigo_muestra']: r for r in read_sheet(CIE / '02_muestra_validacion_ciega.xlsx', 'Muestra')}
K = list(csv.DictReader(open(CIE / '03_clave_muestra_validacion.csv', encoding='utf-8-sig')))
done = [(k, M[k['codigo_muestra']]) for k in K if M.get(k['codigo_muestra'], {}).get('decision_revisor')]
rep = {'muestra_total': len(K), 'muestra_revisada': len(done), 'por_estrato': {}}
N_h = {k['estrato']: int(k['tamano_estrato']) for k in K}
inc_pairs, nuc_pairs, weighted, wsum = [], [], 0.0, 0
est_fn = est_fp = 0.0
for h in sorted(N_h):
    rows = [(k, m) for k, m in done if k['estrato'] == h]
    n = len(rows); agree = sum(k['decision_automatica'] == m['decision_revisor'] for k, m in rows)
    nr = [(k, m) for k, m in rows if k['decision_automatica'] == 'INCLUIDO' and m['decision_revisor'] == 'INCLUIDO']
    nagree = sum(k['nucleo_automatico'] == m['nucleo_revisor'] for k, m in nr)
    rev_inc = sum(m['decision_revisor'] == 'INCLUIDO' for _, m in rows)
    rep['por_estrato'][h] = {
        'tamano_estrato': N_h[h], 'revisadas': n,
        'acuerdo_inclusion': round(agree / n, 3) if n else None, 'ic95_inclusion': wilson(agree, n),
        'revisor_incluye': rev_inc,
        'acuerdo_nucleo_entre_incluidas': round(nagree / len(nr), 3) if nr else None,
        'ic95_nucleo': wilson(nagree, len(nr)), 'n_nucleo': len(nr)}
    inc_pairs += [(k['decision_automatica'], m['decision_revisor']) for k, m in rows]
    nuc_pairs += [(k['nucleo_automatico'], m['nucleo_revisor']) for k, m in nr]
    if n:
        weighted += N_h[h] * agree / n; wsum += N_h[h]
        auto = rows[0][0]['decision_automatica']
        if auto == 'EXCLUIDO': est_fn += N_h[h] * rev_inc / n          # incluibles dentro de lo excluido
        else: est_fp += N_h[h] * (n - rev_inc) / n                      # excluibles dentro de lo incluido
rep['kappa_inclusion_muestra'] = kappa(inc_pairs)
rep['kappa_nucleo_muestra'] = kappa(nuc_pairs)
rep['acuerdo_inclusion_ponderado_corpus'] = round(weighted / wsum, 3) if wsum else None
rep['estimacion_falsos_excluidos_en_corpus'] = round(est_fn) if done else None
rep['estimacion_falsos_incluidos_en_corpus'] = round(est_fp) if done else None
rep['discrepancias'] = [{'codigo': k['codigo_muestra'], 'id_publicacion': k['id_publicacion'], 'estrato': k['estrato'],
                         'automatica': k['decision_automatica'] + '/' + k['nucleo_automatico'],
                         'revisor': m['decision_revisor'] + '/' + m.get('nucleo_revisor', ''),
                         'comentario': m.get('motivo_o_comentario_revisor', '')}
                        for k, m in done if k['decision_automatica'] != m['decision_revisor'] or
                        (k['decision_automatica'] == m['decision_revisor'] == 'INCLUIDO' and k['nucleo_automatico'] != m['nucleo_revisor'])]
rep['nota'] = ('Acuerdo ponderado = suma de (tamaño del estrato x acuerdo del estrato) / corpus. '
               'Las estimaciones de falsos excluidos/incluidos extrapolan la proporción de discrepancias de cada estrato a su tamaño; '
               'con 25 casos por estrato el intervalo es amplio (ver ic95).')
(OUT / 'concordancia_muestra_validacion.json').write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')

# ---------------- B) aplicar revisión humana ---------------------------------------
H = {r['id_publicacion']: r for r in read_sheet(CIE / '01_revision_humana_86.xlsx', 'Revision_86') if r.get('decision_revisor')}
R = list(csv.DictReader(open(DEL / '01_corpus_completo_cribado.csv', encoding='utf-8-sig')))
fields = list(R[0].keys()); changes = Counter()
for r in R:
    h = H.get(r['id_publicacion'])
    if not h: continue
    dec, nuc, com = h['decision_revisor'], h.get('nucleo_revisor', ''), h.get('motivo_o_comentario_revisor', '')
    assert dec in ('INCLUIDO', 'EXCLUIDO'), (r['id_publicacion'], dec)
    changes[f"{r['decision_final']}->{dec}"] += 1
    r['decision_final'] = r['decision_pertinencia_nivel1'] = dec
    if dec == 'EXCLUIDO':
        r['decision_cribado_desempeno'] = 'OUT'
        r['etapa_exclusion'] = 'revision_humana'
        r['motivo_exclusion'] = 'REVISION_HUMANA: ' + (com or 'excluida en la revisión humana de casos con información insuficiente')
    else:
        if nuc in ('IN', 'OUT'): r['decision_cribado_desempeno'] = nuc
        r['etapa_exclusion'] = r['motivo_exclusion'] = ''
    if com: r['justificacion'] = 'Revisión humana: ' + com
    r['procedencia_decision'] = 'revision_humana'
    r['requiere_revision_humana'] = 'no'

def write(p, rs):
    with open(p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fields); w.writeheader(); w.writerows(rs)
inc = [r for r in R if r['decision_final'] == 'INCLUIDO']
write(OUT / '01_corpus_completo_cribado.csv', R)
write(OUT / '02_corpus_incluido.csv', inc)
write(OUT / '03_corpus_excluido.csv', [r for r in R if r['decision_final'] == 'EXCLUIDO'])
write(OUT / '04_nucleo_desempeno_IN.csv', [r for r in R if r['decision_cribado_desempeno'] == 'IN'])
summ = {'revision_humana_aplicada': len(H), 'cambios': dict(changes),
        'pendientes_revision_humana': sum(r['requiere_revision_humana'] == 'si' for r in R),
        'decision_final': dict(Counter(r['decision_final'] for r in R)),
        'nucleo_IN': sum(r['decision_cribado_desempeno'] == 'IN' for r in R)}
(OUT / '05_resumen_cierre.json').write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
print(json.dumps({'concordancia': {k: rep[k] for k in ('muestra_revisada', 'kappa_inclusion_muestra',
      'acuerdo_inclusion_ponderado_corpus')}, 'cierre': summ}, ensure_ascii=False, indent=2))
