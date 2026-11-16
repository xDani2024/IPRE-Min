MD = """## 5. Lectura con IA (ChatGPT, Claude u otra)

El flujo es igual para ambos revisores y no usa API:

1. `exportar_lote('Joaquin', 3)` crea `ia_lotes/Joaquin_L003.txt` con las instrucciones y las publicaciones pendientes del lote. No incluye las filas de la muestra común, que se leen a mano, ni las ya completas.
2. Se pega **todo** el texto en una conversación nueva de la IA. La IA responde con un bloque JSON.
3. Se guarda la respuesta en `respuestas_ia/Joaquin/` con el nombre del lote: `L003.txt` si se pegó el texto, o `L003.json` si la IA entregó un archivo. Basta con la respuesta completa, porque el notebook busca el JSON aunque venga con texto alrededor.
4. `importar_respuestas('Joaquin', 'ChatGPT')` valida los códigos y escribe las lecturas en la planilla (`reparto/planilla_lectura_Joaquin.xlsx`) como `IA sin revisar`. **El Excel debe estar cerrado.**
5. Se revisan las filas en Excel y se cambia `fuente_lectura` a `IA revisada`.

Cada importación queda registrada en `respuestas_ia/registro_importaciones.csv`, con archivo, herramienta, fecha y filas escritas. Una respuesta ya importada no se vuelve a importar. Si se exporta de nuevo un lote para completar publicaciones faltantes, la nueva respuesta puede guardarse con el mismo nombre: se reconoce por su contenido."""

CODE = r"""import datetime, hashlib
IA_LOTES = AQUI / 'ia_lotes'; IA_LOTES.mkdir(exist_ok=True)
RESPUESTAS = AQUI / 'respuestas_ia'
REGISTRO = RESPUESTAS / 'registro_importaciones.csv'
for rev in REVISORES: (RESPUESTAS / rev).mkdir(parents=True, exist_ok=True)

DEF_PROCESOS = {
    'perforacion': 'perforación de pozos',
    'tronadura': 'tronadura/voladura',
    'carguio_excavacion': 'carguío y excavación (palas, excavadoras, cargadores, dragalinas)',
    'acarreo': 'transporte con camiones',
    'riego_control_polvo': 'riego de caminos y control de polvo',
    'caminos': 'diseño y mantención de caminos',
    'abastecimiento': 'abastecimiento de combustible e insumos',
    'desague': 'drenaje y bombeo en el rajo',
    'mantenimiento_equipos': 'mantenimiento de equipos sin un proceso único',
    'transporte_continuo': 'correas, chancado en rajo (IPCC), apiladores',
    'mina_general': 'toda la mina sin un proceso unitario: pit final, secuenciamiento, programación de producción, evaluación energética o económica global',
    'otro': 'proceso que no está en la lista; en observacion escriba "otro: <nombre del proceso>"'}
DEF_PROBLEMAS = {
    'diseno': 'evalúa una alternativa ANTES de implementarla: diseñar, dimensionar, seleccionar o comparar tecnologías o sistemas (aunque estime su productividad)',
    'planificacion': 'planificación o programación',
    'asignacion_despacho': 'asignación de equipos y despacho',
    'ejecucion_operacion': 'mide o mejora el desempeño de una operación que YA EXISTE (productividad, tiempos de ciclo, consumo medidos o modelados para la operación actual)',
    'mantenimiento_confiabilidad': 'mantenimiento, fallas, disponibilidad',
    'reemplazo_ciclo_vida': 'reemplazo y vida útil',
    'ambiente_seguridad': 'ambiente o seguridad',
    'automatizacion_control': 'automatización, control, autonomía',
    'otro': 'otro tipo de problema'}
assert set(DEF_PROCESOS) == set(PROCESOS) and set(DEF_PROBLEMAS) == set(PROBLEMAS)

PROMPT = '''Eres asistente de una revisión bibliométrica sobre operaciones de minería a cielo abierto.
Lee cada publicación (título T, palabras clave K y resumen R) y registra lo que DICE la publicación. No uses categorías propias.

Devuelve SOLO un bloque JSON: una lista con un objeto por publicación, en el mismo orden, con estas claves:
id_publicacion, proceso, procesos_secundarios, problema, objetivo, metodologias, datos, indicadores, resultados, observacion
Sé detallado: esta ficha reemplaza volver a leer el resumen.

Reglas:
- proceso: el proceso principal; UNO de estos códigos:
{procesos}
- procesos_secundarios: otros códigos de la misma lista separados por ";" o "".
- problema: UNO de estos códigos:
{problemas}
- objetivo: 1 o 2 oraciones en español (hasta 50 palabras): qué busca, qué problema aborda y en qué contexto (equipo, proceso, tipo de mina o mineral).
- metodologias: cada método con su detalle, separados por ";": tipo de modelo o algoritmo, función objetivo o variable que optimiza, software y cómo se valida o compara (p. ej. "MILP que maximiza la producción por turno, resuelto con CPLEX; simulación de eventos discretos en Arena para comparar reglas de despacho"). No escribas solo "optimización".
- datos: tipo, fuente, tamaño o período y lugar, separados por ";" (p. ej. "datos del sistema de despacho, 6 meses, 25 camiones, mina de cobre en Chile"; "ensayos de laboratorio"; "datos simulados").
- indicadores: indicadores de desempeño o variables de resultado que mide, separados por ";" (p. ej. "productividad (t/h); tiempo de ciclo; tiempo de espera de palas; costo por tonelada"). Si no mide, "no aplica".
- resultados: hallazgo principal en 1 o 2 oraciones, con las cifras que informe el resumen.
- Revisiones de literatura: metodologias = "revisión de literatura"; datos = "literatura".
- No inventes. Si el resumen no informa algo, escribe "no informado". Si no hay resumen, usa título y palabras clave y anota "sin resumen" en observacion.
- Si dudas entre dos códigos de problema, elige el más cercano según las definiciones y escribe en observacion "alternativa: <otro código>".
- Si proceso = "otro", observacion debe empezar con "otro: <nombre del proceso>" (p. ej. "otro: botaderos de estéril").
- Si la publicación no trata operaciones de minería a cielo abierto (p. ej. método subterráneo, cierre o rehabilitación), clasifícala igual y agrega en observacion "revisar alcance".
- No agregues datos que el resumen no entrega (país, mineral, tamaño): escribe "no informado".
- observacion: lo anterior y otras dudas, separados por ";"; si no hay nada, "" (texto vacío, nunca null).

Ejemplo de salida:
{ejemplos}

Publicaciones ({n}):
'''

def _planilla(revisor):
    return REPARTO / f'planilla_lectura_{revisor}.xlsx'

def exportar_lote(revisor, lote):
    ws = openpyxl.load_workbook(_planilla(revisor), read_only=True)['Lectura']
    filas_ = list(ws.iter_rows(values_only=True)); cab = filas_[0]
    ix = {c: i for i, c in enumerate(cab)}
    pend = [r for r in filas_[1:] if r[ix['lote']] == f'L{lote:03d}' and r[ix['muestra_comun']] == 'no' and not r[ix['proceso']]]
    if not pend:
        print('No hay publicaciones pendientes en ese lote.'); return
    ejemplos = json.dumps([{k: r.get(k, '') for k in ['id_publicacion'] + CAMPOS_LECTURA[:-1]} for r in list(lecturas_ia.values())[:2]],
                          ensure_ascii=False, indent=1)
    texto = PROMPT.format(procesos='\n'.join(f'  {k}: {v}' for k, v in DEF_PROCESOS.items()),
                          problemas='\n'.join(f'  {k}: {v}' for k, v in DEF_PROBLEMAS.items()),
                          ejemplos=ejemplos, n=len(pend))
    for r in pend:
        texto += (f"\n### {r[ix['id_publicacion']]}\nT: {r[ix['titulo']]}\nK: {(r[ix['palabras_clave']] or '')[:250]}\n"
                  f"R: {r[ix['resumen']] or '(sin resumen)'}\n")
    destino = IA_LOTES / f'{revisor}_L{lote:03d}.txt'
    destino.write_text(texto, encoding='utf-8')
    print(f'Exportado {destino.name}: {len(pend)} publicaciones. Pegue el texto completo en una conversación nueva.')
    print(f'Guarde la respuesta en respuestas_ia/{revisor}/L{lote:03d}.txt')

def _leer_json(texto):
    i, j = texto.find('['), texto.rfind(']')
    if i < 0 or j < i:
        raise ValueError('no se encontró una lista JSON en la respuesta')
    return json.loads(texto[i:j + 1])

def importar_respuestas(revisor, herramienta, sobrescribir=False):
    ya = set()
    if REGISTRO.exists():
        ya = {r['huella'] for r in csv.DictReader(open(REGISTRO, encoding='utf-8'))}
    huella = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()[:16]
    archivos = [f for f in sorted((RESPUESTAS / revisor).iterdir()) if f.suffix.lower() in ('.txt', '.json') and huella(f) not in ya]
    if not archivos:
        print('No hay respuestas nuevas para importar.'); return
    wb = openpyxl.load_workbook(_planilla(revisor)); ws = wb['Lectura']
    cab = [c.value for c in ws[1]]
    col = {c: cab.index(c) + 1 for c in cab}
    fila_de = {ws.cell(k, 1).value: k for k in range(2, ws.max_row + 1)}
    registros = []
    for f in archivos:
        try:
            datos_ia = _leer_json(f.read_text(encoding='utf-8'))
        except Exception as e:
            print(f'{f.name}: no se pudo leer ({e}). Revise que esté la respuesta completa.'); continue
        escritas, avisos = 0, []
        devueltos = set()
        for d in datos_ia:
            i = str(d.get('id_publicacion', '')).strip(); devueltos.add(i)
            if i not in fila_de:
                avisos.append(f'id desconocido {i}'); continue
            k = fila_de[i]
            if ws.cell(k, col['muestra_comun']).value == 'si':
                avisos.append(f'{i} es muestra común (se lee a mano)'); continue
            if ws.cell(k, col['proceso']).value and not sobrescribir:
                avisos.append(f'{i} ya tenía lectura'); continue
            obs = str(d.get('observacion', '') or '').strip()
            for campo, validos in (('proceso', PROCESOS), ('problema', PROBLEMAS)):
                v = str(d.get(campo, '') or '').strip().lower()
                if v in validos:
                    d[campo] = v
                else:
                    obs = (f'[{campo} inválido: {v}] ' + obs).strip(); d[campo] = ''
            sec = [x.strip().lower() for x in str(d.get('procesos_secundarios', '') or '').split(';') if x.strip()]
            d['procesos_secundarios'] = '; '.join(x for x in sec if x in PROCESOS)
            for campo in ('proceso', 'procesos_secundarios', 'problema', 'objetivo', 'metodologias', 'datos', 'indicadores', 'resultados'):
                ws.cell(k, col[campo]).value = str(d.get(campo, '') or '').strip()
            ws.cell(k, col['observacion']).value = obs
            ws.cell(k, col['fuente_lectura']).value = 'IA sin revisar'
            escritas += 1
        lote_txt = IA_LOTES / f'{revisor}_{f.stem}.txt'
        if lote_txt.exists():
            pedidas = re.findall(r'^### (\S+)', lote_txt.read_text(encoding='utf-8'), re.M)
            faltan = [p for p in pedidas if p not in devueltos]
            if faltan:
                avisos.append(f'la IA no devolvió {len(faltan)} publicaciones; exporte de nuevo el lote para leerlas')
        registros.append({'revisor': revisor, 'archivo': f.name, 'huella': huella(f), 'herramienta': herramienta,
                          'fecha': datetime.date.today().isoformat(), 'filas_escritas': escritas,
                          'avisos': ' | '.join(avisos)})
        print(f'{f.name}: {escritas} filas escritas' + (f'; {len(avisos)} avisos' if avisos else ''))
        for a_ in avisos[:10]:
            print('   -', a_)
    try:
        wb.save(_planilla(revisor))
    except PermissionError:
        print('No se pudo guardar: cierre el Excel y vuelva a ejecutar.'); return
    nuevo = not REGISTRO.exists()
    with open(REGISTRO, 'a', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['revisor', 'archivo', 'huella', 'herramienta', 'fecha', 'filas_escritas', 'avisos'])
        if nuevo:
            w.writeheader()
        w.writerows(registros)

# Uso:
# exportar_lote('Joaquin', 3)
# importar_respuestas('Joaquin', 'ChatGPT')"""
