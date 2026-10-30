"""Auditoría no destructiva de fusiones archivadas de Scopus.
Ejecutar desde cualquier ubicación con --entrada CARPETA_REFERENCIA_ARCHIVADA.
No modifica archivos fuente ni toma decisiones de exclusión.
"""
from pathlib import Path
import argparse, csv

CAMPOS = ['scopus_id','title','year','doi','merged_scopus_ids','merged_dois',
          'duplicate_count','deduplication_methods','quality_flags',
          'revision_humana','justificacion','evidencia_consultada']

def leer(ruta):
    with ruta.open('r',encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def escribir(ruta,filas):
    with ruta.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=CAMPOS)
        w.writeheader()
        for r in filas:
            w.writerow({campo:r.get(campo,'') for campo in CAMPOS})

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entrada',type=Path,required=True,
                   help='Carpeta con universo_scopus_deduplicado.csv')
    p.add_argument('--salida',type=Path,default=Path('revision_fusiones_scopus'))
    a=p.parse_args()
    origen=a.entrada/'universo_scopus_deduplicado.csv'
    if not origen.is_file():p.error(f'No existe: {origen}')
    destino=a.salida.resolve()
    if destino.exists() and any(destino.iterdir()):
        p.error('La carpeta de salida no debe contener archivos')
    destino.mkdir(parents=True,exist_ok=True)
    registros=leer(origen)
    fusionados=[r for r in registros if int(r.get('duplicate_count') or 1)>1]
    alertados=[r for r in registros if 'fusion_de_registros_con_doi_distintos_revisar' in (r.get('quality_flags') or '')]
    alertas_sin_fusion=[r for r in alertados if int(r.get('duplicate_count') or 1)==1]
    alertas_con_fusion=[r for r in alertados if int(r.get('duplicate_count') or 1)>1]
    otros=[r for r in fusionados if r not in alertas_con_fusion]
    escribir(destino/'01_prioridad_fusiones_con_alerta_doi.csv',alertas_con_fusion)
    escribir(destino/'02_alertas_doi_sin_fusion.csv',alertas_sin_fusion)
    escribir(destino/'03_otras_fusiones.csv',otros)
    print('Publicaciones únicas:',len(registros))
    print('Grupos fusionados:',len(fusionados))
    print('Con alerta de DOI distintos:',len(alertados))
    print('  - fusiones efectivas:',len(alertas_con_fusion))
    print('  - registros sin fusion:',len(alertas_sin_fusion))
    print('Otras fusiones:',len(otros))
    print('Archivos creados en:',destino)
    print('Nota: las alertas son preliminares; DOI separados por punto y coma pueden requerir revisión individual.')

if __name__=='__main__':main()
