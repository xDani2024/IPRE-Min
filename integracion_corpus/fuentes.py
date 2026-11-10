"""Rutas congeladas de las tres fuentes, sin nuevas llamadas a internet/API."""
from __future__ import annotations

import csv
from pathlib import Path
from normalizacion import normalizar_fila

RUTAS = {
    'universo': {
        'OpenAlex': 'Código OpenAlex/IPRE_codigo_y_datos_v9/01_extraccion_y_filtro/datos_reconstruidos/universo_openalex.csv',
        'Scopus': 'Código Scopus/IPRE_Scopus_codigo_y_datos_v9/01_extraccion_y_filtro/referencia_archivada/universo_scopus_deduplicado.csv',
        'WoS': 'Código WoS/IPRE_WoS_cribado_homologado/entrada_fase01/01_registros_unicos_normalizados.csv',
    },
    'base_amplia': {
        'OpenAlex': 'Código OpenAlex/IPRE_codigo_y_datos_v9/01_extraccion_y_filtro/referencia_archivada/corpus_general_aceptado.csv',
        'Scopus': 'Código Scopus/IPRE_Scopus_codigo_y_datos_v9/01_extraccion_y_filtro/referencia_archivada/corpus_general_aceptado_provisional.csv',
        'WoS': 'Código WoS/IPRE_WoS_cribado_homologado/entrada_fase01/04_base_amplia_provisional.csv',
    },
}


def leer_corpus(raiz: Path, etapa: str, rutas_fuentes: dict[str, str] | None = None,
                normalizacion_titulos: str = 'historica_ascii'):
    registros = []
    entradas = {}
    ids = set()
    for fuente, ruta_relativa in (rutas_fuentes or RUTAS[etapa]).items():
        path = raiz / ruta_relativa
        if not path.is_file():
            raise FileNotFoundError(f'No se encontró entrada para {fuente}: {path}')
        total = 0
        with path.open('r', encoding='utf-8-sig', newline='') as f:
            lector = csv.DictReader(f)
            for n, row in enumerate(lector, start=2):
                r = normalizar_fila(row, fuente, n, normalizacion_titulos=normalizacion_titulos)
                if r['registro_uid'] in ids:
                    raise ValueError(f'ID repetido dentro de la fuente: {r["registro_uid"]}')
                ids.add(r['registro_uid'])
                registros.append(r)
                total += 1
        entradas[fuente] = {'ruta': ruta_relativa, 'registros': total}
    return registros, entradas
