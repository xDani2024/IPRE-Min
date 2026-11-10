#!/usr/bin/env python3
"""Auditoría bibliográfica de alertas (v1.3).

Decisiones sugeridas, NO alteran el corpus ni realizan fusiones automáticamente.
Trabaja sobre las entradas ya normalizadas y las 791 alertas del cruce v9.
Sin servicios externos ni llamadas a API, para conservar reproducibilidad local.

Uso (desde IPRE-Min-main):
    python flujo_unificado/verificar_duplicados.py
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_BASE = HERE / 'resultados_calibracion_v1_1'
OUTPUTS = (
    '01_diagnostico_por_alerta.csv',
    '02_evidencia_por_par.csv',
    '03_alertas_que_requieren_revision.csv',
    '04_resumen_verificacion.json',
    '05_plantilla_decisiones_humanas.csv',
    '06_titulos_no_latinos.csv',
)


def leer_csv(path: Path) -> list[dict]:
    with path.open('r', newline='', encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh))


def guardar_csv(path: Path, rows: list[dict], campos: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=campos, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def normalizar_unicode(text: str) -> str:
    """Conserva letras de otros alfabetos (ej. ruso), números y separa puntuación."""
    value = unicodedata.normalize('NFKC', str(text or '')).casefold()
    value = ''.join(ch if (ch.isalpha() or ch.isdigit()) else ' ' for ch in value)
    return ' '.join(value.split())


def similitud(a: str, b: str) -> tuple[float, float, bool]:
    a, b = normalizar_unicode(a), normalizar_unicode(b)
    if not a or not b:
        return 0.0, 0.0, False
    ratio = SequenceMatcher(None, a, b).ratio()
    sa, sb = set(a.split()), set(b.split())
    dice = 2 * len(sa & sb) / (len(sa) + len(sb)) if sa and sb else 0.0
    prefix = (a.startswith(b) or b.startswith(a)) and min(len(sa), len(sb)) >= 4
    return ratio, dice, prefix


def autores_solapados(a: str, b: str) -> bool | None:
    a, b = normalizar_unicode(a), normalizar_unicode(b)
    if not a or not b:
        return None
    # La información de autores puede variar entre APIs (cadena, JSON, etc.).
    tokens_a = {t for t in a.split() if len(t) >= 4}
    tokens_b = {t for t in b.split() if len(t) >= 4}
    return bool(tokens_a & tokens_b) if tokens_a and tokens_b else None


def comparar(a: dict, b: dict) -> dict:
    """Comparación prudente entre dos registros. No decide por título aislado."""
    doi_a, doi_b = a.get('doi_normalizado', ''), b.get('doi_normalizado', '')
    title_a, title_b = a.get('titulo', ''), b.get('titulo', '')
    year_a, year_b = a.get('anio', ''), b.get('anio', '')
    same_source = a.get('fuente') == b.get('fuente')
    rat, dice, prefix = similitud(title_a, title_b)
    norm_a, norm_b = normalizar_unicode(title_a), normalizar_unicode(title_b)
    same_title = bool(norm_a and norm_a == norm_b)
    same_doi = bool(doi_a and doi_b and doi_a == doi_b)
    diff_doi = bool(doi_a and doi_b and doi_a != doi_b)
    years_delta = abs(int(year_a) - int(year_b)) if year_a.isdigit() and year_b.isdigit() else None
    authors = autores_solapados(a.get('autores', ''), b.get('autores', ''))
    journal_a = normalizar_unicode(a.get('revista', ''))
    journal_b = normalizar_unicode(b.get('revista', ''))
    journals_equal = bool(journal_a and journal_a == journal_b)

    state = 'REQUIERE_REVISION'
    reason = 'Los metadatos disponibles no permiten confirmar la identidad bibliográfica.'
    level = 'NO_CONCLUYENTE'

    if same_source:
        reason = 'Hay identificadores distintos dentro de la misma base: verificar versiones, errores de indexación o duplicación interna.'
    elif not norm_a or not norm_b:
        reason = 'Falta título utilizable en uno de los registros; no decidir identidad automáticamente.'
    elif same_doi:
        # El DOI es fuerte, pero por sí solo no basta ante metadatos discordantes.
        titles_support = same_title or rat >= .84 or dice >= .85 or (prefix and rat >= .56)
        if titles_support and (years_delta is None or years_delta <= 2):
            state, level = 'MISMA_PUBLICACION', 'ALTA'
            reason = 'DOI idéntico y títulos concordantes; diferencia de año compatible con variantes de fecha editorial.'
        elif titles_support and years_delta is not None and years_delta > 2:
            reason = 'Mismo DOI y títulos concordantes, pero los años difieren más de dos años: validar fecha original.'
        else:
            reason = 'DOI idéntico, pero títulos muy diferentes: comprobar DOI erróneo, traducción o registro mal indexado.'
    elif diff_doi:
        if rat < .40 and dice < .40 and (years_delta is None or years_delta > 2):
            state, level = 'PUBLICACIONES_DIFERENTES', 'ALTA'
            reason = 'DOI distintos y títulos discordantes: no fusionar.'
        else:
            reason = 'DOI distintos en registros similares; verificar alias de DOI, versión o publicación diferente.'
    else:
        # Sin DOI en uno o ambos registros: evidencia bibliográfica múltiple.
        if same_title and (years_delta is None or years_delta <= 1):
            if (authors is True or journals_equal) and years_delta is not None:
                state, level = 'MISMA_PUBLICACION', 'ALTA'
                reason = 'Título y año concordantes, con coincidencia adicional de autores o revista.'
            elif len(norm_a.split()) >= 6 and years_delta == 0 and authors is not False:
                state, level = 'MISMA_PUBLICACION', 'MEDIA'
                reason = 'Título completo y año idénticos, sin DOI contradictorios; cotejo de autores recomendado.'
            else:
                reason = 'Título equivalente sin DOI contradictorio; metadatos adicionales insuficientes.'
        elif not same_title and rat < .40 and dice < .40 and years_delta is not None and years_delta >= 3:
            state, level = 'PUBLICACIONES_DIFERENTES', 'MEDIA'
            reason = 'Títulos muy distintos y años separados, sin DOI común.'
        else:
            reason = 'Coincidencia parcial o diferencia temporal sin DOI decisivo.'

    return {
        'registro_a': a.get('registro_uid',''), 'registro_b': b.get('registro_uid',''),
        'fuente_a': a.get('fuente',''), 'fuente_b': b.get('fuente',''),
        'titulo_a': title_a, 'titulo_b': title_b, 'anio_a': year_a, 'anio_b': year_b,
        'doi_a': doi_a, 'doi_b': doi_b,
        'decision_sugerida': state, 'grado_evidencia': level,
        'fundamento': reason,
        'doi_coincidente': str(same_doi), 'doi_conflictivo': str(diff_doi),
        'titulo_igual_normalizado': str(same_title),
        'similitud_titulo': f'{rat:.4f}', 'solapamiento_palabras': f'{dice:.4f}',
        'diferencia_anios': '' if years_delta is None else str(years_delta),
        'autores_solapados': 'NO_DISPONIBLE' if authors is None else str(authors),
        'revista_coincidente': str(journals_equal),
        'misma_fuente': str(same_source),
    }


def ejecutar(base: Path=DEFAULT_BASE, salida: Path|None=None, alertas_path: Path|None=None):
    base = Path(base)
    salida = Path(salida) if salida else base/'08_verificacion_bibliografica'
    alertas_path = Path(alertas_path) if alertas_path else base/'07_cruce_historico_v9'/'06_alertas_deduplicacion_para_revisar.csv'
    normalizados = base/'02_integracion_y_deduplicacion'/'01_registros_normalizados.csv'
    if normalizados.exists():
        todos = leer_csv(normalizados)
    else:
        # El ZIP compacto no conserva todos los intermedios. Se reconstruyen los registros
        # normalizados directamente desde las tres entradas archivadas SIN repetir las API.
        sys.path.insert(0,str(HERE.parent/'integracion_corpus'))
        from fuentes import leer_corpus
        todos, _ = leer_corpus(HERE.parent, 'universo')
    registros = {r['registro_uid']: r for r in todos}
    alertas = leer_csv(alertas_path)
    por_alerta, por_par, pendientes, no_latinos = [], [], [], []
    for alerta in alertas:
        aids = alerta['registro_a'].split('|') if alerta['registro_a'] else []
        bids = alerta['registros_b'].split('|') if alerta['registros_b'] else []
        casos = []
        for aid in aids:
            for bid in bids:
                if aid == bid: continue
                if aid not in registros or bid not in registros:
                    casos.append({'decision_sugerida':'REQUIERE_REVISION','fundamento':'Identificador no encontrado en registros normalizados.'})
                else:
                    par = comparar(registros[aid], registros[bid]); par['id_alerta']=alerta['id_alerta']
                    casos.append(par); por_par.append(par)
        if alerta['tipo_alerta']=='MULTIPLES_IDS_MISMA_FUENTE_REVISAR' and casos:
            # El grupo original contiene varios IDs de una fuente, aunque la pareja mostrada sea interfuente.
            for caso in casos:
                caso['decision_sugerida']='REQUIERE_REVISION'
                caso['grado_evidencia']='NO_CONCLUYENTE'
                caso['fundamento']='Grupo con múltiples identificadores en una misma fuente; revisar todos sus miembros antes de fusionar.'
        if not casos:
            r = registros.get(alerta['registro_a'])
            if alerta['tipo_alerta']=='TITULO_VACIO' and r and normalizar_unicode(r['titulo']):
                reason = 'El título existe pero está en un alfabeto no latino: el normalizador anterior lo dejó vacío. No es una alerta de duplicación.'
                no_latinos.append({'id_alerta':alerta['id_alerta'],'registro_uid':r['registro_uid'], 'titulo_original':r['titulo'],'idioma':r.get('idioma',''), 'accion':'Conservar título Unicode; evaluar traducción solo durante el cribado.'})
                etiqueta = 'TITULO_NO_LATINO'
            else:
                reason = 'Registro sin segundo elemento comparable: revisar completitud de metadatos, no inferir duplicación.'
                etiqueta = 'METADATO_INCOMPLETO'
            outcome='REQUIERE_REVISION'
            grades='NO_CONCLUYENTE'
        else:
            opts={x['decision_sugerida'] for x in casos}
            outcome=next(iter(opts)) if len(opts)==1 else 'REQUIERE_REVISION'
            reason=' | '.join(dict.fromkeys(x['fundamento'] for x in casos))
            grades='ALTA' if len(opts)==1 and all(x['grado_evidencia']=='ALTA' for x in casos) else 'MIXTA_O_LIMITADA'
            etiqueta='COMPARACION_BIBLIOGRAFICA'
        new={**alerta,'decision_sugerida':outcome,'grado_evidencia':grades,
             'tipo_diagnostico':etiqueta, 'numero_pares_evaluados':len(casos),
             'fundamento_automatico':reason,
             'decision_humana':'','justificacion_humana':'','revisor_humano':'','fecha_revision_humana':''}
        por_alerta.append(new)
        if outcome=='REQUIERE_REVISION': pendientes.append(new)
    campos_alerta=list(por_alerta[0])
    guardar_csv(salida/OUTPUTS[0],por_alerta,campos_alerta)
    if por_par: guardar_csv(salida/OUTPUTS[1],por_par,list(por_par[0]))
    guardar_csv(salida/OUTPUTS[2],pendientes,campos_alerta)
    # Los formularios ya completados no deben sobrescribirse nunca.
    plantilla=salida/OUTPUTS[4]
    if not plantilla.exists():
        fields=['id_alerta','tipo_alerta','decision_sugerida','grado_evidencia',
                'decision_humana','justificacion_humana','revisor_humano','fecha_revision_humana']
        guardar_csv(plantilla,[{k:r.get(k,'') for k in fields} for r in por_alerta],fields)
    guardar_csv(salida/OUTPUTS[5],no_latinos, ['id_alerta','registro_uid','titulo_original','idioma','accion'])
    total=Counter(r['decision_sugerida'] for r in por_alerta)
    types=Counter(r['tipo_alerta'] for r in por_alerta)
    result={
      'version':'1.3.0', 'alertas_entrada':len(alertas), 'registros_normalizados':len(registros),
      'pares_comparados':len(por_par), 'recuentos_por_decision_sugerida':dict(sorted(total.items())),
      'recuentos_por_tipo_original':dict(sorted(types.items())),
      'titulos_no_latinos_con_valor':len(no_latinos),
      'limitaciones':[
        'Decisiones computacionales sugeridas: NINGUNA fusión o separación se aplica sobre el corpus.',
        'MISMA_PUBLICACION significa coincidencia bibliográfica probable, no igualdad byte a byte de PDF.',
        'Las comparaciones se realizan solo con metadatos archivados, no con Crossref ni PDFs.',
        'Las 791 alertas no son un conjunto exhaustivo de todas las posibles parejas duplicadas.',
        'El número de publicaciones únicas 15.412 NO se actualiza con sugerencias sin confirmar.',
        'No se deben usar decisiones automáticas como evidencia de inclusión temática.',
        'Un título no latino no es un título vacío. No descartar publicaciones por el normalizador latino anterior.',
      ],
    }
    (salida/OUTPUTS[3]).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Alertas revisadas:',len(alertas),'| pares comparados:',len(por_par))
    print('Resultados sugeridos:',dict(sorted(total.items())))
    print('Títulos no latinos recuperables:',len(no_latinos))
    print('Archivos en:',salida)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,default=DEFAULT_BASE)
    p.add_argument('--salida',type=Path)
    p.add_argument('--alertas',type=Path)
    args=p.parse_args()
    ejecutar(args.base,args.salida,args.alertas)

if __name__=='__main__':
    main()
