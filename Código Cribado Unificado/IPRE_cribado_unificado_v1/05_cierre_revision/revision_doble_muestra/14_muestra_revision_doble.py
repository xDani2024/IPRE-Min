"""Muestra para validar el cribado con revisión ciega de Daniela y Joaquín.

Muestra aleatoria estratificada del corpus incluido (semilla fija), igual en ambos modos:
  - 5 % del núcleo de desempeño (29 de 584);
  - 3 % del resto del corpus incluido (98 de 3.267).

Modos de reparto (--modo):
  profesor   (definido por el profesor) muestra general del 1 % de las 3.851 (38) y muestra
             del 5 % del núcleo (29), sin repetir publicaciones. En cada una, 8 y 7 publicaciones
             las revisan ambos y el resto se reparte en mitades: 15 + 15 + 8 y 11 + 11 + 7.
             Las preguntas se evalúan por separado: la muestra general valida la pertenencia
             al corpus y la del núcleo valida el núcleo (A + B + C). El acuerdo entre revisores
             se mide en las 8 comunes (corpus) y en las 7 comunes (núcleo). -> 41 por revisor.
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
  py -3 14_muestra_revision_doble.py --modo profesor              diseño del profesor: 41 por revisor
  py -3 14_muestra_revision_doble.py --modo completa              opción 1: 127 por revisor
  py -3 14_muestra_revision_doble.py --modo repartida             opción 2: 78 por revisor
  py -3 14_muestra_revision_doble.py --modo repartida --comparar  compara las planillas completas de ese modo
  py -3 14_muestra_revision_doble.py --modo profesor --separar    versión por separado: muestra_general_<revisor>.xlsx
          (solo corpus) y muestra_nucleo_<revisor>.xlsx (solo núcleo), con las respuestas ya dadas traspasadas.
          --comparar usa estas planillas si existen las dos de cada revisor.
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
MODOS = ('profesor', 'completa', 'repartida')
SALIDA = AQUI / 'muestra_revision_repartida'
MODO = 'repartida'
CLAVE = SALIDA / 'clave_muestra_NO_ABRIR_hasta_terminar.csv'
REVISORES = ['Daniela', 'Joaquin']
SEMILLA = 20261119
FRACCION = {'IN': 0.05, 'resto': 0.03}
# Modo profesor: 1 % de todo el corpus incluido (muestra general) y 5 % del núcleo.
# En cada muestra, COMUNES publicaciones las revisan ambos y el resto se reparte en mitades.
FRACCION_PROFESOR = {'general': 0.01, 'nucleo': 0.05}
COMUNES = {'general': 8, 'nucleo': 7}
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
    if MODO == 'profesor':
        # Muestra del núcleo (5 % de 584) y muestra general (1 % de las 3.851, sin repetir las del núcleo).
        n_nuc = int(len(nucleo) * FRACCION_PROFESOR['nucleo'])
        n_gen = int(len(filas) * FRACCION_PROFESOR['general'])
        m_nucleo = muestra_estratificada(nucleo, n_nuc, rng)
        ya = {r['id_publicacion'] for r in m_nucleo}
        m_resto = muestra_estratificada([r for r in filas if r['id_publicacion'] not in ya], n_gen, rng)
        muestra_de = {**{r['id_publicacion']: 'nucleo' for r in m_nucleo}, **{r['id_publicacion']: 'general' for r in m_resto}}
        revisores_de = {}
        for nombre, grupo_m in (('nucleo', m_nucleo), ('general', m_resto)):
            orden = list(grupo_m)
            comunes = set(r['id_publicacion'] for r in rng.sample(orden, COMUNES[nombre]))
            inicio, k = rng.randrange(len(REVISORES)), 0
            for r in orden:  # orden por proceso: la alternancia reparte una mezcla similar de procesos
                if r['id_publicacion'] in comunes:
                    revisores_de[r['id_publicacion']] = list(REVISORES)
                else:
                    revisores_de[r['id_publicacion']] = [REVISORES[(inicio + k) % len(REVISORES)]]
                    k += 1
        n_res = n_gen
    else:
        n_nuc, n_res = round(len(nucleo) * FRACCION['IN']), round(len(resto) * FRACCION['resto'])
        m_nucleo = muestra_estratificada(nucleo, n_nuc, rng)
        m_resto = muestra_estratificada(resto, n_res, rng)
        muestra_de = {**{r['id_publicacion']: 'nucleo' for r in m_nucleo}, **{r['id_publicacion']: 'resto' for r in m_resto}}
        # Núcleo: ambos revisores. Resto: ambos (completa) o en alternancia (repartida).
        revisores_de = {r['id_publicacion']: list(REVISORES) for r in m_nucleo}
        inicio = rng.randrange(len(REVISORES))
        for k, r in enumerate(m_resto):
            revisores_de[r['id_publicacion']] = list(REVISORES) if MODO == 'completa' else [REVISORES[(inicio + k) % len(REVISORES)]]
    muestra = m_nucleo + m_resto

    SALIDA.mkdir(exist_ok=True)
    with open(CLAVE, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['id_publicacion', 'muestra', 'grupo', 'revisores', 'decision_automatica_corpus', 'decision_automatica_nucleo', 'proceso_candidato'])
        for r in sorted(muestra, key=lambda r: r['id_publicacion']):
            es_in = r['decision_cribado_desempeno'] == 'IN'
            w.writerow([r['id_publicacion'], muestra_de[r['id_publicacion']], 'nucleo' if es_in else 'resto', ';'.join(revisores_de[r['id_publicacion']]),
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
    if MODO == 'profesor':
        for nombre in ('general', 'nucleo'):
            ids = [i for i, m in muestra_de.items() if m == nombre]
            base = len(filas) if nombre == 'general' else len(nucleo)
            por = Counter(';'.join(revisores_de[i]) for i in ids)
            print(f'Muestra {nombre}: {len(ids)} de {base} ({100 * FRACCION_PROFESOR[nombre]:.0f} %) | '
                  + ' | '.join(f'{k.replace(";", " y ")}: {v}' for k, v in sorted(por.items())))
        print('Por revisor: ' + ', '.join(f'{k} {v}' for k, v in cuenta.items()) + f' | carpeta: {SALIDA.name}')
        return
    print(f'Modo {MODO} | muestra: {len(muestra)} publicaciones | núcleo {n_nuc} de {len(nucleo)} (5 %, ambos revisores) | '
          f'resto {n_res} de {len(resto)} (3 %, {"ambos revisores" if MODO == "completa" else "repartido"}) | '
          f'por revisor: ' + ', '.join(f'{k} {v}' for k, v in cuenta.items()) + f' | carpeta: {SALIDA.name}')


# ---------------------------------------------------------------------------
# Versión por separado (modo profesor): dos planillas por revisor, una por muestra.
# ---------------------------------------------------------------------------
PREGUNTA_DE_MUESTRA = {'general': 'corpus', 'nucleo': 'nucleo'}
INSTRUCCIONES_SEP = {
    'corpus': [
        'Lea título, palabras clave y resumen de cada publicación y responda una sola pregunta. No consulte la planilla del otro revisor ni la clave.',
        INSTRUCCIONES[1],
        'Use duda solo si el resumen no permite decidir (por ejemplo, sin resumen), y explique qué falta.',
        'Si el resumen está en otro idioma, tradúzcalo (traductor o IA) y decida por el contenido.',
        'motivo_corpus: una o dos frases que justifiquen la respuesta con lo que dice la publicación.',
        'Algunas publicaciones también las revisa el otro revisor y otras solo usted; la planilla no indica cuáles. Revise todas con el mismo cuidado.',
    ],
    'nucleo': [
        'Lea título, palabras clave y resumen de cada publicación y responda una sola pregunta. No consulte la planilla del otro revisor ni la clave.',
        INSTRUCCIONES[2],
        'Responda si solo cuando se cumplen A, B y C. Si no es operación minera a cielo abierto, no cumple A: responda no.',
        'C puede ser cualitativo si nombra un indicador de la tarea y el sentido del cambio (p. ej. "reduce el consumo"); '
        'no basta con "resultados positivos", "beneficios" o "viabilidad".',
        'Use duda solo si el resumen no permite decidir (por ejemplo, sin resumen), y explique qué falta.',
        'Si el resumen está en otro idioma, tradúzcalo (traductor o IA) y decida por el contenido.',
        'motivo_nucleo: escriba A, B y C en una o dos frases cada uno (qué tarea, qué evalúa, qué resultado informa).',
        'Algunas publicaciones también las revisa el otro revisor y otras solo usted; la planilla no indica cuáles. Revise todas con el mismo cuidado.',
    ],
}


def archivo_separado(muestra, rev):
    return SALIDA / f'muestra_{muestra}_{rev}.xlsx'


def leer_planilla(ruta):
    ws = openpyxl.load_workbook(ruta, read_only=True)['Revision']
    filas = list(ws.iter_rows(values_only=True))
    cab = list(filas[0])
    return {r[1]: {c: ('' if v is None else str(v).strip()) for c, v in zip(cab, r) if c} for r in filas[1:] if r[1]}


def separar(sobrescribir=False):
    """Crea muestra_general_<revisor>.xlsx (solo corpus) y muestra_nucleo_<revisor>.xlsx (solo núcleo)
    con las mismas publicaciones asignadas, y traspasa las respuestas ya dadas en muestra_revision_<revisor>.xlsx."""
    if MODO != 'profesor':
        raise SystemExit('--separar solo aplica al modo profesor.')
    clave = {r['id_publicacion']: r for r in csv.DictReader(open(CLAVE, encoding='utf-8'))}
    corpus = {r['id_publicacion']: r for r in csv.DictReader(open(CORPUS, encoding='utf-8-sig')) if r['id_publicacion'] in clave} \
        if CORPUS.exists() else {}
    rng = random.Random(SEMILLA + 1)
    for rev in REVISORES:
        unida = SALIDA / f'muestra_revision_{rev}.xlsx'
        previas = leer_planilla(unida) if unida.exists() else {}
        for muestra, pregunta in PREGUNTA_DE_MUESTRA.items():
            destino = archivo_separado(muestra, rev)
            if destino.exists() and not sobrescribir:
                print('Ya existe, no se sobrescribe:', destino.name)
                continue
            ids = sorted(i for i, c in clave.items() if c['muestra'] == muestra and rev in c['revisores'].split(';'))
            rng.shuffle(ids)
            cols = COLUMNAS[:6] + [f'corresponde_{pregunta}', f'motivo_{pregunta}', 'comentario']
            wb = openpyxl.Workbook()
            ins = wb.active
            ins.title = 'Instrucciones'
            titulo = 'pertenencia al corpus' if pregunta == 'corpus' else 'núcleo de desempeño (A + B + C)'
            ins['A1'] = f'Validación del cribado: {titulo} - revisor: {rev} ({len(ids)} publicaciones)'
            ins['A1'].font = Font(bold=True, size=13)
            for k, t in enumerate(INSTRUCCIONES_SEP[pregunta], 3):
                ins.cell(k, 1, f'{k - 2}. {t}').alignment = Alignment(wrap_text=True)
            ins.column_dimensions['A'].width = 120
            ws = wb.create_sheet('Revision')
            ws.append(cols)
            traspasadas = 0
            for n, i in enumerate(ids, 1):
                prev = previas.get(i, {})
                if prev:
                    base = [prev.get(c, '') for c in COLUMNAS[1:6]]
                else:
                    r = corpus.get(i)
                    if r is None:
                        raise SystemExit(f'No encuentro {i} ni en {unida.name} ni en el corpus. Indique --corpus.')
                    base = [i, r['anio_referencia'], r['titulo_usado_en_cribado'] or r['titulo'], r['palabras_clave'],
                            ' '.join(r['resumen'].split()) or '(sin resumen)']
                resp = [prev.get(f'corresponde_{pregunta}', '').lower(), prev.get(f'motivo_{pregunta}', ''), prev.get('comentario', '')]
                traspasadas += resp[0] in RESPUESTAS
                ws.append([n] + base + [v or None for v in resp])
            amarillo = PatternFill('solid', fgColor='FFF2CC')
            for c in ws[1]:
                c.font = Font(bold=True)
                if c.column > 6:
                    c.fill = amarillo
            for col, ancho in zip('ABCDEFGHI', [5, 30, 6, 50, 25, 90, 12, 60, 25]):
                ws.column_dimensions[col].width = ancho
            for fila in ws.iter_rows(min_row=2):
                for c in fila:
                    c.alignment = Alignment(wrap_text=c.column in (4, 6, 8, 9), vertical='top')
            ws.freeze_panes = 'D2'
            dv = DataValidation(type='list', formula1='"si,no,duda"', allow_blank=True)
            dv.add(f'G2:G{len(ids) + 1}')
            ws.add_data_validation(dv)
            wb.save(destino)
            print(f'Creada: {destino.name} | {len(ids)} publicaciones | respuestas traspasadas: {traspasadas}')


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


def preguntas_de(c):
    """Pregunta que valida cada muestra. En modo profesor se evalúan por separado:
    la muestra general valida la pertenencia al corpus y la del núcleo valida el núcleo (A + B + C).
    En los otros modos se evalúan ambas preguntas en todas las publicaciones."""
    if MODO == 'profesor':
        return ('corpus',) if c.get('muestra') == 'general' else ('nucleo',)
    return ('corpus', 'nucleo')


def comparar():
    clave = {r['id_publicacion']: r for r in csv.DictReader(open(CLAVE, encoding='utf-8'))}
    resp = {}
    for rev in REVISORES:
        separadas = [archivo_separado(m, rev) for m in PREGUNTA_DE_MUESTRA] if MODO == 'profesor' else []
        if separadas and all(f.exists() for f in separadas):
            fuentes = separadas  # versión por separado: una planilla por muestra
        else:
            fuentes = [SALIDA / f'muestra_revision_{rev}.xlsx']
        print(f'{rev}: ' + ', '.join(f.name for f in fuentes))
        resp[rev] = {}
        for f in fuentes:
            for i, r in leer_planilla(f).items():
                resp[rev].setdefault(i, {}).update({c: v.lower() if c.startswith('corresponde_') else v for c, v in r.items()})
    a, b = REVISORES
    comunes = [i for i, c in clave.items() if len(c['revisores'].split(';')) > 1]
    incompletas = [(rev, i) for rev in REVISORES for i, r in resp[rev].items() if i in clave
                   and any(r.get(f'corresponde_{p}') not in RESPUESTAS for p in preguntas_de(clave[i]))]
    salida = {'modo': MODO, 'publicaciones': len(clave), 'comunes': len(comunes), 'filas_incompletas': len(incompletas)}
    casos = []

    for pregunta in ('corpus', 'nucleo'):
        campo, col_auto = f'corresponde_{pregunta}', f'decision_automatica_{pregunta}'
        aplica = {i for i, c in clave.items() if pregunta in preguntas_de(c)}
        # 1. Acuerdo entre revisores en las publicaciones comunes donde aplica la pregunta.
        validas = [i for i in comunes if i in aplica and resp[a][i].get(campo, '') in RESPUESTAS and resp[b][i].get(campo, '') in RESPUESTAS]
        salida[f'{pregunta}_entre_revisores'] = resumen([(resp[a][i].get(campo, ''), resp[b][i].get(campo, '')) for i in validas])
        if MODO != 'profesor':
            for m in sorted({c.get('muestra', c['grupo']) for c in clave.values()}):
                ids = [i for i in validas if clave[i].get('muestra', clave[i]['grupo']) == m]
                if ids and len(ids) < len(validas):
                    salida[f'{pregunta}_entre_revisores_muestra_{m}'] = resumen([(resp[a][i].get(campo, ''), resp[b][i].get(campo, '')) for i in ids])
        # 2. Decisión humana de referencia: consenso en las comunes; respuesta del revisor en las propias.
        humana = {}
        for i, c in clave.items():
            if i not in aplica:
                continue
            revs = c['revisores'].split(';')
            if len(revs) > 1:
                va, vb = resp[a][i].get(campo, ''), resp[b][i].get(campo, '')
                if va == vb and va in ('si', 'no'):
                    humana[i] = va
            else:
                v = resp[revs[0]].get(i, {}).get(campo, '')
                if v in ('si', 'no'):
                    humana[i] = v
        if MODO == 'profesor':
            # Toda la muestra general es 'si' en corpus y toda la del núcleo es 'si' en núcleo:
            # el acuerdo con la decisión automática es la proporción confirmada por la revisión (precisión).
            m = 'general' if pregunta == 'corpus' else 'nucleo'
            salida[f'{pregunta}_confirmado_en_muestra_{m}'] = resumen([(humana[i], clave[i][col_auto]) for i in humana])
        else:
            for grupo in ('nucleo', 'resto'):
                ids = [i for i in humana if clave[i]['grupo'] == grupo]
                salida[f'{pregunta}_revision_vs_automatico_{grupo}'] = resumen([(humana[i], clave[i][col_auto]) for i in ids])
            salida[f'{pregunta}_revision_vs_automatico_total'] = resumen([(humana[i], clave[i][col_auto]) for i in humana])

    for i, c in sorted(clave.items(), key=lambda x: (x[1].get('muestra', x[1]['grupo']), x[0])):
        revs = c['revisores'].split(';')
        ps = preguntas_de(c)
        r_ = {rv: resp[rv].get(i, {}) for rv in REVISORES}
        valores = [r_[rv].get(f'corresponde_{p}', '') for rv in revs for p in ps]
        desacuerdo = len(revs) > 1 and any(r_[a].get(f'corresponde_{p}') != r_[b].get(f'corresponde_{p}') for p in ps)
        distinto_auto = any(r_[rv].get(f'corresponde_{p}') in ('si', 'no') and r_[rv].get(f'corresponde_{p}') != c[f'decision_automatica_{p}']
                            for rv in revs for p in ps)
        if desacuerdo or distinto_auto or 'duda' in valores:
            casos.append([i, c.get('muestra', c['grupo']), '/'.join(ps), c['revisores'], c['decision_automatica_corpus'], c['decision_automatica_nucleo']]
                         + [r_[rv].get(k, '') for rv in REVISORES for k in ('corresponde_corpus', 'corresponde_nucleo')]
                         + [r_[rv].get('motivo_nucleo' if 'nucleo' in ps else 'motivo_corpus', '') for rv in REVISORES] + [''])

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Resumen'
    ws.append(['indicador', 'n', 'acuerdo', 'kappa'])
    for k, v in salida.items():
        ws.append([k, v['n'], v['acuerdo'], v['kappa']] if isinstance(v, dict) else [k, v])
    ws2 = wb.create_sheet('Casos_a_conversar')
    ws2.append(['id_publicacion', 'muestra', 'pregunta', 'revisores', 'auto_corpus', 'auto_nucleo', f'{a}_corpus', f'{a}_nucleo',
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
                    help='profesor: 41 por revisor (1 %% general + 5 %% núcleo); completa: 127; repartida: 78')
    ap.add_argument('--comparar', action='store_true')
    ap.add_argument('--separar', action='store_true', help='modo profesor: crea una planilla por muestra y traspasa las respuestas ya dadas')
    ap.add_argument('--sobrescribir', action='store_true', help='con --separar, rehace planillas separadas existentes')
    ap.add_argument('--corpus', default=str(CORPUS))
    ap.add_argument('--motor', default=str(MOTOR_V8))
    ap.add_argument('--salida', default=None, help='carpeta de salida (por defecto muestra_revision_<modo>)')
    args = ap.parse_args()
    MODO = args.modo
    CORPUS, MOTOR_V8 = Path(args.corpus), Path(args.motor)
    SALIDA = Path(args.salida) if args.salida else AQUI / f'muestra_revision_{MODO}'
    CLAVE = SALIDA / 'clave_muestra_NO_ABRIR_hasta_terminar.csv'
    for f in (CORPUS, MOTOR_V8):
        if not args.comparar and not args.separar and not f.exists():
            raise SystemExit(f'No se encontró {f}. Deje el script en 05_cierre_revision/revision_doble_muestra o indique la ruta con --corpus y --motor.')
    if args.separar:
        separar(args.sobrescribir)
    elif args.comparar:
        comparar()
    else:
        crear()
