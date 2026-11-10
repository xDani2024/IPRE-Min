"""Reproduce el cribado del corpus unificado sin red ni API key.

Cadena: filtro amplio original -> reglas originales v6/v7/v8/v9 -> reglas de pertinencia operacional
(Nivel 1) -> integración con las decisiones de lectura dirigida congeladas -> PRISMA -> verificación.
Con openpyxl aplica además las planillas completadas de 05_cierre_revision/planillas/ (revisión humana y
muestra de validación) y recalcula PRISMA y la verificación sobre el corpus cerrado, que es el corpus final.
La descripción bibliométrica se ejecuta sobre el corpus final (tablas y redes con la biblioteca estándar).

No regenera juicios de lectura: las decisiones de entrada/lectura_dirigida/ son entradas congeladas.
No modifica los archivos archivados: cada ejecución exige una carpeta de destino nueva.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
csv.field_size_limit(10**9)
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sha_lf(p): return hashlib.sha256(Path(p).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
CLAVES_08 = ('registros_originales', 'publicaciones_unificadas', 'reduccion_total', 'publicaciones_multifuente', 'por_fuente')
def valores_08(p):
    """Contenido de 08_resumen_validacion.json que usa el cribado: conteos y entradas por base (ruta normalizada)."""
    d = json.loads(Path(p).read_text(encoding='utf-8'))
    ent = {b: {'registros': v['registros'], 'ruta': v['ruta'].replace('\\', '/'), 'sha256': v['sha256']} for b, v in d['entradas'].items()}
    return {**{k: d[k] for k in CLAVES_08}, 'entradas': ent}
def verificar_entrada(proj, rel, h, proc):
    """Exige la misma instantánea. Tolera solo diferencias que no cambian el contenido:
    saltos de línea CRLF/LF (p. ej., Git en Windows) y, en 08_resumen_validacion.json, campos que el cribado no usa."""
    f = proj / rel
    if not f.exists(): raise FileNotFoundError('Falta la entrada: ' + rel)
    if sha(f) == h: return 'identica'
    if sha_lf(f) == proc['entradas_sha256_lf'].get(rel): return 'identica_salvo_saltos_de_linea'
    if rel.endswith('08_resumen_validacion.json'):
        actual, esperado = valores_08(f), proc['valores_usados_de_08_resumen_validacion']
        if actual == esperado: return 'contenido_usado_identico'
        dif = [k for k in esperado if actual.get(k) != esperado[k]]
        raise ValueError('08_resumen_validacion.json difiere en datos que usa el cribado: ' + ', '.join(dif) +
                         '. Use la integración cerrada del 09-nov-2026 sin volver a ejecutarla.')
    raise ValueError('La entrada no coincide con la instantánea registrada: ' + rel +
                     '. Si el repositorio se clonó con Git, revise la conversión de saltos de línea (.gitattributes).')
def buscar_proyecto(p):
    if p: return Path(p).resolve()
    for d in ROOT.parents:
        if (d / 'integracion_corpus/resultados_validados/universo').is_dir(): return d
    sys.exit('No se encontró IPRE-Min-main (carpeta con integracion_corpus/). Indíquela con --proyecto.')
def run(script, *args):
    print('Ejecutando', script.relative_to(ROOT), flush=True)
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    r = subprocess.run([sys.executable, '-I', str(script), *map(str, args)], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env)
    (logs / (script.stem + '.txt')).write_text(r.stdout + '\n' + r.stderr, encoding='utf-8', newline='\n')
    if r.returncode: raise RuntimeError(script.name + '\n' + r.stdout[-3000:] + '\n' + r.stderr[-3000:])
def same(stage, produced):
    """Coteja una salida con su copia archivada o, si no se archivó el archivo, con su huella SHA-256."""
    arch = ROOT / stage / 'salida_archivada'
    huellas = json.loads((arch / 'huellas_sha256.json').read_text(encoding='utf-8'))['archivos']
    expected = huellas.get(produced.name)
    if expected is None: raise KeyError('Sin referencia archivada para ' + produced.name)
    got = sha(produced)
    if got != expected and not ((arch / produced.name).exists() and sha_lf(arch / produced.name) == sha_lf(produced)):
        raise ValueError(f'No coincide la reproducción: {stage}/{produced.name}. Ver bitácoras en la carpeta de salida.')
    checks.append({'etapa': stage, 'archivo': produced.name, 'sha256': got, 'reproducido_identico': True})

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida', type=Path, default=ROOT / 'reproduccion_local')
    p.add_argument('--proyecto', help='Carpeta IPRE-Min-main (por defecto se busca hacia arriba).')
    args = p.parse_args(); dest = args.salida.resolve(); proj = buscar_proyecto(args.proyecto)
    if dest.exists() and any(dest.iterdir()):
        p.error(f'La carpeta de salida ya tiene archivos ({dest.name}). Bórrela o use --salida con otra carpeta.')
    checks = []

    # Entradas y motores: se verifican antes de crear la carpeta de salida
    proc = json.loads((ROOT / 'PROCEDENCIA_DEL_PAQUETE.json').read_text(encoding='utf-8'))
    for rel, h in proc['entradas_sha256'].items():
        estado = verificar_entrada(proj, rel, h, proc)
        if estado != 'identica': print('Entrada verificada (' + estado.replace('_', ' ') + '):', rel, flush=True)
        checks.append({'etapa': 'entradas', 'archivo': rel, 'sha256': h, 'reproducido_identico': True, 'verificacion': estado})
    for rel, h in proc['motores_originales_sha256'].items():
        if sha_lf(ROOT / 'motores_originales' / rel) != proc['motores_originales_sha256_lf'][rel]: raise ValueError('Motor original modificado: ' + rel)

    dest.mkdir(parents=True, exist_ok=True); logs = dest / 'bitacoras'; logs.mkdir(exist_ok=True)
    S = {k: dest / k for k in ('01_filtro_amplio', '02_nucleo_desempeno', '03_pertinencia_operacional',
                               '04_integracion_final', '05_cierre_revision', '06_descriptivos')}

    run(ROOT / '01_filtro_amplio/01_aplicar_filtro_amplio.py', '--proyecto', proj, '--salida', S['01_filtro_amplio'])
    for n in ('etapa2_filtro_amplio.csv', 'etapa2_resumen.json'): same('01_filtro_amplio', S['01_filtro_amplio'] / n)
    run(ROOT / '02_nucleo_desempeno/02_aplicar_reglas_v6_a_v9.py', '--entrada', S['01_filtro_amplio'], '--salida', S['02_nucleo_desempeno'])
    for n in ('etapa3a_nucleo_reglas.csv', 'etapa3a_resumen.json'): same('02_nucleo_desempeno', S['02_nucleo_desempeno'] / n)
    run(ROOT / '03_pertinencia_operacional/03_proponer_reglas_nivel1.py', '--filtro', S['01_filtro_amplio'],
        '--nucleo', S['02_nucleo_desempeno'], '--salida', S['03_pertinencia_operacional'])
    for n in ('etapa3b_nivel1_reglas.csv', 'etapa3b_resumen.json'): same('03_pertinencia_operacional', S['03_pertinencia_operacional'] / n)
    run(ROOT / '04_integracion_final/04_integrar_decisiones.py', '--proyecto', proj, '--filtro', S['01_filtro_amplio'],
        '--nucleo', S['02_nucleo_desempeno'], '--nivel1', S['03_pertinencia_operacional'], '--salida', S['04_integracion_final'])
    run(ROOT / '04_integracion_final/05_generar_cifras_prisma.py', '--proyecto', proj, '--entrada', S['04_integracion_final'])
    run(ROOT / '04_integracion_final/06_verificar_integracion.py', '--proyecto', proj, '--entrada', S['04_integracion_final'])
    for n in ('01_corpus_completo_cribado.csv', '02_corpus_incluido.csv', '03_corpus_excluido.csv', '04_nucleo_desempeno_IN.csv',
              '05_resumen_cribado.json', '06_prisma.json', 'Verificacion_integridad.json'):
        same('04_integracion_final', S['04_integracion_final'] / n)

    # ---- cierre: revisión humana y concordancia (requiere openpyxl para leer las planillas completadas) ----
    corpus_desc = S['04_integracion_final'] / '02_corpus_incluido.csv'; final = S['04_integracion_final']
    cierre = {'estado': 'omitido: falta openpyxl; el corpus final queda sin la revisión humana'}
    try:
        import openpyxl  # noqa: F401
        tiene_openpyxl = True
    except ImportError:
        tiene_openpyxl = False
        print('AVISO: falta openpyxl. Instale requirements_complementarios.txt para aplicar la revisión humana.', flush=True)
    if tiene_openpyxl:
        C = S['05_cierre_revision']
        run(ROOT / '05_cierre_revision/07_preparar_planillas.py', '--entrada', S['04_integracion_final'], '--filtro', S['01_filtro_amplio'],
            '--salida', C / 'planillas_en_blanco')
        same('05_cierre_revision', C / 'planillas_en_blanco/03_clave_muestra_validacion.csv')
        run(ROOT / '05_cierre_revision/08_aplicar_revision_y_concordancia.py', '--entrada', S['04_integracion_final'],
            '--planillas', ROOT / '05_cierre_revision/planillas', '--salida', C / 'salida')
        run(ROOT / '04_integracion_final/05_generar_cifras_prisma.py', '--proyecto', proj, '--entrada', C / 'salida')
        run(ROOT / '04_integracion_final/06_verificar_integracion.py', '--proyecto', proj, '--entrada', C / 'salida')
        for n in ('01_corpus_completo_cribado.csv', '02_corpus_incluido.csv', '03_corpus_excluido.csv', '04_nucleo_desempeno_IN.csv',
                  '05_resumen_cierre.json', '06_prisma.json', 'Verificacion_integridad.json', 'concordancia_muestra_validacion.json'):
            same('05_cierre_revision', C / 'salida' / n)
        cierre = json.loads((C / 'salida/05_resumen_cierre.json').read_text(encoding='utf-8'))
        corpus_desc = C / 'salida/02_corpus_incluido.csv'; final = C / 'salida'

    # ---- descriptivos sobre el corpus final (tablas y redes se cotejan con las archivadas) ----
    run(ROOT / '06_descriptivos/09_descripcion_bibliometrica.py', '--corpus', corpus_desc, '--proyecto', proj, '--salida', S['06_descriptivos'])
    if tiene_openpyxl:
        for sub in ('tablas', 'redes'):
            for f in sorted((S['06_descriptivos'] / sub).iterdir()):
                ref = ROOT / '06_descriptivos' / sub / f.name
                if sha_lf(f) != sha_lf(ref): raise ValueError('No coincide la reproducción: 06_descriptivos/' + sub + '/' + f.name)
                checks.append({'etapa': '06_descriptivos', 'archivo': sub + '/' + f.name, 'sha256': sha(f), 'reproducido_identico': True})

    pr = json.loads((final / '06_prisma.json').read_text(encoding='utf-8'))
    fin = list(csv.DictReader(open(final / '01_corpus_completo_cribado.csv', encoding='utf-8-sig', newline='')))
    d = {k: sum(r['decision_final'] == k for r in fin) for k in ('INCLUIDO', 'EXCLUIDO')}
    nucleo = sum(r['decision_cribado_desempeno'] == 'IN' for r in fin)
    report = {'estado': 'REPRODUCIDO', 'consulta_api': False, 'api_key_necesaria': False,
              'punto_de_inicio': 'Corpus unificado validado (15.297 publicaciones) e instantáneas por base registradas por la integración',
              'corpus_final': 'con revisión humana aplicada' if tiene_openpyxl else 'sin revisión humana (falta openpyxl)',
              'resultado_cribado': {'decision_final': d, 'nucleo_desempeno_IN': nucleo,
                                    'requiere_revision_humana': sum(r['requiere_revision_humana'] == 'si' for r in fin)},
              'cierre_revision_humana': cierre,
              'descriptivos_cotejados_con_archivo': tiene_openpyxl,
              'cotejos': checks,
              'limite': 'Las decisiones de lectura dirigida y de revisión humana son entradas congeladas; no se regeneran sus lecturas.'}
    (dest / 'VERIFICACION_REPRODUCCION.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Reproducción completada. INCLUIDOS:', d['INCLUIDO'], '| EXCLUIDOS:', d['EXCLUIDO'],
          '| NÚCLEO IN:', nucleo, '| cotejos SHA-256:', len(checks), flush=True)
    print('Resultados:', dest)
