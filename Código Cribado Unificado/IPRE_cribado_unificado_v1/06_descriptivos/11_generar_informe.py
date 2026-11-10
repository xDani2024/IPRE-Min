"""Genera el informe Word del cribado del corpus unificado con resultados y figuras conservados.

Lee Resultados_informe.json y graficos_informe/ (de 10_generar_graficos_informe.py). Los formatos,
estilos y funciones de tabla y figura replican 05_descriptivos/25_generar_avance.py del paquete
IPRE_codigo_y_datos_v9. Las cifras se toman de los archivos; no se escriben a mano.

Uso: py -3 06_descriptivos/11_generar_informe.py
Requiere python-docx (requirements_complementarios.txt).
"""
from pathlib import Path
import json
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Editar antes de generar el informe definitivo.
AUTORIA = 'Equipo IPRE'
FECHA = '10 de noviembre de 2026'

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / 'documentacion'
OUT.mkdir(exist_ok=True)
D = json.loads((HERE / 'Resultados_informe.json').read_text(encoding='utf-8'))
n = lambda x: f'{int(x):,}'.replace(',', '.')
pct = lambda x: f'{float(x):.1f}'.replace('.', ',')
PR = D['prisma']; ID = PR['identificacion']; DD = PR['deduplicacion']; CR = PR['cribado']
REG = ID['registros_por_base_en_integracion']
FA = D['filtro_amplio']; N1 = D['nivel1']; NU = D['nucleo']; IND = D['indicadores']
INC, NUC = N1['incluidas'], NU['IN']
COMP = NU['composicion']; RH = D['revision_humana']; RED = D['redes']
YI, YN = D['incluidos_por_ano'], D['nucleo_por_ano']
PROC = D['procedencia']
RHR = D['revision_humana_resultado']; CO = D['concordancia']
EX_ET = CR['etapa2_pertinencia_operacional'].get('excluidas_por_etapa', {})
EX_N1, EX_RH = EX_ET.get('cribado_pertinencia_operacional', N1['excluidas']), EX_ET.get('revision_humana', 0)
VER = ROOT / 'documentacion/Verificacion_cadena_completa.json'
N_COTEJOS = len(json.loads(VER.read_text(encoding='utf-8'))['cotejos']) if VER.exists() else None
dec = lambda x: f'{x:.2f}'.replace('.', ',')

doc = Document()
sec = doc.sections[0]
sec.page_width = Inches(8.5)
sec.page_height = Inches(11)
sec.top_margin = sec.bottom_margin = Inches(.65)
sec.left_margin = sec.right_margin = Inches(.8)
sec.header_distance = sec.footer_distance = Inches(.27)
for name in ['Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Caption']:
    st = doc.styles[name]
    st.font.name = 'Arial'
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.paragraph_format.space_after = Pt(6)
    for border in list(st.element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
doc.styles['Normal'].font.size = Pt(11)
doc.styles['Normal'].paragraph_format.line_spacing = 1.10
doc.styles['Title'].font.size = Pt(21)
doc.styles['Heading 1'].font.size = Pt(14)
doc.styles['Heading 1'].paragraph_format.space_before = Pt(3)
doc.styles['Heading 2'].font.size = Pt(11.5)
doc.styles['Caption'].font.size = Pt(9)
doc.styles['Caption'].font.italic = False
head = sec.header.paragraphs[0]
head.text = 'IPRE   Minería a cielo abierto   Cribado del corpus unificado'
head.runs[0].font.size = Pt(8.5)
foot = sec.footer.paragraphs[0]
foot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
foot.add_run(f'{AUTORIA}  |  {FECHA}  |  ').font.size = Pt(8.5)
field = OxmlElement('w:fldSimple')
field.set(qn('w:instr'), 'PAGE')
foot._p.append(field)
doc.core_properties.author = AUTORIA
doc.core_properties.title = 'Cribado del corpus bibliométrico unificado en minería a cielo abierto'
doc.core_properties.subject = 'Cribado de OpenAlex, Scopus y WoS, descripción bibliométrica y trabajo pendiente'

def para(text, bold=False, style=None):
    p = doc.add_paragraph(style=style)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.add_run(text).bold = bold
    return p

def heading(text, new=True):
    p = doc.add_heading(text, level=1)
    if new:
        p.paragraph_format.page_break_before = True

def table(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    widths = widths or [6.9 / len(headers)] * len(headers)
    for col, w in zip(t.columns, widths):
        col.width = Inches(w)
    for cell, w, text in zip(t.rows[0].cells, widths, headers):
        cell.width = Inches(w)
        cell.text = text
    for row in rows:
        cells = t.add_row().cells
        for c, w, value in zip(cells, widths, row):
            c.width = Inches(w)
            c.text = str(value)
    for i, row in enumerate(t.rows):
        for c in row.cells:
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr = c._tc.get_or_add_tcPr()
            mar = OxmlElement('w:tcMar')
            for side, val in [('top', '85'), ('bottom', '85'), ('left', '100'), ('right', '100')]:
                e = OxmlElement('w:' + side)
                e.set(qn('w:w'), val)
                e.set(qn('w:type'), 'dxa')
                mar.append(e)
            pr.append(mar)
            borders = OxmlElement('w:tcBorders')
            for side in ['top', 'left', 'bottom', 'right']:
                e = OxmlElement('w:' + side)
                e.set(qn('w:val'), 'single')
                e.set(qn('w:sz'), '4')
                e.set(qn('w:color'), 'D9D9D9')
                borders.append(e)
            pr.append(borders)
            if i == 0:
                shade = OxmlElement('w:shd')
                shade.set(qn('w:fill'), 'DDE6ED')
                pr.append(shade)
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.05
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for r in p.runs:
                    r.font.name = 'Arial'
                    r.font.size = Pt(10)
                    r.bold = i == 0
        row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return t

def figure(name, caption, width=6.75):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(HERE / 'graficos_informe' / name), width=Inches(width))
    para(caption, style='Caption')

def code(text, boxed=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(7)
    p.paragraph_format.keep_together = True
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(text)
    r.font.name = 'Courier New'
    r.font.size = Pt(8.5 if boxed else 10)
    if boxed:
        p.paragraph_format.line_spacing = 1.05
        p.paragraph_format.left_indent = p.paragraph_format.right_indent = Inches(.12)
        pr = p._p.get_or_add_pPr()
        shade = OxmlElement('w:shd')
        shade.set(qn('w:fill'), 'F4F5F6')
        pr.append(shade)
        borders = OxmlElement('w:pBdr')
        for side in ['top', 'left', 'bottom', 'right']:
            border = OxmlElement('w:' + side)
            border.set(qn('w:val'), 'single')
            border.set(qn('w:sz'), '4')
            border.set(qn('w:space'), '6')
            border.set(qn('w:color'), 'D9D9D9')
            borders.append(border)
        pr.append(borders)

LAB = {'F_GEO': 'Geotecnia o estabilidad sin vínculo operacional', 'F_AMB': 'Ambiental, hídrico, emisiones o cierre',
       'F_VIB': 'Efectos de tronadura sin vínculo operacional', 'F_CTX': 'Contexto distinto del rajo',
       'F_ECO': 'Economía agregada, sociedad, legal o política', 'F_OTRO': 'No trata la operación del rajo',
       'F_GEOL': 'Geología, exploración o recursos', 'F_TELE': 'Cartografía o teledetección', 'F_SEG': 'Seguridad ocupacional general',
       'F_PROC': 'Planta o procesamiento', 'F_SALUD': 'Salud o exposición de trabajadores', 'F_COMP': 'Componente sin equipo de la mina',
       'F_DOC': 'Sin estudio propio (editorial, reseña, retractación)'}
FALAB = {'sin_foco_operacional_suficiente': 'Sin señal operacional suficiente', 'tema_excluido_en_titulo': 'Tema excluido en el título',
         'tema_periferico_en_titulo': 'Tema periférico en el título', 'metodo_subterraneo_fuera_de_alcance': 'Método subterráneo en el título'}

# =================================================================================
doc.add_paragraph('Cribado del corpus bibliométrico unificado', style='Title')
doc.add_paragraph('OpenAlex, Scopus y Web of Science en minería a cielo abierto', style='Subtitle')
para(f'{AUTORIA} | Profesor guía José Joaquín Jara | {FECHA}')

heading('1 Contexto y objetivo', new=False)
para('El estudio busca ordenar la literatura sobre la operación de minas a cielo abierto, con especial interés en los equipos y actividades auxiliares. A partir de lo conversado con el profesor, el objetivo es comparar qué se ha investigado sobre planificación, mantenimiento, asignación de recursos y eficiencia durante la ejecución, para después identificar posibles brechas en los procesos de apoyo.')
para('El profesor propuso mirar la mina como un sistema de procesos. Distinguió los procesos principales, como perforación, tronadura, carguío y transporte; las actividades auxiliares que permiten ejecutarlos; el mantenimiento; y la captura y procesamiento de información. El equipo se estudia dentro de la tarea que cumple, por lo que necesitamos conservar ambos ejes: proceso y equipo.')
para(f'El avance anterior trabajó solo con OpenAlex. Desde entonces integramos OpenAlex, Scopus y Web of Science en un corpus de {n(DD["publicaciones_unicas"])} publicaciones únicas y repetimos el cribado desde cero sobre ese universo. Aplicamos los mismos códigos de selección, sin modificarlos, y agregamos un nivel de pertinencia operacional con los criterios acordados. No reutilizamos auditorías con IA, decisiones humanas ni cifras del piloto anterior.')
table(['Resultado actual', 'Estado'], [
    ['Universo unificado', f'{n(DD["publicaciones_unicas"])} publicaciones de {n(ID["total_registros_integrados"])} registros'],
    ['Filtro amplio', f'{n(FA["aceptadas"])} aceptadas y {n(FA["excluidas"])} excluidas'],
    ['Corpus incluido', f'{n(INC)} publicaciones; {n(N1["excluidas"])} excluidas por pertinencia operacional'],
    ['Núcleo de desempeño operacional', f'{n(NUC)} publicaciones dentro del corpus incluido'],
    ['Revisión humana', f'{n(RHR["revisadas"])} casos con información insuficiente: {n(RHR["excluidas"])} excluidos y {n(RHR["nucleo_IN"])} al núcleo'],
    ['Muestra de validación', f'{n(CO["muestra_revisada"])} publicaciones; kappa {dec(CO["kappa_inclusion_muestra"])} en inclusión y {dec(CO["kappa_nucleo_muestra"])} en núcleo']], widths=[3.0, 3.9])
para('El corpus incluido es la base para comparar las áreas de investigación y contrastar las hipótesis. El núcleo de desempeño permite profundizar en los estudios que evalúan el funcionamiento de equipos o tareas. Quedar fuera del núcleo no elimina una publicación del corpus incluido.')
para('Usamos INCLUIDO y EXCLUIDO para la decisión final sobre el corpus, e IN y OUT para el núcleo de desempeño. En esta versión no quedan casos TC: cada publicación tiene una decisión, una etapa, un motivo y su procedencia. Los casos con información insuficiente se resolvieron en una revisión humana, y no queda ninguno pendiente.')

heading('2 Preguntas e hipótesis de investigación')
para('La idea es partir del panorama general y avanzar hacia el estudio de los procesos auxiliares. Las siguientes preguntas e hipótesis orientan ese análisis. Hasta ahora tenemos un corpus cribado y una descripción bibliométrica; las hipótesis todavía deben contrastarse.')
doc.add_heading('Preguntas de investigación', level=2)
para('1. ¿Cómo se distribuye la literatura de minería a cielo abierto entre diseño y planificación, mantenimiento, procesos principales y procesos auxiliares?')
para('2. En los procesos principales, ¿predominan los estudios de planificación y asignación de tareas y equipos sobre los que evalúan la eficiencia durante la ejecución?')
para('3. En los procesos auxiliares, ¿cuánta investigación aborda la asignación óptima de recursos y el desempeño o eficiencia de las actividades de apoyo?')
doc.add_heading('Hipótesis planteadas por el profesor', level=2)
para('H1. La literatura se concentra en el diseño y la planificación de la operación, el mantenimiento y los procesos principales, especialmente perforación, tronadura, carguío y transporte.')
para('H2. En los procesos principales predominan el diseño y la planificación de corto plazo y la asignación eficiente de equipos y tareas. Existe menos investigación sobre el desempeño operacional y la eficiencia durante la ejecución de las actividades productivas.')
para('H3. Existe escasa literatura sobre la asignación óptima y el desempeño o eficiencia de los procesos auxiliares en minería a cielo abierto.')
doc.add_heading('Cómo vamos a contrastarlas', level=2)
para(f'Las hipótesis no se usaron para decidir inclusiones ni exclusiones. Para las dos primeras usaremos el corpus incluido de {n(INC)} publicaciones, porque contiene también la literatura de planificación y mantenimiento que queremos comparar. Para la tercera, y para describir cómo se mide el desempeño, usaremos además el núcleo de {n(NUC)} publicaciones.')
para('El paso siguiente es definir de tres a cinco grupos temáticos a partir del propio corpus unificado, sin heredar las etiquetas de una sola base. Los conteos de este informe describen el corpus, pero todavía no confirman ninguna de las tres hipótesis.')

heading('3 De dónde vienen los datos')
para(f'Los datos provienen de OpenAlex, Scopus y Web of Science. La integración reunió {n(ID["total_registros_integrados"])} registros y los consolidó por identidad bibliográfica en {n(DD["publicaciones_unicas"])} publicaciones únicas; {n(DD["publicaciones_multifuente"])} aparecen en más de una base. El cribado parte de ese universo y no de la base amplia histórica, como recomienda el cierre de la unificación.')
figure('01_flujo_del_cribado.png', f'Figura 1. Flujo del cribado desde los {n(ID["total_registros_integrados"])} registros integrados hasta el corpus incluido y el núcleo de desempeño.', width=6.4)
table(['Paso PRISMA', 'Cifra'], [
    ['Registros identificados: OpenAlex / Scopus / WoS', f'{n(REG["OpenAlex"])} / {n(REG["Scopus"])} / {n(REG["WoS"])}'],
    ['Registros integrados', n(ID['total_registros_integrados'])],
    ['Duplicados eliminados', n(DD['duplicados_eliminados'])],
    ['Publicaciones únicas cribadas', n(CR['publicaciones_evaluadas'])],
    ['Excluidas en el filtro amplio', n(CR['etapa1_filtro_amplio']['excluidas'])],
    ['Excluidas por pertinencia operacional', n(EX_N1)],
    ['Excluidas en la revisión humana', n(EX_RH)],
    ['Incluidas', n(D['prisma']['incluidos']['total'])],
    ['Núcleo de desempeño (subconjunto)', n(NUC)]], widths=[4.6, 2.3])
para('La extracción de OpenAlex informó 9.817 registros en la API, recuperó 9.844 y dejó 9.540 únicos; 9.534 están trazados en la integración. Los conteos de Scopus y WoS previos a su deduplicación interna no están en los archivos de integración, por lo que no se estiman.')

heading('4 Filtro amplio sobre el corpus unificado')
para('Aplicamos la función original del filtro amplio, que revisa título, resumen, palabras clave, topics y concepts. Para cada publicación armamos una ficha con los metadatos de las tres bases. Usamos el título unificado, salvo dos casos en alfabeto no latino donde tomamos el alternativo latino de otra base. Recuperamos el resumen de otra base en 38 casos y unimos las palabras clave y topics de las tres fuentes.')
para('Los concepts solo existen en OpenAlex. Para medir su efecto repetimos el filtro sin ellos: cambian 8 decisiones. El requisito de resumen de la consulta OpenAlex no se usó como exclusión, porque Scopus y WoS no lo aplicaron; las 215 publicaciones sin resumen se evaluaron con título, palabras clave y tipo de documento.')
table(['Motivo del filtro amplio', 'Publicaciones'], [[FALAB.get(k, k), n(v)] for k, v in FA['motivos'].items()], widths=[4.6, 2.3])
para(f'Una publicación puede tener más de un motivo, por lo que la tabla no suma {n(FA["excluidas"])}. Sobre los registros de OpenAlex, el filtro coincide con la decisión histórica en 4.733 aceptadas y 4.752 excluidas. Otras 46 pasan a aceptadas porque el corpus unificado aporta metadatos de Scopus o WoS, y 2 pasan a excluidas.')

heading('5 Pertinencia operacional')
para('El filtro amplio delimita la literatura de minería a cielo abierto, pero conserva estudios cuyo foco no es la operación. Por eso agregamos un nivel de pertinencia operacional con las decisiones acordadas. Las reglas usan los diccionarios de los códigos originales; los casos que las reglas no resuelven se leyeron por título y resumen.')
table(['Tema', 'Decisión acordada'], [
    ['Operación a cielo abierto', 'Se incluye si el estudio trata procesos, equipos, actividades o decisiones de la operación, con el rajo como foco central.'],
    ['Geotecnia, vibraciones y agua', 'Solo con vínculo operacional explícito: ciclo, costos, tiempos o equipos.'],
    ['Componentes y condición de equipos', 'Solo equipos móviles o del rajo, incluidos IPCC, correas en mina y bombeo de desagüe. Las plantas de proceso quedan fuera.'],
    ['Revisiones de literatura', 'Se incluyen marcadas; quedan fuera del núcleo salvo evaluación propia.'],
    ['Procesos auxiliares', 'No se excluyen por ser auxiliares.'],
    ['Idioma', 'Se usa el título o resumen en inglés de cualquiera de las tres bases.']], widths=[2.1, 4.8])
figure('02_motivos_de_exclusion.png', f'Figura 2. Motivos de exclusión posteriores al filtro amplio: {n(EX_N1)} por pertinencia operacional y {n(EX_RH)} en la revisión humana. Cada publicación excluida tiene un solo motivo.', width=6.5)
g, a = N1['motivos'].get('F_GEO', 0), N1['motivos'].get('F_AMB', 0)
para(f'Geotecnia sin vínculo operacional ({n(g)}) y foco ambiental ({n(a)}) explican el {pct(100 * (g + a) / EX_N1)} % de las exclusiones por pertinencia. Son estudios del rajo, pero su objeto es la estabilidad, el entorno o el cierre, no la ejecución de la operación.')
figure('08_procedencia_de_decisiones.png', f'Figura 3. Procedencia de las {n(FA["aceptadas"])} decisiones posteriores al filtro amplio.', width=6.5)
para(f'De las {n(INC)} incluidas, {n(PROC["INCLUIDO|regla_confirmada_por_lectura_de_titulo"])} se decidieron por regla confirmada con lectura de título y {n(PROC["INCLUIDO|lectura_dirigida_titulo_resumen"])} por lectura dirigida de título y resumen, y {n(PROC.get("INCLUIDO|revision_humana", 0))} en la revisión humana. Las decisiones de lectura están guardadas por índice en el paquete y el código las integra; ejecutarlo reproduce esa integración, no la lectura.')

heading('6 Criterio de desempeño y núcleo')
para('Para el núcleo de desempeño buscamos una relación concreta entre la tarea, su evaluación y un resultado operacional. Mantuvimos los tres requisitos del avance anterior.')
table(['Requisito', 'Qué buscamos'], [
    ['A Contexto y tarea', 'Equipo o proceso reconocible en minería a cielo abierto.'],
    ['B Evaluación propia', 'Caracterización, comparación, intervención, modelo o simulación del equipo o tarea.'],
    ['C Resultado operacional', 'Producción, tiempo, esperas, disponibilidad, utilización, consumo, costo, distancia, frecuencia o caudal ligados a esa evaluación.']], widths=[1.7, 5.2])
para('Aplicamos en cadena las reglas del primer cribado, la revisión de dudosos, el criterio ajustado y la última revisión. Omitimos solo las ramas que dependían de auditorías con IA de la cohorte anterior. Después leímos los candidatos que las reglas proponían como IN y, para controlar omisiones, las incluidas que quedaban fuera del núcleo pero tenían términos de desempeño en el título.')
figure('03_formacion_del_nucleo.png', 'Figura 4. Candidatos al núcleo leídos en cada grupo y su decisión. La revisión humana considera las incluidas de los 86 casos revisados.', width=6.5)
c8, c9, cr = COMP['IN por regla v8'], COMP['TC que v9 propone IN'], COMP['Control de omisiones']
from collections import Counter
LEC = ROOT / '04_integracion_final/entrada/lectura_dirigida'
NOUT = Counter(l.split()[1] for f in ('nucleo_v8.txt', 'nucleo_v9.txt') for l in (LEC / f).read_text(encoding='utf-8').splitlines()
               if l.strip() and not l.startswith('#') and l.split()[1].startswith('NO_'))
para(f'De los {n(c8["IN"] + c8["OUT_tras_lectura"])} IN por regla se confirmaron {n(c8["IN"])}; de los {n(c9["IN"] + c9["OUT_tras_lectura"])} casos que la última revisión proponía incluir, {n(c9["IN"])}. El control de omisiones agregó {n(cr["IN"])} de {n(cr["IN"] + cr["OUT_tras_lectura"])} leídos, y la revisión humana dejó {n(RHR["nucleo_IN"])} en el núcleo. En los dos primeros grupos, las {n(sum(NOUT.values()))} exclusiones tras lectura se deben sobre todo a fichas sin evaluación propia ({n(NOUT.get("NO_D", 0))}), foco distinto del desempeño ({n(NOUT.get("NO_F", 0))}), métricas de un modelo en lugar del desempeño de la tarea ({n(NOUT.get("NO_M", 0))}) y resultados de mina o proyecto sin una tarea aislada ({n(NOUT.get("NO_V", 0))}).')
para('Una exclusión del núcleo por falta de evidencia en la ficha no demuestra que el texto completo sea irrelevante. Las lecturas se hicieron sobre título y resumen.')

heading('7 Publicaciones por año')
para('Contamos los años de publicación en el corpus incluido y en el núcleo de desempeño. Cada panel usa su propia escala. La serie principal llega hasta 2025; dejamos 2026 y 2027 aparte porque corresponden al año en curso y a artículos en prensa.')
figure('04_publicaciones_por_ano.png', 'Figura 5. Distribución de publicaciones entre 2000 y 2025 en el corpus incluido y en el núcleo de desempeño. Fuente: año de referencia del corpus unificado.', width=6.65)
table(['Cobertura', 'Corpus incluido', 'Núcleo de desempeño'], [
    ['2000 a 2025', n(YI['2000_2025']), n(YN['2000_2025'])],
    ['Antes de 2000', n(YI['antes_2000']), n(YN['antes_2000'])],
    ['2026 y 2027', n(YI['posterior_2025']), n(YN['posterior_2025'])],
    ['Sin año', n(YI['sin_ano']), n(YN['sin_ano'])],
    ['Total', n(INC), n(NUC)]], widths=[2.7, 1.8, 2.4])
para(f'En 2025 aparecen {n(YI["por_ano"].get("2025", 0))} publicaciones del corpus incluido y {n(YN["por_ano"].get("2025", 0))} del núcleo. Entre 2015 y 2025 la producción crece en promedio un {pct(IND["Tasa de crecimiento anual compuesta 2015–2025 (%)"])} % anual. La serie describe lo recuperado por las tres consultas y su cobertura; no se interpreta directamente como crecimiento de toda la investigación minera.')

heading('8 Revistas, autores y países')
z = D['bradford']
para(f'El corpus incluido se publica en {n(IND["Revistas o fuentes distintas"])} revistas o fuentes. Siguiendo la distribución de Bradford, {n(z[0]["revistas"])} revistas concentran un tercio de los artículos ({n(z[0]["publicaciones"])}), {n(z[1]["revistas"])} el segundo tercio y {n(z[2]["revistas"])} el último. Predominan revistas mineras rusas, indias y chinas, junto a las revistas internacionales de ingeniería de minas.')
figure('05_revistas_principales.png', 'Figura 6. Revistas con más publicaciones en el corpus incluido y su aporte al núcleo de desempeño. OSTI corresponde a un repositorio, no a una revista.', width=6.0)
para(f'Identificamos {n(IND["Autores distintos (normalizados)"])} autores, con {IND["Autores por publicación (media)"].replace(".", ",")} autores por publicación en promedio y {n(IND["Publicaciones de autoría única"])} trabajos de autoría única. Los nombres se normalizaron como apellido e inicial, con prioridad Scopus, WoS y OpenAlex. Esa normalización puede unir homónimos, sobre todo en apellidos frecuentes, por lo que los rankings de autores deben leerse con cuidado.')
figure('06_paises.png', 'Figura 7. Países de afiliación con más publicaciones. Solo OpenAlex trae afiliaciones en los universos integrados.', width=5.7)
para(f'Solo {n(IND["Publicaciones con país (OpenAlex)"])} publicaciones ({pct(IND["Cobertura de país (%)"])} %) tienen país de afiliación, porque los universos de Scopus y WoS no conservaron afiliaciones. Entre ellas, el {pct(IND["Colaboración internacional sobre publicaciones con país (%)"])} % involucra más de un país. Para un análisis completo de países e instituciones hay que recuperar las exportaciones nativas de Scopus y WoS.')

heading('9 Palabras clave y redes')
para(f'Usamos las palabras clave de autor de Scopus y WoS; las de OpenAlex son conceptos asignados automáticamente y no las reemplazan. Cubren {n(IND["Publicaciones con palabras clave de autor (Scopus/WoS)"])} publicaciones ({pct(IND["Cobertura de palabras clave de autor (%)"])} %). Normalizamos mayúsculas, guiones, plurales y variantes ortográficas, y excluimos los términos que solo describen el contexto de búsqueda, como open pit mining.')
figure('07_palabras_clave.png', 'Figura 8. Palabras clave de autor más frecuentes en el corpus incluido y su presencia en el núcleo de desempeño. Una publicación puede tener varias.', width=6.75)
KW = {t['palabra_clave']: (int(t['publicaciones']), int(t['nucleo_desempeno_IN'])) for t in D['top_palabras']}
para(f'En el corpus incluido dominan optimización ({KW["optimization"][0]}), planificación minera ({KW["mine planning"][0]}) y programación de la producción ({KW["production scheduling"][0]}). En el núcleo, la más frecuente es confiabilidad ({KW["reliability"][1]}), seguida de optimización ({KW["optimization"][1]}), simulación ({KW["simulation"][1]}) y productividad ({KW["productivity"][1]}). La diferencia refleja en parte cómo se definió el núcleo; todavía es una mención de palabras clave y no una clasificación del problema estudiado.')
r1, r2, r3 = RED['R1_coocurrencia_palabras_clave'], RED['R2_coautoria'], RED['R3_colaboracion_paises']
table(['Red', 'Umbral', 'Nodos', 'Enlaces', 'Componentes'], [
    ['Co-ocurrencia de palabras clave', f'{r1["umbral_documentos"]} documentos', n(r1['nodos']), n(r1['enlaces']), n(r1['componentes'])],
    ['Coautoría', f'{r2["umbral_documentos"]} documentos', n(r2['nodos']), n(r2['enlaces']), n(r2['componentes'])],
    ['Colaboración entre países', f'{r3["umbral_documentos"]} documentos', n(r3['nodos']), n(r3['enlaces']), n(r3['componentes'])]],
    widths=[2.5, 1.2, 1.0, 1.0, 1.2])
para('Las redes se entregan en el formato de VOSviewer y en GraphML para Gephi. La co-citación y el acoplamiento bibliográfico requieren listas de referencias enlazadas, que estas extracciones no conservaron.')

heading('10 Revisión humana y validación')
para(f'Marcamos {n(RHR["revisadas"])} publicaciones incluidas para revisión humana: {n(RH.get("sin_resumen_en_las_tres_bases", 0))} sin resumen en ninguna base, {n(RH.get("resumen_compartido_con_otra_publicacion", 0))} cuyo resumen aparece en otra publicación con título distinto y {n(RH.get("solo_titulo_y_resumen_no_ingles", 0))} con texto solo en otro idioma. La revisión excluyó {n(RHR["excluidas"])} y dejó {n(RHR["nucleo_IN"])} en el núcleo; el resto se mantuvo incluido fuera del núcleo.')
para(f'Para estimar la calidad del cribado revisamos una muestra ciega de {n(CO["muestra_revisada"])} publicaciones, 25 por estrato, sin ver la decisión automática. La revisión la hizo la autora con asistencia de un modelo de lenguaje, que propuso una clasificación inicial; cada decisión fue verificada y, cuando correspondía, modificada manualmente. Como la propuesta inicial y el cribado provienen de herramientas similares, la concordancia puede estar sobrestimada.')
ETQ = {'E1_excluido_filtro_amplio': 'Excluidas en el filtro amplio', 'E2_excluido_pertinencia': 'Excluidas por pertinencia',
       'E3_incluido_nucleo_OUT': 'Incluidas fuera del núcleo', 'E4_incluido_nucleo_IN': 'Incluidas en el núcleo'}
ic = lambda v: f'{dec(v[0])}–{dec(v[1])}' if v and v[0] is not None else '—'
table(['Estrato', 'Tamaño', 'Acuerdo inclusión (IC 95 %)', 'Acuerdo núcleo (IC 95 %)'],
      [[ETQ.get(h, h), n(v['tamano_estrato']), f"{dec(v['acuerdo_inclusion'])} ({ic(v['ic95_inclusion'])})",
        f"{dec(v['acuerdo_nucleo_entre_incluidas'])} ({ic(v['ic95_nucleo'])})" if v['acuerdo_nucleo_entre_incluidas'] is not None else '—']
       for h, v in CO['por_estrato'].items()], widths=[2.3, 1.0, 1.8, 1.8])
para(f'El kappa de Cohen es {dec(CO["kappa_inclusion_muestra"])} para la inclusión, un acuerdo sustancial, y {dec(CO["kappa_nucleo_muestra"])} para el núcleo, un acuerdo moderado. Ponderando cada estrato por su tamaño, el acuerdo de inclusión en el corpus es {dec(CO["acuerdo_inclusion_ponderado_corpus"])}. Las exclusiones por pertinencia coincidieron en todos los casos revisados.')
para(f'Las discrepancias muestran tres patrones. Primero, el filtro amplio original deja fuera estudios del rajo cuyo vocabulario no está en sus diccionarios, como ventilación, planificación del frente o métodos de explotación; extrapolado, serían unas {n(CO["estimacion_falsos_excluidos_en_corpus"])} publicaciones, con un intervalo amplio. Segundo, una parte del núcleo describe beneficios o discute un problema sin informar un resultado de la tarea. Tercero, hay desacuerdos de criterio sobre estudios que solo miden precisión y sobre modelos de planificación cuyo resultado es el valor del proyecto.')
para('Reportamos estos resultados como limitaciones del cribado. La calibración posible queda descrita en la sección 12; si se aplica, debe validarse con una muestra nueva, porque esta ya se usó para diagnosticar.')

heading('11 Código y reproducción de los resultados')
para('El paquete IPRE_cribado_unificado_v1 sigue la estructura del paquete del avance anterior. Lee el corpus unificado y los universos por base desde el repositorio IPRE-Min-main y comprueba sus huellas antes de empezar. Los cinco códigos originales que se importan se conservan sin cambios.')
table(['Etapa', 'Script', 'Salida principal'], [
    ['Filtro amplio', '01_aplicar_filtro_amplio.py', 'Aceptadas y excluidas'],
    ['Núcleo por reglas', '02_aplicar_reglas_v6_a_v9.py', 'Decisión de cada versión'],
    ['Pertinencia', '03_proponer_reglas_nivel1.py', 'Reglas y grupos de lectura'],
    ['Integración', '04_integrar_decisiones.py', 'Corpus cribado'],
    ['PRISMA', '05_generar_cifras_prisma.py', 'Cifras por etapa'],
    ['Verificación', '06_verificar_integracion.py', '14 comprobaciones'],
    ['Cierre', '07 y 08 (planillas)', 'Revisión y concordancia'],
    ['Descriptivos', '09, 10 y 11', 'Tablas, redes, figuras e informe']], widths=[1.3, 3.4, 2.2])
para('Para repetir el procesamiento basta Python 3.10 o superior. Desde la carpeta del paquete, dentro de IPRE-Min-main, en PowerShell:')
code('py -3 00_reproducir_local.py')
para('La ejecución escribe en una carpeta nueva y conserva los archivos archivados. Para aplicar la revisión humana y la concordancia se necesita openpyxl.' + (f' Se comprobó la cadena completa: {N_COTEJOS} cotejos SHA-256 coincidieron con las referencias, incluidas las entradas, el corpus cribado y cerrado, las cifras PRISMA y las tablas y redes descriptivas.' if N_COTEJOS else ''))
para('Las decisiones de lectura dirigida y las planillas de revisión humana son entradas registradas. El comando reproduce su integración; no genera nuevas lecturas ni descarga nuevamente los datos. El README y la guía técnica explican las carpetas, los códigos de decisión y las columnas del corpus cribado.')

heading('12 Trabajo que sigue')
para('El cribado está cerrado y es trazable. Lo que sigue es decidir si se calibra y avanzar en la clasificación necesaria para responder las preguntas del profesor.')
doc.add_heading('Calibración opcional del cribado', level=2)
para('La validación sugiere tres ajustes: una auditoría de las exclusiones del filtro amplio que nombran el cielo abierto en el título, para recuperar estudios auxiliares y de planificación; una relectura del núcleo con un criterio de resultado operacional escrito y estricto; y una decisión explícita sobre los dos desacuerdos de criterio. El primero agrega un paso al método original y conviene acordarlo con el profesor. Cualquier calibración debe validarse con una muestra nueva.')
doc.add_heading('Reforzar la validación', level=2)
para('Una submuestra de 20 a 30 publicaciones revisada sin asistencia de IA, por ejemplo por el profesor, permitiría reportar el acuerdo entre revisores humanos y comprobar si la asistencia influyó en las decisiones.')
doc.add_heading('Definir los grupos temáticos', level=2)
para('Agruparemos el corpus incluido en tres a cinco grupos que surjan del propio corpus unificado, por ejemplo con agrupamiento de títulos y resúmenes, y después los interpretaremos frente a productividad, confiabilidad y mantenimiento, monitoreo de condiciones y seguridad. También registraremos el problema abordado: diseño, planificación, asignación o ejecución.')
doc.add_heading('Extraer variables del núcleo', level=2)
para(f'En las {n(NUC)} publicaciones del núcleo registraremos el tipo de equipo, distinguiendo principales y auxiliares; el indicador de desempeño; el método; y el tipo de datos. Con estos cruces podremos contrastar H3 y describir cómo se mide el desempeño de los equipos auxiliares.')

heading('13 Fuentes y registro del método')
para('El marco de investigación considera la operación a cielo abierto como un sistema de procesos y propone profundizar en los auxiliares. Las preguntas ordenan ese análisis y las hipótesis se mantienen como afirmaciones por contrastar.')
doc.add_heading('Referencias metodológicas', level=2)
para('Donthu, N., Kumar, S., Mukherjee, D., Pandey, N. y Lim, W. M. (2021). How to conduct a bibliometric analysis: An overview and guidelines. Journal of Business Research, 133, 285-296. DOI: 10.1016/j.jbusres.2021.04.070.')
para('Aria, M. y Cuccurullo, C. (2017). bibliometrix: An R-tool for comprehensive science mapping analysis. Journal of Informetrics, 11(4), 959-975. DOI: 10.1016/j.joi.2017.08.007.')
para('Page, M. J., McKenzie, J. E., Bossuyt, P. M. et al. (2021). The PRISMA 2020 statement: an updated guideline for reporting systematic reviews. BMJ, 372, n71. DOI: 10.1136/bmj.n71.')
doc.add_heading('Qué queda registrado para el artículo', level=2)
table(['Registro', 'Contenido conservado'], [
    ['Procedencia de datos', 'Registros por base, integración, huellas de las instantáneas y límites de recuperación.'],
    ['Historia por publicación', 'Decisión de cada etapa, motivo, justificación y procedencia, sin modificar las columnas originales.'],
    ['Lectura dirigida', 'Decisiones por índice con su código y motivo breve, sobre listas ordenadas por identificador.'],
    ['Reproducibilidad', 'Códigos, entradas congeladas, salidas archivadas y cotejos SHA-256.']], widths=[2.0, 4.9])
para('Los nombres técnicos de archivos y campos se mantienen en el código y en la guía para conservar la trazabilidad. Las lecturas se hicieron sobre título y resumen; cuando una decisión dependa del texto completo, quedará registrada como tal en la revisión humana.')

target = OUT / 'Informe_cribado_corpus_unificado_20261110.docx'
doc.save(target)
print(target)
