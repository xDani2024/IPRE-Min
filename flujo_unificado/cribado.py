"""Cribado exploratorio común, versión 1.1.

Se ejecuta DESPUÉS de integrar y deduplicar OpenAlex, Scopus y WoS.
Usa únicamente título, resumen y tipo documental para decidir; no consulta
las etiquetas, fuentes ni decisiones antiguas. Las decisiones son *sugerencias*,
no inclusiones/exclusiones finales. Requiere validación humana.

Las expresiones nuevas complementan (no reemplazan) los diccionarios
históricos de OpenAlex; todas las tres fuentes reciben las mismas reglas.
"""
from __future__ import annotations
import importlib.util
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OA_ORIGINAL = ROOT / 'Código OpenAlex/IPRE_codigo_y_datos_v9/01_extraccion_y_filtro/01_extraer_openalex.py'
VERSION_CRIBADO = '1.1.0-calibracion-pendiente'


@lru_cache(maxsize=1)
def diccionarios_originales():
    spec = importlib.util.spec_from_file_location('ipre_diccionarios_abiertos', OA_ORIGINAL)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(OA_ORIGINAL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normal(texto):
    texto = unicodedata.normalize('NFKD', str(texto or '').lower())
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', texto).strip()


@lru_cache(maxsize=1024)
def patron(frases: tuple[str, ...]):
    terminos = [normal(t) for t in frases if normal(t)]
    if not terminos:
        return None
    return re.compile(r'(?<![a-z0-9])(?:' + '|'.join(re.escape(t) for t in sorted(set(terminos), key=len, reverse=True)) + r')(?![a-z0-9])')


def coincide(texto, frases):
    p = patron(tuple(frases))
    return bool(p and p.search(texto))


def categorias(texto, diccionario):
    return sorted(k for k, terms in diccionario.items() if coincide(texto, terms))


# Los patrones permiten formas plurales y guiones de las expresiones
# que no eran reconocidas en la primera versión (ej. 'open-pit mines').
DOMINIO_FUERTE = re.compile(
    r'\b(?:open[\s-]?pit\s+min(?:e|es|ing)|open[\s-]?cast\s+mining|'
    r'open[\s-]?cut\s+mining|surface\s+min(?:e|es|ing)|'
    r'open[\s-]?pit\b|opencast\s+mine|'
    r'mine\s+haul(?:age|ing)?|haul\s+road(?:s)?|mine\s+road(?:s)?|'
    r'quarr(?:y|ies)|cantera(?:s)?|mineria\s+a\s+cielo\s+abierto)\b'
)
DOMINIO_MINERO = re.compile(r'\b(?:mining|mines?|mineral\s+extraction|ore\s+extraction|cantera(?:s)?)\b')
# Incluye procesos, vehículos auxiliares y tecnologías directamente
# relacionadas con la medición de operación y condición de equipos.
PROCESO_EQUIPO = re.compile(
    r'\b(?:auxiliary\s+(?:vehicle|vehicles|equipment|operation|operations|fleet)|'
    r'service\s+vehicle(?:s)?|support\s+vehicle(?:s)?|'
    r'drill(?:ing|ability|er|ers|\s+rig|\s+machine)|blast(?:ing|ability|hole)|'
    r'haul(?:age|ing|\s+truck|\s+road)|truck(?:s)?|vehicle(?:s)?|'
    r'dozers?|bulldozers?|wheel[\s-]?dozers?|graders?|motor\s+graders?|'
    r'road\s+maintenan(?:ce|ces)|road\s+grading|'
    r'water\s+trucks?|water\s+cart(?:s)?|watering|dust\s+suppression|'
    r'shovels?|excavator(?:s)?|loaders?|crushers?|chancador(?:es)?|'
    r'conveyors?|pumps?|mining\s+machin(?:e|es)|heavy\s+equip(?:ment)?|'
    r'maintenan(?:ce|ces)|reliability|machine\s+condition|equipment\s+condition|'
    r'wheel\s+loader(?:s)?|operational\s+(?:equipment|fleet))\b'
)
# Algunas entradas son conceptos generales; nunca bastan sin contexto minero
# y sin proceso/equipo para decidir inclusión.
OBJETIVO_OPERACIONAL = re.compile(
    r'\b(?:productivit(?:y|ies)|performance|operational|operation(?:s)?|'
    r'efficien(?:cy|cies|t)|utili[sz]ation|availability|downtime|'
    r'cycle\s+time|production\s+rate|rate\s+of\s+drilling|drilling\s+rate(?:s)?|'
    r'failure(?:s)?|breakdown(?:s)?|wear|tribolog\w*|'
    r'vibration(?:s)?|sensor(?:s)?|condition\s+monitoring|oil\s+analys(?:is|es)|'
    r'predicti(?:on|ve)|optimization|optimisation|optim(?:al|ize|ise)|'
    r'route(?:s)?|routing|travel\s+time|traveling\s+salesman|'
    r'dispatch(?:ing)?|schedul(?:e|es|ing)|maintenan(?:ce|ces)|'
    r'work\s+task(?:s)?|task\s+identification|road\s+roughness|'
    r'work\s+quality|monitor(?:ing)?|simulation|digital\s+technology|'
    r'repair(?:s)?|automatic|automation|autonomous)\b'
)
# Motivos explícitamente editoriales. No se excluye por mencionar 'fair' o
# 'exhibition' en el abstract de un estudio, solo cuando el título es del evento.
TITULO_EVENTO = re.compile(
    r'\b(?:\d{4}\s+hanover\s+fair|industrial\s+(?:fair|exhibition)|'
    r'conference\s+(?:calendar|program(?:me)?)|trade\s+(?:fair|show)|'
    r'exhibition\s+(?:news|report))\b'
)
SUBTERRANEA = re.compile(r'\b(?:longwall|block\s+cav(?:ing|e)|subterranean|underground\s+coal\s+mine)\b')
TERMINOS_SECUNDARIOS = re.compile(r'\b(?:reclamation|revegetation|post[\s-]?mining|ecosystem|ecology|wildlife|land\s+cover)\b')


def _result(estado, razones, procesos, equipos, focos, contexto, tarea, objetivo, prioridad):
    return {
        'cribado_automatico': estado,
        'motivos_cribado': '|'.join(razones),
        'procesos_sugeridos': '|'.join(procesos),
        'equipos_sugeridos': '|'.join(equipos),
        'focos_sugeridos': '|'.join(focos),
        'evidencia_contexto_minero': contexto,
        'evidencia_proceso_equipo': tarea,
        'evidencia_objetivo': objetivo,
        'prioridad_revision': prioridad,
        'version_cribado': VERSION_CRIBADO,
        'decision_humana': '', 'motivo_decision_humana': '',
        'revisor': '', 'fecha_revision': '',
    }


def evaluar(publicacion):
    """Proponer, NUNCA confirmar, elegibilidad a partir de título y abstract.

    'CANDIDATO' necesita señales de actividad concreta y contexto minero.
    'REVISION_PRIORITARIA' retiene casos con evidencia parcial o contradictoria.
    'PENDIENTE_REVISION' retiene metadatos insuficientes.
    'EXCLUSION_PROPUESTA' requiere revisión humana antes de excluir.
    """
    d = diccionarios_originales()
    titulo = normal(publicacion.get('titulo'))
    resumen = normal(publicacion.get('resumen'))
    todo = f'{titulo} {resumen}'
    tipo = normal(publicacion.get('tipo_documento'))
    procesos = categorias(todo, d.PROCESS_TERMS)
    equipos = categorias(todo, d.EQUIPMENT_TERMS)
    focos = categorias(todo, d.FOCUS_TERMS)

    ctx_t = bool(DOMINIO_FUERTE.search(titulo))
    ctx_a = bool(DOMINIO_FUERTE.search(resumen))
    mine_general = bool(DOMINIO_MINERO.search(todo))
    # 'data mining' no aporta por sí solo contexto operacional.
    ctx = ctx_t or ctx_a
    tarea_t = bool(PROCESO_EQUIPO.search(titulo))
    tarea_a = bool(PROCESO_EQUIPO.search(resumen))
    foco_t = bool(OBJETIVO_OPERACIONAL.search(titulo))
    foco_a = bool(OBJETIVO_OPERACIONAL.search(resumen))
    # Para mantener trazabilidad, mostramos la primera evidencia exacta.
    contexto = (DOMINIO_FUERTE.search(titulo) or DOMINIO_FUERTE.search(resumen))
    tarea = (PROCESO_EQUIPO.search(titulo) or PROCESO_EQUIPO.search(resumen))
    objetivo = (OBJETIVO_OPERACIONAL.search(titulo) or OBJETIVO_OPERACIONAL.search(resumen))
    evidencia_ctx = contexto.group() if contexto else ('mineria_generica' if mine_general else '')
    evidencia_tarea = tarea.group() if tarea else ''
    evidencia_foco = objetivo.group() if objetivo else ''

    if not titulo:
        estado, razones = 'PENDIENTE_REVISION', ['sin_titulo']
    elif not resumen:
        estado, razones = 'PENDIENTE_REVISION', ['sin_resumen']
    elif not tipo:
        estado, razones = 'PENDIENTE_REVISION', ['tipo_no_informado']
    elif not any(x.strip() in {'article', 'review'} for x in tipo.split(';')):
        # Se aplica el criterio DOCUMENTAL heredado, no uno temático.
        estado, razones = 'EXCLUSION_PROPUESTA', ['tipo_documental_no_admitido']
    elif TITULO_EVENTO.search(titulo) and not (ctx_t and tarea_t and foco_t):
        estado, razones = 'EXCLUSION_PROPUESTA', ['publicacion_de_evento_sin_estudio_operacional']
    elif SUBTERRANEA.search(titulo) and not ctx:
        estado, razones = 'EXCLUSION_PROPUESTA', ['metodo_subterraneo_fuera_de_alcance']
    elif ctx and tarea_t and (foco_t or foco_a or tarea_a):
        if TERMINOS_SECUNDARIOS.search(titulo) and not (foco_t and tarea_t):
            estado, razones = 'REVISION_PRIORITARIA', ['tema_potencialmente_secundario']
        else:
            estado, razones = 'CANDIDATO', ['contexto_minero_y_proceso_en_titulo']
    elif ctx and tarea_a and (foco_t or foco_a):
        if ctx_t or foco_t:
            estado, razones = 'CANDIDATO', ['contexto_minero_y_proceso_en_resumen']
        else:
            estado, razones = 'REVISION_PRIORITARIA', ['proceso_operacional_solo_en_resumen']
    elif ctx and (tarea_t or tarea_a or foco_t):
        estado, razones = 'REVISION_PRIORITARIA', ['contexto_minero_con_evidencia_parcial']
    elif ctx:
        estado, razones = 'PENDIENTE_REVISION', ['contexto_minero_sin_proceso_identificado']
    elif mine_general and tarea_t and (foco_t or foco_a or tarea_a):
        estado, razones = 'REVISION_PRIORITARIA', ['contexto_minero_general_revisar_pertinencia']
    else:
        estado, razones = 'EXCLUSION_PROPUESTA', ['sin_evidencia_de_operacion_minera']
    prioridad = 'ALTA' if estado == 'REVISION_PRIORITARIA' else (
        'BAJA' if 'contexto_minero_sin_proceso_identificado' in razones else
        'MEDIA' if estado == 'PENDIENTE_REVISION' else 'NORMAL')
    return _result(estado, razones, procesos, equipos, focos, evidencia_ctx, evidencia_tarea, evidencia_foco, prioridad)
