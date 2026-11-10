#!/usr/bin/env python3
"""Regenera snapshots reducidos de las matrices v9 desde el ZIP original.

Ejemplo: python flujo_unificado/preparar_historial_v9.py --zip-origen IPRE-Min-main.zip
No realiza nuevas consultas a las API ni modifica los universos originales.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
MATRICES={
 'OpenAlex':'Código OpenAlex/IPRE_codigo_y_datos_v9/04_cierre_v9/salida/Matriz_4735_con_cierre_v9.csv',
 'Scopus':'Código Scopus/IPRE_Scopus_codigo_y_datos_v9/04_cierre_v9/salida/Matriz_Scopus_4614_con_pre_cierre_v9.csv',
 'WoS':'Código WoS/IPRE_WoS_cribado_homologado/resultados_cribado_wos/04_v9_preliminar/matriz_completa_v9_preliminar.csv',
}


def ejecutar(archivo_zip: Path, salida: Path):
    salida.mkdir(parents=True,exist_ok=True)
    manifiesto = {}
    with zipfile.ZipFile(archivo_zip) as z:
        for fuente, relativa in MATRICES.items():
            nombre='IPRE-Min-main/'+relativa
            datos=z.read(nombre)
            original=list(csv.DictReader(io.StringIO(datos.decode('utf-8-sig'))))
            colid={'OpenAlex':'openalex_id','Scopus':'scopus_id','WoS':'wos_id'}[fuente]
            salida_rows = []
            for r in original:
                salida_rows.append({
                    'fuente':fuente, 'id_fuente':r[colid], 'doi_original':r.get('doi',''),
                    'titulo_original':r.get('title',''), 'anio_original':r.get('year',''),
                    'decision_v9_propuesta':r.get('decision_nucleo_v9_propuesta',''),
                    'decision_humana_historica':r.get('decision_humana_conservada_v9','') or r.get('consenso_humano',''),
                    'validacion_humana_reportada':r.get('validacion_humana_independiente','') or r.get('validacion_academica','') or r.get('estatus_validacion',''),
                    'origen_decision_v9':r.get('origen_v9',''),
                    'regla_cierre_v9':r.get('regla_cierre_v9',''),
                })
            outfile=salida/(fuente.lower()+'_v9.csv')
            with outfile.open('w',newline='',encoding='utf-8-sig') as h:
                w=csv.DictWriter(h,fieldnames=list(salida_rows[0]));w.writeheader();w.writerows(salida_rows)
            manifiesto[fuente]={
                'ruta_matriz_original':relativa,
                'sha256_matriz_original':hashlib.sha256(datos).hexdigest(),
                'filas':len(salida_rows),
                'sha256_snapshot_reducido':hashlib.sha256(outfile.read_bytes()).hexdigest(),
                'nombre_snapshot':outfile.name,
            }
    (salida/'procedencia.json').write_text(json.dumps(manifiesto,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Historias v9 preparadas:',{k:v['filas'] for k,v in manifiesto.items()})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--zip-origen',required=True,type=Path,help='ZIP del repositorio original con las matrices v9 completas')
    p.add_argument('--salida',type=Path,default=HERE/'entrada_historial_v9')
    args=p.parse_args()
    ejecutar(args.zip_origen,args.salida)

if __name__=='__main__':main()
