#!/usr/bin/env python3
"""Reproduce decisiones bibliográficas humanas aprobadas sobre el universo congelado.

No aplica fusiones, exclusiones temáticas ni modifica los CSV originales.
Ancla decisiones por registro_uid estable y no por el ID secuencial de alertas.
Todos los cambios posteriores deben crear una nueva versión del registro aprobado.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(__file__).resolve().parent / 'decisiones_aprobadas'
INTEGRACION = ROOT / 'integracion_corpus'
sys.path.insert(0, str(INTEGRACION))
from fuentes import RUTAS, leer_corpus  # noqa: E402
from normalizacion import hash_archivo, normalizar_titulo, normalizar_titulo_unicode  # noqa: E402

FICHEROS = {
    'matriz': '01_matriz_791_decisiones_aprobadas.csv',
    'bitacora': '02_bitacora_decisiones_chat.csv',
    'seguimientos': '03_seguimientos_especiales.csv',
    'cobertura': '04_auditoria_cobertura_105.csv',
    'prioritarios': '05_prioritarios_15_sin_dictamen.csv',
    'pendientes': '06_pendientes_bibliograficos.csv',
    'cierre': '07_cierre_unificacion_6_excepciones_aprobadas.csv',
}
PENDIENTES_ESPERADOS = set()
CIERRE_ESPERADO = {'ALERTA-0111','ALERTA-0500','ALERTA-0529','ALERTA-0534','ALERTA-0467','ALERTA-0519'}
FUSIONES_TOTALES = {'MISMA_PUBLICACION', 'AMPLIACION_FUSION_PREVIA_WOS',
                    'AMPLIACION_FUSION_PREVIA_OPENALEX', 'REFERENCIA_FUSION_PREVIA'}
SEPARACIONES = {'PUBLICACIONES_DIFERENTES', 'PUBLICACIONES_DIFERENTES_VINCULADAS',
                'SEPARACION_DEFINITIVA_VINCULADA', 'SEPARACION_PROVISIONAL'}
PARTICIALES = {
 'ALERTA-0112': (
    ('OpenAlex::https://openalex.org/W1593269834', 'Scopus::0029165531', 'WoS::WOS:A1995QV54300005'),
    ('WoS::WOS:A1988R375300004', 'WoS::WOS:A1983RV47600002')),
 'ALERTA-0229': (
    ('OpenAlex::https://openalex.org/W2611770560', 'Scopus::85016069521', 'WoS::WOS:000400569600018'),
    ('WoS::WOS:000338769100011',)),
 'ALERTA-0316': (
    ('OpenAlex::https://openalex.org/W3093007547', 'Scopus::85092378939'),
    ('WoS::WOS:000870865200001',)),
 'ALERTA-0384': (
    ('OpenAlex::https://openalex.org/W4312395089', 'WoS::WOS:000885016000017'),
    ('Scopus::85153721041',)),
 'ALERTA-0519': (
    ('OpenAlex::https://openalex.org/W7128946536', 'WoS::WOS:001755932400016'),
    ('WoS::WOS:001892639000034',)),
}


def leer_csv(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f'Falta archivo de referencia: {path}')
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def escribir_csv(path: Path, rows: list[dict], campos: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def uid_de_alerta(row: dict) -> list[str]:
    return list(dict.fromkeys([row['registro_a']] + [x.strip() for x in row.get('registros_b', '').split('|') if x.strip()]))


def id_grupo(uids: list[str] | tuple[str, ...]) -> str:
    txt = '\n'.join(sorted(uids))
    return 'GRUPO-' + hashlib.sha256(txt.encode('utf-8')).hexdigest()[:16].upper()


class UF:
    def __init__(self, ids):
        self.parent = {x: x for x in ids}
        self.sizes = {x: 1 for x in ids}

    def find(self, a):
        if a not in self.parent:
            raise ValueError(f'UID inexistente en universo congelado: {a}')
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def join(self, a, b):
        a, b = self.find(a), self.find(b)
        if a == b:
            return
        if self.sizes[a] < self.sizes[b]:
            a, b = b, a
        self.parent[b] = a
        self.sizes[a] += self.sizes[b]


def auditar(raiz: Path = ROOT, datos: Path = DATA, salida: Path | None = None,
            validar_fuentes: bool = True) -> dict:
    raiz, datos = Path(raiz).resolve(), Path(datos).resolve()
    salida = (Path(salida) if salida else raiz/'flujo_unificado'/'auditoria_revision_aprobada').resolve()
    if datos == salida or datos in salida.parents:
        raise ValueError('La carpeta de salida no puede sobrescribir las decisiones originales')
    matrices = {k: leer_csv(datos/v) for k, v in FICHEROS.items()}
    matriz = matrices['matriz']
    # Congelación reproducible: rechazar entradas distintas a las aprobadas.
    manifiesto = datos/'00_manifiesto_entradas_congeladas.json'
    if manifiesto.is_file() and validar_fuentes:
        esperado = json.loads(manifiesto.read_text(encoding='utf-8'))
        for rel, checksum in esperado['sha256'].items():
            path = (datos/rel[4:]) if rel.startswith('DAT/') else (raiz/rel[5:])
            if not path.is_file() or hash_archivo(path) != checksum:
                raise ValueError(f'La instantánea no coincide con la aprobada: {rel}. Revalidar la matriz antes de usarla.')
    assert len(matriz) == 791, 'La matriz congelada debe contener las 791 alertas'
    assert len({r['id_alerta'] for r in matriz}) == 791, 'Existen IDs de alerta duplicados'
    assert {r['id_alerta'] for r in matriz if not r['decision_humana']} == PENDIENTES_ESPERADOS
    assert len(matrices['cobertura']) == 105, 'Revisar cohorte de cobertura'
    assert len(matrices['prioritarios']) == 15, 'Revisar lista de priorización humana'
    assert len({r['id_openalex'] for r in matrices['cobertura']}) == 105
    assert len({r['id_openalex'] for r in matrices['prioritarios']}) == 15
    assert {r['id_openalex'] for r in matrices['prioritarios']} <= {r['id_openalex'] for r in matrices['cobertura']}
    assert len(matrices['pendientes']) == 0, 'No deben quedar cuatro pendientes antiguos'
    assert {r['id_alerta'] for r in matrices['cierre']} == CIERRE_ESPERADO
    decisiones_cierre = {r['id_alerta']:r for r in matrices['cierre']}
    for r in matriz:
        if r['id_alerta'] in decisiones_cierre:
            act = decisiones_cierre[r['id_alerta']]
            if (r['decision_humana'] != act['decision_aprobada'] or act['aprobacion_usuario'] != 'APROBADA_EN_CHAT'):
                raise ValueError(f"Decisión de cierre inconsistente: {r['id_alerta']}")
    assert len(matrices['seguimientos']) == 3
    assert {r['id_alerta'] for r in matrices['seguimientos']} == {'ALERTA-0182', 'ALERTA-0467', 'ALERTA-0519'}

    all_uids = set()
    for a in matriz:
        all_uids.update(uid_de_alerta(a))
    por_uid = {}
    if validar_fuentes:
        # Siempre se contrasta contra los registros originales, no contra publicaciones consolidadas.
        originales, _ = leer_corpus(raiz, 'universo', normalizacion_titulos='historica_ascii')
        por_uid = {r['registro_uid']: r for r in originales}
        faltantes = sorted(all_uids - por_uid.keys())
        if faltantes:
            raise ValueError(f'{len(faltantes)} identificadores aprobados no coinciden con la instantánea: {faltantes[:5]}')
    else:
        por_uid = {uid: {} for uid in all_uids}
    uf = UF(all_uids)
    pares_fusion = []
    pares_separacion = []
    vinculados = []
    aprobados = []
    unicode = []
    enriquecimientos = []
    for a in sorted(matriz, key=lambda r: r['id_alerta']):
        key = a['id_alerta']; dec = a['decision_humana']
        ids = uid_de_alerta(a)
        if not ids or len(ids) != len(set(ids)):
            raise ValueError(f'{key}: referencia UID vacía o duplicada')
        if dec in FUSIONES_TOTALES:
            grupos = [(ids, [])]
        elif key in PARTICIALES:
            if not dec.startswith('FUSION_PARCIAL'):
                raise ValueError(f'{key}: la decisión aprobada no coincide con la regla parcial')
            a_fundir, a_dejar_fuera = PARTICIALES[key]
            if set(a_fundir) | set(a_dejar_fuera) != set(ids) or set(a_fundir) & set(a_dejar_fuera):
                raise ValueError(f'{key}: la regla parcial no cubre exactamente sus registros')
            grupos = [(list(a_fundir), list(a_dejar_fuera))]
        else:
            grupos = []
        for agregar, no_agregar in grupos:
            if len(agregar) < 2:
                raise ValueError(f'{key}: fusión sin al menos dos registros')
            primero = agregar[0]
            for otro in agregar[1:]:
                uf.join(primero, otro)
                pares_fusion.append({'id_alerta': key, 'registro_uid_a': primero, 'registro_uid_b': otro,
                                     'decision_humana': dec, 'estado': 'APROBADO_NO_APLICADO'})
            for x in agregar:
                for y in no_agregar:
                    pares_separacion.append({'id_alerta': key, 'registro_uid_a': x, 'registro_uid_b': y,
                                             'caracter': 'EXCLUIDO_DE_FUSION_PARCIAL',
                                             'estado': 'PENDIENTE_VERSION_EDITORIAL' if key == 'ALERTA-0519' else 'APROBADO_NO_APLICADO'})
                    vinculados.append({'id_alerta': key, 'registro_uid_a': x, 'registro_uid_b': y,
                                       'relacion': 'VERSIONES_RELACIONADAS_NO_FUSIONAR'})
        if dec in SEPARACIONES:
            for otro in ids[1:]:
                pares_separacion.append({'id_alerta': key, 'registro_uid_a': ids[0], 'registro_uid_b': otro,
                                         'caracter': dec, 'estado': 'APROBADO_NO_APLICADO'})
                vinculados.append({'id_alerta': key, 'registro_uid_a': ids[0], 'registro_uid_b': otro,
                                   'relacion': 'PUBLICACIONES_RELACIONADAS_SIN_FUSION'})
        if dec == 'FALSO_POSITIVO_TITULO_VACIO_UNICODE':
            if len(ids) != 1:
                raise ValueError(f'{key}: falsa alerta de título vacío con varios registros')
            titulo = por_uid[ids[0]].get('titulo') or a.get('titulo_a', '')
            if not titulo or normalizar_titulo(titulo) or not normalizar_titulo_unicode(titulo):
                raise ValueError(f'{key}: título Unicode no cumple condición del falso positivo')
            unicode.append({'id_alerta': key, 'registro_uid': ids[0], 'titulo_original': titulo,
                            'titulo_normalizado_unicode_v2': normalizar_titulo_unicode(titulo),
                            'accion': 'CORREGIR_NORMALIZACION_SIN_FUSION', 'decision_cribado': 'SIN_CAMBIOS'})
        if dec == 'ENRIQUECIMIENTO_TITULO_EDITORIAL_SIN_FUSION' or a.get('anio_volumen_editorial_verificado') or a.get('fecha_online_editorial_verificada'):
            enriquecimientos.append({'id_alerta': key, 'registro_uids': '|'.join(ids),
                  'titulo_editorial_enriquecido': a.get('titulo_editorial_enriquecido',''),
                  'fuente_editorial_enriquecimiento': a.get('fuente_editorial_enriquecimiento',''),
                  'anio_volumen_editorial_verificado': a.get('anio_volumen_editorial_verificado',''),
                  'fecha_online_editorial_verificada': a.get('fecha_online_editorial_verificada',''),
                  'nota_revision_chat': a.get('nota_revision_chat',''),
                  'accion': 'ANOTACION_ADICIONAL_NO_SOBREESCRIBIR_ORIGEN'})
        aprobados.append({'id_alerta': key, 'decision_humana': dec or 'PENDIENTE',
                          'estado_aprobacion': 'PENDIENTE' if not dec else 'APROBADA_POR_USUARIO',
                          'tipo_alerta_origen': a['tipo_alerta'],
                          'registro_uids': '|'.join(ids), 'v9_a_original': a.get('v9_a',''),
                          'v9_b_original': a.get('decisiones_v9_b',''),
                          'justificacion': a.get('justificacion_humana',''),
                          'fuentes': a.get('fuentes_seguimiento_especial',''),
                          'doi_original_a': a.get('doi_a',''), 'doi_original_b': a.get('dois_b',''),
                          'anio_original_a': a.get('anio_a',''), 'anios_originales_b': a.get('anios_b','')})

    # Comprobar que ninguna separación explícita contradiga una fusión aprobada.
    contradicciones = [r for r in pares_separacion if uf.find(r['registro_uid_a']) == uf.find(r['registro_uid_b'])]
    if contradicciones:
        raise ValueError(f'Contradicción entre fusiones y separaciones aprobadas: {contradicciones[:3]}')
    grupos = defaultdict(list)
    for uid in all_uids:
        grupos[uf.find(uid)].append(uid)
    agrupaciones = []
    for g in sorted((sorted(v) for v in grupos.values() if len(v) > 1), key=lambda v: v[0]):
        agrupaciones.append({'grupo_estable': id_grupo(g), 'registros_uid': '|'.join(g),
                             'n_registros': len(g), 'fuentes': '|'.join(sorted({uid.split('::')[0] for uid in g})),
                             'estado': 'FUSION_APROBADA_PENDIENTE_APLICACION',
                             'metadatos_origen_json': json.dumps([{'registro_uid': uid,
                              'titulo_original': por_uid[uid].get('titulo',''),
                              'anio_original': por_uid[uid].get('anio',''),
                              'fecha_publicacion_original': por_uid[uid].get('fecha_publicacion',''),
                              'doi_original': por_uid[uid].get('doi_original',''),
                              'resumen_fuente_no_alterado': bool(por_uid[uid].get('resumen',''))}
                              for uid in g], ensure_ascii=False, sort_keys=True)})
    # Reconstruir estado de cobertura mediante la instantánea, sin revisar ni cambiar inclusión temática.
    cobertura = []
    origenes_cobertura = {}
    if validar_fuentes:
        ruta_original = raiz / RUTAS['universo']['OpenAlex']
        ids_cobertura = {r['id_openalex'] for r in matrices['cobertura']}
        with ruta_original.open('r', encoding='utf-8-sig', newline='') as f:
            for raw in csv.DictReader(f):
                if raw['openalex_id'] in ids_cobertura:
                    origenes_cobertura[raw['openalex_id']] = raw
        if set(origenes_cobertura) != ids_cobertura:
            raise ValueError('No se localizaron los 105 registros de OpenAlex en la instantánea original')
    for r in matrices['cobertura']:
        uid = 'OpenAlex::' + r['id_openalex']
        if uid not in por_uid:
            raise ValueError(f'No se pudo verificar UID de cobertura: {uid}')
        origen = por_uid[uid]
        if validar_fuentes:
            raw = origenes_cobertura[r['id_openalex']]
            if (raw['auto_screen_status'] != 'exclude'
                    or raw['auto_screen_reasons'] != 'sin_foco_operacional_suficiente'
                    or raw['title'] != r['titulo_original_unicode']
                    or raw['year'] != r['anio_original']):
                raise ValueError(f'Cambió filtro, motivo, título o año de origen en: {uid}')
        cobertura.append({**r, 'estado_comprobacion': 'ORIGEN_CONFIRMADO' if validar_fuentes else 'SIN_VERIFICAR_FUENTES',
                          'estado_filtro_observado': origen.get('estado_filtro_fuente',''),
                          'titulo_unicode_observado': origen.get('titulo',''),
                          'normalizacion_unicode_v2': normalizar_titulo_unicode(origen.get('titulo',''))})
    priorizados = []
    for row in matrices['prioritarios']:
        priorizados.append({**row, 'decision_temática_humana': 'PENDIENTE',
                            'accion_automatica': 'NINGUNA', 'aprobacion_reincorporacion': 'NO'})
    seguimiento = []
    for row in matrices['seguimientos']:
        seguimiento.append({'id_alerta': row['id_alerta'], 'decision_aprobada': row['decision_aprobada'],
                             'estado_seguimiento_actual': row['estado_seguimiento_actual'],
                             'pendiente_especifico': row['pendiente_especifico'],
                             'fecha_confirmacion': row['fecha_confirmacion']})

    # Retirar únicamente el CSV heredado de la versión anterior para evitar resultados ambiguos.
    legado = salida/'10_pendientes_bibliograficos_4.csv'
    if legado.is_file(): legado.unlink()
    escribir_csv(salida/'01_decisiones_bibliograficas.csv', aprobados, list(aprobados[0]))
    escribir_csv(salida/'02_aristas_fusion_aprobadas_NO_APLICAR.csv', pares_fusion,
                 ['id_alerta','registro_uid_a','registro_uid_b','decision_humana','estado'])
    escribir_csv(salida/'03_restricciones_no_fusionar.csv', pares_separacion,
                 ['id_alerta','registro_uid_a','registro_uid_b','caracter','estado'])
    escribir_csv(salida/'04_grupos_fusion_aprobados_NO_APLICAR.csv', agrupaciones,
                 ['grupo_estable','registros_uid','n_registros','fuentes','estado','metadatos_origen_json'])
    escribir_csv(salida/'05_correcciones_unicode_aprobadas.csv', unicode, list(unicode[0]))
    escribir_csv(salida/'06_enriquecimientos_editoriales.csv', enriquecimientos,
                 list(enriquecimientos[0]) if enriquecimientos else ['id_alerta'])
    escribir_csv(salida/'07_seguimientos_especiales.csv', seguimiento, list(seguimiento[0]))
    escribir_csv(salida/'08_cobertura_105_SIN_REINCORPORACION.csv', cobertura, list(cobertura[0]))
    escribir_csv(salida/'09_prioritarios_15_PENDIENTES_CRIBADO.csv', priorizados, list(priorizados[0]))
    escribir_csv(salida/'10_pendientes_bibliograficos.csv',
                 [a for a in aprobados if a['estado_aprobacion']=='PENDIENTE'], list(aprobados[0]))
    escribir_csv(salida/'11_relaciones_no_fusionar.csv', vinculados,
                 ['id_alerta','registro_uid_a','registro_uid_b','relacion'])
    escribir_csv(salida/'13_decisiones_cierre_aprobadas.csv', matrices['cierre'], list(matrices['cierre'][0]))
    huellas_entradas = {str((datos/n).relative_to(raiz)) if (datos/n).is_relative_to(raiz) else n: hash_archivo(datos/n)
                        for n in sorted(FICHEROS.values())}
    if validar_fuentes:
        for fuente, path in sorted(RUTAS['universo'].items()):
            huellas_entradas[f'universo_{fuente}'] = hash_archivo(raiz/path)
    estado = Counter(a['decision_humana'] or 'PENDIENTE' for a in matriz)
    resumen = {
      'version_procedimiento': '2026-11-09_v2_cierre_bibliografico',
      'alcance': 'Identidad bibliográfica y trazabilidad, SIN cribado ni aplicación de fusiones',
      'alertas_totales': len(matriz),
      'estado_decisiones_por_tipo': dict(sorted(estado.items())),
      'alertas_sin_dictamen': sorted(PENDIENTES_ESPERADOS),
      'registros_universo': len(por_uid) if validar_fuentes else None,
      'n_aristas_fusion_aprobadas_sin_aplicar': len(pares_fusion),
      'n_grupos_con_fusion_aprobada': len(agrupaciones),
      'n_pares_restringidos_no_fusionar': len(pares_separacion),
      'n_unicode_aprobados': len(unicode),
      'n_cobertura_excluidos_filtro_original_sin_reincorporar': len(cobertura),
      'n_prioritarios_cribado_pendiente': len(priorizados),
      'n_seguimientos_especiales': len(seguimiento),
      'n_decisiones_cierre_aprobadas': len(matrices['cierre']),
      'normalizador_para_reproducir_alertas': 'historica_ascii',
      'normalizador_unicode_alternativo': 'unicode_v2 (aplicado en la unificación validada; histórico solo para reproducir las alertas)',
      'politica_fusiones': 'Aristas por registro_uid, sin inferir fusión desde título solo; excepciones parciales explícitas',
      'modificaciones_a_fuentes': False,
      'fusiones_aplicadas': False,
      'reincorporaciones_automaticas': False,
      'criterios_tematicos_modificados': False,
      'huellas_sha256_entradas': huellas_entradas,
      'huellas_sha256_salidas': {p.name:hash_archivo(p) for p in sorted(salida.glob('*.csv'))},
    }
    (salida/'12_resumen_y_huellas.json').write_text(json.dumps(resumen, ensure_ascii=False, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    return resumen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raiz', type=Path, default=ROOT)
    parser.add_argument('--decisiones', type=Path, default=DATA)
    parser.add_argument('--salida', type=Path, default=ROOT/'flujo_unificado'/'auditoria_revision_aprobada')
    parser.add_argument('--sin-verificar-fuentes', action='store_true', help='Sólo para diagnóstico; no valida UID ni metadatos de universo')
    args = parser.parse_args()
    r = auditar(args.raiz, args.decisiones, args.salida, not args.sin_verificar_fuentes)
    print('Alertas verificadas:', r['alertas_totales'])
    print('Fusiones registradas como grupos NO APLICADOS:', r['n_grupos_con_fusion_aprobada'])
    print('Correcciones Unicode:', r['n_unicode_aprobados'])
    print('Pendientes bibliográficos:', ', '.join(r['alertas_sin_dictamen']))
    print('Cobertura sin decisión de reintegración:', r['n_cobertura_excluidos_filtro_original_sin_reincorporar'])
    print('Salidas auditables:', args.salida.resolve())


if __name__ == '__main__':
    main()
