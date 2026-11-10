"""Etapa 4c: verificación de integridad del cribado integrado.

Comprueba, sin modificar nada:
  - cobertura: cada publicación del corpus unificado aparece una sola vez y conserva sus columnas originales;
  - partición: incluidos + excluidos = corpus; archivos 02/03/04 coinciden con el corpus completo;
  - coherencia de etapas: excluido en filtro amplio => no evaluado después; núcleo IN => incluido;
  - motivos: toda exclusión tiene etapa, motivo y justificación; toda decisión tiene procedencia;
  - lectura dirigida: cada archivo de decisiones se refiere a índices existentes;
  - PRISMA: las cifras de 06_prisma.json cuadran con el corpus.
Escribe Verificacion_integridad.json en la carpeta de entrada y termina con error si algo falla.

Uso: py -3 04_integracion_final/06_verificar_integracion.py [--proyecto RUTA] [--entrada RUTA]
"""
import argparse, csv, json, sys
from collections import Counter
from pathlib import Path

csv.field_size_limit(10**9)
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
def buscar_proyecto(p):
    if p: return Path(p).resolve()
    for d in ROOT.parents:
        if (d / 'integracion_corpus/resultados_validados/universo').is_dir(): return d
    sys.exit('No se encontró IPRE-Min-main (carpeta con integracion_corpus/). Indíquela con --proyecto.')
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--proyecto')
ap.add_argument('--entrada', type=Path, default=HERE / 'salida')
ap.add_argument('--lectura', type=Path, default=HERE / 'entrada/lectura_dirigida')
args = ap.parse_args()
PROJ, D = buscar_proyecto(args.proyecto), args.entrada.resolve()
rd = lambda p: list(csv.DictReader(open(p, encoding='utf-8-sig', newline='')))

U = rd(PROJ / 'integracion_corpus/resultados_validados/universo/01_corpus_unificado_identidad.csv')
R = rd(D / '01_corpus_completo_cribado.csv')
F = {n: rd(D / n) for n in ('02_corpus_incluido.csv', '03_corpus_excluido.csv', '04_nucleo_desempeno_IN.csv')}
PR = json.loads((D / '06_prisma.json').read_text(encoding='utf-8'))
checks = []
def check(name, ok, detail=''):
    checks.append({'comprobacion': name, 'resultado': 'OK' if ok else 'FALLA', 'detalle': detail})

orig = list(U[0].keys())
check('Una fila por publicación del corpus unificado', len(R) == len(U) == len({r['id_publicacion'] for r in R}), f'{len(R)} filas')
check('Columnas originales conservadas sin cambios', all({k: r[k] for k in orig} == u for r, u in zip(R, U)))
inc = [r for r in R if r['decision_final'] == 'INCLUIDO']; exc = [r for r in R if r['decision_final'] == 'EXCLUIDO']
check('Partición incluidos/excluidos', len(inc) + len(exc) == len(R), f'{len(inc)} + {len(exc)}')
ids = lambda rs: [r['id_publicacion'] for r in rs]
check('02_corpus_incluido coincide', ids(F['02_corpus_incluido.csv']) == ids(inc))
check('03_corpus_excluido coincide', ids(F['03_corpus_excluido.csv']) == ids(exc))
check('04_nucleo coincide con decision_cribado_desempeno = IN',
      ids(F['04_nucleo_desempeno_IN.csv']) == ids([r for r in R if r['decision_cribado_desempeno'] == 'IN']))
ex1 = [r for r in R if r['decision_filtro_amplio'] == 'EXCLUIDO']
check('Excluidos en filtro amplio no se evalúan después',
      all(r['decision_pertinencia_nivel1'] == 'NO_EVALUADO' and r['decision_final'] == 'EXCLUIDO'
          and r['etapa_exclusion'] == 'filtro_amplio' for r in ex1), f'{len(ex1)} publicaciones')
check('Núcleo IN siempre incluido', all(r['decision_final'] == 'INCLUIDO' for r in R if r['decision_cribado_desempeno'] == 'IN'))
check('Toda exclusión tiene etapa, motivo y justificación',
      all(r['etapa_exclusion'] and r['motivo_exclusion'] and r['justificacion'] for r in exc))
check('Toda decisión tiene procedencia', all(r['procedencia_decision'] for r in R))
check('Valores permitidos en decisiones',
      {r['decision_final'] for r in R} <= {'INCLUIDO', 'EXCLUIDO'} and
      {r['decision_cribado_desempeno'] for r in R} <= {'IN', 'OUT', 'NO_EVALUADO'} and
      {r['requiere_revision_humana'] for r in R} <= {'si', 'no'})
check('Revisión humana solo marca incluidos', all(r['decision_final'] == 'INCLUIDO' for r in R if r['requiere_revision_humana'] == 'si'))

# Archivos de lectura dirigida: formato válido
bad = []
for p in sorted(args.lectura.glob('*.txt')):
    for n, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
        t = line.strip()
        if not t or t.startswith('#') or p.name.endswith('_candidatos.txt'): continue
        parts = t.split(' ')
        if len(parts) < 2 or not parts[0].replace('v8:', '').replace('v9:', '').isdigit(): bad.append(f'{p.name}:{n}')
check('Formato de los archivos de lectura dirigida', not bad, '; '.join(bad[:5]))

c = PR['cribado']
check('PRISMA cuadra con el corpus',
      c['publicaciones_evaluadas'] == len(R) and PR['incluidos']['total'] == len(inc)
      and c['etapa1_filtro_amplio']['excluidas'] == len(ex1)
      and c['etapa2_pertinencia_operacional']['excluidas'] == len(exc) - len(ex1)
      and PR['deduplicacion']['registros_integrados'] - PR['deduplicacion']['duplicados_eliminados'] == len(R))

res = {'estado': 'VERIFICADO' if all(x['resultado'] == 'OK' for x in checks) else 'CON_FALLAS',
       'resumen': {'publicaciones': len(R), 'incluidas': len(inc), 'excluidas': len(exc),
                   'nucleo_IN': sum(r['decision_cribado_desempeno'] == 'IN' for r in R),
                   'requiere_revision_humana': sum(r['requiere_revision_humana'] == 'si' for r in R),
                   'procedencia': dict(Counter(r['procedencia_decision'] for r in R).most_common())},
       'comprobaciones': checks}
(D / 'Verificacion_integridad.json').write_text(json.dumps(res, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
for x in checks: print(f"[{x['resultado']}] {x['comprobacion']}" + (f" ({x['detalle']})" if x['detalle'] else ''))
if res['estado'] != 'VERIFICADO': sys.exit('Verificación con fallas: revisar Verificacion_integridad.json')
print('Verificación completa:', len(checks), 'comprobaciones OK')
