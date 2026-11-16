"""Construye 13_reparto_y_consolidacion.ipynb (se mantiene como fuente versionable)."""
import sys
import nbformat as nbf

from pathlib import Path

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell
celdas = []

celdas.append(md("""# Lectura del corpus incluido: reparto y consolidación

Este notebook organiza la última etapa de la revisión bibliométrica. Cada publicación del corpus incluido (3.851) se lee para registrar en detalle su **objetivo, metodologías, datos, indicadores, resultados y proceso**. Con eso se agrupan las temáticas por proceso y se construye el mapa de brechas.

Tiene dos partes:

1. **Reparto.** Divide el corpus entre los revisores y genera una planilla Excel para cada uno. Se ejecuta una vez.
2. **Consolidación.** Lee las planillas completas, valida, mide el acuerdo en la muestra común y genera el Excel unificado. Se ejecuta cuando las planillas estén listas, y puede repetirse.

Las reglas de lectura están en `PROTOCOLO_LECTURA.md`."""))

celdas.append(md("## 0. Parámetros"))
celdas.append(code("""from pathlib import Path
import ast, csv, json, random, re
from collections import Counter, defaultdict

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

AQUI = Path.cwd()
PAQUETE = AQUI.parent                       # IPRE_cribado_unificado_v1
CORPUS = PAQUETE / '05_cierre_revision/salida_archivada/01_corpus_completo_cribado.csv'
MOTOR_V8 = PAQUETE / 'motores_originales/03_cribado_v8/15_aplicar_criterio_calibrado.py'

REVISORES = ['Daniela', 'Joaquin']
SEMILLA = 20261116
FRACCION_COMUN = 0.05        # muestra leída por ambos revisores
TAMANO_LOTE = 50

REPARTO = AQUI / 'reparto'               # planillas que se entregan
COMPLETAS = AQUI / 'planillas_completas'  # aquí se dejan las planillas ya llenas
CONSOLIDADO = AQUI / 'consolidado'
for d in (REPARTO, COMPLETAS, CONSOLIDADO):
    d.mkdir(exist_ok=True)
csv.field_size_limit(10**9)"""))

celdas.append(md("""## 1. Corpus incluido

Se lee el corpus cerrado del cribado y se verifica que tenga 3.851 publicaciones incluidas."""))
celdas.append(code("""filas = [r for r in csv.DictReader(open(CORPUS, encoding='utf-8-sig')) if r['decision_final'] == 'INCLUIDO']
assert len(filas) == 3851, len(filas)
print('Incluidas:', len(filas), '| núcleo IN:', sum(r['decision_cribado_desempeno'] == 'IN' for r in filas))"""))

celdas.append(md("""## 2. Proceso candidato y listas de códigos

Los procesos y problemas se toman de los diccionarios del código v8 (`PROCESS_PATTERNS` y `PROBLEM_PATTERNS`). Se leen del archivo original con `ast`, sin ejecutarlo ni copiarlos a mano.

El proceso candidato solo sirve para repartir de forma pareja. **No es una etiqueta**: el proceso de cada publicación lo decide quien la lee."""))
celdas.append(code("""def diccionario_v8(nombre):
    arbol = ast.parse(MOTOR_V8.read_text(encoding='utf-8'))
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and getattr(nodo.targets[0], 'id', None) == nombre:
            return ast.literal_eval(nodo.value)
    raise KeyError(nombre)

PROCESOS_V8 = diccionario_v8('PROCESS_PATTERNS')
PROBLEMAS_V8 = diccionario_v8('PROBLEM_PATTERNS')
PROCESOS = list(PROCESOS_V8) + ['mina_general', 'otro']
PROBLEMAS = list(PROBLEMAS_V8) + ['otro']
FUENTES_LECTURA = ['manual', 'IA revisada', 'IA sin revisar']

def proceso_candidato(r):
    texto = ' '.join([r['titulo_usado_en_cribado'] or r['titulo'], r['palabras_clave'], r['resumen']]).lower()
    conteo = {p: len(re.findall(pat, texto, re.I)) for p, pat in PROCESOS_V8.items()}
    mejor = max(conteo, key=conteo.get)
    return mejor if conteo[mejor] else 'sin_senal'

for r in filas:
    r['_candidato'] = proceso_candidato(r)
print('Procesos:', PROCESOS)
print('Problemas:', PROBLEMAS)
print(Counter(r['_candidato'] for r in filas).most_common())"""))

celdas.append(md("""## 3. Reparto

1. Se ordena por estrato (núcleo × proceso candidato) y se mezcla con semilla fija, para que el reparto sea reproducible.
2. En cada estrato se separa un 5 % para la **muestra común**, que leen ambos revisores.
3. El resto se reparte en forma alterna, de modo que cada revisor recibe una mezcla similar de procesos y de núcleo.
4. Cada revisor recibe sus publicaciones en lotes de 50, con el núcleo primero."""))
celdas.append(code("""rng = random.Random(SEMILLA)
estratos = defaultdict(list)
for r in sorted(filas, key=lambda r: r['id_publicacion']):
    estratos[(r['decision_cribado_desempeno'], r['_candidato'])].append(r)

asignacion = {}          # id -> lista de revisores
turno = 0
for clave in sorted(estratos):
    grupo = estratos[clave]
    rng.shuffle(grupo)
    n_comun = round(len(grupo) * FRACCION_COMUN)
    for r in grupo[:n_comun]:
        asignacion[r['id_publicacion']] = list(REVISORES)
    for r in grupo[n_comun:]:
        asignacion[r['id_publicacion']] = [REVISORES[turno % len(REVISORES)]]
        turno += 1

por_revisor = {rev: [r for r in filas if rev in asignacion[r['id_publicacion']]] for rev in REVISORES}
for rev, lista in por_revisor.items():
    lista.sort(key=lambda r: (r['decision_cribado_desempeno'] != 'IN', r['id_publicacion']))
comun = [i for i, revs in asignacion.items() if len(revs) > 1]
print('Muestra común:', len(comun))
for rev, lista in por_revisor.items():
    print(rev, len(lista), 'publicaciones | núcleo', sum(r['decision_cribado_desempeno'] == 'IN' for r in lista))
assert len(asignacion) == len(filas)"""))

celdas.append(md("""## 4. Planillas por revisor

Cada planilla tiene cuatro hojas:

- **Lectura:** una fila por publicación. Las columnas para completar llevan fondo amarillo, y `proceso`, `problema` y `fuente_lectura` tienen lista desplegable.
- **Instrucciones:** resumen del protocolo.
- **Listas:** códigos válidos.
- **Ejemplos:** lecturas completas con el nivel de detalle esperado.

Las publicaciones que ya se leyeron con IA (`entrada/lectura/*.json`) vienen prellenadas con `fuente_lectura = IA sin revisar`, y quien las recibe debe verificarlas. Las de la muestra común nunca se prellenan, para no sesgar la medición del acuerdo.

Si una planilla ya existe en `reparto/`, no se sobrescribe. Para regenerarla hay que borrarla primero."""))
celdas.append(code("""CAMPOS_LECTURA = ['proceso', 'procesos_secundarios', 'problema', 'objetivo', 'metodologias', 'datos', 'indicadores', 'resultados', 'observacion', 'fuente_lectura']
CAMPOS_FICHA = ['id_publicacion', 'lote', 'muestra_comun', 'nucleo', 'revision_literatura', 'anio', 'titulo', 'palabras_clave', 'resumen']

lecturas_ia = {}
for f in sorted((AQUI / 'entrada/lectura').glob('*.json')):
    for r in json.load(open(f, encoding='utf-8')):
        lecturas_ia[r['id_publicacion']] = r

INSTRUCCIONES = [
    'Lea título, palabras clave y resumen. Complete las columnas amarillas. No hay etiquetas previas: registre lo que dice la publicación.',
    'proceso: proceso principal (lista). mina_general: toda la mina sin proceso unitario (pit final, secuenciamiento, programación, evaluación energética global). otro: escriba en observacion "otro: <nombre del proceso>".',
    'procesos_secundarios: otros procesos que aborda, separados por ;',
    'problema: tipo de problema (lista). diseno = evalúa una alternativa antes de implementarla (diseñar, dimensionar, seleccionar, comparar tecnologías). ejecucion_operacion = mide o mejora el desempeño de una operación que ya existe. Si duda entre dos, elija uno y escriba en observacion "alternativa: <código>".',
    'Si la publicación no trata operaciones a cielo abierto (método subterráneo, cierre, rehabilitación), clasifíquela igual y escriba "revisar alcance" en observacion.',
    'objetivo: 1 o 2 oraciones en español (hasta 50 palabras): qué busca, qué problema aborda y en qué contexto (equipo, proceso, tipo de mina).',
    'metodologias: cada método con su detalle, separados por ; (tipo de modelo o algoritmo, función objetivo, software, cómo se valida). P. ej.: MILP que maximiza producción por turno, resuelto con CPLEX; simulación de eventos discretos en Arena para evaluar reglas de despacho.',
    'datos: tipo, fuente, tamaño o período y lugar, separados por ; (p. ej. datos del sistema de despacho Modular, 6 meses, 25 camiones, mina de cobre en Chile; ensayos de laboratorio; datos simulados).',
    'indicadores: qué miden como desempeño o resultado, separados por ; (p. ej. productividad t/h; tiempo de ciclo; tiempo de espera de palas; disponibilidad; costo por tonelada; consumo de diésel). Si no mide, escriba no aplica.',
    'resultados: hallazgo principal en 1 o 2 oraciones, con cifras si las informa (p. ej. aumenta la producción 8 % y reduce esperas 20 %).',
    'Si el resumen no entrega algún dato, escriba no informado. No complete con supuestos.',
    'Revisiones de literatura: metodologia = revisión de literatura; datos = literatura.',
    'Sin resumen: complete con título y palabras clave y anote "sin resumen" en observacion. No excluya.',
    'fuente_lectura: manual, IA revisada o IA sin revisar. Si usa IA, revise cada fila y cambie a IA revisada.',
    'muestra_comun = si: la otra persona también la lee. Hágalo sin consultar su lectura.',
]

def planilla(rev, lista, destino):
    if destino.exists():
        print('Ya existe, no se sobrescribe:', destino.name); return
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = 'Lectura'
    cab = CAMPOS_FICHA + CAMPOS_LECTURA
    ws.append(cab)
    amarillo = PatternFill('solid', fgColor='FFF2CC')
    for i, r in enumerate(lista):
        es_comun = len(asignacion[r['id_publicacion']]) > 1
        previa = {} if es_comun else lecturas_ia.get(r['id_publicacion'], {})
        fila = [r['id_publicacion'], f'L{i // TAMANO_LOTE + 1:03d}', 'si' if es_comun else 'no',
                r['decision_cribado_desempeno'], r['revision_de_literatura'], r['anio_referencia'],
                r['titulo_usado_en_cribado'] or r['titulo'], r['palabras_clave'], ' '.join(r['resumen'].split())]
        fila += [previa.get(c, '') for c in CAMPOS_LECTURA[:-1]] + ['IA sin revisar' if previa else '']
        ws.append(fila)
    for c in ws[1]:
        c.font = Font(bold=True)
        if c.value in CAMPOS_LECTURA: c.fill = amarillo
    anchos = dict(id_publicacion=30, lote=6, muestra_comun=8, nucleo=7, revision_literatura=8, anio=6, titulo=50,
                  palabras_clave=25, resumen=80, proceso=20, procesos_secundarios=20, problema=22, objetivo=45,
                  metodologias=55, datos=50, indicadores=35, resultados=55, observacion=25, fuente_lectura=14)
    for j, nombre in enumerate(cab, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(j)].width = anchos.get(nombre, 15)
    ws.freeze_panes = 'C2'
    ws.auto_filter.ref = ws.dimensions

    li = wb.create_sheet('Listas')
    for j, (titulo, valores) in enumerate([('proceso', PROCESOS), ('problema', PROBLEMAS), ('fuente_lectura', FUENTES_LECTURA)], 1):
        li.cell(1, j, titulo).font = Font(bold=True)
        for k, v in enumerate(valores, 2): li.cell(k, j, v)
    n = len(lista) + 1
    for campo, col_lista, valores in [('proceso', 'A', PROCESOS), ('problema', 'B', PROBLEMAS), ('fuente_lectura', 'C', FUENTES_LECTURA)]:
        dv = DataValidation(type='list', formula1=f'=Listas!${col_lista}$2:${col_lista}${len(valores) + 1}', allow_blank=True)
        letra = openpyxl.utils.get_column_letter(cab.index(campo) + 1)
        dv.add(f'{letra}2:{letra}{n}'); ws.add_data_validation(dv)

    ins = wb.create_sheet('Instrucciones', 0)
    ins['A1'] = f'Planilla de lectura - {rev}'; ins['A1'].font = Font(bold=True, size=13)
    ins['A2'] = f'{len(lista)} publicaciones en {(len(lista) - 1) // TAMANO_LOTE + 1} lotes; muestra común: {sum(len(asignacion[r["id_publicacion"]]) > 1 for r in lista)}.'
    for k, t in enumerate(INSTRUCCIONES, 4):
        ins.cell(k, 1, f'{k - 3}. {t}').alignment = Alignment(wrap_text=True)
    ins.column_dimensions['A'].width = 120

    ej = wb.create_sheet('Ejemplos')
    ej.append(['titulo'] + CAMPOS_LECTURA[:-1])
    titulos = {r['id_publicacion']: r['titulo_usado_en_cribado'] or r['titulo'] for r in filas}
    for r in list(lecturas_ia.values())[:8]:
        ej.append([titulos.get(r['id_publicacion'], '')] + [r.get(c, '') for c in CAMPOS_LECTURA[:-1]])
    for c in ej[1]: c.font = Font(bold=True)
    for col in ej.columns:
        ej.column_dimensions[col[0].column_letter].width = 40
        for c in col: c.alignment = Alignment(wrap_text=True, vertical='top')
    wb.save(destino)
    print('Creada:', destino.name, '|', len(lista), 'filas')

for rev, lista in por_revisor.items():
    planilla(rev, lista, REPARTO / f'planilla_lectura_{rev}.xlsx')

with open(REPARTO / 'asignacion.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['id_publicacion', 'revisores', 'muestra_comun', 'nucleo', 'proceso_candidato'])
    for r in filas:
        revs = asignacion[r['id_publicacion']]
        w.writerow([r['id_publicacion'], ';'.join(revs), 'si' if len(revs) > 1 else 'no', r['decision_cribado_desempeno'], r['_candidato']])"""))

from _seccion5 import MD as MD5, CODE as CODE5
celdas.append(md(MD5))
celdas.append(code(CODE5))

celdas.append(md("""---
# Parte 2. Consolidación

Se ejecuta cuando las planillas completas están en `planillas_completas/`, con el mismo nombre de archivo que tenían en `reparto/`.

## 6. Leer y validar"""))
celdas.append(code("""def leer_planilla(rev):
    f = COMPLETAS / f'planilla_lectura_{rev}.xlsx'
    if not f.exists():
        print('Falta', f.name); return {}
    ws = openpyxl.load_workbook(f, read_only=True)['Lectura']
    filas_ = list(ws.iter_rows(values_only=True))
    cab = [str(c) for c in filas_[0]]
    return {r[0]: {k: ('' if v is None else str(v).strip()) for k, v in zip(cab, r)} for r in filas_[1:] if r[0]}

lecturas = {rev: leer_planilla(rev) for rev in REVISORES}
if not all(lecturas.values()):
    raise RuntimeError('Faltan planillas completas en planillas_completas/. La parte 2 se ejecuta cuando ambas estén listas.')

problemas_validacion = []
for rev, datos_rev in lecturas.items():
    for i, r in datos_rev.items():
        faltan = [c for c in ('proceso', 'problema', 'objetivo', 'metodologias', 'datos') if not r.get(c)]
        if faltan: problemas_validacion.append((rev, i, 'incompleta: ' + ', '.join(faltan)))
        if r.get('proceso') and r['proceso'] not in PROCESOS: problemas_validacion.append((rev, i, 'proceso inválido: ' + r['proceso']))
        if r.get('problema') and r['problema'] not in PROBLEMAS: problemas_validacion.append((rev, i, 'problema inválido: ' + r['problema']))
        for s in filter(None, (x.strip() for x in r.get('procesos_secundarios', '').split(';'))):
            if s not in PROCESOS: problemas_validacion.append((rev, i, 'secundario inválido: ' + s))
        if r.get('fuente_lectura') == 'IA sin revisar': problemas_validacion.append((rev, i, 'IA sin revisar'))
        if r.get('proceso') == 'otro' and not re.search(r'otro:\\s*\\S', r.get('observacion', '')):
            problemas_validacion.append((rev, i, 'otro sin nombre: escriba "otro: <proceso>" en observacion'))
        alt = re.search(r'alternativa:\\s*(\\w+)', r.get('observacion', ''))
        if alt and alt.group(1) not in PROBLEMAS: problemas_validacion.append((rev, i, 'alternativa inválida: ' + alt.group(1)))
    asignadas = {r['id_publicacion'] for r in por_revisor[rev]}
    if datos_rev and set(datos_rev) != asignadas:
        problemas_validacion.append((rev, '-', f'filas distintas a las asignadas ({len(datos_rev)} vs {len(asignadas)})'))
print('Observaciones de validación:', len(problemas_validacion))
print(Counter(p[2].split(':')[0] for p in problemas_validacion))"""))

celdas.append(md("""## 7. Acuerdo entre revisores en la muestra común

Se calcula el porcentaje de acuerdo y el kappa de Cohen para `proceso` y `problema`. Las discrepancias se guardan en `consolidado/discrepancias.xlsx`. Allí se completa `decision_final` después de conversarlas, y la consolidación usa esa decisión."""))
celdas.append(code("""def kappa(pares):
    n = len(pares)
    if not n: return None
    po = sum(a == b for a, b in pares) / n
    ca, cb = Counter(a for a, _ in pares), Counter(b for _, b in pares)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n**2
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0

a, b = REVISORES
acuerdo, discrepancias = {}, []
for campo in ('proceso', 'problema'):
    pares = [(lecturas[a][i][campo], lecturas[b][i][campo]) for i in comun
             if i in lecturas[a] and i in lecturas[b] and lecturas[a][i].get(campo) and lecturas[b][i].get(campo)]
    acuerdo[campo] = {'n': len(pares), 'acuerdo': round(sum(x == y for x, y in pares) / len(pares), 3) if pares else None,
                      'kappa': kappa(pares)}
    for i in comun:
        if i in lecturas[a] and i in lecturas[b] and lecturas[a][i].get(campo) != lecturas[b][i].get(campo):
            discrepancias.append([i, campo, lecturas[a][i].get(campo), lecturas[b][i].get(campo), ''])
print(json.dumps(acuerdo, indent=1))

# Se reescribe en cada ejecución, conservando las decisiones ya anotadas.
archivo_disc = CONSOLIDADO / 'discrepancias.xlsx'
resueltas = {}
if archivo_disc.exists():
    for r in list(openpyxl.load_workbook(archivo_disc, read_only=True).active.iter_rows(values_only=True))[1:]:
        if r[4]: resueltas[(r[0], r[1])] = str(r[4]).strip()
wb = openpyxl.Workbook(); ws = wb.active
ws.append(['id_publicacion', 'campo', a, b, 'decision_final'])
for d in discrepancias:
    d[4] = resueltas.get((d[0], d[1]), '')
    ws.append(d)
for c in ws[1]: c.font = Font(bold=True)
wb.save(archivo_disc)
resueltas = {k: v for k, v in resueltas.items() if any((d[0], d[1]) == k for d in discrepancias)}
invalidas = [k for k, v in resueltas.items() if v not in (PROCESOS if k[1] == 'proceso' else PROBLEMAS)]
assert not invalidas, f'decision_final con códigos inválidos: {invalidas}'
print('Discrepancias:', len(discrepancias), '| resueltas:', len(resueltas))"""))

celdas.append(md("""## 8. Corpus unificado y conteos por proceso

En la muestra común se usa la lectura del primer revisor. Si existe una `decision_final` para la discrepancia, se usa esa decisión.

Las metodologías y los datos se cuentan por término, y una publicación puede sumar en varios. Además se calcula cuántas temáticas corresponde agrupar en cada proceso, según la regla acordada: más de 1.000 → 12, de 500 a 1.000 → 10, de 200 a 499 → 8, de 100 a 199 → 6, menos de 100 → 5, siempre más «Otros»."""))
celdas.append(code("""def n_tematicas(n):
    return 12 if n > 1000 else 10 if n >= 500 else 8 if n >= 200 else 6 if n >= 100 else 5

ficha = {r['id_publicacion']: r for r in filas}
unificado = []
for i in sorted(ficha):
    revs = asignacion[i]
    base = next((lecturas[rv][i] for rv in revs if i in lecturas[rv]), None)
    if base is None: continue
    reg = {c: base.get(c, '') for c in CAMPOS_LECTURA}
    for campo in ('proceso', 'problema'):
        if (i, campo) in resueltas: reg[campo] = resueltas[(i, campo)]
    r = ficha[i]
    unificado.append({'id_publicacion': i, 'anio': r['anio_referencia'], 'titulo': r['titulo_usado_en_cribado'] or r['titulo'],
                      'revista': r['revista'], 'doi': r['doi'], 'nucleo': r['decision_cribado_desempeno'],
                      'revision_literatura': r['revision_de_literatura'], 'lector': ';'.join(rv for rv in revs if i in lecturas[rv]),
                      'muestra_comun': 'si' if len(revs) > 1 else 'no', **reg})
print('Publicaciones con lectura:', len(unificado), 'de', len(filas))

def terminos(texto):
    return [t.strip().lower() for t in texto.split(';') if t.strip()]

por_proceso = Counter(u['proceso'] for u in unificado)
resumen = []
for p in PROCESOS:
    sub = [u for u in unificado if u['proceso'] == p]
    resumen.append({'proceso': p, 'publicaciones': len(sub), 'nucleo_IN': sum(u['nucleo'] == 'IN' for u in sub),
                    'como_secundario': sum(p in terminos(u['procesos_secundarios']) for u in unificado),
                    'tematicas_a_agrupar': n_tematicas(len(sub)) if sub else 0,
                    **{f'problema_{q}': sum(u['problema'] == q for u in sub) for q in PROBLEMAS}})
met = Counter((u['proceso'], t) for u in unificado for t in terminos(u['metodologias']))
dat = Counter((u['proceso'], t) for u in unificado for t in terminos(u['datos']))
ind = Counter((u['proceso'], t) for u in unificado for t in terminos(u['indicadores']))"""))

celdas.append(md("""## 9. Excel unificado

Hojas:

- **Corpus_lectura:** una fila por publicación.
- **Resumen_procesos:** N, núcleo, N como proceso secundario, temáticas a agrupar y problemas.
- **Metodologias / Datos / Indicadores:** términos por proceso con su N, que es la base para agruparlos en familias.
- **Casos_otro / Resumen_otro:** publicaciones con proceso `otro` y cuántas veces se nombra cada proceso, para decidir si alguno merece código propio.
- **Problema_alternativas:** cuántas veces se dudó entre dos tipos de problema, para revisar si el criterio funciona.
- **Revisar_alcance:** publicaciones marcadas como posiblemente fuera de alcance.
- **Acuerdo:** resultado de la muestra común.
- **Validacion:** filas que hay que corregir.
- **Agrupacion_tematicas:** plantilla del paso siguiente, con un bloque por proceso y el número de temáticas que le corresponde."""))
celdas.append(code("""wb = openpyxl.Workbook()
def hoja(nombre, cab, filas_):
    ws = wb.create_sheet(nombre); ws.append(cab)
    for f in filas_: ws.append(f)
    for c in ws[1]: c.font = Font(bold=True)
    ws.freeze_panes = 'A2'
    return ws

wb.remove(wb.active)
cab_u = list(unificado[0]) if unificado else []
hoja('Corpus_lectura', cab_u, [[u[c] for c in cab_u] for u in unificado])
hoja('Resumen_procesos', list(resumen[0]), [list(r.values()) for r in resumen])
hoja('Metodologias', ['proceso', 'metodologia', 'n'], [[p, t, n] for (p, t), n in sorted(met.items(), key=lambda x: (x[0][0], -x[1]))])
hoja('Datos', ['proceso', 'dato', 'n'], [[p, t, n] for (p, t), n in sorted(dat.items(), key=lambda x: (x[0][0], -x[1]))])
hoja('Indicadores', ['proceso', 'indicador', 'n'], [[p, t, n] for (p, t), n in sorted(ind.items(), key=lambda x: (x[0][0], -x[1]))])
casos_otro = [[u['id_publicacion'], u['titulo'], (re.search(r'otro:\\s*([^;]+)', u['observacion']) or [None, ''])[1].strip(), u['observacion']]
              for u in unificado if u['proceso'] == 'otro']
hoja('Casos_otro', ['id_publicacion', 'titulo', 'proceso_nombrado', 'observacion'], sorted(casos_otro, key=lambda x: x[2]))
hoja('Resumen_otro', ['proceso_nombrado', 'n'], Counter(c[2].lower() for c in casos_otro).most_common())
alternativas = Counter((u['problema'], m) for u in unificado for m in re.findall(r'alternativa:\\s*(\\w+)', u['observacion']))
hoja('Problema_alternativas', ['problema_elegido', 'alternativa', 'n'], [[a_, b_, n] for (a_, b_), n in alternativas.most_common()])
hoja('Revisar_alcance', ['id_publicacion', 'titulo', 'proceso', 'observacion'],
     [[u['id_publicacion'], u['titulo'], u['proceso'], u['observacion']] for u in unificado if 'revisar alcance' in u['observacion'].lower()])
hoja('Acuerdo', ['campo', 'n', 'acuerdo', 'kappa'], [[k, v['n'], v['acuerdo'], v['kappa']] for k, v in acuerdo.items()])
hoja('Validacion', ['revisor', 'id_publicacion', 'observacion'], problemas_validacion)
filas_ag = []
for r in resumen:
    if r['publicaciones']:
        for k in range(1, r['tematicas_a_agrupar'] + 1):
            filas_ag.append([r['proceso'], r['publicaciones'], f'T{k:02d}', '', '', ''])
        filas_ag.append([r['proceso'], r['publicaciones'], 'Otros', '', '', ''])
hoja('Agrupacion_tematicas', ['proceso', 'N_proceso', 'tematica', 'nombre_tematica', 'n', 'descripcion'], filas_ag)
salida = CONSOLIDADO / 'lectura_corpus_unificado.xlsx'
wb.save(salida)
print('Guardado:', salida)
print(json.dumps({'publicaciones_leidas': len(unificado), 'por_proceso': dict(por_proceso.most_common()),
                  'acuerdo': acuerdo, 'observaciones_validacion': len(problemas_validacion)}, ensure_ascii=False, indent=1))"""))

nb = nbf.v4.new_notebook(); nb.cells = celdas
nb.metadata['kernelspec'] = {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}
nbf.write(nb, Path(__file__).with_name('13_reparto_y_consolidacion.ipynb'))
print('ok')
