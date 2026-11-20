"""Muestra para validar el cribado con revisión ciega de Daniela y Joaquín.

Muestra aleatoria estratificada del corpus incluido (semilla fija), igual en ambos modos:
  - 5 % del núcleo de desempeño (29 de 584);
  - 3 % del resto del corpus incluido (98 de 3.267).

Dos modos de reparto (--modo):
  completa   (opción 1) ambos revisan las 127 publicaciones -> 127 por revisor.
             El acuerdo entre revisores se mide en toda la muestra.
  repartida  (opción 2) ambos revisan las 29 del núcleo y las 98 del resto se
             reparten 49 y 49 -> 78 por revisor. El acuerdo se mide en el núcleo.
Cada modo guarda sus archivos en su propia carpeta: muestra_revision_completa/ o
muestra_revision_repartida/. Las planillas van en orden aleatorio y sin la decisión
automática, que queda en un archivo clave aparte.

Para cada publicación se responde:
  1. ¿Corresponde al corpus incluido (pertinencia operacional)?  si / no / duda + motivo
  2. ¿Corresponde al núcleo de desempeño (A + B + C)?           si / no / duda + motivo

Ubicación: 05_cierre_revision/revision_doble_muestra/

Uso (desde esa carpeta):
  py -3 14_muestra_revision_doble.py --modo completa              opción 1: 127 por revisor
  py -3 14_muestra_revision_doble.py --modo repartida             opción 2: 78 por revisor
  py -3 14_muestra_revision_doble.py --modo repartida --comparar  compara las planillas completas de ese modo
Si el script está en otra carpeta, indique el corpus:
  py -3 14_muestra_revision_doble.py --corpus "ruta/01_corpus_completo_cribado.csv" --motor "ruta/15_aplicar_criterio_calibrado.py"
"""
import argparse, ast, csv, json, random, re
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

AQUI = Path(__file__).resolve().parent
# Carpeta del paquete IPRE_cribado_unificado_v1: la primera carpeta superior que contiene 05_cierre_revision.
PAQUETE = next((d for d in AQUI.parents if (d / '05_cierre_revision').is_dir()), AQUI.parent)
CORPUS = PAQUETE / '05_cierre_revision/salida_archivada/01_corpus_completo_cribado.csv'
MOTOR_V8 = PAQUETE / 'motores_originales/03_cribado_v8/15_aplicar_criterio_calibrado.py'
MODOS = ('completa', 'repartida')
SALIDA = AQUI / 'muestra_revision_repartida'
MODO = 'repartida'
CLAVE = SALIDA / 'clave_muestra_NO_ABRIR_hasta_terminar.csv'
REVISORES = ['Daniela', 'Joaquin']
SEMILLA = 20261119
FRACCION = {'IN': 0.05, 'resto': 0.03}
RESPUESTAS = ['si', 'no', 'duda']

COLUMNAS = ['n', 'id_publicacion', 'anio', 'titulo', 'palabras_clave', 'resumen',
            'corresponde_corpus', 'motivo_corpus', 'corresponde_nucleo', 'motivo_nucleo', 'comentario']
A_COMPLETAR = COLUMNAS[6:]

INSTRUCCIONES = [
    'Lea título, palabras clave y resumen de cada publicación y responda las dos preguntas. No consulte la planilla del otro revisor ni la clave.',
    'corresponde_corpus: ¿la publicación trata la operación de minería a cielo abierto (procesos, equipos o actividades de la operación)? '
    'Responda no si su foco no es operacional: por ejemplo, geotecnia sin vínculo con la operación, temas ambientales, procesamiento de mineral o minería subterránea.',
    'corresponde_nucleo: ¿cumple A + B + C? A) contexto y tarea operacional en mina a cielo abierto; B) evaluación propia: el estudio mide, modela, '
    'simula u optimiza esa tarea; C) resultado operacional: informa un resultado de desempeño de la tarea (productividad, tiempos, costos, disponibilidad, consumo, etc.).',
    'Si responde no en corresponde_corpus, responda también no en corresponde_nucleo.',
    'Use duda solo si el resumen no permite decidir, y explique qué falta.',
    'motivo: una o dos frases que justifiquen la respuesta con lo que dice la publicación (p. ej. "no informa resultado de la tarea; solo describe beneficios").',
    'Algunas publicaciones también las revisa el otro revisor y otras solo usted; la planilla no indica cuáles. Revise todas con el mismo cuidado.',
]

csv.field_size_limit(10**9)


def diccionario_v8(nombre):
    for nodo in ast.parse(MOTOR_V8.read_text(encoding='utf-8')).body:
        if isinstance(nodo, ast.Assign) and getattr(nodo.targets[0], 'id', None) == nombre:
            return ast.literal_eval(nodo.value)
    raise KeyError(nombre)


def proceso_candidato(r, patrones):
    texto = ' '.join([r['titulo_usado_en_cribado'] or r['titulo'], r['palabras_clave'], r['resumen']]).lower()
    conteo = {p: len(re.findall(pat, texto, re.I)) for p, pat in patrones.items()}
    mejor = max(conteo, key=conteo.get)
    return mejor if conteo[mejor] else 'sin_senal'


def muestra_estratificada(filas, n, rng):
    """Reparte n entre procesos en proporción a su tamaño (mayor resto) y sortea al azar dentro de cada uno."""
    estratos = defaultdict(list)
    for r in filas:
        estratos[r['_candidato']].append(r)
    cuota = {k: n * len(v) / len(filas) for k, v in estratos.items()}
    asignado = {k: int(c) for k, c in cuota.items()}
    for k in sorted(cuota, key=lambda k: (-(cuota[k] - asignado[k]), k))[:n - sum(asignado.values())]:
        asignado[k] += 1
    elegidos = []
    for k in sorted(estratos):
        elegidos += rng.sample(sorted(estratos[k], key=lambda r: r['id_publicacion']), asignado[k])
    return elegidos


def crear():
    patrones = diccionario_v8('PROCESS_PATTERNS')
    filas = [r for r in csv.DictReader(open(CORPUS, encoding='utf-8-sig')) if r['decision_final'] == 'INCLUIDO']
    assert len(filas) == 3851, len(filas)
    for r in filas:
        r['_candidato'] = proceso_candidato(r, patrones)
    rng = random.Random(SEMILLA)
    nucleo = [r for r in filas if r['decision_cribado_desempeno'] == 'IN']
    resto = [r for r in filas if r['decision_cribado_desempeno'] != 'IN']
    n_nuc, n_res = round(len(nucleo) * FRACCION['IN']), round(len(resto) * FRACCION['resto'])
    m_nucleo = muestra_estratificada(nucleo, n_nuc, rng)
    m_resto = muestra_estratificada(resto, n_res, rng)

    # Núcleo: ambos revisores. Resto: en alternancia dentro del orden por proceso,
    # para que cada uno reciba una mezcla similar de procesos.
    revisores_de = {r['id_publicacion']: list(REVISORES) for r in m_nucleo}
    inicio = rng.randrange(len(REVISORES))
    for k, r in enumerate(m_resto):
        revisores_de[r['id_publicacion']] = list(REVISORES) if MODO == 'completa' else [REVISORES[(inicio + k) % len(REVISORES)]]
    muestra = m_nucleo + m_resto

    SALIDA.mkdir(exist_ok=True)
    with open(CLAVE, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['id_publicacion', 'grupo', 'revisores', 'decision_automatica_corpus', 'decision_automatica_nucleo', 'proceso_candidato'])
        for r in sorted(muestra, key=lambda r: r['id_publicacion']):
            es_in = r['decision_cribado_desempeno'] == 'IN'
            w.writerow([r['id_publicacion'], 'nucleo' if es_in else 'resto', ';'.join(revisores_de[r['id_publicacion']]),
                        'si', 'si' if es_in else 'no', r['_candidato']])

    for rev in REVISORES:
        propia = [r for r in muestra if rev in revisores_de[r['id_publicacion']]]
        rng.shuffle(propia)  # orden aleatorio: la posición no revela el grupo ni si es común
        destino = SALIDA / f'muestra_revision_{rev}.xlsx'
        if destino.exists():
            print('Ya existe, no se sobrescribe:', destino.name)
            continue
        wb = openpyxl.Workbook()
        ins = wb.active
        ins.title = 'Instrucciones'
        ins['A1'] = f'Validación del cribado - revisor: {rev} ({len(propia)} publicaciones)'
        ins['A1'].font = Font(bold=True, size=13)
        for k, t in enumerate(INSTRUCCIONES, 3):
            ins.cell(k, 1, f'{k - 2}. {t}').alignment = Alignment(wrap_text=True)
        ins.column_dimensions['A'].width = 120
        ws = wb.create_sheet('Revision')
        ws.append(COLUMNAS)
        for i, r in enumerate(propia, 1):
            ws.append([i, r['id_publicacion'], r['anio_referencia'], r['titulo_usado_en_cribado'] or r['titulo'],
                       r['palabras_clave'], ' '.join(r['resumen'].split()) or '(sin resumen)'] + [''] * len(A_COMPLETAR))
        amarillo = PatternFill('solid', fgColor='FFF2CC')
        for c in ws[1]:
            c.font = Font(bold=True)
            if c.value in A_COMPLETAR:
                c.fill = amarillo
        for col, ancho in zip('ABCDEFGHIJK', [5, 30, 6, 50, 25, 90, 12, 45, 12, 45, 25]):
            ws.column_dimensions[col].width = ancho
        ws.freeze_panes = 'D2'
        for campo in ('corresponde_corpus', 'corresponde_nucleo'):
            dv = DataValidation(type='list', formula1='"si,no,duda"', allow_blank=True)
            letra = openpyxl.utils.get_column_letter(COLUMNAS.index(campo) + 1)
            dv.add(f'{letra}2:{letra}{len(propia) + 1}')
            ws.add_data_validation(dv)
        wb.save(destino)
        print(f'Creada: {destino.name} | {len(propia)} publicaciones')
    cuenta = Counter(rv for revs in revisores_de.values() for rv in revs)
    print(f'Modo {MODO} | muestra: {len(muestra)} publicaciones | núcleo {n_nuc} de {len(nucleo)} (5 %, ambos revisores) | '
          f'resto {n_res} de {len(resto)} (3 %, {"ambos revisores" if MODO == "completa" else "repartido"}) | '
          f'por revisor: ' + ', '.join(f'{k} {v}' for k, v in cuenta.items()) + f' | carpeta: {SALIDA.name}')


def kappa(pares):
    """Kappa de Cohen. Si un lado usa una sola categoría (p. ej. la decisión automática es siempre 'si'),
    el kappa no es interpretable y se devuelve None: se informa solo el porcentaje de acuerdo."""
    n = len(pares)
    if not n or len({a for a, _ in pares}) < 2 or len({b for _, b in pares}) < 2:
        return None
    po = sum(a == b for a, b in pares) / n
    ca, cb = Counter(a for a, _ in pares), Counter(b for _, b in pares)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n ** 2
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def resumen(pares):
    return {'n': len(pares), 'acuerdo': round(sum(a == b for a, b in pares) / len(pares), 3) if pares else None, 'kappa': kappa(pares)}


def comparar():
    clave = {r['id_publicacion']: r for r in csv.DictReader(open(CLAVE, encoding='utf-8'))}
    resp = {}
    for rev in REVISORES:
        ws = openpyxl.load_workbook(SALIDA / f'muestra_revision_{rev}.xlsx', read_only=True)['Revision']
        filas = list(ws.iter_rows(values_only=True))
        cab = list(filas[0])
        resp[rev] = {r[1]: {c: ('' if v is None else str(v).strip().lower()) for c, v in zip(cab, r)} for r in filas[1:] if r[1]}
    a, b = REVISORES
    comunes = [i for i, c in clave.items() if len(c['revisores'].split(';')) > 1]
    incompletas = [(rev, i) for rev in REVISORES for i, r in resp[rev].items()
                   if r['corresponde_corpus'] not in RESPUESTAS or r['corresponde_nucleo'] not in RESPUESTAS]
    salida = {'modo': MODO, 'publicaciones': len(clave), 'comunes': len(comunes), 'filas_incompletas': len(incompletas)}
    casos = []

    for pregunta in ('corpus', 'nucleo'):
        campo, col_auto = f'corresponde_{pregunta}', f'decision_automatica_{pregunta}'
        # 1. Acuerdo entre revisores en las publicaciones comunes (todas en modo completa; las del núcleo en modo repartida).
        validas = [i for i in comunes if resp[a][i][campo] in RESPUESTAS and resp[b][i][campo] in RESPUESTAS]
        salida[f'{pregunta}_entre_revisores'] = resumen([(resp[a][i][campo], resp[b][i][campo]) for i in validas])
        for grupo in ('nucleo', 'resto'):
            ids = [i for i in validas if clave[i]['grupo'] == grupo]
            if ids and MODO == 'completa':
                salida[f'{pregunta}_entre_revisores_{grupo}'] = resumen([(resp[a][i][campo], resp[b][i][campo]) for i in ids])
        # 2. Decisión humana de referencia: consenso en las comunes; respuesta del revisor en las propias.
        humana = {}
        for i, c in clave.items():
            revs = c['revisores'].split(';')
            if len(revs) > 1:
                va, vb = resp[a][i][campo], resp[b][i][campo]
                if va == vb and va in ('si', 'no'):
                    humana[i] = va
            else:
                v = resp[revs[0]].get(i, {}).get(campo, '')
                if v in ('si', 'no'):
                    humana[i] = v
        for grupo in ('nucleo', 'resto'):
            ids = [i for i in humana if clave[i]['grupo'] == grupo]
            salida[f'{pregunta}_revision_vs_automatico_{grupo}'] = resumen([(humana[i], clave[i][col_auto]) for i in ids])
        salida[f'{pregunta}_revision_vs_automatico_total'] = resumen([(humana[i], clave[i][col_auto]) for i in humana])

    for i, c in sorted(clave.items(), key=lambda x: (x[1]['grupo'], x[0])):
        revs = c['revisores'].split(';')
        r_ = {rv: resp[rv].get(i, {}) for rv in REVISORES}
        valores = [r_[rv].get(f'corresponde_{p}', '') for rv in revs for p in ('corpus', 'nucleo')]
        desacuerdo = len(revs) > 1 and any(r_[a].get(f'corresponde_{p}') != r_[b].get(f'corresponde_{p}') for p in ('corpus', 'nucleo'))
        distinto_auto = any(r_[rv].get(f'corresponde_{p}') in ('si', 'no') and r_[rv].get(f'corresponde_{p}') != c[f'decision_automatica_{p}']
                            for rv in revs for p in ('corpus', 'nucleo'))
        if desacuerdo or distinto_auto or 'duda' in valores:
            casos.append([i, c['grupo'], c['revisores'], c['decision_automatica_corpus'], c['decision_automatica_nucleo']]
                         + [r_[rv].get(k, '') for rv in REVISORES for k in ('corresponde_corpus', 'corresponde_nucleo')]
                         + [r_[rv].get('motivo_nucleo') or r_[rv].get('motivo_corpus', '') for rv in REVISORES] + [''])

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Resumen'
    ws.append(['indicador', 'n', 'acuerdo', 'kappa'])
    for k, v in salida.items():
        ws.append([k, v['n'], v['acuerdo'], v['kappa']] if isinstance(v, dict) else [k, v])
    ws2 = wb.create_sheet('Casos_a_conversar')
    ws2.append(['id_publicacion', 'grupo', 'revisores', 'auto_corpus', 'auto_nucleo', f'{a}_corpus', f'{a}_nucleo',
                f'{b}_corpus', f'{b}_nucleo', f'motivo_{a}', f'motivo_{b}', 'decision_final'])
    for d in casos:
        ws2.append(d)
    for hoja in (ws, ws2):
        for c in hoja[1]:
            c.font = Font(bold=True)
    wb.save(SALIDA / 'resultado_validacion_muestra.xlsx')
    (SALIDA / 'resultado_validacion_muestra.json').write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
    print(json.dumps(salida, ensure_ascii=False, indent=1))
    print('Casos a conversar:', len(casos), '| guardado en resultado_validacion_muestra.xlsx')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--modo', choices=MODOS, required=True,
                    help='completa: 127 por revisor (opción 1); repartida: 78 por revisor (opción 2)')
    ap.add_argument('--comparar', action='store_true')
    ap.add_argument('--corpus', default=str(CORPUS))
    ap.add_argument('--motor', default=str(MOTOR_V8))
    ap.add_argument('--salida', default=None, help='carpeta de salida (por defecto muestra_revision_<modo>)')
    args = ap.parse_args()
    MODO = args.modo
    CORPUS, MOTOR_V8 = Path(args.corpus), Path(args.motor)
    SALIDA = Path(args.salida) if args.salida else AQUI / f'muestra_revision_{MODO}'
    CLAVE = SALIDA / 'clave_muestra_NO_ABRIR_hasta_terminar.csv'
    for f in (CORPUS, MOTOR_V8):
        if not args.comparar and not f.exists():
            raise SystemExit(f'No se encontró {f}. Deje el script en 05_cierre_revision/revision_doble_muestra o indique la ruta con --corpus y --motor.')
    comparar() if args.comparar else crear()
