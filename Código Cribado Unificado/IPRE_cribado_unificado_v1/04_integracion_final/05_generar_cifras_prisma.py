"""Etapa 4b: cifras PRISMA (identificación, deduplicación, cribado, inclusión).

Las cifras previas al cribado se leen de los archivos de integración; no se estiman.
Uso: py -3 04_integracion_final/05_generar_cifras_prisma.py [--proyecto RUTA] [--entrada RUTA]
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
ap.add_argument('--entrada', type=Path, default=HERE / 'salida', help='Carpeta con 01_corpus_completo_cribado.csv; 06_prisma.json se escribe ahí.')
args = ap.parse_args()
PROJ, DEL = buscar_proyecto(args.proyecto), args.entrada.resolve()
uni = PROJ/'integracion_corpus/resultados_validados/universo'
P = list(csv.DictReader(open(uni/'02_procedencia_registros.csv', encoding='utf-8-sig')))
V = json.load(open(uni/'08_resumen_validacion.json', encoding='utf-8'))
R = list(csv.DictReader(open(DEL/'01_corpus_completo_cribado.csv', encoding='utf-8-sig')))
src_col = next(c for c in P[0] if c.lower() in ('fuente','base','base_datos','fuente_registro'))
per = Counter(p[src_col] for p in P)
def by_base(rs):
    c = Counter()
    for r in rs:
        for b in r['fuentes'].split('|'): c[b] += 1
    return dict(c)
acc = [r for r in R if r['decision_filtro_amplio']=='ACEPTADO']
inc = [r for r in R if r['decision_final']=='INCLUIDO']
nuc = [r for r in R if r['decision_cribado_desempeno']=='IN']
out = {
 'identificacion': {
   'registros_por_base_en_integracion': dict(per),
   'total_registros_integrados': len(P),
   'nota_openalex': 'Extracción OpenAlex: API informó 9.817; recuperados 9.844; 304 duplicados internos eliminados -> 9.540 únicos; 9.534 trazados en la integración (6 sin identificador reconstruible).',
   'nota_scopus_wos': 'Los conteos crudos previos a la deduplicación interna de Scopus y WoS no están en los archivos de integración entregados; no se estiman.',
 },
 'deduplicacion': {'registros_integrados': len(P), 'duplicados_eliminados': len(P)-len(R),
                   'publicaciones_unicas': len(R), 'publicaciones_multifuente': sum('|' in r['fuentes'] for r in R),
                   'entradas_segun_08_resumen_validacion': {b: v['registros'] for b, v in V['entradas'].items()}},
 'cribado': {
   'publicaciones_evaluadas': len(R),
   'etapa1_filtro_amplio': {'aceptadas': len(acc), 'excluidas': len(R)-len(acc),
       'motivos_exclusion': dict(Counter(m.split(':')[0] for r in R if r['decision_filtro_amplio']=='EXCLUIDO' for m in r['motivo_filtro_amplio'].split('; ')))},
   'etapa2_pertinencia_operacional': {'evaluadas': len(acc), 'incluidas': len(inc), 'excluidas': len(acc)-len(inc),
       'excluidas_por_etapa': dict(Counter(r['etapa_exclusion'] for r in acc if r['decision_final']=='EXCLUIDO').most_common()),
       'motivos_exclusion': dict(Counter(r['motivo_exclusion'].split(':')[0] for r in acc if r['decision_final']=='EXCLUIDO').most_common())},
   'etapa3_cribado_desempeno_en_incluidas': {'IN': len(nuc), 'OUT': len(inc)-len(nuc)},
 },
 'incluidos': {'total': len(inc), 'por_base': by_base(inc), 'revisiones_de_literatura': sum(r['revision_de_literatura']=='si' for r in inc),
               'sin_resumen': sum('sin_resumen' in r['limitacion_informacion'] for r in inc),
               'requiere_revision_humana': sum(r['requiere_revision_humana']=='si' for r in inc)},
 'nucleo_desempeno_por_base': by_base(nuc),
 'evaluadas_por_base': by_base(R), 'nota_por_base': 'Conteos por base de publicaciones únicas; una publicación multifuente cuenta en cada base. Una publicación puede agrupar dos registros de la misma base, por eso OpenAlex suma 9.533 y WoS 5.069.',
 'glosario_motivos_nivel2': dict(sorted({r['motivo_exclusion'].split(': ',1)[0]: ('Excluida en la revisión humana de casos con información insuficiente (motivo individual en motivo_exclusion)' if r['etapa_exclusion']=='revision_humana' else r['motivo_exclusion'].split(': ',1)[1]) for r in acc if r['decision_final']=='EXCLUIDO'}.items())), 'aceptadas_filtro_amplio_por_base': by_base(acc),
}
(DEL/'06_prisma.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
print('PRISMA: registros', out['identificacion']['total_registros_integrados'], '| únicos', out['deduplicacion']['publicaciones_unicas'], '| incluidos', out['incluidos']['total'])
