"""Herramienta usada para la lectura dirigida: imprime fichas compactas de un grupo, en el mismo orden
(id_publicacion) que usan los índices de 04_integracion_final/entrada/lectura_dirigida/.

Uso: py -3 documentacion/herramientas_lectura/ver_fichas.py <carpeta_reproduccion> <grupo> [desde] [hasta] [modo]
  carpeta_reproduccion: la carpeta creada por 00_reproducir_local.py (p. ej. reproduccion_local)
  grupo: nucleo_v9 | nucleo_v8 | rescate | n1:<prefijo de código>   (p. ej. n1:N1_O03)
  modo:  t (título) | a (título + inicio del resumen) | e (título + evidencia del núcleo)
Variables opcionales: TTL (largo del título, 115) y ABL (largo del resumen, 230).
"""
import csv, os, re, sys
from pathlib import Path
csv.field_size_limit(10**9)
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parents[2]
D = Path(sys.argv[1]); grp = sys.argv[2]
a0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
a1 = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
mode = sys.argv[5] if len(sys.argv) > 5 else 't'
rd = lambda p: list(csv.DictReader(open(D / p, encoding='utf-8-sig', newline='')))
A = {r['id_publicacion']: r for r in rd('01_filtro_amplio/etapa2_filtro_amplio.csv')}
N = {r['id_publicacion']: r for r in rd('02_nucleo_desempeno/etapa3a_nucleo_reglas.csv')}
L = rd('03_pertinencia_operacional/etapa3b_nivel1_reglas.csv')
if grp == 'nucleo_v9':
    S = [l['id_publicacion'] for l in L if N[l['id_publicacion']]['decision_v8'] == 'TC' and N[l['id_publicacion']]['decision_v9_regla'] == 'IN']
elif grp == 'nucleo_v8':
    S = [l['id_publicacion'] for l in L if N[l['id_publicacion']]['decision_v8'] == 'IN']
elif grp == 'rescate':
    f = ROOT / '04_integracion_final/entrada/lectura_dirigida/nucleo_rescate_candidatos.txt'
    S = [x.strip() for x in f.read_text(encoding='utf-8').splitlines() if x.strip() and not x.startswith('#')]
else:
    pre = grp.split(':', 1)[1]; S = [l['id_publicacion'] for l in L if l['nivel1_codigo_regla'].startswith(pre)]
S = sorted(S)
for i, pid in enumerate(S):
    if not (a0 <= i < a1): continue
    a, n = A[pid], N[pid]
    title = re.sub(r'\s+', ' ', a['title'])[:int(os.environ.get('TTL', '115'))]
    line = f'{i}|{title}'
    if a['type'] == 'review' or n['revision_secundaria_detectada'] == 'si': line += ' [REV]'
    if a['tiene_resumen'] == 'no': line += ' [SIN_RES]'
    if mode == 'a': line += ' ## ' + re.sub(r'\s+', ' ', a['abstract'])[:int(os.environ.get('ABL', '230'))]
    elif mode == 'e':
        ev = n['evidencia_v9'] if n['decision_v8'] == 'TC' else n['evidencia_v8']
        line += ' ## ' + re.sub(r'\s+', ' ', ev)[:210]
    print(line)
print('TOTAL', len(S))
