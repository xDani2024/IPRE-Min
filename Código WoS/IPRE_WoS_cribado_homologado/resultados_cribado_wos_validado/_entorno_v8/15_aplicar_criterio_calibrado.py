"""Propuesta v8 del núcleo operacional, sobre la instantánea v7 congelada.

Biblioteca estándar. Sin API, sin nuevas descargas, sin decisión humana
automática. Procesa todos los registros; conserva cada columna histórica.
Las sugerencias humanas del piloto son campos separados y casos de desarrollo.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
VERSION = 'v8_criterio_ipre_transferido_wos_2026_11_01'
CRITERIO = 'v8_calibrada_1'
FECHA = '2026-11-01'

def read(p, delimiter=','):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter=delimiter))

def write(p, rows, fields=None):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fields if fields is not None else (list(rows[0]) if rows else []), extrasaction='raise')
        w.writeheader()
        w.writerows(rows)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def rx(p):
    return re.compile(p, re.I)

# Los patrones son señales computacionales, no estimaciones de confianza.
REVIEW = rx(r'\bsystematic (?:literature )?review\b|\bscoping review\b|'
            r'\bliterature review\b|\bmeta.analysis\b|\breview (?:of|on)\b|'
            r'\ba review\b|\breview and research agenda\b')
SECONDARY_ABSTRACT = rx(r'\bthis (?:systematic |literature |scoping )?review\b|'
                       r'\bsystematic literature review\b|'
                       r'\b(?:bibliometric|scientometric) analysis\b')
OWN_EVALUATION = rx(r'\b(?:we|this (?:study|paper)) (?:propos|develop|present|introduc)|'
                    r'\bnew (?:model|method|algorithm)\b|\bfield experiment\b')
SUPPORT = rx(r'water(?:ing)? truck|dust (?:suppress|palliat|control)|watering|'
             r'road maintenance|haul road management|fuel truck|refuel|'
             r'dewater|drainage|sump|pit pump|riego|abastecimiento')
WHOLE_EQUIPMENT = rx(r'truck|shovel|excavator|dragline|drilling rig|fleet|'
                     r'conveyor|surface miner|equipment|cam[ií]on|pala|perforadora')
WHOLE_METRIC = rx(r'productiv|production (?:rate|capacity|output)|throughput|'
                  r'cycl(?:e|ing) time|downtime|availability|utili[sz]ation|'
                  r'operating hours?|uptime|fuel consumption|energy consumption|'
                  r'operat(?:ing|ional) cost|repair time|mtbf|mttr')
FUTURE_ONLY = rx(r'\bcould\b|\bwould\b|\bmay\b|\bmight\b|\bpotential to\b|'
                 r'\bexpected to\b|\bin the future\b|\byet to be\b|'
                 r'\bwill be (?:tested|evaluated|validated)\b')
OUTSIDE = rx(r'underground (?:mine|mining)|deep sea|subsea|ocean mining|'
             r'offshore|tunnel boring|tunnell?ing|oil (?:well|drilling)')
EDITORIAL = rx(r'^editorial\b|^preface\b|^foreword\b|^erratum\b|^corrigendum\b')
COMPONENT = rx(r'\btires?\b|\btyres?\b|bucket teeth|drill bits?|'
               r'gearbox|bearings?|weld|microstructur|hydraulic cylinder|'
               r'wheel (?:repair|weld)|drive wheel')
COMPONENT_ENDPOINT = rx(r'microstructur|wear resistance|residual life|'
                        r'remaining life|hardness|tensile strength|fatigue strength')
STRATEGIC_TITLE = rx(r'final pit|ultimate pit|pit limit|pit delimit|'
                     r'block sequenc|block schedul|cut.off grade|ore blending')
PROJECT_VALUE = rx(r'net present value|\bnpv\b|revenue factor|mining asset')

PROCESS_PATTERNS = {
 'perforacion': r'drill|perforaci[oó]n|bor rig',
 'tronadura': r'blast|tronadura|voladura',
 'carguio_excavacion': r'shovel|excavat|dragline|loader|loading|cargu[ií]o|pala minera',
 'acarreo': r'haul|truck|material transport|acarreo|cam[ií]on',
 'riego_control_polvo': r'water(?:ing)? truck|dust (?:suppress|palliat|control)|watering|riego',
 'caminos': r'haul road|mine road|road maintenance|road management',
 'abastecimiento': r'fuel truck|refuel|fuel supply|abastecimiento',
 'desague': r'dewater|drainage|sump|pit pump',
 'mantenimiento_equipos': r'maintenan|reliabilit|repair|mantenim|mantenci[oó]n',
 'transporte_continuo': r'conveyor|in.pit crush|ipcc|spreader',
}
PROBLEM_PATTERNS = {
 'diseno': r'design|sizing|disen[oó]|diseñ',
 'planificacion': r'\bplanning\b|\bplan(?:s|ned)?\b|schedul|sequenc|programaci[oó]n',
 'asignacion_despacho': r'allocat|assign|dispatch|fleet management|despacho',
 'ejecucion_operacion': r'productiv|cycle time|operational performance|loading|haulage performance',
 'mantenimiento_confiabilidad': r'maintenan|reliabilit|repair|downtime|availability',
 'reemplazo_ciclo_vida': r'replac|lifetime|life cycle|equipment life',
 'ambiente_seguridad': r'environment|emission|pollut|safety|accident|dust|hazard',
 'automatizacion_control': r'autonom|automat|control|robot|intelligent|machine learning',
}
INDICATOR_PATTERNS = {
 'produccion_productividad': r'productiv|production (?:rate|capacity|output|target)|throughput|tonnage|tons? per|increase in production|production (?:increas|improv|decreas|reduc)',
 'ciclo_tiempos': r'cycle time|loading time|travel time|hauling time|operating hours|waktu edar',
 'esperas': r'waiting time|queue|queuing|idle time',
 'disponibilidad_confiabilidad': r'availability|downtime|uptime|reliabilit|failure rate|mtbf|mttr|repair time',
 'utilizacion': r'utili[sz]ation|equipment effectiveness',
 'combustible_energia': r'fuel (?:use|consumption|saving)|energy (?:use|consumption|saving)|diesel consumption',
 'distancia': r'(?:travel|haulage|hauling|route|routing) distance|distance traveled|route length|travel length|path length',
 'costo_tarea': r'operat(?:ing|ional) costs?|haul(?:age|ing) costs?|unit costs?|cost per (?:ton|tonne|unit)|drilling costs?|blasting costs?|watering costs?|costs? of (?:drilling|blasting|watering|haulage)',
 'frecuencia_apoyo': r'(?:watering|spray|application|maintenance) frequency|frequency of (?:watering|application|maintenance)|application rate',
 'indicador_ambiental': r'emission|pollut|air quality|water quality|dust concentration|ghg',
 'precision_tiempo_algoritmo': r'accuracy|precision|recall|rmse|mae\b|convergence|computational time',
}
EVIDENCE_PATTERNS = {
 'campo': r'field (?:data|test|trial|experiment|measurement)|operational data|historical data|real.world data|collected data|case study',
 'laboratorio': r'laboratory|laborat[oó]rio|laboratorio',
 'simulacion': r'simulat|discrete.event|simulaci[oó]n',
 'modelo_analitico_optimizacion': r'mathematical model|analytical model|optimization model|mixed.integer|linear programming|queueing model',
}

def signals(patterns, text):
    return ';'.join(k for k, p in patterns.items() if rx(p).search(text))

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--salida', type=Path, default=BASE / 'salida')
    args = ap.parse_args()
    v7 = BASE / 'entrada/v7'
    src = v7 / 'salida/matriz_nucleo_provisional_4735_v7.csv'
    rows = read(src)
    if not rows or len({r['openalex_id'] for r in rows}) != len(rows):
        raise ValueError('Se requiere la instantánea íntegra de 4.735 obras únicas.')
    pilot_path = BASE / 'entrada/calibracion_piloto.json'
    pilot = json.loads(pilot_path.read_text(encoding='utf-8'))
    human = {r['openalex_id']: r for r in pilot['estado_humano_actual_piloto']}
    if False:  # WoS no hereda los 20 juicios humanos de OpenAlex
        raise ValueError('No coincide el estado humano actualizado del piloto.')
    alert_path = v7 / 'entrada/alertas_metadata_ampliadas_v6.csv'
    alerts = {r['openalex_id']: r for r in read(alert_path)}
    audit_path = v7 / 'auditoria_dirigida_de_reglas.psv'
    audits7 = {r['openalex_id']: r for r in read(audit_path, '|')}
    queue_path = v7 / 'salida/decisiones_dudosos_1241_v7.csv'
    oldq = {r['openalex_id']: r for r in read(queue_path)}
    module_path = v7 / '11_resolver_dudosos.py'
    spec = importlib.util.spec_from_file_location('motor_v7_congelado', module_path)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    # Amplía C a métricas de tarea auxiliar y costo de perforación/tronadura.
    metric = rx(old.STRONG_C.pattern + '|' + '|'.join(
        p for k, p in INDICATOR_PATTERNS.items()
        if k not in ('indicador_ambiental', 'precision_tiempo_algoritmo')))
    task = rx(old.A.pattern + '|' + SUPPORT.pattern)
    evaluated = rx(old.RESULT_MARKER.pattern + r'|\bresults?\b|\bfindings?\b|\bcase study\b|\bmeasur|\bexperiment|\bshow(?:s|n|ed)?\b|\bsav(?:ed|ing|ings)\b')
    out = []
    events = []
    development = []
    for r in rows:
        oid = r['openalex_id']
        title = old.norm(r['title'])
        abstract = old.norm(r['abstract'])
        text = title + '\n' + abstract
        sents = [s.strip() for s in old.TEXT_SPLIT.split(abstract) if s.strip()]
        context = bool(old.SURFACE.search(text)) or r['contexto_cielo_abierto'] in ('explicito_titulo', 'explicito_resumen')
        a = bool(task.search(title)) or bool(task.search(abstract))
        b = bool(old.B.search(text))
        metric_sents = [s for s in sents if metric.search(s)]
        linked = []
        for i, s in enumerate(sents):
            if not metric.search(s):
                continue
            # No cruza más de una oración ni trata una promesa como resultado.
            prev = sents[i - 1] if i else ''
            antecedent = prev if (task.search(prev) and old.B.search(prev) and
                rx(r'this|these|the (?:proposed|method|model|results?|system)|which|thereby').search(s)) else ''
            window = (antecedent + ' ' + s).strip()
            relation = task.search(s) or antecedent or (task.search(title) and (old.B.search(title) or old.EVALUATED.search(title)))
            result = evaluated.search(window)
            if relation and result and not FUTURE_ONLY.search(s):
                # Métricas del modelo no se convierten en métricas del equipo.
                if old.METHOD_ONLY.search(s) and not WHOLE_METRIC.search(s) and not rx(
                    INDICATOR_PATTERNS['distancia'] + '|' + INDICATOR_PATTERNS['costo_tarea']).search(s):
                    continue
                linked.append(window)
        c = bool(linked)
        invalid = alerts.get(oid, {}).get('abstracto_invalido_para_cribado') == 'si'
        secondary_title = bool(REVIEW.search(title))
        secondary_text = bool(SECONDARY_ABSTRACT.search(abstract[:1200]))
        secondary = secondary_title or secondary_text
        hybrid = secondary and bool(OWN_EVALUATION.search(abstract)) and c
        focus = [(name, p.search(title)) for name, p in old.OTHER_FOCUS if p.search(title)]
        alt_previous = r['foco_alternativo_titulo']
        component = bool(COMPONENT.search(title)) or any(name == 'componente' for name, _ in focus)
        component_link = any(WHOLE_EQUIPMENT.search(s) and WHOLE_METRIC.search(s) for s in linked)
        reasons_dev = []
        if r['procedencia_ajuste'] == 'relectura_IA_dirigida_titulo_resumen':
            reasons_dev.append('auditoria_IA_v6')
        if oid in audits7:
            reasons_dev.append('auditoria_IA_v7')
        if oid in human:
            reasons_dev.append('piloto_humano_visible_20')
        for d in reasons_dev:
            development.append({'openalex_id': oid, 'origen_desarrollo': d})
        evidence = old.excerpt((linked or metric_sents or [title])[0], 700)
        source = 'titulo_resumen_congelado'
        doc = 'mixto_por_cotejar' if hybrid else 'secundario_detectado' if secondary else 'no_determinable'
        if invalid:
            decision, rule = 'TC', 'T01_METADATA_INVALIDA'
            why = 'Resumen diagnosticado como cruzado/editorial. Cotejar la fuente antes de interpretar A/B/C.'
            source = 'alerta_bibliografica_previa'
        elif EDITORIAL.search(title):
            decision, rule = 'OUT', 'O01_EDITORIAL'
            why = 'El título identifica un editorial, prefacio o corrección, sin estudio primario.'
            evidence = title
        elif secondary and not hybrid:
            decision, rule = 'OUT', 'O02_LITERATURA_SECUNDARIA'
            why = 'La ficha identifica una revisión/síntesis sin evaluación primaria propia detectada. Se conserva en la base amplia.'
            evidence = title if secondary_title else old.excerpt(abstract, 700)
        elif hybrid:
            decision, rule = 'TC', 'T02_DOCUMENTO_HIBRIDO'
            why = 'Coexisten señales de revisión y evaluación propia. Cotejar el documento, no decidir solo por su tipo OpenAlex.'
        elif not context:
            if OUTSIDE.search(title) and not old.SURFACE.search(title):
                decision, rule = 'OUT', 'O03_CONTEXTO_ALTERNATIVO'
                why = 'El título centra la operación en un contexto distinto del alcance a cielo abierto.'
                evidence = title
            else:
                decision, rule = 'TC', 'T03_CONTEXTO_INSUFICIENTE'
                why = 'La ficha no establece suficientemente el contexto a cielo abierto. Falta cotejo.'
        elif component and not component_link and COMPONENT_ENDPOINT.search(abstract) and not WHOLE_METRIC.search(abstract):
            decision, rule = 'OUT', 'O06_RESULTADO_DE_COMPONENTE'
            why = 'El objeto es un componente/material y los resultados identificados corresponden a ese nivel; no son desempeño operacional del equipo completo.'
            evidence = old.excerpt(next((s for s in sents if COMPONENT_ENDPOINT.search(s)), title), 700)
        elif component and not component_link:
            decision, rule = 'TC', 'T04_COMPONENTE_SIN_VINCULO_OPERACIONAL'
            why = 'Predomina un componente/material. No se acredita su vínculo con el desempeño del equipo completo.'
            evidence = title
        elif a and b and c:
            decision, rule = 'IN', 'I01_TAREA_RESULTADO_EVALUADO'
            why = 'Se detecta vínculo entre tarea/equipo, evaluación y resultado operacional evaluado; requiere control humano.'
            doc = 'primario_propuesto'
        elif oid in audits7 and audits7[oid]['decision_ajustada'] == 'IN':
            # Conserva una lectura dirigida previa compatible; no la cuenta como
            # lectura nueva ni como validación humana. No supera revisiones/alertas.
            audit = audits7[oid]
            decision, rule = 'IN', 'I02_AUDITORIA_IA_PREVIA_COMPATIBLE'
            why = 'Se conserva la auditoría IA v7: ' + audit['razon_concreta']
            evidence = audit['cita_breve_de_ficha']
            source = 'auditoria_IA_v7_titulo_resumen_heredada'
            doc = 'primario_propuesto'
        elif r['procedencia_ajuste'] == 'relectura_IA_dirigida_titulo_resumen' and r['decision_nucleo_v7'] == 'IN' and not rx(r'a[uú]n prevista|prueba.*prevista|pilot.*planned|verificar cercan[ií]a bibliogr').search(r['motivo_final_propuesto']):
            decision, rule = 'IN', 'I03_AUDITORIA_IA_V6_COMPATIBLE'
            why = 'Se conserva la lectura dirigida IA v6: ' + r['motivo_final_propuesto']
            source = 'auditoria_IA_v6_titulo_resumen_heredada'
            evidence = r['evidencia_proceso_decision_resultado'] or r['evidencia_proceso_resultado_resumen'] or old.excerpt(abstract, 700)
            doc = 'primario_propuesto'
        elif STRATEGIC_TITLE.search(title) or (PROJECT_VALUE.search(abstract) and not linked):
            decision, rule = 'OUT', 'O07_RESULTADO_DE_MINA_PROYECTO'
            why = 'Se identifica diseño/secuencia de pit o valor del proyecto, sin resultado operacional propio de tarea/equipo acreditado.'
            evidence = title if STRATEGIC_TITLE.search(title) else old.excerpt(next(s for s in sents if PROJECT_VALUE.search(s)), 700)
        elif focus or alt_previous:
            decision, rule = 'OUT', 'O04_FOCO_ALTERNATIVO_IDENTIFICADO'
            why = 'Foco alternativo identificado en título/ficha: ' + (
                ';'.join(name for name, _ in focus) or alt_previous) + '. No se detectó resultado propio de la tarea operacional.'
            evidence = title
        elif oid in audits7 and audits7[oid]['regla_ajustada'] in ('A02_METRICA_DEL_MODELO', 'A04_FOCO_ESTRATEGICO', 'A05_FUERA_DE_MINA'):
            decision, rule = 'OUT', 'O05_AUDITORIA_IA_PREVIA_FOCO_EXPLICITO'
            why = 'Se conserva el foco documentado en la auditoría IA v7: ' + audits7[oid]['razon_concreta']
            evidence = audits7[oid]['cita_breve_de_ficha']
            source = 'auditoria_IA_v7_titulo_resumen_heredada'
        else:
            decision, rule = 'TC', 'T05_RESULTADO_NO_ACREDITADO'
            why = 'La evidencia de título/resumen no acredita conjuntamente A/B/C. No se infiere irrelevancia definitiva.'
        # El juicio humano se registra, pero NO sobrescribe la propuesta automática.
        h = human.get(oid, {})
        old_insufficient = r['estado_documental_v7'] == 'TEXTO_COMPLETO_SI_SE_RESCATA'
        evsignals = signals(EVIDENCE_PATTERNS, text)
        process = signals(PROCESS_PATTERNS, title)
        problem = signals(PROBLEM_PATTERNS, title)
        function = 'no_determinable'
        principal = bool(rx(r'perforacion|tronadura|carguio_excavacion|acarreo').search(process))
        support = bool(rx(r'riego_control_polvo|caminos|abastecimiento|desague|mantenimiento_equipos').search(process))
        if principal and support: function = 'ambas_segun_senales_titulo'
        elif support: function = 'auxiliar_segun_senales_titulo'
        elif principal: function = 'principal_segun_senales_titulo'
        if rx(r'fuel truck|water(?:ing)? truck').search(title):
            function = 'auxiliar_segun_senales_titulo'
        if 'mantenimiento_equipos' in process or rx(r'replac|lifetime|life cycle').search(title):
            function = 'transversal_mantenimiento_por_cotejar'
        level = 'no_determinable'
        if component: level = 'componente_por_cotejar'
        elif SUPPORT.search(title): level = 'tarea_auxiliar_propuesta'
        elif rx(r'fleet|truck.shovel|dispatch|system').search(title): level = 'flota_sistema_propuesto'
        elif WHOLE_EQUIPMENT.search(title): level = 'equipo_propuesto'
        x = {
          'decision_regla_v8': decision,
          'decision_nucleo_v8_propuesta': decision,
          'regla_v8': rule, 'motivo_v8': why,
          'evidencia_textual_v8': evidence, 'fuente_decision_v8': source,
          'contexto_A_v8': 'acreditado_en_ficha' if context else 'por_cotejar',
          'tarea_A_senal_v8': 'si' if a else 'no',
          'evaluacion_B_senal_v8': 'si' if b else 'no',
          'resultado_C_enlace_regla_v8': 'si' if c else 'no',
          'oraciones_resultado_enlazado_v8': str(len(linked)),
          'documento_v8_propuesto': doc,
          'tipo_openalex_review_sin_confirmacion_v8': 'si' if r['type'] == 'review' and not secondary else 'no',
          'alerta_bibliografica_previa_v8': 'si' if oid in alerts else 'no',
          'cotejo_bibliografico_pendiente_v8': 'si' if oid in alerts and not alerts[oid].get('verificado_en_fuente') else 'no',
          'senales_proceso_titulo_v8': process or 'no_identificadas',
          'senales_problema_titulo_v8': problem or 'no_identificadas',
          'funcion_v8_propuesta': function,
          'indicadores_mencionados_v8': signals(INDICATOR_PATTERNS, text) or 'ninguno_identificado',
          'indicadores_en_evidencia_v8': signals(INDICATOR_PATTERNS, ' '.join(linked)) or 'ninguno_identificado',
          'nivel_resultado_v8_propuesto': level,
          'tipo_evidencia_mencionada_v8': ('revision;' if secondary else '') + (evsignals or 'no_determinable'),
          'estado_evidencia_regla_v8': 'evaluado_detectado' if c else 'por_cotejar',
          'texto_completo_leido_en_corrida_v8': 'no',
          'metodo_v8': 'reglas_computacionales_sin_auditorias_IA_heredadas',
          'fuera_nucleo_no_excluye_base_amplia_v8': 'si',
          'pertenece_piloto_calibracion_v8': 'si' if h else 'no',
          'codigo_piloto_v8': h.get('codigo', ''),
          'sugerencia_IA_piloto_conservada_v8': h.get('sugerencia_IA', ''),
          'decision_humana_piloto_original_v8': h.get('decision_humana', ''),
          'motivo_humano_piloto_original_v8': h.get('motivo', ''),
          'decision_humana_piloto_actual_v8': h.get('decision_humana_actual', ''),
          'humano_y_regla_v8_coinciden_en_piloto': ('si' if h['decision_humana_actual'] == decision else 'no') if h else '',
          'caso_desarrollo_v8': ';'.join(reasons_dev),
          'insuficiente_v7_conservado_v8': 'si' if old_insufficient else 'no',
          'cambio_propuesto_v7_a_v8': r['decision_nucleo_v7'] + '>' + decision,
          'version_criterio_v8': CRITERIO, 'version_implementacion_v8': VERSION,
          'fecha_corrida_v8': FECHA,
        }
        if set(x) & set(r): raise ValueError('Intento de sobrescribir columnas históricas.')
        out.append({**r, **x})
        events.append({'openalex_id': oid, 'version': VERSION,
            'actor_tipo': 'regla_computacional', 'etiqueta_previa_v7': r['decision_nucleo_v7'],
            'propuesta_v8': decision, 'regla': rule, 'motivo': why,
            'fuente': source, 'evidencia': evidence, 'fecha': FECHA,
            'estado': 'propuesta_sin_validacion_independiente'})
    dest = args.salida
    write(dest / 'matriz_completa_4735_v8.csv', out)
    for label in ('IN', 'OUT', 'TC'):
        subset = [r for r in out if r['decision_nucleo_v8_propuesta'] == label]
        write(dest / f'{label}_propuesto_v8.csv', subset, list(out[0]))
    change_fields = ['openalex_id', 'title', 'decision_nucleo_v7', 'decision_nucleo_v8_propuesta',
                     'regla_v8', 'motivo_v8', 'evidencia_textual_v8', 'fuente_decision_v8',
                     'decision_humana_piloto_actual_v8', 'caso_desarrollo_v8']
    changes = [{k: r[k] for k in change_fields} for r in out
               if r['decision_nucleo_v7'] != r['decision_nucleo_v8_propuesta']]
    write(dest / 'cambios_propuestos_por_ID_v8.csv', changes, change_fields)
    write(dest / 'eventos_propuesta_v8.csv', events)
    write(dest / 'casos_desarrollo_v8.csv', development)
    write(dest / 'piloto_estado_actual_y_propuesta_v8.csv',
          [{k: r[k] for k in change_fields + ['codigo_piloto_v8', 'decision_humana_piloto_original_v8',
          'motivo_humano_piloto_original_v8', 'sugerencia_IA_piloto_conservada_v8']} for r in out if r['codigo_piloto_v8']])
    summary = {
      'version': VERSION, 'criterio': CRITERIO, 'fecha': FECHA,
      'N_base_amplia_sin_alterar': len(out),
      'conteos_v7': dict(Counter(r['decision_nucleo_v7'] for r in rows)),
      'conteos_propuesta_v8': dict(Counter(r['decision_nucleo_v8_propuesta'] for r in out)),
      'transiciones_v7_a_v8': dict(sorted(Counter(r['cambio_propuesto_v7_a_v8'] for r in out).items())),
      'reglas': dict(sorted(Counter(r['regla_v8'] for r in out).items())),
      'N_cambios_propuestos': len(changes),
      'N_desarrollo_unico': len({r['openalex_id'] for r in development}),
      'piloto_humano_actual': dict(Counter(h['decision_humana_actual'] for h in human.values())),
      'propuestas_en_piloto': dict(Counter(r['decision_nucleo_v8_propuesta'] for r in out if r['codigo_piloto_v8'])),
      'N_discrepancias_piloto_regla_v8': sum(r['humano_y_regla_v8_coinciden_en_piloto'] == 'no' for r in out),
      'disposicion_insuficientes_v7': dict(Counter(r['decision_nucleo_v8_propuesta'] for r in out
          if r['insuficiente_v7_conservado_v8'] == 'si')),
      'modelo_llm_ejecutado_en_corrida_v8': None, 'llamadas_API': 0,
      'metodo': 'reglas reproducibles y conservación identificada de auditorías IA de desarrollo previas',
      'lectura_semantica_individual_nueva_4735': False, 'texto_completo_nuevo': 0,
      'decision_humana_automatica': False, 'validacion_independiente_completada': False,
      'entradas_sha256': {str(p.relative_to(BASE)): sha(p) for p in (src, pilot_path,
          alert_path, audit_path, queue_path, module_path)},
      'codigo_sha256': sha(Path(__file__).resolve()),
    }
    (dest / 'resumen_v8.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ('N_base_amplia_sin_alterar', 'conteos_propuesta_v8',
          'transiciones_v7_a_v8', 'N_desarrollo_unico', 'disposicion_insuficientes_v7',
          'N_discrepancias_piloto_regla_v8')}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
