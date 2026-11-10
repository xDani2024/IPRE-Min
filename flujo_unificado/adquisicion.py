"""Interfaz común de *lanzamiento* de los extractores existentes.

Mantiene internamente los protocolos/consultas originales de cada API.
No realiza cribado ni modifica archivos históricos.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path
from importar_wos import exportar


def consolidar_paginas_scopus(salida: Path, modo: str):
    """Solo construye el universo deduplicado, SIN cribado temático Scopus."""
    dir_scopus = SC.parent
    sys.path.insert(0, str(dir_scopus))
    import scopus_fase1 as motor
    import criterios_joaquin_adaptados as jq
    subdir = salida / ("fase1_piloto" if modo == "piloto" else "fase1_completo")
    crudos, estado, _config = motor.cargar_descarga(subdir)
    if modo == "completo" and (len(estado) != 10 or not all(x["completa"] for x in estado)):
        raise RuntimeError("No se generará un universo final a partir de una descarga Scopus incompleta.")
    unicos = jq.deduplicate(crudos)
    motor.guardar_csv(salida / "universo_scopus_deduplicado.csv", unicos, motor.RAW_FIELDS)
    print(f"Scopus: {len(crudos)} fichas descargadas, {len(unicos)} identificadores únicos (sin cribado temático).")
    if modo == "piloto":
        print("ADVERTENCIA: es solo un PILOTO; NO utilizar como extracción completa de Scopus.")

ROOT=Path(__file__).resolve().parents[1]
OA=ROOT/'Código OpenAlex/IPRE_codigo_y_datos_v9/01_extraccion_y_filtro/01_extraer_openalex.py'
SC=ROOT/'Código Scopus/IPRE_Scopus_codigo_y_datos_v9/01_extraccion_y_filtro/01_extraer_scopus.py'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fuente',choices=['openalex','scopus','wos'],required=True)
    p.add_argument('--modo',choices=['piloto','completo'],default='piloto')
    p.add_argument('--salida',type=Path,required=True)
    p.add_argument('--carpeta-wos',type=Path)
    args=p.parse_args()
    out=args.salida.expanduser().resolve()
    if args.fuente=='wos':
        if not args.carpeta_wos: p.error('WoS requiere --carpeta-wos con exportaciones manuales.')
        reporte=exportar(args.carpeta_wos,out/'universo_wos_importado.csv')
        print(f"Importados {reporte['filas_importadas']} registros WoS. Revise el manifiesto.")
        return
    if args.fuente=='openalex':
        if args.modo=='piloto':
            p.error('El extractor original de OpenAlex no implementa modo piloto. No se simulará un piloto; use --modo completo y una carpeta nueva.')
        cmd=[sys.executable,str(OA),'--output-dir',str(out)]
    else:
        cmd=[sys.executable,str(SC),'--salida',str(out),'--modo',args.modo.upper()]
    print('Se ejecutará el extractor original de',args.fuente,'en una carpeta independiente:',out,flush=True)
    subprocess.run(cmd,check=True,cwd=str(OA.parent if args.fuente=='openalex' else SC.parent))
    if args.fuente == "scopus":
        consolidar_paginas_scopus(out, args.modo)

if __name__=='__main__': main()
