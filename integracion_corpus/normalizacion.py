"""Normalización bibliográfica conservadora, sin dependencias externas."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata

DOI_RE = re.compile(r'^10\.\d{4,9}/\S+$', re.IGNORECASE)


def limpia_texto(value: object) -> str:
    return ' '.join(str(value or '').replace('\ufeff', '').split())


def normalizar_doi(value: object) -> str:
    doi = limpia_texto(value).lower()
    doi = re.sub(r'^(?:https?://)?(?:dx\.)?doi\.org/', '', doi)
    doi = re.sub(r'^(?:doi\s*:\s*|urn:doi:)', '', doi)
    doi = doi.split('#', 1)[0].split('?', 1)[0].strip('.,; \"\'<>[]')
    return doi if DOI_RE.fullmatch(doi) else ''


def normalizar_titulo(value: object) -> str:
    title = unicodedata.normalize('NFKD', limpia_texto(value).casefold())
    title = ''.join(c for c in title if not unicodedata.combining(c))
    title = re.sub(r'[^a-z0-9]+', ' ', title)
    return ' '.join(title.split())



def normalizar_titulo_unicode(value: object) -> str:
    """Normalización Unicode conservadora (opcional).

    Conserva letras y números en cualquier alfabeto, incluyendo cirílico,
    coreano, japonés y chino. Separa puntuación por espacios sin eliminar
    diacríticos distintivos como la letra cirílica й. La versión histórica
    normalizar_titulo() permanece sin cambios para reproducir las 791 alertas.
    """
    title = unicodedata.normalize('NFKC', limpia_texto(value).casefold())
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in title).split())


def normalizar_anio(value: object) -> str:
    text = limpia_texto(value)
    m = re.match(r'^(?:19|20)\d{2}$', text)
    return m.group(0) if m else ''


def hash_registro(original: dict) -> str:
    stable = json.dumps(original, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(stable.encode('utf-8')).hexdigest()


def hash_archivo(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(2 ** 20), b''):
            h.update(block)
    return h.hexdigest()


def normalizar_fila(row: dict, fuente: str, nro: int,
                    normalizacion_titulos: str = 'historica_ascii') -> dict:
    nombre_id = {'OpenAlex': 'openalex_id', 'Scopus': 'scopus_id', 'WoS': 'wos_id'}[fuente]
    sid = limpia_texto(row.get(nombre_id))
    if not sid:
        raise ValueError(f'{fuente}, fila {nro}: falta identificador {nombre_id}')
    titulo = limpia_texto(row.get('title'))
    doi_original = limpia_texto(row.get('doi'))
    doi = normalizar_doi(doi_original)
    if normalizacion_titulos not in {'historica_ascii', 'unicode_v2'}:
        raise ValueError('Normalización de títulos no reconocida')
    titulo_normalizado = (normalizar_titulo_unicode(titulo) if normalizacion_titulos == 'unicode_v2'
                          else normalizar_titulo(titulo))
    return {
        'registro_uid': f'{fuente}::{sid}',
        'fuente': fuente,
        'id_fuente': sid,
        'doi_original': doi_original,
        'doi_normalizado': doi,
        'doi_invalido': bool(doi_original and not doi),
        'titulo': titulo,
        'titulo_normalizado': titulo_normalizado,
        'anio': normalizar_anio(row.get('year')),
        'fecha_publicacion': limpia_texto(row.get('publication_date')),
        'tipo_documento': limpia_texto(row.get('type') or row.get('document_type')),
        'resumen': limpia_texto(row.get('abstract')),
        'autores': limpia_texto(row.get('authors')),
        'revista': limpia_texto(row.get('source') or row.get('source_title')),
        'idioma': limpia_texto(row.get('language')),
        'palabras_clave': limpia_texto(row.get('keywords')),
        'topics': limpia_texto(row.get('topics')),
        'etiquetas_proceso_fuente': limpia_texto(row.get('auto_process_tags')),
        'etiquetas_equipo_fuente': limpia_texto(row.get('auto_equipment_tags')),
        'etiquetas_foco_fuente': limpia_texto(row.get('auto_focus_tags')),
        'estado_filtro_fuente': limpia_texto(row.get('auto_screen_status')),
        'rama_busqueda': limpia_texto(row.get('retrieval_branches') or row.get('first_discovery_query')),
        'archivo_exportacion_wos': limpia_texto(row.get('source_files')) if fuente == 'WoS' else '',
        'hash_fila_original': hash_registro(row),
    }
