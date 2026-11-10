#!/usr/bin/env python3
"""Flujo común: universos → normalizar → unificar → deduplicar → cribado.

Por defecto se procesan instantáneas guardadas, sin conexión de red ni API.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INTEGRADOR=ROOT/'integracion_corpus'
sys.path.insert(0,str(INTEGRADOR))
from main import construir, guardar_csv, guardar_json  # noqa: E402
from fuentes import RUTAS  # noqa: E402
from normalizacion import hash_archivo  # noqa: E402
from cribado import evaluar, VERSION_CRIBADO  # noqa: E402
from validacion import muestra_estratificada, comparar  # noqa: E402
from importar_wos import exportar  # noqa: E402
from cruce_historico_v9 import ejecutar as cruce_historico  # noqa: E402
from verificar_duplicados import ejecutar as verificar_duplicados  # noqa: E402


def leer_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def ejecutar(raiz, salida, rutas, importar_desde=None, matriz_anterior=None, usar_historico_v9=True):
    """No sobreescribe registros originales: genera todos los archivos en salida."""
    raiz=Path(raiz).resolve(); salida=Path(salida).resolve()
    entradas=dict(rutas)
    if importar_desde:
        ruta_wos=salida/'01_importacion_wos'/'universo_wos_importado.csv'
        exportar(Path(importar_desde),ruta_wos)
        entradas['WoS']=str(ruta_wos)
    carpeta_unificacion=salida/'02_integracion_y_deduplicacion'
    reporte_union=construir('universo',carpeta_unificacion,raiz,rutas_fuentes=entradas)
    corpus=leer_csv(carpeta_unificacion/'02_corpus_consolidado_provisional.csv')
    alertas=leer_csv(carpeta_unificacion/'04_alertas_revision.csv')
    # Orden determinista: el ID provisional queda vinculado al mismo conjunto de entrada.
    valores=[]
    for row in corpus:
        decidido=evaluar(row)
        valores.append({**row, **decidido})
    recuentos=dict(sorted(Counter(x['cribado_automatico'] for x in valores).items()))
    campos=list(valores[0])
    guardar_csv(salida/'03_cribado_comun'/'01_matriz_cribado_automatico.csv',valores,campos)
    guardar_csv(salida/'03_cribado_comun'/'02_candidatos_para_revision.csv',
                [r for r in valores if r['cribado_automatico']=='CANDIDATO'], campos)
    guardar_csv(salida/'03_cribado_comun'/'03_pendientes_de_revision.csv',
                [r for r in valores if r['cribado_automatico']=='PENDIENTE_REVISION'], campos)
    guardar_csv(salida/'03_cribado_comun'/'04_exclusiones_propuestas.csv',
                [r for r in valores if r['cribado_automatico']=='EXCLUSION_PROPUESTA'], campos)
    guardar_csv(salida/'03_cribado_comun'/'05_revision_prioritaria.csv',
                [r for r in valores if r['cribado_automatico']=='REVISION_PRIORITARIA'], campos)
    muestra=muestra_estratificada(valores)
    guardar_csv(salida/'04_revision_humana'/'02_muestra_validacion.csv',muestra,list(muestra[0]))
    if matriz_anterior is None:
        matriz_anterior=raiz/'flujo_unificado'/'resultados'/'03_cribado_comun'/'01_matriz_cribado_automatico.csv'
    cambios,comp=comparar(valores,matriz_anterior)
    if cambios:
        guardar_csv(salida/'06_auditoria'/'01_cambios_vs_cribado_previo.csv', cambios, list(cambios[0]))

    # Toda la cohorte queda disponible para cribado HUMANO sin dar por válidas etiquetas previas.
    plantilla=[{
        'id_publicacion':r['id_publicacion'], 'titulo':r['titulo'], 'resumen':r['resumen'],
        'doi':r['doi'], 'anio':r['anio_referencia'], 'fuentes':r['fuentes'],
        'cribado_automatico':r['cribado_automatico'], 'motivos_cribado':r['motivos_cribado'],
        'prioridad_revision':r['prioridad_revision'], 'evidencia_contexto_minero':r['evidencia_contexto_minero'],
        'decision_humana':'', 'motivo_decision_humana':'', 'revisor':'', 'fecha_revision':'',
    } for r in valores]
    guardar_csv(salida/'04_revision_humana'/'01_plantilla_cribado_humano.csv',plantilla,list(plantilla[0]))
    # Etiquetado solo posterior a decisión humana; no prejuzgar elegibilidad.
    temas=[{
        'id_publicacion':r['id_publicacion'],'titulo':r['titulo'],'fuentes':r['fuentes'],
        'inclusion_confirmada_humanamente':'', 'grupo_tematico_principal':'',
        'tematica_especifica':'', 'proceso_o_equipo':'', 'objetivo_del_paper':'',
        'metodologia':'', 'datos_utilizados':'', 'evidencia_textual':'', 'observaciones':'',
    } for r in valores if r['cribado_automatico']=='CANDIDATO']
    if temas:
        guardar_csv(salida/'05_clasificacion_posterior'/'01_plantilla_tematica_PENDIENTE.csv',temas,list(temas[0]))
    reporte={
        'version_flujo':'1.2.0',
        'orden':['extraccion_independiente','normalizacion','unificacion','deduplicacion',
                 'cribado_automatico_comun_titulo_resumen','revision_humana_pendiente','clasificacion_tematica_pendiente'],
        'metodo_fuentes':{'OpenAlex':'API, instantanea archivada','Scopus':'API, instantanea archivada',
                         'WoS':'exportaciones manuales'},
        'fuentes':{k:{'ruta':str(v),'sha256':hash_archivo(raiz/v)} for k,v in sorted(entradas.items())},
        'integracion':reporte_union,
        'cribado':{'entradas':len(valores),'recuentos_automaticos':recuentos,
                   'version_cribado':VERSION_CRIBADO, 'muestra_para_validacion':len(muestra),
                   'comparacion_con_anterior':comp,
                   'solo_campos_para_decidir':['titulo','resumen','tipo_documento'],
                   'clasificador':'reglas comunes con señales de dominio minero, procesos y objetivo; más diccionarios históricos solo para sugerir etiquetas, sin campos exclusivos de fuente',
                   'revision_humana_realizada':False},
        'alertas_integracion':len(alertas),
        'limitaciones':[
          'Los universos archivados ya fueron deduplicados internamente por cada fuente antes de esta etapa.',
          'La consulta y los filtros documentales de cada API/exportación no son equivalentes de forma automática.',
          'Los archivos originales XLS de WoS no están incluidos en el repositorio analizado; sin ellos solo se reproduce la importación desde CSV existente.',
          'La vinculación bibliográfica automática tiene alertas pendientes y los conteos son provisionales.',
          'El cribado v1.1 es una propuesta computacional. Los casos centinela son pruebas de regresión, NO estimaciones de sensibilidad ni precisión.',
          'CANDIDATO y EXCLUSION_PROPUESTA no son decisiones finales. REVISION_PRIORITARIA indica evidencia ambigua o parcial.',
          'La muestra de validación requiere revisión humana independiente para evaluar errores por cada grupo.',
          'Los resultados históricos v6-v9 por base se conservan como referencia, no se heredan como decisiones del corpus unificado.',
          'Las etiquetas temáticas finales requieren revisión de papers seleccionados y acuerdo metodológico.',
        ],
    }
    if usar_historico_v9:
        historial = cruce_historico(salida, salida/'07_cruce_historico_v9')
        reporte['cruce_historico_v9'] = {
            'registros_historicos':historial['n_registros_provenientes_de_v9'],
            'in_v9_registros':historial['registros_in_v9_total'],
            'in_v9_publicaciones_unicas':historial['publicaciones_unicas_con_al_menos_un_in_v9'],
            'contradicciones_v9_entre_fuentes':historial['publicaciones_unicas_con_in_v9_y_out_v9'],
            'v9_in_vs_nuevo':historial['comparacion_estado_nuevo_para_publicaciones_con_in_v9'],
            'matriz_cruce':'07_cruce_historico_v9/02_cruce_por_publicacion.csv',
            'decision_final_humana':'PENDIENTE',
        }
    if usar_historico_v9:
        reporte['verificacion_bibliografica_v1_3'] = verificar_duplicados(salida)
    hashes={str(p.relative_to(salida)):hash_archivo(p) for p in sorted(salida.rglob('*.csv'))}
    reporte['sha256_resultados']=hashes
    guardar_json(salida/'06_auditoria'/'resumen_flujo.json',reporte)
    print('Entradas por fuente:',reporte_union['registros_por_fuente'])
    print('Publicaciones únicas provisionales:',len(valores))
    print('Cribado automático común:',recuentos)
    print('Alertas de deduplicación:',len(alertas))
    print('Resultados en:',salida)
    return reporte


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raiz',type=Path,default=ROOT)
    parser.add_argument('--solo-revision-bibliografica', action='store_true',
                        help='Reproduce auditoría de decisiones humanas sin ejecutar deduplicación ni cribado')
    parser.add_argument('--auditar-revision-aprobada', action='store_true',
                        help='Después de generar el corpus provisional, reproduce la auditoría humana, sin aplicarla')
    parser.add_argument('--salida',type=Path,default=ROOT/'flujo_unificado'/'resultados_calibracion_v1_1')
    parser.add_argument('--openalex-csv',type=Path,help='Universo nuevo OpenAlex (antes del cribado)')
    parser.add_argument('--scopus-csv',type=Path,help='Universo nuevo Scopus (antes del cribado)')
    parser.add_argument('--wos-csv',type=Path,help='WoS normalizado CSV (antes del cribado)')
    parser.add_argument('--wos-exportaciones',type=Path,help='Carpeta CSV/XLS/XLSX de exportaciones manuales WoS')
    parser.add_argument('--matriz-anterior',type=Path,help='Ruta a la matriz de cribado anterior para comparar decisiones')
    parser.add_argument('--sin-cruce-v9',action='store_true',help='Omite comparación histórica cuando se usa un universo nuevo sin snapshots v9 compatibles')
    args=parser.parse_args()
    if args.solo_revision_bibliografica:
        from reproducir_revision_bibliografica import auditar
        report = auditar(args.raiz, salida=args.salida/'09_revision_bibliografica_aprobada')
        print('Auditoría bibliográfica reproducida:', report['alertas_totales'], 'alertas')
        print('Sin aplicar fusiones, correcciones o inclusiones temáticas.')
        return
    if args.wos_csv and args.wos_exportaciones:
        parser.error('Use --wos-csv O --wos-exportaciones, no ambos.')
    rutas=dict(RUTAS['universo'])
    for fuente, alternativa in [('OpenAlex',args.openalex_csv),('Scopus',args.scopus_csv),('WoS',args.wos_csv)]:
        if alternativa: rutas[fuente]=str(alternativa.expanduser().resolve())
    ejecutar(args.raiz,args.salida,rutas,args.wos_exportaciones,args.matriz_anterior,not args.sin_cruce_v9)
    if args.auditar_revision_aprobada:
        from reproducir_revision_bibliografica import auditar
        auditar(args.raiz, salida=args.salida/'09_revision_bibliografica_aprobada')
        print('Auditoría de decisiones aprobadas terminada; no modifica el corpus generado.')

if __name__=='__main__': main()
