"""IPRE Etapa 01: extracción y filtro amplio Scopus, adaptado a Joaquín.

RESTRICCIONES METODOLÓGICAS:
- Misma lista de 10 frases y búsqueda en TÍTULO / RESUMEN (NO keywords).
- Sin corte temporal, idioma o DOI obligatorio, como fuente.
- Solo artículos / revisiones. Resumen obligatorio.
- Los campos is_retracted / is_paratext de OpenAlex NO tienen equivalentes
  garantizados en Scopus Search; se identifican explícitamente como NO_VERIFICADO.
- Filtro amplio con diccionarios y screen_record originales, sin recalibrar.
- Piloto antes de cualquier ejecución completa, y cada consulta deja evidencia.

No publica API Key. El usuario debe comprobar condiciones de uso de la API.
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
import re
import time
import unicodedata
import urllib.parse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import criterios_joaquin_adaptados as jq
ENDPOINT = 'https://api.elsevier.com/content/search/scopus'
ABSTRACT_ENDPOINT = 'https://api.elsevier.com/content/abstract/scopus_id'
VERSION = '01_scopus_desde_cero_v1'
QUERY_STYLE = 'exacta_llaves_scopus'
ALLOWED_SUBTYPES = {'ar': 'article', 're': 'review'}
CONSULTAS = tuple(jq.OPEN_PIT_PHRASES[:10])
if not len(CONSULTAS) == 10:
    raise ValueError('Control de integridad incumplido')
RAW_FIELDS = ['retrieval_branches', 'scopus_id', 'eid', 'doi', 'title', 'year', 'publication_date', 'type', 'subtype', 'language', 'cited_by', 'source', 'authors', 'institutions', 'countries', 'keywords', 'topics', 'concepts', 'matched_open_pit_phrases', 'auto_process_tags', 'auto_equipment_tags', 'equipment_title_tags', 'equipment_mention_level', 'auto_focus_tags', 'auto_screen_status', 'auto_screen_reasons', 'operational_signals', 'duplicate_count', 'deduplication_methods', 'quality_flags', 'shared_abstract_scopus_ids', 'merged_scopus_ids', 'merged_dois', 'abstract', 'documental_tipo', 'documental_resumen', 'documental_retractacion', 'documental_paratexto', 'documental_estado', 'documental_motivo', 'metadatos_scopus_completos', 'fuente_resumen']

class AccesoError(RuntimeError):
    pass

class CuotaError(RuntimeError):
    pass

class PaginacionError(RuntimeError):
    pass

def fecha_utc():
    return datetime.now(timezone.utc).isoformat()

def huella_archivo(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for piece in iter(lambda: f.read(1024 * 1024), b''):
            h.update(piece)
    return h.hexdigest()

def hash_config(d: dict):
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]

def guardar_json(path: Path, d: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.temp')
    tmp.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    tmp.replace(path)

def guardar_csv(path: Path, rows: list[dict], fields: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)

def _text(v: Any):
    if v is None:
        return ''
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        return '; '.join((_text(x) for x in v if x is not None))
    if isinstance(v, dict):
        return _text(v.get('$') or v.get('#text') or v.get('name') or v.get('text') or '')
    return str(v).strip()

def _scopus_id(entry: dict):
    ident = _text(entry.get('dc:identifier'))
    if ident.startswith('SCOPUS_ID:'):
        return ident.split(':', 1)[1]
    return _text(entry.get('scopus-id'))

def _author_names(entry: dict):
    creators = entry.get('author') or []
    if isinstance(creators, dict):
        creators = [creators]
    if creators:
        return '; '.join(dict.fromkeys((_text(x.get('authname') or x.get('ce:indexed-name') or x.get('dc:creator') or '') for x in creators if isinstance(x, dict))))
    return _text(entry.get('dc:creator'))

def _keywords(entry: dict):
    raw = entry.get('authkeywords') or entry.get('auth-keywords') or ''
    if isinstance(raw, dict):
        terms = raw.get('author-keyword') or []
        if isinstance(terms, dict):
            terms = [terms]
        return '; '.join((_text(x) for x in terms))
    return _text(raw)

def parsear_entrada_scopus(entry: dict, ramo: str):
    """Scopus -> esquema semántico de Joaquín; NUNCA inventa topics/concepts."""
    t = _text(entry.get('subtype'))
    label = _text(entry.get('subtypeDescription') or entry.get('prism:aggregationType') or entry.get('dc:type'))
    if not t and label.lower() in {'article', 'review'}:
        t = 'ar' if label.lower() == 'article' else 're'
    abstract = _text(entry.get('dc:description'))
    titulo = _text(entry.get('dc:title'))
    keywords = _keywords(entry)
    texto_etiquetas = ' '.join([titulo, abstract, keywords])
    equipos_texto = jq.tag_categories(texto_etiquetas, jq.EQUIPMENT_TERMS)
    equipos_titulo = jq.tag_categories(titulo, jq.EQUIPMENT_TERMS)
    return dict(retrieval_branches=ramo, scopus_id=_scopus_id(entry), eid=_text(entry.get('eid')), doi=_text(entry.get('prism:doi')), title=titulo, year=_text(entry.get('prism:coverDate'))[:4], publication_date=_text(entry.get('prism:coverDate')), type=ALLOWED_SUBTYPES.get(t, 'otro'), subtype=t, language=_text(entry.get('language') or entry.get('dc:language')), cited_by=_text(entry.get('citedby-count')) or '0', source=_text(entry.get('prism:publicationName')), authors=_author_names(entry), institutions='', countries='', keywords=keywords, topics='', concepts='', matched_open_pit_phrases='; '.join(jq.matched_terms(titulo + ' ' + abstract, CONSULTAS)), auto_process_tags='; '.join(jq.tag_categories(texto_etiquetas, jq.PROCESS_TERMS)), auto_equipment_tags='; '.join(equipos_texto), equipment_title_tags='; '.join(equipos_titulo), equipment_mention_level='titulo' if equipos_titulo else 'resumen_o_palabras_clave' if equipos_texto else 'sin_equipo', auto_focus_tags='; '.join(jq.tag_categories(texto_etiquetas, jq.FOCUS_TERMS)), auto_screen_status='', auto_screen_reasons='', operational_signals='', duplicate_count=1, deduplication_methods='', quality_flags='', shared_abstract_scopus_ids='', merged_scopus_ids=_scopus_id(entry), merged_dois=_text(entry.get('prism:doi')), abstract=abstract, documental_tipo='', documental_resumen='', documental_retractacion='no_verificado_api_scopus', documental_paratexto='no_verificado_api_scopus', documental_estado='', documental_motivo='', metadatos_scopus_completos=bool(t), fuente_resumen='search_COMPLETE' if abstract else '')

def armar_consulta(frase: str, estilo: str='EXACTA'):
    """Separa 10 frases, conserva contexto TITLE-ABS, añade subtipos ar/re."""
    if frase not in CONSULTAS:
        raise ValueError('Frase no está en diccionario original')
    if estilo == 'EXACTA':
        term = '{' + frase + '}'
    elif estilo == 'APROXIMADA':
        term = '"' + frase + '"'
    else:
        raise ValueError('Estilo debe ser EXACTA o APROXIMADA')
    return f'(TITLE-ABS({term})) AND (DOCTYPE(ar) OR DOCTYPE(re))'

def _get(api_key: str, params: dict, tiempo_espera: int=35, reintentos: int=3):
    import requests
    headers = {'X-ELS-APIKey': api_key, 'Accept': 'application/json'}
    token = os.environ.get('ELSEVIER_INSTTOKEN', '').strip()
    if token:
        headers['X-ELS-Insttoken'] = token
    for intento in range(reintentos):
        try:
            r = requests.get(ENDPOINT, headers=headers, params=params, timeout=tiempo_espera)
        except requests.RequestException as exc:
            if intento + 1 == reintentos:
                raise RuntimeError('Error de conexión. Reanude más tarde.') from exc
            time.sleep(min(3 * (intento + 1), 10))
            continue
        if r.status_code in (401, 403):
            raise AccesoError(f"Scopus denegó {params.get('view')} HTTP {r.status_code}. Requiere red UC/permisos. No pasar a STANDARD.")
        if r.status_code == 429:
            raise CuotaError('Cuota de Scopus agotada. Las páginas guardadas se conservan. Reanudar al renovar cuota.')
        if 500 <= r.status_code < 600:
            if intento + 1 == reintentos:
                raise RuntimeError(f'HTTP {r.status_code}, fallo temporal de Elsevier')
            time.sleep(min(4 * (intento + 1), 10))
            continue
        if r.status_code != 200:
            msg = r.text[:250].replace(api_key, '[CLAVE_OCULTA]')
            raise RuntimeError(f'HTTP {r.status_code}: {msg}')
        try:
            return (r.json(), dict(r.headers))
        except ValueError as exc:
            raise RuntimeError('La API no devolvió JSON válido') from exc
    raise RuntimeError('No se pudo completar la solicitud')

def diagnosticar(api_key: str, estilo: str='EXACTA', count: int=5):
    q = armar_consulta(CONSULTAS[0], estilo)
    payload, hdr = _get(api_key, dict(query=q, view='COMPLETE', count=count, start=0))
    sr = payload.get('search-results', {})
    entries = [x for x in sr.get('entry') or [] if isinstance(x, dict) and 'error' not in x]
    out = {'consulta': q, 'coincidencias_primera_frase': int(sr.get('opensearch:totalResults') or 0), 'registros_solicitados': count, 'registros_entregados': len(entries), 'con_resumen': sum((bool(x.get('dc:description')) for x in entries)), 'cuota_restante': hdr.get('X-RateLimit-Remaining', 'no_reportada')}
    print('PRUEBA SCOPUS:', json.dumps(out, ensure_ascii=False, indent=2))
    if not entries or not out['con_resumen']:
        raise AccesoError('La muestra de Search COMPLETE no devolvió resúmenes. Revisar acceso antes de descargar.')
    return out

def extraer_siguiente_cursor(data: dict):
    sr = data.get('search-results') or {}
    cursor = sr.get('cursor') or {}
    if isinstance(cursor, dict) and cursor.get('@next') not in (None, ''):
        return str(cursor['@next'])
    for link in sr.get('link') or []:
        if isinstance(link, dict) and link.get('@ref') == 'next':
            url = link.get('@href', '')
            query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if query.get('cursor'):
                return query['cursor'][0]
    return ''

def _paginas_de_ramo(pages_dir: Path):
    return sorted(pages_dir.glob('pagina_*.json'))

def descargar(api_key: str, carpeta: Path, modo: str='PILOTO', estilo: str='EXACTA', confirmar_completo: bool=False, limite_piloto: int=10, tamano_pagina: int=25, pausa_segundos: float=0.35):
    """Descarga reversible y reanudable. No declara completa una descarga parcial."""
    modo = modo.upper()
    carpeta = Path(carpeta)
    if modo not in {'PILOTO', 'COMPLETO'}:
        raise ValueError('Modo inválido')
    if modo == 'COMPLETO' and (not confirmar_completo):
        raise ValueError('Modo COMPLETO requiere confirmar_completo=True, tras aprobación metodológica.')
    if modo == 'PILOTO' and limite_piloto < 1:
        raise ValueError('Piloto sin registros')
    cfg = {'version': VERSION, 'modo': modo, 'estilo': estilo, 'frases': CONSULTAS, 'documentos': ['ar', 're'], 'sin_limite_de_anio': True, 'sin_limite_de_idioma': True, 'doi_no_obligatorio': True, 'limite_piloto': limite_piloto if modo == 'PILOTO' else None, 'tamano_pagina': tamano_pagina if modo == 'COMPLETO' else min(tamano_pagina, limite_piloto)}
    destino = carpeta / ('fase1_piloto' if modo == 'PILOTO' else 'fase1_completo')
    destino.mkdir(parents=True, exist_ok=True)
    cfg_path = destino / 'configuracion.json'
    if cfg_path.exists():
        prev = json.loads(cfg_path.read_text(encoding='utf-8'))
        if prev.get('configuracion') != json.loads(json.dumps(cfg)):
            raise RuntimeError('Configuración cambió; use otra carpeta para evitar mezclar corridas.')
    else:
        guardar_json(cfg_path, {'configuracion': cfg, 'huella': hash_config(cfg)})
    resumen = []
    for idx, frase in enumerate(CONSULTAS, 1):
        rama = f'{idx:02d}'
        paginas = destino / 'paginas' / rama
        paginas.mkdir(parents=True, exist_ok=True)
        prev = _paginas_de_ramo(paginas)
        last = json.loads(prev[-1].read_text(encoding='utf-8')) if prev else None
        if last and last.get('completa'):
            print(f'[{rama}/10] Ya completa: {frase}')
            resumen.append({'frase': frase, 'completa': True, 'paginas': len(prev)})
            continue
        cursor = last.get('cursor_siguiente') if last else '*'
        start = len(prev) * min(tamano_pagina, limite_piloto) if modo == 'PILOTO' else 0
        n_prev = sum((len(json.loads(p.read_text(encoding='utf-8')).get('entry') or []) for p in prev))
        query = armar_consulta(frase, estilo)
        n = n_prev
        if cursor in ('', None) and prev:
            raise PaginacionError(f'La rama {rama} está incompleta pero el cursor anterior no avanza. Revisión manual.')
        if modo == 'COMPLETO' and cursor == '*':
            print(f'[{rama}/10] Inicio cursor Scopus: {frase}')
        else:
            print(f'[{rama}/10] Continuando: {frase} ({n} ya guardados)')
        vistos = {json.loads(p.read_text(encoding='utf-8')).get('cursor_solicitado') for p in prev}
        while True:
            cant = min(tamano_pagina, limite_piloto - n) if modo == 'PILOTO' else tamano_pagina
            if cant <= 0:
                break
            params = {'query': query, 'view': 'COMPLETE', 'count': cant}
            if modo == 'COMPLETO':
                params['cursor'] = cursor
            else:
                params['start'] = start
            payload, hdr = _get(api_key, params)
            sr = payload.get('search-results') or {}
            entries = [x for x in sr.get('entry') or [] if isinstance(x, dict) and 'error' not in x]
            reported = int(sr.get('opensearch:totalResults') or 0)
            next_cursor = extraer_siguiente_cursor(payload) if modo == 'COMPLETO' else ''
            n += len(entries)
            if modo == 'COMPLETO':
                complete = n >= reported and reported > 0 or reported == 0
                if not complete and (not next_cursor):
                    raise PaginacionError(f'Rama {rama}: no hay next_cursor con {n}/{reported}. NO se considera completa.')
                if not complete and next_cursor in vistos | {cursor}:
                    raise PaginacionError(f'Rama {rama}: cursor repetido, se detuvo sin marcar completa.')
                if not entries and (not complete):
                    raise PaginacionError(f'Rama {rama}: página vacía antes de completar. Se detuvo.')
            else:
                complete = n >= limite_piloto or n >= reported
            page = {'numero': len(prev) + 1, 'frase': frase, 'consulta': query, 'cursor_solicitado': cursor if modo == 'COMPLETO' else None, 'cursor_siguiente': next_cursor, 'reportado': reported, 'descargados_acumulados': n, 'entry': entries, 'completa': complete, 'cuota_restante': hdr.get('X-RateLimit-Remaining', ''), 'fecha_guardado_utc': fecha_utc()}
            guardar_json(paginas / f'pagina_{len(prev) + 1:05d}.json', page)
            prev.append(paginas / f'pagina_{len(prev) + 1:05d}.json')
            print(f"  Página {len(prev)}: {len(entries)} filas, acum. {n}, total API {reported}; restantes {page['cuota_restante']}")
            if complete:
                break
            cursor = next_cursor
            start += len(entries)
            vistos.add(page['cursor_solicitado'])
            time.sleep(pausa_segundos)
        last = json.loads(prev[-1].read_text(encoding='utf-8')) if prev else None
        resumen.append({'frase': frase, 'completa': bool(last and last.get('completa')), 'paginas': len(prev), 'descargados': n, 'reportado_api': last.get('reportado') if last else None})
    guardar_json(destino / 'estado_descarga.json', {'modo': modo, 'rama': resumen, 'termino_utc': fecha_utc(), 'todas_las_ramas_terminadas': all((x['completa'] for x in resumen)) and len(resumen) == 10})
    return destino

def cargar_descarga(destino: Path):
    destino = Path(destino)
    config = json.loads((destino / 'configuracion.json').read_text(encoding='utf-8'))['configuracion']
    all_rows = []
    stats = []
    for idx, frase in enumerate(config['frases'], 1):
        ruta = destino / 'paginas' / f'{idx:02d}'
        files = _paginas_de_ramo(ruta)
        if not files:
            stats.append({'frase': frase, 'completa': False, 'reportado_api': None, 'descargados': 0})
            continue
        pages = [json.loads(p.read_text(encoding='utf-8')) for p in files]
        consulta = armar_consulta(frase, config['estilo'])
        acumulado = 0
        cursores_vistos = set()
        for numero, pg in enumerate(pages, 1):
            contexto = f'Consulta {idx}, página {numero}'
            if pg.get('numero') != numero:
                raise RuntimeError(f'{contexto}: numeración discontinua.')
            if pg.get('frase') != frase or pg.get('consulta') != consulta:
                raise RuntimeError(f'{contexto}: pertenece a otra consulta.')
            entries = pg.get('entry')
            if not isinstance(entries, list):
                raise RuntimeError(f'{contexto}: registros de página inválidos.')
            acumulado += len(entries)
            if pg.get('descargados_acumulados') != acumulado:
                raise RuntimeError(f'{contexto}: acumulado inconsistente.')
            if not isinstance(pg.get('completa'), bool):
                raise RuntimeError(f'{contexto}: estado de finalización inválido.')
            if pg['completa'] and numero != len(pages):
                raise RuntimeError(f'{contexto}: hay páginas después del cierre.')
            if config['modo'] == 'COMPLETO':
                cursor = pg.get('cursor_solicitado')
                esperado = '*' if numero == 1 else pages[numero - 2].get('cursor_siguiente')
                if not cursor or cursor != esperado:
                    raise RuntimeError(f'{contexto}: cadena de cursores interrumpida.')
                if cursor in cursores_vistos:
                    raise RuntimeError(f'{contexto}: cursor solicitado repetido.')
                cursores_vistos.add(cursor)
                if not pg['completa']:
                    siguiente = pg.get('cursor_siguiente')
                    if not siguiente or siguiente in cursores_vistos:
                        raise RuntimeError(f'{contexto}: cursor siguiente inválido.')
            all_rows.extend((parsear_entrada_scopus(row, f'consulta_{idx:02d}') for row in entries))
        last = pages[-1]
        if config['modo'] == 'COMPLETO' and last['completa']:
            reportado = int(last['reportado'])
            if acumulado != reportado:
                raise RuntimeError(f'Consulta {idx}: se declara completa, pero contiene {acumulado} de {reportado} registros.')
        stats.append({'frase': frase, 'completa': last['completa'], 'reportado_api': last.get('reportado'), 'descargados': acumulado})
    return (all_rows, stats, config)

def _aplicar_controles_doc(row: dict):
    r = dict(row)
    motivos = []
    r['documental_tipo'] = 'admitido' if r.get('type') in ('article', 'review') else 'excluido'
    if r['documental_tipo'] != 'admitido':
        motivos.append('tipo_no_articulo_revision')
    r['documental_resumen'] = 'disponible' if _text(r.get('abstract')) else 'sin_resumen'
    if r['documental_resumen'] == 'sin_resumen':
        motivos.append('resumen_obligatorio_no_disponible')
    r['documental_retractacion'] = 'no_verificado_api_scopus'
    r['documental_paratexto'] = 'no_verificado_api_scopus'
    r['documental_estado'] = 'excluido_documental' if motivos else 'admisible_provisional_pendiente_verificacion'
    r['documental_motivo'] = '; '.join(motivos)
    return r

def _muestra(rows: list[dict], n: int=25):
    import random
    rng = random.Random(20261019)
    pools = [([x for x in rows if x.get('auto_screen_status') == 'include'], 10), ([x for x in rows if x.get('auto_screen_status') == 'exclude' and x.get('documental_estado') != 'excluido_documental'], 10), ([x for x in rows if x.get('documental_estado') == 'excluido_documental'], 5)]
    sample = []
    for pool, k in pools:
        for row in rng.sample(sorted(pool, key=lambda x: x.get('scopus_id', '')), min(k, len(pool))):
            sample.append({**row, 'decision_humana': '', 'motivo_revision_humana': '', 'revisor': '', 'fecha_revision': ''})
    return sample[:n]

def generar_revision_amplia(out, accepted, rejected):
    import random
    rng=random.Random(20261019)
    grupos={'aceptados_amplios':sorted(accepted,key=lambda r:r['scopus_id'])}
    for row in rejected:
        clave='excluidos:'+str(row.get('auto_screen_reasons') or 'sin_motivo')
        grupos.setdefault(clave,[]).append(row)
    cupos={k:0 for k in grupos if k!='aceptados_amplios'}
    objetivo=min(80,len(rejected))
    if objetivo>=len(cupos):cupos={k:1 for k in cupos}
    while sum(cupos.values())<objetivo:
        opciones=[k for k in cupos if cupos[k]<len(grupos[k])]
        k=max(opciones,key=lambda k:(objetivo*len(grupos[k])/max(1,len(rejected))-cupos[k],k))
        cupos[k]+=1
    cupos['aceptados_amplios']=min(240,len(accepted))
    seleccion=[]
    for k in sorted(grupos):
        pool=sorted(grupos[k],key=lambda r:r['scopus_id'])
        for row in rng.sample(pool,cupos[k]):seleccion.append((row,k,len(pool),cupos[k]))
    rng.shuffle(seleccion)
    ciega=[];clave=[]
    for i,(row,estrato,N,n) in enumerate(seleccion,1):
        codigo=f'R-{i:04d}'
        ciega.append({'codigo':codigo,**{k:row.get(k,'') for k in ['title','abstract','doi','year']},'decision_humana':'','motivo_revision_humana':'','revisor':'','fecha_revision':''})
        clave.append({'codigo':codigo,'scopus_id':row['scopus_id'],'estrato':estrato,'N':N,'n':n,'probabilidad':n/N,'peso':N/n})
    guardar_csv(out/'revision_amplia_ciega.csv',ciega,['codigo','title','abstract','doi','year','decision_humana','motivo_revision_humana','revisor','fecha_revision'])
    guardar_csv(out/'clave_revision_amplia_NO_ENTREGAR_A_REVISORES.csv',clave,['codigo','scopus_id','estrato','N','n','probabilidad','peso'])

def filtrar_y_exportar(destino: Path, permitir_parcial: bool=False):
    """Orden Joaquín: universo bruto -> deduplicación -> controles -> filtro amplio."""
    destino = Path(destino)
    raw, stats, cfg = cargar_descarga(destino)
    todas = len(stats) == 10 and all((x['completa'] for x in stats))
    if not todas and (not permitir_parcial):
        raise RuntimeError('Descarga parcial; no se presenta corpus final. Use permitir_parcial=True SOLO para diagnóstico.')
    if not raw:
        raise RuntimeError('No hay registros descargados')
    unique = jq.deduplicate(raw)
    unique = [_aplicar_controles_doc(x) for x in unique]
    for r in unique:
        dois = {jq.canonical_doi(x) for x in jq.doi_values(r.get('merged_dois')) if jq.canonical_doi(x)}
        if len(dois) > 1:
            flags = {x.strip() for x in str(r.get('quality_flags') or '').split(';') if x.strip()}
            flags.add('fusion_de_registros_con_doi_distintos_revisar')
            r['quality_flags'] = '; '.join(sorted(flags))
    docs_excluidos = [r for r in unique if r['documental_estado'] == 'excluido_documental']
    docs_admisibles = [r for r in unique if r['documental_estado'] != 'excluido_documental']
    accepted, rejected = jq.screen_records(docs_admisibles)
    out = destino / 'resultados'
    out.mkdir(exist_ok=True)
    guardar_csv(out / 'descarga_sin_deduplicar.csv', raw, RAW_FIELDS)
    guardar_csv(out / 'universo_scopus_deduplicado.csv', unique, RAW_FIELDS)
    guardar_csv(out / 'excluidos_documentales.csv', docs_excluidos, RAW_FIELDS)
    guardar_csv(out / 'corpus_general_aceptado_provisional.csv', accepted, RAW_FIELDS)
    guardar_csv(out / 'excluidos_amplios_con_motivo.csv', rejected, RAW_FIELDS)
    pendientes_control = [r for r in docs_admisibles if r['documental_retractacion'].startswith('no_verificado') or r['documental_paratexto'].startswith('no_verificado')]
    guardar_csv(out / 'pendientes_control_retractacion_paratexto.csv', pendientes_control, RAW_FIELDS)
    sample = _muestra(accepted + rejected + docs_excluidos)
    guardar_csv(out / 'muestra_revision_humana.csv', sample, RAW_FIELDS + ['decision_humana', 'motivo_revision_humana', 'revisor', 'fecha_revision'])
    generar_revision_amplia(out, accepted, rejected)
    fechas_descarga = []
    for pagina in sorted((destino / 'paginas').glob('*/*.json')):
        contenido = json.loads(pagina.read_text(encoding='utf-8'))
        fecha = contenido.get('fecha_guardado_utc')
        if not fecha:
            raise ValueError(f'Falta fecha_guardado_utc en {pagina.name}')
        fecha_utc_pagina = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
        if fecha_utc_pagina.tzinfo is None:
            raise ValueError(f'La fecha no tiene zona horaria en {pagina.name}')
        fechas_descarga.append(fecha_utc_pagina.astimezone(timezone.utc).date())
    if not fechas_descarga:
        raise ValueError('No hay páginas para determinar la fecha de corte.')
    fecha_corte = max(fechas_descarga).isoformat()
    alertas = []
    for r in unique:
        scopus_id = r.get('scopus_id') or ''
        if not r.get('doi'):
            alertas.append({'scopus_id': scopus_id, 'tipo': 'doi_no_disponible', 'detalle': 'No se exige DOI'})
        if not r.get('scopus_id'):
            alertas.append({'scopus_id': scopus_id, 'tipo': 'id_no_disponible', 'detalle': 'Revisar clave bibliográfica'})
        if 'fusion_de_registros_con_doi_distintos_revisar' in str(r.get('quality_flags') or ''):
            alertas.append({'scopus_id': scopus_id, 'tipo': 'fusion_doi_distintos', 'detalle': str(r.get('merged_dois') or '')})
        if r.get('publication_date') and r['publication_date'] > fecha_corte:
            alertas.append({'scopus_id': scopus_id, 'tipo': 'fecha_editorial_futura', 'detalle': r['publication_date']})
        if not r.get('abstract'):
            alertas.append({'scopus_id': scopus_id, 'tipo': 'sin_resumen', 'detalle': 'Requiere excluir o completar'})
        alertas.append({'scopus_id': scopus_id, 'tipo': 'retractacion_sin_verificar', 'detalle': 'No equivalente confirmado de is_retracted:false'})
        alertas.append({'scopus_id': scopus_id, 'tipo': 'paratexto_sin_verificar', 'detalle': 'No equivalente confirmado de is_paratext:false'})
    guardar_csv(out / 'alertas_calidad.csv', alertas, ['scopus_id', 'tipo', 'detalle'])
    manifest = {'version': VERSION, 'generado_utc': fecha_utc(), 'fuente': 'Scopus Search API view COMPLETE', 'modo': cfg['modo'], 'consulta_estilo': cfg['estilo'], 'frases': list(CONSULTAS), 'consulta_tipo': 'TITLE-ABS de frases exactas, DOCTYPE ar/re' if cfg['estilo'] == 'EXACTA' else f"TITLE-ABS, estilo {cfg['estilo']}, DOCTYPE ar/re", 'sin_limite_explicito_anios': True, 'sin_limite_explicito_idioma': True, 'doi_requerido': False, 'consultas': stats, 'consultas_terminadas': todas, 'extraccion_completa': todas and cfg['modo'] == 'COMPLETO', 'filtro_automatico_ejecutado': True, 'filtro_validado_academicamente': False, 'filtro_completo': False, 'filas_descargadas': len(raw), 'publicaciones_unicas': len(unique), 'duplicados_eliminados': len(raw) - len(unique), 'con_resumen': sum((bool(x.get('abstract')) for x in unique)), 'documentales_excluidos': len(docs_excluidos), 'documentales_admisibles_provisionales': len(docs_admisibles), 'aceptados_amplios_provisionales': len(accepted), 'excluidos_amplios': len(rejected), 'pendientes_retractacion_y_paratexto': len(pendientes_control), 'revision_humana_finalizada': False, 'sin_fusion_historica_openalex': True, 'nota': 'Clasificaciones automáticas provisionales. No declarar replica documental exacta de OpenAlex ni corpus final mientras haya controles no verificados.', 'archivo_sha256': {p.name: huella_archivo(p) for p in out.glob('*.csv')}, 'fecha_corte_controles_editoriales': fecha_corte, 'criterio_fecha_corte': 'ultima_pagina_guardada_utc'}
    guardar_json(out / 'manifest_fase01.json', manifest)
    if not len(unique) == len(accepted) + len(rejected) + len(docs_excluidos):
        raise ValueError('Control de integridad incumplido')
    print('RESULTADO:', json.dumps({k: manifest[k] for k in ('modo', 'extraccion_completa', 'filas_descargadas', 'publicaciones_unicas', 'duplicados_eliminados', 'con_resumen', 'aceptados_amplios_provisionales', 'excluidos_amplios', 'documentales_excluidos', 'pendientes_retractacion_y_paratexto')}, indent=2, ensure_ascii=False))
    return manifest
