#!/usr/bin/env python3
"""Integración bibliográfica reproducible OpenAlex/Scopus/WoS. Python >= 3.10."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from deduplicacion import vincular
from fuentes import RUTAS, leer_corpus
from normalizacion import hash_archivo

DIR = Path(__file__).resolve().parent
RAIZ = DIR.parent


def guardar_csv(path: Path, filas: list[dict], campos: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=campos, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(filas)


def guardar_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def primero_mas_completo(rows: list[dict], campo: str):
    return max(rows, key=lambda r: (len(r.get(campo, '')), r.get(campo, ''), r['registro_uid']))[campo]


def construir(etapa: str, salida: Path, raiz: Path, rutas_fuentes: dict[str, str] | None = None,
             normalizacion_titulos: str = 'historica_ascii'):
    registros, entradas = leer_corpus(raiz, etapa, rutas_fuentes=rutas_fuentes,
                                      normalizacion_titulos=normalizacion_titulos)
    grupos, alertas, _metodos = vincular(registros)
    grupos = [sorted(indices, key=lambda i: registros[i]['registro_uid']) for indices in grupos]
    grupos.sort(key=lambda indices: (registros[indices[0]]['titulo_normalizado'],
                                      registros[indices[0]]['anio'], registros[indices[0]]['registro_uid']))
    unidos = []
    correspondencias = []
    vistos = Counter()
    duplicados_de_fuentes = 0
    registros_de_grupos_multi = 0

    for posicion, indices in enumerate(grupos, 1):
        rows = [registros[i] for i in indices]
        pid = f'IPRE-{etapa.upper()}-{posicion:06d}'
        fuentes = sorted(set(r['fuente'] for r in rows))
        todos_doi = sorted({r['doi_normalizado'] for r in rows if r['doi_normalizado']})
        years = sorted({r['anio'] for r in rows if r['anio']})
        if len(todos_doi) > 1:
            alertas.append({'tipo': 'GRUPO_DOIS_MULTIPLES_REVISAR', 'registro_a': rows[0]['registro_uid'],
                            'registro_b': '|'.join(r['registro_uid'] for r in rows[1:]),
                            'detalle': '|'.join(todos_doi)})
        if len(fuentes) > 1:
            duplicados_de_fuentes += len(rows) - 1
            registros_de_grupos_multi += len(rows)
        for fuente, cantidad in Counter(r['fuente'] for r in rows).items():
            if cantidad > 1:
                alertas.append({'tipo': 'VARIOS_IDS_MISMA_FUENTE_EN_UN_GRUPO',
                                'registro_a': rows[0]['registro_uid'],
                                'registro_b': '|'.join(r['registro_uid'] for r in rows[1:]),
                                'detalle': f'{fuente}: {cantidad}'})
        # Los criterios aplicados al grupo se reconstruyen desde DOI y título-año,
        # sin extrapolar decisiones de clasificación temática.
        criterio = []
        if len(rows) > 1:
            if todos_doi and len(todos_doi) == 1 and sum(r['doi_normalizado'] == todos_doi[0] for r in rows) > 1:
                criterio.append('DOI')
            if any(not r['doi_normalizado'] for r in rows) and len({(r['titulo_normalizado'], r['anio']) for r in rows}) == 1:
                criterio.append('TITULO_ANIO_EXACTOS')
        etiqueta_por_fuente = [{
            'fuente': r['fuente'], 'id_fuente': r['id_fuente'],
            'filtro': r['estado_filtro_fuente'],
            'procesos': r['etiquetas_proceso_fuente'],
            'equipos': r['etiquetas_equipo_fuente'],
            'foco': r['etiquetas_foco_fuente'],
        } for r in rows]
        resumen_mejor = max(rows, key=lambda r: (len(r['resumen']), r['registro_uid']))
        titulo = primero_mas_completo(rows, 'titulo')
        ano = Counter(r['anio'] for r in rows if r['anio'])
        elegido_ano = sorted(ano, key=lambda k: (-ano[k], k))[0] if ano else ''
        unidos.append({
            'id_publicacion': pid,
            'titulo': titulo,
            'anio_referencia': elegido_ano,
            'anios_observados': '|'.join(years),
            'doi': todos_doi[0] if len(todos_doi) == 1 else '',
            'dois_observados': '|'.join(todos_doi),
            'autores': primero_mas_completo(rows, 'autores'),
            'revista': primero_mas_completo(rows, 'revista'),
            'tipo_documento': primero_mas_completo(rows, 'tipo_documento'),
            'resumen': resumen_mejor['resumen'],
            'fuente_resumen': resumen_mejor['registro_uid'],
            'palabras_clave': primero_mas_completo(rows, 'palabras_clave'),
            'fuentes': '|'.join(fuentes),
            'numero_fuentes': len(fuentes),
            'numero_registros': len(rows),
            'identificadores_openalex': '|'.join(r['id_fuente'] for r in rows if r['fuente'] == 'OpenAlex'),
            'identificadores_scopus': '|'.join(r['id_fuente'] for r in rows if r['fuente'] == 'Scopus'),
            'identificadores_wos': '|'.join(r['id_fuente'] for r in rows if r['fuente'] == 'WoS'),
            'criterios_vinculacion': '|'.join(criterio) if criterio else 'UNICO',
            'etiquetas_originales_por_fuente_json': json.dumps(etiqueta_por_fuente, ensure_ascii=False, sort_keys=True),
            'clasificacion_tematica_consolidada': '',
            'estado_revision_humana': 'PENDIENTE',
        })
        for r in rows:
            correspondencias.append({
                'id_publicacion': pid,
                'registro_uid': r['registro_uid'],
                'fuente': r['fuente'],
                'id_fuente': r['id_fuente'],
                'doi_original': r['doi_original'],
                'doi_normalizado': r['doi_normalizado'],
                'anio': r['anio'],
                'titulo': r['titulo'],
                'criterios_vinculacion': '|'.join(criterio) if criterio else 'UNICO',
                'hash_fila_original': r['hash_fila_original'],
            })
            vistos[r['fuente']] += 1

    assert sum(r['numero_registros'] for r in unidos) == len(registros)
    assert len(correspondencias) == len(registros)
    assert vistos == Counter(r['fuente'] for r in registros)
    alertas.sort(key=lambda a: (a['tipo'], a['registro_a'], a['registro_b']))
    correspondencias.sort(key=lambda r: (r['id_publicacion'], r['registro_uid']))

    for fuente in entradas:
        rel = entradas[fuente]['ruta']
        entradas[fuente]['sha256'] = hash_archivo(raiz / rel)

    conteo_fuentes = Counter(r['fuente'] for r in registros)
    resumen = {
        'etapa': etapa,
        'version_normalizador_titulo': normalizacion_titulos,
        'alcance': ('Registros únicos disponibles por fuente antes del cribado temático'
                    if etapa == 'universo' else 'Bases amplias preseleccionadas por cada fuente; selección no validada homogéneamente'),
        'entradas': entradas,
        'total_registros_entrada': len(registros),
        'registros_por_fuente': dict(sorted(conteo_fuentes.items())),
        'publicaciones_unicas_provisionales': len(unidos),
        'reduccion_por_vinculacion': len(registros) - len(unidos),
        'publicaciones_con_multiples_fuentes': sum(r['numero_fuentes'] > 1 for r in unidos),
        'registros_en_publicaciones_multifuente': registros_de_grupos_multi,
        'reduccion_en_grupos_multifuente': duplicados_de_fuentes,
        'publicaciones_por_cantidad_de_fuentes': dict(sorted(Counter(str(r['numero_fuentes']) for r in unidos).items())),
        'alertas_por_tipo': dict(sorted(Counter(a['tipo'] for a in alertas).items())),
        'limites': [
            'Vinculación automática conservadora. Los casos alertados no se resuelven sin revisión bibliográfica.',
            'No se trasladan decisiones humanas ni etiquetas temáticas entre bases.',
            'Las bases de origen ya tienen procesos propios de deduplicación y filtrado.',
            'La extracción nueva por API no se ejecuta en este flujo local.',
            'WoS corresponde a una exportación manual, y los archivos originales XLS no están en este paquete.',
            'Corpus consolidado provisional: no equivale a conjunto final de estudios incluidos.',
        ],
    }
    salida.mkdir(parents=True, exist_ok=True)
    guardar_csv(salida / '01_registros_normalizados.csv', registros, list(registros[0]))
    guardar_csv(salida / '02_corpus_consolidado_provisional.csv', unidos, list(unidos[0]))
    guardar_csv(salida / '03_correspondencias_procedencia.csv', correspondencias, list(correspondencias[0]))
    guardar_csv(salida / '04_alertas_revision.csv', alertas, ['tipo', 'registro_a', 'registro_b', 'detalle'])
    if etapa == 'base_amplia':
        plantilla = [{
            'id_publicacion': r['id_publicacion'],
            'titulo': r['titulo'],
            'fuentes': r['fuentes'],
            'grupo_tematico_principal': '',
            'tematica_especifica': '',
            'proceso_equipo': '',
            'objetivo_del_articulo': '',
            'metodologia': '',
            'datos_utilizados': '',
            'evidencia_bibliografica': '',
            'decision_de_revision_humana': '',
            'observaciones': '',
        } for r in unidos]
        guardar_csv(salida / '07_plantilla_clasificacion_tematica.csv', plantilla, list(plantilla[0]))
    guardar_json(salida / '05_resumen_y_fuentes.json', resumen)
    salida_hashes = {f.name: hash_archivo(f) for f in sorted(salida.glob('0*.csv'))}
    guardar_json(salida / '06_huellas_salidas.json', salida_hashes)
    return resumen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normalizacion-titulos', choices=['historica_ascii', 'unicode_v2'],
                        default='historica_ascii', help='unicode_v2 altera grupos e IDs provisionales; no reusar alertas por número')
    parser.add_argument('--etapa', choices=['ambas', 'universo', 'base_amplia'], default='ambas')
    parser.add_argument('--raiz', type=Path, default=RAIZ, help='Ruta a IPRE-Min-main')
    parser.add_argument('--salida', type=Path, default=DIR / 'resultados', help='Carpeta de resultados')
    args = parser.parse_args()
    raiz = args.raiz.expanduser().resolve()
    salida = args.salida.expanduser().resolve()
    stages = ('universo', 'base_amplia') if args.etapa == 'ambas' else (args.etapa,)
    informes = {}
    for etapa in stages:
        resumen = construir(etapa, salida / etapa, raiz, normalizacion_titulos=args.normalizacion_titulos)
        informes[etapa] = resumen
        print(f"{etapa}: {resumen['total_registros_entrada']} registros -> "
              f"{resumen['publicaciones_unicas_provisionales']} publicaciones "
              f"({resumen['reduccion_por_vinculacion']} coincidencias tratadas); "
              f"{sum(resumen['alertas_por_tipo'].values())} alertas")
    if args.etapa == 'ambas':
        guardar_json(salida / 'RESUMEN_INTEGRACION.json', informes)
    print(f'Resultados guardados en: {salida}')


if __name__ == '__main__':
    main()
